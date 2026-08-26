import { useEffect, useRef, useState } from 'react'

import { useCreateSignature } from '../../api/evidence'
import { saveSignatureOffline } from '../../db/repositories'
import useNetworkStore from '../../store/networkStore'

function extractError(err) {
  const data = err?.response?.data
  if (!data) return err?.message || 'Error al guardar la firma.'
  if (typeof data === 'string') return data
  if (data.detail) return String(data.detail)
  const firstKey = Object.keys(data)[0]
  const val = firstKey ? data[firstKey] : null
  return Array.isArray(val) ? val[0] : val ? String(val) : 'Error al guardar la firma.'
}

export default function SignaturePad({
  workOrderId,
  signatureType = 'TECHNICIAN',
  disabled = false,
  onSuccess,
}) {
  const mountDisabled = useRef(disabled)
  const canvasRef = useRef(null)
  const isDrawing = useRef(false)
  const [hasStrokes, setHasStrokes] = useState(false)
  const [signerName, setSignerName] = useState('')
  const [signerRole, setSignerRole] = useState('')
  const [validationError, setValidationError] = useState('')
  const [apiError, setApiError] = useState('')
  const [success, setSuccess] = useState(false)
  const [savingOffline, setSavingOffline] = useState(false)

  const isOnline = useNetworkStore((s) => s.isOnline)
  const showOfflineNotice = useNetworkStore((s) => s.showOfflineNotice)
  const refreshPendingCount = useNetworkStore((s) => s.refreshPendingCount)

  const createSignature = useCreateSignature()
  const busy = createSignature.isPending || savingOffline

  function initCtx(ctx, w, h) {
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, w, h)
    ctx.strokeStyle = '#000000'
    ctx.lineWidth = 2
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
  }

  function resizeCanvas() {
    const canvas = canvasRef.current
    if (!canvas) return
    const container = canvas.parentElement
    if (!container) return
    const w = container.clientWidth
    const h = Math.round(180 * (w / 400))
    canvas.width = w
    canvas.height = h
    initCtx(canvas.getContext('2d'), w, h)
    setHasStrokes(false)
  }

  useEffect(() => {
    resizeCanvas()
    window.addEventListener('resize', resizeCanvas)
    return () => window.removeEventListener('resize', resizeCanvas)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function getPos(e) {
    const canvas = canvasRef.current
    const rect = canvas.getBoundingClientRect()
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height
    if (e.touches) {
      return {
        x: (e.touches[0].clientX - rect.left) * scaleX,
        y: (e.touches[0].clientY - rect.top) * scaleY,
      }
    }
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    }
  }

  function startDraw(e) {
    if (mountDisabled.current) return
    const ctx = canvasRef.current.getContext('2d')
    const { x, y } = getPos(e)
    ctx.beginPath()
    ctx.moveTo(x, y)
    isDrawing.current = true
    setHasStrokes(true)
  }

  function draw(e) {
    if (!isDrawing.current || mountDisabled.current) return
    const ctx = canvasRef.current.getContext('2d')
    const { x, y } = getPos(e)
    ctx.lineTo(x, y)
    ctx.stroke()
  }

  function endDraw() {
    isDrawing.current = false
  }

  function handleTouchStart(e) {
    e.preventDefault()
    startDraw(e)
  }

  function handleTouchMove(e) {
    e.preventDefault()
    draw(e)
  }

  function clearCanvas() {
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    initCtx(ctx, canvas.width, canvas.height)
    setHasStrokes(false)
    setValidationError('')
    setApiError('')
  }

  function resetForm() {
    clearCanvas()
    setSignerName('')
    setSignerRole('')
  }

  /**
   * Deja la firma en SQLite. syncSignatures() la sube al recuperar la conexion,
   * respetando el signature_type con el que se capturo.
   */
  async function saveOffline(base64) {
    setSavingOffline(true)
    try {
      const localId = await saveSignatureOffline({
        work_order_id: workOrderId,
        signature_type: signatureType,
        image_base64: base64,
        signer_name: signerName.trim(),
        signer_role: signerRole.trim(),
        latitude: null,
        longitude: null,
        signed_at: new Date().toISOString(),
      })
      if (!localId) {
        setApiError('No hay base de datos local disponible para guardar la firma.')
        return
      }
      resetForm()
      showOfflineNotice('Firma guardada. Se sincronizara al reconectar.')
      await refreshPendingCount()
      onSuccess?.()
    } catch (err) {
      setApiError(err?.message ?? 'No se pudo guardar la firma en el dispositivo.')
    } finally {
      setSavingOffline(false)
    }
  }

  async function handleSubmit() {
    setValidationError('')
    setApiError('')
    if (!hasStrokes) {
      setValidationError('Por favor firme en el area antes de guardar.')
      return
    }
    if (!signerName.trim()) {
      setValidationError('El nombre del firmante es requerido.')
      return
    }

    // toDataURL siempre trae el prefijo data:image/png;base64,
    const base64 = canvasRef.current.toDataURL('image/png').split(',')[1]

    if (!isOnline) {
      await saveOffline(base64)
      return
    }

    createSignature.mutate(
      {
        work_order: workOrderId,
        signature_type: signatureType,
        image_data: base64,
        signer_name: signerName.trim(),
        signer_role: signerRole.trim(),
      },
      {
        onSuccess: () => {
          resetForm()
          setSuccess(true)
          setTimeout(() => setSuccess(false), 4000)
          onSuccess?.()
        },
        onError: (err) => setApiError(extractError(err)),
      }
    )
  }

  if (mountDisabled.current) {
    return (
      <p className="text-sm text-gray-500">
        Solo se puede firmar mientras la orden esta en progreso.
      </p>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <canvas
          ref={canvasRef}
          className="w-full border border-gray-300 rounded-lg bg-white touch-none"
          style={{ display: 'block', cursor: 'crosshair' }}
          onMouseDown={startDraw}
          onMouseMove={draw}
          onMouseUp={endDraw}
          onMouseLeave={endDraw}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={endDraw}
        />
        <button
          type="button"
          onClick={clearCanvas}
          className="mt-2 text-xs text-gray-500 hover:text-gray-700 underline"
        >
          Limpiar
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
            Nombre del firmante <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={signerName}
            onChange={(e) => setSignerName(e.target.value)}
            placeholder="Nombre completo de quien firma"
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
            Cargo
          </label>
          <input
            type="text"
            value={signerRole}
            onChange={(e) => setSignerRole(e.target.value)}
            placeholder="Cargo"
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30"
          />
        </div>
      </div>

      {!isOnline && (
        <p className="text-xs text-amber-600">
          Sin conexion: la firma se guardara en el dispositivo y se subira al reconectar.
        </p>
      )}
      {validationError && <p className="text-sm text-red-500">{validationError}</p>}
      {apiError && <p className="text-sm text-red-500">{apiError}</p>}
      {success && <p className="text-sm text-green-600">Firma guardada correctamente.</p>}

      <button
        type="button"
        onClick={handleSubmit}
        disabled={busy || !hasStrokes || !signerName.trim()}
        className="inline-flex items-center gap-2 px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand/90 disabled:opacity-60 transition-colors"
      >
        {busy && (
          <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
        )}
        {busy ? 'Guardando...' : 'Guardar firma'}
      </button>
    </div>
  )
}
