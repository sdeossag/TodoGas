import { useEffect, useRef, useState } from 'react'
import { Capacitor } from '@capacitor/core'
import { Camera, CameraResultType, CameraSource } from '@capacitor/camera'
import { Geolocation } from '@capacitor/geolocation'

import { useUploadPhoto } from '../../api/evidence'
import { savePhotoOffline } from '../../db/repositories'
import useNetworkStore from '../../store/networkStore'

const MAX_FILE_BYTES = 10 * 1024 * 1024 // 10 MB
const MAX_CAPTION = 255

// Se evalua una vez: la plataforma no cambia durante la vida de la app.
const isNative = Capacitor.isNativePlatform()

function extractError(err) {
  const data = err?.response?.data
  if (!data) return err?.message || 'Error al subir la foto.'
  if (typeof data === 'string') return data
  if (data.detail) return String(data.detail)
  const firstKey = Object.keys(data)[0]
  const val = firstKey ? data[firstKey] : null
  return Array.isArray(val) ? val[0] : val ? String(val) : 'Error al subir la foto.'
}

/**
 * La camara nativa devuelve base64, pero /api/evidence/photos/ solo acepta
 * multipart con un FileField. Convertimos antes de subir.
 *
 * El backend valida la extension del nombre, asi que no puede ir vacia.
 */
async function dataUrlToFile(dataUrl, filename) {
  const blob = await (await fetch(dataUrl)).blob()
  const ext = (blob.type.split('/')[1] ?? 'jpg').replace('jpeg', 'jpg')
  return new File([blob], `${filename}.${ext}`, { type: blob.type || 'image/jpeg' })
}

/** Coordenadas del dispositivo. Nunca lanza: sin GPS la foto se sube igual. */
async function getPosition() {
  try {
    const pos = await Geolocation.getCurrentPosition({
      timeout: 10000,
      enableHighAccuracy: true,
    })
    return { latitude: pos.coords.latitude, longitude: pos.coords.longitude }
  } catch {
    return { latitude: null, longitude: null }
  }
}

