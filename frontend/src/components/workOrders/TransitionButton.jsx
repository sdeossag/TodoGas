import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import useAuthStore from '../../store/authStore'
import useNetworkStore from '../../store/networkStore'
import { useCancelWorkOrder, useTransitionWorkOrder } from '../../api/workOrders'
import { useWorkOrderSignatures } from '../../api/evidence'
import { markStatusChangedOffline } from '../../db/repositories'
import Icon from '../ui/Icon'

const NO_SIGNATURE_MSG =
  'No se puede enviar a revision sin al menos una firma digital registrada.'

const OFFLINE_SIGNATURE_MSG =
  'Sin conexion no se puede verificar la firma. Reconecta para enviar a revision.'

// Cancelar usa otro endpoint que el motor de sincronizacion no reproduce,
// asi que no se permite sin conexion en vez de encolar algo que fallaria.
const OFFLINE_CANCEL_MSG =
  'Cancelar una OT requiere conexion. Intenta de nuevo al recuperar la red.'

function Spinner() {
  return (
    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}

function extractBackendError(err) {
  const data = err?.response?.data
  if (!data) return err?.message || 'Error al realizar la transicion.'
  if (typeof data === 'string') return data
  if (data.detail) return String(data.detail)
  const firstKey = Object.keys(data)[0]
  const val = firstKey ? data[firstKey] : null
  return Array.isArray(val) ? val[0] : val ? String(val) : 'Error al realizar la transicion.'
}

export default function TransitionButton({ workOrder, onSuccess }) {
  const { user } = useAuthStore()
  const role = user?.role
  const status = workOrder?.status

  const [rejecting, setRejecting] = useState(false)
  const [rejectComment, setRejectComment] = useState('')
  const [showCancelModal, setShowCancelModal] = useState(false)
  const [cancelComment, setCancelComment] = useState('')
  const [transitionError, setTransitionError] = useState('')
  const [savingOffline, setSavingOffline] = useState(false)

  const isOnline = useNetworkStore((s) => s.isOnline)
  const refreshPendingCount = useNetworkStore((s) => s.refreshPendingCount)
  const showOfflineNotice = useNetworkStore((s) => s.showOfflineNotice)
  const queryClient = useQueryClient()

  const transitionMut = useTransitionWorkOrder(workOrder?.id)
  const cancelMut = useCancelWorkOrder(workOrder?.id)

  // Sin red esta consulta solo generaria ruido de errores.
  const { data: signatures = [] } = useWorkOrderSignatures(
    isOnline && status === 'IN_PROGRESS' ? workOrder?.id : null
  )
  const hasSignatures = signatures.length > 0

  const isTecAssigned = role === 'TEC' && workOrder?.assigned_to?.id === user?.id

  async function doTransition(new_status, comment = '') {
    setTransitionError('')

    if (isOnline) {
      try {
        await transitionMut.mutateAsync({ new_status, comment })
        onSuccess?.()
      } catch (err) {
        setTransitionError(extractBackendError(err))
      }
      return
    }

    // Sin red el cambio se anota en SQLite y el motor de sincronizacion lo
    // empuja al servidor al reconectar.
    setSavingOffline(true)
    try {
      const saved = await markStatusChangedOffline(workOrder.id, new_status, comment)
      if (!saved) {
        setTransitionError('El almacenamiento offline no esta disponible en este dispositivo.')
        return
      }

      // Refleja el cambio en la vista de detalle sin tocar la API.
      queryClient.setQueryData(['work-orders', workOrder.id], (old) =>
        old ? { ...old, status: new_status } : old
      )

      await refreshPendingCount()
      // El aviso va antes del refetch: este puede sacar la tarjeta de la
      // pestaña activa y desmontar este componente.
      showOfflineNotice('Estado guardado. Se sincronizara al reconectar.')
      onSuccess?.()
    } catch (err) {
      console.warn('[transition] fallo el guardado offline:', err?.message ?? err)
      setTransitionError('No se pudo guardar el cambio en el dispositivo.')
    } finally {
      setSavingOffline(false)
    }
  }

  async function doCancel() {
    if (!cancelComment.trim()) return
    setTransitionError('')
    if (!isOnline) {
      setTransitionError(OFFLINE_CANCEL_MSG)
      return
    }
    try {
      await cancelMut.mutateAsync({ comment: cancelComment.trim() })
      setShowCancelModal(false)
      setCancelComment('')
      onSuccess?.()
    } catch (err) {
      setTransitionError(extractBackendError(err))
    }
  }

  if (!workOrder || !role) return null

  const activeStatuses = ['PENDING', 'IN_PROGRESS', 'IN_REVIEW']
  const isActive = activeStatuses.includes(status)
  const loading = transitionMut.isPending || cancelMut.isPending || savingOffline

  const reviewBlocked = isTecAssigned && status === 'IN_PROGRESS' && !hasSignatures
  const reviewBlockedReason = isOnline ? NO_SIGNATURE_MSG : OFFLINE_SIGNATURE_MSG

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2 items-center">
        {/* TEC: Iniciar */}
        {isTecAssigned && status === 'PENDING' && (
          <button
            onClick={() => doTransition('IN_PROGRESS')}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60"
          >
            {loading ? <Spinner /> : <span>&#9654;</span>}
            Iniciar OT
          </button>
        )}

        {/* TEC: Enviar a revision */}
        {isTecAssigned && status === 'IN_PROGRESS' && (
          <div className="relative group">
            <button
              onClick={() => !reviewBlocked && doTransition('IN_REVIEW')}
              disabled={loading || reviewBlocked}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 text-white text-sm font-medium rounded-lg hover:bg-amber-600 disabled:opacity-60"
            >
              {loading ? <Spinner /> : <span>&#8593;</span>}
              Enviar a revision
            </button>
            {reviewBlocked && (
              <span className="absolute bottom-full left-0 mb-1 w-64 text-xs bg-gray-800 text-white rounded px-2 py-1 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                {reviewBlockedReason}
              </span>
            )}
          </div>
        )}

        {/* ADMIN/SUP: Completar */}
        {['ADMIN', 'SUP'].includes(role) && status === 'IN_REVIEW' && !rejecting && (
          <button
            onClick={() => doTransition('COMPLETED')}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-60"
          >
            {loading ? <Spinner /> : <Icon name="check" className="w-4 h-4" />}
            Completar
          </button>
        )}

        {/* ADMIN/SUP: Rechazar (volver a IN_PROGRESS) */}
        {['ADMIN', 'SUP'].includes(role) && status === 'IN_REVIEW' && (
          rejecting ? (
            <div className="flex items-center gap-2 flex-wrap">
              <input
                autoFocus
                value={rejectComment}
                onChange={(e) => setRejectComment(e.target.value)}
                placeholder="Motivo del rechazo..."
                className="border border-red-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-300 w-52"
              />
              <button
                onClick={async () => {
                  await doTransition('IN_PROGRESS', rejectComment)
                  setRejecting(false)
                  setRejectComment('')
                }}
                disabled={loading || !rejectComment.trim()}
                className="inline-flex items-center gap-1 px-3 py-1.5 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 disabled:opacity-60"
              >
                {loading ? <Spinner /> : 'Confirmar rechazo'}
              </button>
              <button
                onClick={() => { setRejecting(false); setRejectComment('') }}
                className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700"
              >
                Cancelar
              </button>
            </div>
          ) : (
            <button
              onClick={() => setRejecting(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-100 text-red-700 text-sm font-medium rounded-lg hover:bg-red-200"
            >
              <Icon name="close" className="w-4 h-4" />
              Rechazar
            </button>
          )
        )}

        {/* ADMIN: Cancelar OT */}
        {role === 'ADMIN' && isActive && (
          <button
            onClick={() => setShowCancelModal(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 text-gray-600 text-sm font-medium rounded-lg hover:bg-gray-200"
          >
            &#8856; Cancelar OT
          </button>
        )}
      </div>

      {/* Aviso de firma faltante debajo del boton (mobile-friendly) */}
      {reviewBlocked && (
        <p className="text-xs text-amber-600 sm:hidden">{reviewBlockedReason}</p>
      )}

      {/* Error de transicion del backend */}
      {transitionError && (
        <p className="text-sm text-red-500">{transitionError}</p>
      )}

      {/* Modal de cancelacion */}
      {showCancelModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-semibold text-gray-800 mb-1">Cancelar OT</h3>
            <p className="text-sm text-gray-500 mb-4">
              Esta accion no se puede deshacer. Indica el motivo.
            </p>
            <textarea
              autoFocus
              rows={3}
              value={cancelComment}
              onChange={(e) => setCancelComment(e.target.value)}
              placeholder="Motivo de cancelacion..."
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 resize-none mb-4"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => { setShowCancelModal(false); setCancelComment('') }}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                Cerrar
              </button>
              <button
                onClick={doCancel}
                disabled={cancelMut.isPending || !cancelComment.trim()}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-60"
              >
                {cancelMut.isPending ? <Spinner /> : null}
                Confirmar cancelacion
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
