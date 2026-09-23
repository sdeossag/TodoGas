import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom'
import useAuthStore from '../store/authStore'

import LoginPage from '../pages/auth/LoginPage'
import ChangePasswordPage from '../pages/auth/ChangePasswordPage'
import DashboardPage from '../pages/dashboard/DashboardPage'
import MisActivosPage from '../pages/assets/MisActivosPage'
import HospitalsPage from '../pages/assets/HospitalsPage'
import ContractsPage from '../pages/assets/ContractsPage'
import LocationsPage from '../pages/assets/LocationsPage'
import AssetsPage from '../pages/assets/AssetsPage'
import AssetDetailPage from '../pages/assets/AssetDetailPage'
import AssetFormPage from '../pages/assets/AssetFormPage'
import WorkOrdersPage from '../pages/work-orders/WorkOrdersPage'
import CreateWorkOrderPage from '../pages/work-orders/CreateWorkOrderPage'
import WorkOrderDetailPage from '../pages/work-orders/WorkOrderDetailPage'
import MyWorkOrdersPage from '../pages/work-orders/MyWorkOrdersPage'
import ChecklistTemplatesPage from '../pages/checklists/ChecklistTemplatesPage'
import ChecklistEditorPage from '../pages/checklists/ChecklistEditorPage'
import MaintenancePlansPage from '../pages/maintenance/MaintenancePlansPage'
import MaintenancePlanDetailPage from '../pages/maintenance/MaintenancePlanDetailPage'
import MaintenancePlanFormPage from '../pages/maintenance/MaintenancePlanFormPage'
import MaintenanceCalendarPage from '../pages/maintenance/MaintenanceCalendarPage'
import PendingTasksPage from '../pages/maintenance/PendingTasksPage'
import FindingsInboxPage from '../pages/maintenance/FindingsInboxPage'
import TaskTypesPage from '../pages/maintenance/TaskTypesPage'
import ReportsPage from '../pages/reports/ReportsPage'
import ReportSettingsPage from '../pages/reports/ReportSettingsPage'
import InventoryPage from '../pages/inventory/InventoryPage'
import ItemMovementsPage from '../pages/inventory/ItemMovementsPage'
import AuditLogPage from '../pages/audit/AuditLogPage'
import UsersPage from '../pages/users/UsersPage'
import ProfilePage from '../pages/users/ProfilePage'
import ClientDashboard from '../pages/client/ClientDashboard'
import ClientReportsPage from '../pages/client/ClientReportsPage'
import ClientAssetPage from '../pages/client/ClientAssetPage'
import ClientWorkOrderPage from '../pages/client/ClientWorkOrderPage'
import NotFoundPage from '../pages/NotFoundPage'
import UiSpinner from '../components/ui/Spinner'

import AdminLayout from '../layouts/AdminLayout'
import TechnicianLayout from '../layouts/TechnicianLayout'
import ClientLayout from '../layouts/ClientLayout'

const ROLE_HOME = {
  ADMIN: '/dashboard',
  SUP: '/dashboard',
  TEC: '/mis-ordenes',
  CLI: '/mis-dashboard',
}

function Spinner() {
  return (
    <div className="min-h-dvh flex items-center justify-center bg-gray-50">
      <UiSpinner className="h-8 w-8 text-brand" label="Cargando la aplicacion" />
    </div>
  )
}

function ProtectedRoute({ allowedRoles, redirectTo }) {
  const { isAuthenticated, isLoading, user } = useAuthStore()

  if (isLoading) return <Spinner />

  if (!isAuthenticated) return <Navigate to="/login" replace />

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    const home = ROLE_HOME[user.role] ?? '/login'
    return <Navigate to={home} replace />
  }

  return <Outlet />
}