export default function PhotoCapture({ workOrderId, disabled = false }) {
  const inputRef = useRef(null)
  const previewUrlRef = useRef(null)

  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [caption, setCaption] = useState('')
  const [takenAt, setTakenAt] = useState(null)
  const [coords, setCoords] = useState(null)
  const [geoWarning, setGeoWarning] = useState(false)
  const [validationError, setValidationError] = useState('')
  const [apiError, setApiError] = useState('')
  const [successVisible, setSuccessVisible] = useState(false)
  const [capturing, setCapturing] = useState(false)
  const [savingOffline, setSavingOffline] = useState(false)

  const isOnline = useNetworkStore((s) => s.isOnline)
  const showOfflineNotice = useNetworkStore((s) => s.showOfflineNotice)
  const refreshPendingCount = useNetworkStore((s) => s.refreshPendingCount)

  const upload = useUploadPhoto()
  const hasPhoto = !!previewUrl
  const busy = upload.isPending || savingOffline

  useEffect(() => {
    return () => {
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current)
    }
  }, [])

  function revokePreview() {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current)
      previewUrlRef.current = null
    }
  }

  function resetMessages() {
    setValidationError('')
    setApiError('')
    setGeoWarning(false)
    setCoords(null)
  }

  // ── Captura nativa (Android) ───────────────────────────────────────────────

  /**
   * Foto y GPS se piden en paralelo: el fix de posicion tarda varios segundos
   * y no hay razon para que el tecnico los espere en serie.
   *
   * Si el tecnico tarda mas que el timeout del GPS en disparar la foto, el
   * primer intento vuelve vacio; ahi si se reintenta ya con la foto tomada.
   */
  async function handleNativeCapture() {
    revokePreview()
    resetMessages()
    setCapturing(true)
    try {
      const [photo, firstFix] = await Promise.all([
        Camera.getPhoto({
          quality: 80,
          allowEditing: false,
          resultType: CameraResultType.Base64,
          source: CameraSource.Camera,
          saveToGallery: false,
          correctOrientation: true,
          width: 1920,
        }),
        getPosition(),
      ])

      const position = firstFix.latitude == null ? await getPosition() : firstFix

      const mime = photo.format === 'png' ? 'image/png' : 'image/jpeg'
      const dataUrl = `data:${mime};base64,${photo.base64String}`

      // base64 ocupa 4 caracteres por cada 3 bytes reales.
      if ((photo.base64String?.length ?? 0) * 0.75 > MAX_FILE_BYTES) {
        setValidationError('La foto supera el limite de 10 MB.')
        return
      }

      setFile(null)
      setPreviewUrl(dataUrl)
      setTakenAt(new Date().toISOString())
      if (position.latitude == null) {
        setGeoWarning(true)
      } else {
        setCoords(position)
      }
    } catch (err) {
      // El usuario cancelando la camara tambien llega aqui; no es un error.
      const message = err?.message ?? ''
      if (!/cancel/i.test(message)) {
        setValidationError(message || 'No se pudo abrir la camara.')
      }
    } finally {
      setCapturing(false)
    }
  }

  // ── Captura web (sin cambios respecto al flujo existente) ──────────────────

  function handleFileChange(e) {
    const selected = e.target.files?.[0]
    if (!selected) return

    revokePreview()
    resetMessages()

    if (!selected.type.startsWith('image/')) {
      setValidationError('Solo se aceptan imagenes (JPEG, PNG, WEBP).')
      if (inputRef.current) inputRef.current.value = ''
      return
    }

    if (selected.size > MAX_FILE_BYTES) {
      setValidationError('El archivo supera el limite de 10 MB.')
      if (inputRef.current) inputRef.current.value = ''
      return
    }

    const url = URL.createObjectURL(selected)
    previewUrlRef.current = url
    setFile(selected)
    setPreviewUrl(url)
    setTakenAt(new Date().toISOString())

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => setCoords({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
        () => setGeoWarning(true),
        { timeout: 8000 }
      )
    } else {
      setGeoWarning(true)
    }
  }

  function handleCancel() {
    revokePreview()
    setFile(null)
    setPreviewUrl(null)
    setCaption('')
    setTakenAt(null)
    setCoords(null)
    setGeoWarning(false)
    setValidationError('')
    setApiError('')
    if (inputRef.current) inputRef.current.value = ''
  }

  function flashSuccess() {
    handleCancel()
    setSuccessVisible(true)
    setTimeout(() => setSuccessVisible(false), 3000)
  }

  /** Deja la foto en SQLite; syncPhotos() la sube al recuperar la conexion. */
  async function saveOffline() {
    setSavingOffline(true)
    try {
      const offlineUuid = await savePhotoOffline({
        work_order_id: workOrderId,
        file_path: previewUrl, // data:image/jpeg;base64,...
        latitude: coords?.latitude ?? null,
        longitude: coords?.longitude ?? null,
        taken_at: takenAt,
        caption: caption.trim(),
      })
      if (!offlineUuid) {
        setApiError('No hay base de datos local disponible para guardar la foto.')
        return
      }
      handleCancel()
      showOfflineNotice('Foto guardada. Se sincronizara al reconectar.')
      await refreshPendingCount()
    } catch (err) {
      setApiError(err?.message ?? 'No se pudo guardar la foto en el dispositivo.')
    } finally {
      setSavingOffline(false)
    }
  }

  async function handleSubmit() {
    setApiError('')

    if (isNative && !isOnline) {
      await saveOffline()
      return
    }

    let uploadFile = file
    if (!uploadFile) {
      try {
        uploadFile = await dataUrlToFile(previewUrl, `ot-${workOrderId}-${Date.now()}`)
      } catch (err) {
        setApiError(err?.message ?? 'No se pudo preparar la foto para subirla.')
        return
      }
    }

    upload.mutate(
      {
        work_order: workOrderId,
        file: uploadFile,
        latitude: coords?.latitude ?? null,
        longitude: coords?.longitude ?? null,
        taken_at: takenAt,
        caption: caption.trim(),
      },
      {
        onSuccess: flashSuccess,
        onError: (err) => setApiError(extractError(err)),
      }
    )
  }

  if (disabled) {
    return (
      <p className="text-sm text-gray-500">
        Solo se pueden subir fotos mientras la orden esta en progreso.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      {!hasPhoto &&
        (isNative ? (
          <button
            type="button"
            onClick={handleNativeCapture}
            disabled={capturing}
            className="inline-flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-60 transition-colors"
          >
            {capturing ? 'Abriendo camara...' : 'Tomar foto'}
          </button>
        ) : (
          <label className="inline-flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-50 cursor-pointer transition-colors">
            Seleccionar foto
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="sr-only"
              onChange={handleFileChange}
            />
          </label>
        ))}

      {validationError && <p className="text-sm text-red-500">{validationError}</p>}

      {hasPhoto && (
        <div className="space-y-3">
          <img
            src={previewUrl}
            alt="Vista previa"
            className="w-full max-w-xs rounded-lg border border-gray-200 object-cover"
          />

          {geoWarning && (
            <p className="text-xs text-amber-600">
              No se pudo obtener la ubicacion. La foto se subira sin coordenadas GPS.
            </p>
          )}
          {coords && (
            <p className="text-xs text-gray-500">
              GPS: {coords.latitude.toFixed(4)}, {coords.longitude.toFixed(4)}
            </p>
          )}

          <div>
            <input
              type="text"
              value={caption}
              maxLength={MAX_CAPTION}
              onChange={(e) => setCaption(e.target.value)}
              placeholder="Descripcion (opcional)"
              className="w-full max-w-xs border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30"
            />
            <p className="text-xs text-gray-500 mt-1">{MAX_CAPTION - caption.length} caracteres restantes</p>
          </div>

          {isNative && !isOnline && (
            <p className="text-xs text-amber-600">
              Sin conexion: la foto se guardara en el dispositivo y se subira al reconectar.
            </p>
          )}

          {apiError && <p className="text-sm text-red-500">{apiError}</p>}

          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={busy}
              className="inline-flex items-center gap-2 px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand/90 disabled:opacity-60 transition-colors"
            >
              {busy && (
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              )}
              {busy ? 'Guardando...' : isNative && !isOnline ? 'Guardar foto' : 'Subir foto'}
            </button>
            <button
              type="button"
              onClick={handleCancel}
              disabled={busy}
              className="px-4 py-2 border border-gray-200 text-gray-600 text-sm rounded-lg hover:bg-gray-50 disabled:opacity-60 transition-colors"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {successVisible && (
        <p className="text-sm text-green-600">Foto subida correctamente.</p>
      )}
    </div>
  )
}
