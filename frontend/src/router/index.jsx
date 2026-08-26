import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom'
import useAuthStore from '../store/authStore'

import LoginPage from '../pages/auth/LoginPage'
import ChangePasswordPage from '../pages/auth/ChangePasswordPage'
import DashboardPage from '../pages/dashboard/DashboardPage'
import MisActivosPage from '../pages/assets/MisActivosPage'
import HospitalsPage from '../pages/assets/HospitalsPage'
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
import ReportsPage from '../pages/reports/ReportsPage'
import InventoryPage from '../pages/inventory/InventoryPage'
import ItemMovementsPage from '../pages/inventory/ItemMovementsPage'
import AuditLogPage from '../pages/audit/AuditLogPage'
import UsersPage from '../pages/users/UsersPage'
import ClientDashboard from '../pages/client/ClientDashboard'

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
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <svg
        className="animate-spin h-8 w-8 text-brand"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
      </svg>
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
            { path: '/reportes', element: <ReportsPage /> },
            { path: '/inventario', element: <InventoryPage /> },
            { path: '/inventario/:id/movimientos', element: <ItemMovementsPage /> },
            { path: '/usuarios', element: <UsersPage /> },
            { path: '/auditoria', element: <AuditLogPage /> },
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
          ],
        },
      ],
    },

    // Raíz → redirige según rol
    {
      path: '/',
      element: <RootRedirect />,
    },
    { path: '*', element: <Navigate to="/login" replace /> },
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
