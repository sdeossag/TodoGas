import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import client from './client'
import { fetchAllPages } from './pagination'
import {
  getOfflineWorkOrderDetail,
  saveWorkOrderBundle,
  saveWorkOrderDetailOffline,
} from '../db/repositories'
import useAuthStore from '../store/authStore'
import useNetworkStore from '../store/networkStore'

export const NOT_DOWNLOADED_MSG =
  'Esta OT no está descargada en el teléfono. Ábrela con conexión para poder trabajarla sin red.'

/**
 * Fetcher suelto: lo comparten useWorkOrders y el hook offline.
 *
 * Devuelve siempre un array. useOfflineWorkOrders se lo pasa tal cual a
 * saveWorkOrdersOffline() para sembrar SQLite, asi que si aqui se colara la
 * envoltura paginada la cache offline del tecnico se quedaria vacia sin dar
 * ningun error.
 */
export function fetchWorkOrders(params = {}) {
  return fetchAllPages(client, '/api/work-orders/', params)
}

export function useWorkOrders(params = {}, options = {}) {
  return useQuery({
    queryKey: ['work-orders', params],
    queryFn: () => fetchWorkOrders(params),
    ...options,
  })
}

/**
 * Detalle de una OT. Sin red se lee de SQLite (lo descargado mas lo que el
 * tecnico hizo despues en el telefono); con red, al tecnico se le guarda para
 * poder abrirla despues sin conexion.
 */
export function useWorkOrder(id) {
  const isOnline = useNetworkStore((s) => s.isOnline)
  const role = useAuthStore((s) => s.user?.role)
  return useQuery({
    queryKey: ['work-orders', id, isOnline ? 'online' : 'offline'],
    queryFn: async () => {
      if (!isOnline) {
        const detalle = await getOfflineWorkOrderDetail(id)
        if (!detalle) throw new Error(NOT_DOWNLOADED_MSG)
        return detalle
      }
      const { data } = await client.get(`/api/work-orders/${id}/`)
      if (role === 'TEC') {
        saveWorkOrderDetailOffline(data).catch((error) =>
          console.warn('[offline] no se pudo guardar la OT:', error?.message ?? error)
        )
      }
      return data
    },
    enabled: !!id,
    // Al perder o recuperar la red cambia la clave: sin esto la pagina
    // parpadearia vacia mientras se lee la otra fuente.
    placeholderData: (previous) => previous,
    // Sin red lee SQLite: que TanStack no la pause por navigator.onLine.
    networkMode: 'always',
  })
}

let descargando = null

/**
 * Descarga el paquete offline (detalle y checklists) de las OT abiertas del
 * tecnico. Corre en segundo plano al cargar su lista con conexion; una sola
 * tanda a la vez aunque la lista se refresque.
 */
export function downloadOfflineBundles(workOrders = []) {
  if (descargando) return descargando
  const abiertas = workOrders.filter((wo) => ['PENDING', 'IN_PROGRESS'].includes(wo.status))
  descargando = (async () => {
    for (const wo of abiertas) {
      try {
        const { data } = await client.get(`/api/work-orders/${wo.id}/offline-bundle/`)
        await saveWorkOrderBundle(data)
      } catch (error) {
        console.warn('[offline] no se pudo descargar la OT', wo.id, error?.message ?? error)
      }
    }
  })().finally(() => {
    descargando = null
  })
  return descargando
}

export function useCreateWorkOrder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.post('/api/work-orders/', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['work-orders'] }),
  })
}

export function useUpdateWorkOrder(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => client.patch(`/api/work-orders/${id}/`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-orders', id] })
      qc.invalidateQueries({ queryKey: ['work-orders'] })
    },
  })
}

export function useTransitionWorkOrder(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ new_status, comment = '' }) =>
      client.post(`/api/work-orders/${id}/transition/`, { new_status, comment }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-orders', id] })
      qc.invalidateQueries({ queryKey: ['work-orders'] })
    },
  })
}

export function useAssignWorkOrder(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ assigned_to }) =>
      client.post(`/api/work-orders/${id}/assign/`, { assigned_to }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['work-orders', id] }),
  })
}

export function useCancelWorkOrder(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ comment }) =>
      client.post(`/api/work-orders/${id}/cancel/`, { comment }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-orders', id] })
      qc.invalidateQueries({ queryKey: ['work-orders'] })
    },
  })
}

/** Agrega tareas pendientes a una OT que aun no empezo. */
export function useAddWorkOrderTasks(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (taskIds) =>
      client.post(`/api/work-orders/${id}/tasks/`, { task_ids: taskIds }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-orders'] })
      qc.invalidateQueries({ queryKey: ['tasks'] })
    },
  })
}

/** Saca una tarea de una OT que aun no empezo; vuelve a pendientes. */
export function useRemoveWorkOrderTask(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (taskId) =>
      client.post(`/api/work-orders/${id}/remove-task/`, { task_id: taskId }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-orders'] })
      qc.invalidateQueries({ queryKey: ['tasks'] })
    },
  })
}

/**
 * Cambia el checklist de una tarea de la OT. El checklist es de la tarea: con
 * varios activos cada uno lleva el suyo.
 */
export function useSetTaskChecklist(id) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (datos) =>
      client.post(`/api/work-orders/${id}/task-checklist/`, datos).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-orders'] })
      qc.invalidateQueries({ queryKey: ['checklist-responses'] })
    },
  })
}

export function useWorkOrderHistory(id, allowed = true) {
  return useQuery({
    queryKey: ['work-orders', id, 'history'],
    queryFn: () => fetchAllPages(client, `/api/work-orders/${id}/history/`),
    enabled: !!id && allowed,
  })
}
