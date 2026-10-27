import { useState } from 'react'

import {
  useDeleteMySignature,
  useMySignature,
  useSaveMySignature,
} from '../../api/evidence'
import useNetworkStore from '../../store/networkStore'
import SignaturePad from './SignaturePad'

function mensajeDeError(err, porDefecto) {
  const data = err?.response?.data
  if (!data) return porDefecto
  if (typeof data === 'string') return data
  if (data.detail) return String(data.detail)
  const val = data[Object.keys(data)[0]]
  return Array.isArray(val) ? val[0] : val ? String(val) : porDefecto
}

/**
 * Registrar, reemplazar o borrar la firma propia (perfil). Se dibuja una vez y
 * se aplica a las OT del usuario como una copia; la de quien recibe en el
 * hospital se sigue dibujando en cada visita. Cambiarla no toca las actas ya
 * firmadas.
 */
export default function MiFirmaGuardada() {
  const isOnline = useNetworkStore((s) => s.isOnline)
  const { data, isLoading } = useMySignature()
  const guardar = useSaveMySignature()
  const borrar = useDeleteMySignature()
  const [editando, setEditando] = useState(false)
  const [confirmaBorrar, setConfirmaBorrar] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')

  const actual = data?.dataUrl ?? null
  const mostrarPad = editando || (!actual && !isLoading)

  async function alCapturar(dataUrl) {
    setError('')
    setAviso('')
    try {
      await guardar.mutateAsync(dataUrl)
      setEditando(false)
      setAviso('Firma guardada. Ya puedes usarla al firmar tus órdenes.')
    } catch (err) {
      setError(mensajeDeError(err, 'No se pudo guardar la firma.'))
    }
  }

  async function alBorrar() {
    setError('')
    setAviso('')
    try {
      await borrar.mutateAsync()
      setConfirmaBorrar(false)
      setAviso('Firma borrada.')
    } catch (err) {
      setError(mensajeDeError(err, 'No se pudo borrar la firma.'))
    }
  }

  return (
    <section className="bg-white rounded-xl border border-gray-200 shadow-card p-5">
      <h2 className="text-xs font-semibold text-gray-500 border-b border-gray-200 pb-2 mb-4">
        Mi firma
      </h2>

      <p className="text-sm text-gray-600 mb-4">
        Tu firma es un dato personal. Se usa solo para firmar tus órdenes de trabajo y actas, y
        puedes borrarla cuando quieras. Al firmar una orden se guarda una copia en esa orden:
        si luego cambias o borras tu firma, las actas anteriores no cambian.
      </p>

      {aviso && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-green-50 border border-green-200 text-green-800 text-sm">
          {aviso}
        </div>
      )}
      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
          {error}
        </div>
      )}

      {isLoading && <p className="text-sm text-gray-500">Cargando...</p>}

      {actual && !editando && (
        <div className="space-y-3">
          <div className="border border-gray-200 rounded-lg bg-white p-3 inline-block max-w-full">
            <img src={actual} alt="Tu firma guardada" className="max-h-28 max-w-full" />
          </div>
          {!isOnline && (
            <p className="text-xs text-amber-600">
              Sin conexión: para reemplazar o borrar tu firma necesitas red.
            </p>
          )}
          {confirmaBorrar ? (
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-sm text-gray-700">¿Borrar tu firma guardada?</span>
              <button
                type="button"
                onClick={alBorrar}
                disabled={borrar.isPending || !isOnline}
                className="px-3 py-1.5 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-60"
              >
                {borrar.isPending ? 'Borrando...' : 'Sí, borrar'}
              </button>
              <button
                type="button"
                onClick={() => setConfirmaBorrar(false)}
                className="text-sm text-gray-500 hover:text-gray-700 underline"
              >
                Cancelar
              </button>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-4">
              <button
                type="button"
                onClick={() => {
                  setAviso('')
                  setEditando(true)
                }}
                disabled={!isOnline}
                className="px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand/90 disabled:opacity-60 transition-colors"
              >
                Reemplazar
              </button>
              <button
                type="button"
                onClick={() => setConfirmaBorrar(true)}
                disabled={!isOnline}
                className="text-sm text-red-600 hover:text-red-700 underline disabled:opacity-60"
              >
                Borrar
              </button>
            </div>
          )}
        </div>
      )}

      {mostrarPad && (
        <div className="space-y-3">
          <p className="text-sm font-medium text-gray-700">
            {actual ? 'Dibuja tu nueva firma' : 'Dibuja tu firma'}
          </p>
          {!isOnline ? (
            <p className="text-sm text-amber-600">
              Necesitas conexión para registrar tu firma. Hazlo antes de salir a campo.
            </p>
          ) : (
            <SignaturePad
              onCapture={alCapturar}
              captureLabel="Guardar mi firma"
              captureBusy={guardar.isPending}
            />
          )}
          {actual && (
            <button
              type="button"
              onClick={() => setEditando(false)}
              className="text-sm text-gray-500 hover:text-gray-700 underline"
            >
              Cancelar
            </button>
          )}
        </div>
      )}
    </section>
  )
}
