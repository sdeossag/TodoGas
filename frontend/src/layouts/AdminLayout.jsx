import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import NotificationBell from '../components/notifications/NotificationBell'
import { useStockAlerts } from '../api/inventory'
import Icon from '../components/ui/Icon'
import OfflineBanner from '../components/ui/OfflineBanner'

const ROLE_LABELS = {
  ADMIN: 'Administrador',
  SUP: 'Supervisor',
  TEC: 'Tecnico',
  CLI: 'Cliente',
}

const SIDEBAR_KEY = 'todogas.sidebar'

// Por debajo de lg el sidebar flota sobre el contenido en vez de empujarlo.
const isNarrow = () => window.matchMedia('(max-width: 1023px)').matches

// Grupos de navegacion — cada grupo se separa visualmente en el sidebar
const NAV_GROUPS = [
  {
    id: 'inicio',
    links: [{ to: '/dashboard', label: 'Dashboard', icon: 'dashboard' }],
  },
  {
    id: 'activos',
    title: 'Activos',
    links: [
      { to: '/hospitales', label: 'Hospitales', icon: 'hospital' },
      { to: '/activos', label: 'Activos', icon: 'asset' },
    ],
  },
  {
    id: 'mantenimiento',
    title: 'Mantenimiento',
    links: [
      { to: '/ordenes', label: 'Ordenes de trabajo', icon: 'workOrder' },
      { to: '/planes-pm', label: 'Planes PM', icon: 'plan' },
      { to: '/calendario-pm', label: 'Calendario', icon: 'calendar' },
    ],
  },
  {
    id: 'checklists',
    title: 'Checklists',
    links: [{ to: '/checklists', label: 'Checklists', icon: 'checklist' }],
  },
  {
    id: 'administracion',
    title: 'Administracion',
    links: [
      { to: '/inventario', label: 'Inventario', icon: 'inventory', alertKey: 'inventory' },
      { to: '/usuarios', label: 'Usuarios', icon: 'users' },
      { to: '/reportes', label: 'Reportes', icon: 'report' },
      { to: '/auditoria', label: 'Auditoria', icon: 'audit', adminOnly: true },
    ],
  },
]

function navClasses({ isActive }) {
  return [
    'flex items-center gap-3 pl-4 pr-4 py-2 text-sm border-l-4 transition-colors duration-100',
    isActive
      ? 'bg-brand-700 border-white text-white font-semibold'
      : 'border-transparent text-brand-100 hover:bg-brand-700/60 hover:text-white',
  ].join(' ')
}

export default function AdminLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const { data: alertData } = useStockAlerts()
  const [showLogo, setShowLogo] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    if (isNarrow()) return false
    return localStorage.getItem(SIDEBAR_KEY) !== 'closed'
  })
  const lowStockCount = alertData?.low_stock_count ?? 0

  // La preferencia solo se recuerda en escritorio: en movil siempre arranca cerrado.
  useEffect(() => {
    if (!isNarrow()) localStorage.setItem(SIDEBAR_KEY, sidebarOpen ? 'open' : 'closed')
  }, [sidebarOpen])

  // En movil el panel tapa el contenido, asi que al navegar hay que replegarlo.
  useEffect(() => {
    if (isNarrow()) setSidebarOpen(false)
  }, [location.pathname])

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex flex-col h-screen bg-gray-100">
      {/* Barra superior — ocupa todo el ancho, independiente del sidebar */}
      <header className="h-20 flex-shrink-0 bg-white border-b border-gray-200 shadow-sm flex items-center gap-3 px-4 sm:px-6 z-30">
        <button
          type="button"
          onClick={() => setSidebarOpen((open) => !open)}
          aria-label={sidebarOpen ? 'Ocultar menu' : 'Mostrar menu'}
          aria-expanded={sidebarOpen}
          className="p-2 -ml-1 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-400"
        >
          <Icon name="menu" className="w-6 h-6" />
        </button>

        <Link to="/dashboard" className="flex items-center gap-3">
          {showLogo ? (
            <img
              src="/logo-mejorado-.png"
              alt="TodoGas"
              className="h-12 w-auto"
              onError={() => setShowLogo(false)}
            />
          ) : (
            <span className="text-xl font-bold text-brand tracking-tight">TodoGas</span>
          )}
          {/* En pantallas estrechas la barra no da de si: basta con el logo */}
          <span className="hidden md:block h-9 w-px bg-gray-200" aria-hidden="true" />
          <span className="hidden md:block text-sm font-semibold uppercase tracking-[0.2em] text-gray-500">
            CMMS
          </span>
        </Link>

        <div className="flex-1" />

        <NotificationBell />
        <div className="text-right leading-tight hidden sm:block">
          <p className="text-sm font-medium text-gray-800">
            {user?.first_name} {user?.last_name}
          </p>
          <p className="text-xs text-gray-500">{ROLE_LABELS[user?.role] ?? user?.role}</p>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-red-600 transition-colors duration-150"
        >
          <span className="hidden md:inline">Cerrar sesion</span>
          <Icon name="logout" className="w-5 h-5" />
        </button>
      </header>

      <OfflineBanner />

      {/* Sidebar desplegable + vista del router */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Fondo oscuro que cierra el panel al tocarlo (solo movil) */}
        {sidebarOpen && (
          <div
            className="absolute inset-0 bg-gray-900/40 z-20 lg:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
        )}

        <aside
          className={[
            'bg-brand-800 overflow-hidden transition-all duration-200 ease-out',
            // movil: capa flotante que entra desde la izquierda
            'absolute left-0 inset-y-0 z-20 w-60',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full',
            // escritorio: parte del flujo, se pliega por ancho
            'lg:static lg:inset-auto lg:z-auto lg:translate-x-0 lg:flex-shrink-0',
            sidebarOpen ? 'lg:w-60' : 'lg:w-0',
          ].join(' ')}
        >
          {/* Ancho fijo para que el contenido no se reflow mientras se anima */}
          <div className="w-60 h-full flex flex-col">
            <nav className="flex-1 py-4 overflow-y-auto no-scrollbar">
              {NAV_GROUPS.map((group, gi) => {
                const links = group.links.filter((l) => !l.adminOnly || user?.role === 'ADMIN')
                if (links.length === 0) return null
                return (
                  <div
                    key={group.id}
                    className={gi > 0 ? 'mt-1.5 pt-1.5 border-t border-white/10' : ''}
                  >
                    {group.title && (
                      <p className="px-5 pb-1 pt-1 text-[10px] font-semibold uppercase tracking-wider text-brand-200">
                        {group.title}
                      </p>
                    )}
                    {links.map(({ to, label, icon, alertKey }) => (
                      <NavLink key={to} to={to} className={navClasses}>
                        <Icon name={icon} className="w-[18px] h-[18px] flex-shrink-0" />
                        <span className="flex-1">{label}</span>
                        {alertKey === 'inventory' && lowStockCount > 0 && (
                          <span className="flex items-center justify-center h-5 min-w-[1.25rem] px-1 rounded-full bg-red-500 text-white text-xs font-bold">
                            {lowStockCount > 99 ? '99+' : lowStockCount}
                          </span>
                        )}
                      </NavLink>
                    ))}
                  </div>
                )
              })}
            </nav>

            <div className="p-4 border-t border-white/10">
              <p className="text-brand-100 text-xs truncate">{user?.email}</p>
              <p className="text-brand-300 text-xs">{ROLE_LABELS[user?.role] ?? user?.role}</p>
            </div>
          </div>
        </aside>

        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
