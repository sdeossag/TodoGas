import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import Icon from '../components/ui/Icon'
import Avatar from '../components/ui/Avatar'
import OfflineBanner from '../components/ui/OfflineBanner'
import { useTaskTypes } from '../api/taskTypes'

const NAV_LINKS = [
  { to: '/mis-ordenes', label: 'Mis ordenes', icon: 'wrench' },
  { to: '/mi-perfil', label: 'Mi perfil', icon: 'profile' },
]

// El tecnico trabaja desde el telefono: por debajo de lg el panel flota sobre
// el contenido en vez de robarle 224px de ancho.
const isNarrow = () => window.matchMedia('(max-width: 1023px)').matches

export default function TechnicianLayout() {
  // Nombres del catálogo de tipos de tarea, guardados para verlos también sin red.
  useTaskTypes()
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const [showLogo, setShowLogo] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(() => !isNarrow())

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

      <header className="h-16 sm:h-20 flex-shrink-0 bg-white border-b border-gray-200 shadow-sm flex items-center gap-3 px-4 sm:px-6 z-30">
        <button
          type="button"
          onClick={() => setSidebarOpen((open) => !open)}
          aria-label={sidebarOpen ? 'Ocultar menu' : 'Mostrar menu'}
          aria-expanded={sidebarOpen}
          className="p-2 -ml-1 rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800 active:bg-gray-200 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/25"
        >
          <Icon name="menu" className="w-6 h-6" />
        </button>

        {showLogo ? (
          <img
            src="/logo-mejorado-.png"
            alt="TodoGas CMMS"
            className="h-8 sm:h-10 w-auto"
            onError={() => setShowLogo(false)}
          />
        ) : (
          <span className="text-brand font-semibold text-lg tracking-tight">TodoGas</span>
        )}

        <div className="flex-1" />

        <div className="hidden sm:flex items-center gap-2.5">
          <Avatar user={user} size="sm" />
          <span className="text-gray-800 font-medium text-sm truncate max-w-[14rem]">
            {user?.first_name} {user?.last_name}
          </span>
        </div>

        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 px-2.5 py-2 rounded-lg text-sm text-gray-500 transition-colors hover:bg-red-50 hover:text-red-700 active:bg-red-100 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-red-500/25"
        >
          <span className="hidden md:inline">Cerrar sesión</span>
          <Icon name="logout" className="w-5 h-5" />
        </button>
      </header>

      <OfflineBanner />

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
            'absolute left-0 inset-y-0 z-20 w-56',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full',
            'lg:static lg:inset-auto lg:z-auto lg:translate-x-0 lg:flex-shrink-0',
            sidebarOpen ? 'lg:w-56' : 'lg:w-0',
          ].join(' ')}
        >
          {/* Ancho fijo para que el contenido no se reflow mientras se anima */}
          <div className="w-56 h-full flex flex-col">
            <nav aria-label="Navegacion principal" className="flex-1 py-3">
              {NAV_LINKS.map(({ to, label, icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `group relative flex items-center gap-3 mx-2 pl-3 pr-2.5 py-2.5 rounded-lg text-sm
                     transition-[background-color,color] duration-150
                     ${
                       isActive
                         ? 'bg-white/[0.10] text-white font-medium'
                         : 'text-brand-100/75 hover:bg-white/[0.06] hover:text-white'
                     }`
                  }
                >
                  {({ isActive }) => (
                    <>
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
                    </>
                  )}
                </NavLink>
              ))}
            </nav>

            <div className="flex items-center gap-2.5 p-4 border-t border-white/[0.07]">
              <Avatar user={user} size="sm" tone="dark" />
              <p className="text-brand-200 text-xs truncate">{user?.email}</p>
            </div>
          </div>
        </aside>

        <main id="contenido" className="flex-1 overflow-y-auto p-4 sm:p-6 pb-10">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