export const router = createBrowserRouter(
  [
    // Rutas públicas
    { path: '/login', element: <LoginPage /> },
    { path: '/cambiar-contrasena', element: <ChangePasswordPage /> },

    // Rutas para ADMIN y SUP
    {
      element: <ProtectedRoute allowedRoles={['ADMIN', 'SUP']} />,
      children: [
        {
          element: <AdminLayout />,
          children: [
            { path: '/dashboard', element: <DashboardPage /> },
            { path: '/hospitales', element: <HospitalsPage /> },
            { path: '/hospitales/:id/ubicaciones', element: <LocationsPage /> },
            { path: '/contratos', element: <ContractsPage /> },
            { path: '/activos', element: <AssetsPage /> },
            { path: '/activos/nuevo', element: <AssetFormPage /> },
            { path: '/activos/:id', element: <AssetDetailPage /> },
            { path: '/activos/:id/editar', element: <AssetFormPage /> },
            // Órdenes de trabajo
            { path: '/ordenes', element: <WorkOrdersPage /> },
            { path: '/ordenes/nueva', element: <CreateWorkOrderPage /> },
            { path: '/ordenes/:id', element: <WorkOrderDetailPage /> },
            { path: '/checklists', element: <ChecklistTemplatesPage /> },
            { path: '/checklists/:id/editar', element: <ChecklistEditorPage /> },
            { path: '/planes-pm', element: <MaintenancePlansPage /> },
            { path: '/planes-pm/nuevo', element: <MaintenancePlanFormPage /> },
            { path: '/planes-pm/:id', element: <MaintenancePlanDetailPage /> },
            { path: '/planes-pm/:id/editar', element: <MaintenancePlanFormPage /> },
            { path: '/calendario-pm', element: <MaintenanceCalendarPage /> },
            { path: '/tareas-pendientes', element: <PendingTasksPage /> },
            { path: '/hallazgos', element: <FindingsInboxPage /> },
            { path: '/reportes', element: <ReportsPage /> },
            { path: '/inventario', element: <InventoryPage /> },
            { path: '/inventario/:id/movimientos', element: <ItemMovementsPage /> },
            { path: '/mi-perfil', element: <ProfilePage /> },

            // Gestion de usuarios y auditoria: ADMIN, no SUP.
            {
              element: <ProtectedRoute allowedRoles={['ADMIN']} />,
              children: [
                { path: '/usuarios', element: <UsersPage /> },
                { path: '/auditoria', element: <AuditLogPage /> },
                { path: '/formato-acta', element: <ReportSettingsPage /> },
                { path: '/tipos-de-tarea', element: <TaskTypesPage /> },
              ],
            },
          ],
        },
      ],
    },

    // Rutas para TEC
    {
      element: <ProtectedRoute allowedRoles={['TEC']} />,
      children: [
        {
          element: <TechnicianLayout />,
          children: [
            { path: '/mis-ordenes', element: <MyWorkOrdersPage /> },
            { path: '/mis-ordenes/:id', element: <WorkOrderDetailPage /> },
            { path: '/mi-perfil', element: <ProfilePage /> },
          ],
        },
      ],
    },

    // Rutas para CLI
    {
      element: <ProtectedRoute allowedRoles={['CLI']} />,
      children: [
        {
          element: <ClientLayout />,
          children: [
            { path: '/mis-dashboard', element: <ClientDashboard /> },
            { path: '/mis-activos', element: <MisActivosPage /> },
            { path: '/mis-activos/:id', element: <ClientAssetPage /> },
            { path: '/historial/:id', element: <ClientWorkOrderPage /> },
            { path: '/mis-reportes', element: <ClientReportsPage /> },
            { path: '/mi-perfil', element: <ProfilePage /> },
          ],
        },
      ],
    },

    // Raíz → redirige según rol
    {
      path: '/',
      element: <RootRedirect />,
    },
    { path: '*', element: <NotFound /> },
  ],
  {
    future: {
      v7_startTransition: true,
      v7_relativeSplatPath: true,
    },
  }
)

function RootRedirect() {
  const { isAuthenticated, isLoading, user } = useAuthStore()
  if (isLoading) return <Spinner />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  const home = ROLE_HOME[user?.role] ?? '/login'
  return <Navigate to={home} replace />
}

/**
 * Sin sesion, una ruta desconocida sigue llevando al login: no hay nada que
 * ensenar y tampoco conviene confirmar que URLs existen. Con sesion abierta se
 * muestra el 404 real, con su enlace de vuelta al inicio del rol.
 */
function NotFound() {
  const { isAuthenticated, isLoading, user } = useAuthStore()
  if (isLoading) return <Spinner />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <NotFoundPage homePath={ROLE_HOME[user?.role] ?? '/'} />
}
