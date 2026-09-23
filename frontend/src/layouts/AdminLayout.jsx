import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import NotificationBell from '../components/notifications/NotificationBell'
import { useStockAlerts } from '../api/inventory'
import Icon from '../components/ui/Icon'
import Avatar from '../components/ui/Avatar'
import OfflineBanner from '../components/ui/OfflineBanner'
import { useFindingsSummary } from '../api/findings'

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
      { to: '/tareas-pendientes', label: 'Tareas pendientes', icon: 'clock' },
      { to: '/hallazgos', label: 'Hallazgos', icon: 'warning', alertKey: 'findings' },
      { to: '/ordenes', label: 'Ordenes de trabajo', icon: 'workOrder' },
      { to: '/planes-pm', label: 'Planes de tareas', icon: 'plan' },
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
      { to: '/usuarios', label: 'Usuarios', icon: 'users', adminOnly: true },
      { to: '/reportes', label: 'Reportes', icon: 'report' },
      { to: '/formato-acta', label: 'Formato del acta', icon: 'settings', adminOnly: true },
      { to: '/auditoria', label: 'Auditoria', icon: 'audit', adminOnly: true },
    ],
  },
  {
    id: 'cuenta',
    title: 'Cuenta',
    links: [{ to: '/mi-perfil', label: 'Mi perfil', icon: 'profile' }],
  },
]

function navClasses({ isActive }) {
  return [
    'group relative flex items-center gap-3 mx-2 pl-3 pr-2.5 py-2 rounded-lg text-sm',
    'transition-[background-color,color] duration-150',
    isActive
      ? 'bg-white/[0.10] text-white font-medium'
      : 'text-brand-100/75 hover:bg-white/[0.06] hover:text-white',
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
  // Hallazgos esperando decisión del planificador (bloque E).
  const { data: hallazgos } = useFindingsSummary()
  const alertas = { inventory: lowStockCount, findings: hallazgos?.pending ?? 0 }

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
    <div className="flex flex-col h-dvh bg-gray-100">
      <a href="#contenido" className="skip-link">
        Saltar al contenido
      </a>

      {/* Barra superior — ocupa todo el ancho, independiente del sidebar */}
      <header className="h-20 flex-shrink-0 bg-white border-b border-gray-200 shadow-sm flex items-center gap-3 px-4 sm:px-6 z-30">
        <button
          type="button"
          onClick={() => setSidebarOpen((open) => !open)}
          aria-label={sidebarOpen ? 'Ocultar menu' : 'Mostrar menu'}
          aria-expanded={sidebarOpen}
          className="p-2 -ml-1 rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800 active:bg-gray-200 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/25"
        >
          <Icon name="menu" className="w-6 h-6" />
        </button>

        <Link
          to="/dashboard"
          className="flex items-center gap-3 rounded-lg focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/25"
        >
          {showLogo ? (
            <img
              src="/logo-mejorado-.png"
              alt="TodoGas"
              className="h-12 w-auto"
              onError={() => setShowLogo(false)}
            />
          ) : (
            <span className="text-xl font-semibold text-brand tracking-tight">TodoGas</span>
          )}
          {/* En pantallas estrechas la barra no da de si: basta con el logo */}
          <span className="hidden md:block h-8 w-px bg-gray-200" aria-hidden="true" />
          <span className="hidden md:block text-xs font-medium tracking-[0.18em] text-gray-400">
            CMMS
          </span>
        </Link>

        <div className="flex-1" />

        <NotificationBell />

        <div className="hidden sm:flex items-center gap-2.5 pl-1">
          <Avatar user={user} size="md" />
          <div className="text-left leading-tight">
            <p className="text-sm font-medium text-gray-800">
              {user?.first_name} {user?.last_name}
            </p>
            <p className="text-xs text-gray-500">{ROLE_LABELS[user?.role] ?? user?.role}</p>
          </div>
        </div>

        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 px-2.5 py-2 rounded-lg text-sm text-gray-500 transition-colors hover:bg-red-50 hover:text-red-700 active:bg-red-100 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-red-500/25"
        >
          <span className="hidden md:inline">Cerrar sesion</span>
          <Icon name="logout" className="w-5 h-5" />
        </button>
      </header>

      <OfflineBanner />

      {/* Sidebar desplegable + vista del router */}
      <div className="flex-1 flex overflow-frame relative">
        {/* Fondo oscuro que cierra el panel al tocarlo (solo movil) */}
        {sidebarOpen && (
          <div
            className="absolute inset-0 bg-gray-900/50 backdrop-blur-[2px] z-20 lg:hidden animate-fade"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
        )}

        <aside
          className={[
            'bg-brand-900 overflow-hidden transition-all duration-200 ease-spring',
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
            <nav aria-label="Navegacion principal" className="flex-1 py-3 overflow-y-auto no-scrollbar">
              {NAV_GROUPS.map((group, gi) => {
                const links = group.links.filter((l) => !l.adminOnly || user?.role === 'ADMIN')
                if (links.length === 0) return null
                return (
                  <div
                    key={group.id}
                    className={gi > 0 ? 'mt-4 pt-4 border-t border-white/[0.07]' : ''}
                  >
                    {group.title && (
                      <p className="px-5 pb-2 text-[11px] font-medium text-brand-300/70">
                        {group.title}
                      </p>
                    )}
                    {links.map(({ to, label, icon, alertKey }) => (
                      <NavLink key={to} to={to} className={navClasses}>
                        {({ isActive }) => (
                          <>
                            {/* Guia fina pegada al borde del panel: marca la
                                pagina activa sin el borde de 4px que partia
                                en dos la fila. */}
                            <span
                              className={`absolute -left-2 top-1/2 -translate-y-1/2 w-[3px] rounded-r-full bg-brand-300 transition-all duration-200 ease-spring ${
                                isActive ? 'h-5 opacity-100' : 'h-0 opacity-0'
                              }`}
                              aria-hidden="true"
                            />
                            <Icon
                              name={icon}
                              className={`w-[18px] h-[18px] flex-shrink-0 transition-colors ${
                                isActive ? 'text-brand-200' : 'text-brand-300/60 group-hover:text-brand-200'
                              }`}
                            />
                            <span className="flex-1 truncate">{label}</span>
                            {alertKey && alertas[alertKey] > 0 && (
                              <span className="flex items-center justify-center h-5 min-w-[1.25rem] px-1.5 rounded-md bg-red-500/90 text-white text-[11px] font-semibold tabular-nums">
                                {alertas[alertKey] > 99 ? '99+' : alertas[alertKey]}
                              </span>
                            )}
                          </>
                        )}
                      </NavLink>
                    ))}
                  </div>
                )
              })}
            </nav>

            <div className="flex items-center gap-2.5 p-4 border-t border-white/[0.07]">
              <Avatar user={user} size="sm" tone="dark" />
              <div className="min-w-0 leading-tight">
                <p className="text-brand-100 text-xs truncate">{user?.email}</p>
                <p className="text-brand-300/70 text-[11px]">
                  {ROLE_LABELS[user?.role] ?? user?.role}
                </p>
              </div>
            </div>
          </div>
        </aside>

        <main id="contenido" className="flex-1 overflow-y-auto">
          {/* Tope de ancho para que en monitores anchos las tablas no se
              estiren de canto a canto y se pierda la linea de lectura. */}
          <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-6 pb-10">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
