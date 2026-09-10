import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import Icon from '../components/ui/Icon'
import Avatar from '../components/ui/Avatar'

const NAV_LINKS = [
  { to: '/mis-dashboard', label: 'Dashboard' },
  { to: '/mis-activos', label: 'Mis activos' },
  { to: '/mis-reportes', label: 'Mis reportes' },
  { to: '/mi-perfil', label: 'Mi perfil' },
]

export default function ClientLayout() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const [showLogo, setShowLogo] = useState(true)

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-dvh bg-gray-50">
      <a href="#contenido" className="skip-link">
        Saltar al contenido
      </a>

      <header className="relative bg-brand-900 text-white shadow-md grain">
        <div className="relative max-w-5xl mx-auto px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-x-6 gap-y-3 sm:h-16">
          {showLogo ? (
            <img
              src="/logo-invertido-.png"
              alt="TodoGas CMMS"
              className="h-9 w-auto"
              onError={() => setShowLogo(false)}
            />
          ) : (
            <span className="font-semibold text-base tracking-tight">TodoGas CMMS</span>
          )}

          <div className="flex items-center gap-4 sm:gap-6 order-3 sm:order-none w-full sm:w-auto">
            {/* La pagina activa se marca con una superficie, no con un
                subrayado: sobre fondo navy el subrayado casi no se ve. */}
            <nav
              aria-label="Navegacion del portal"
              className="flex gap-1 overflow-x-auto no-scrollbar flex-1 sm:flex-none -mx-1 px-1"
            >
              {NAV_LINKS.map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap
                     transition-[background-color,color] duration-150
                     focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-white/25
                     ${
                       isActive
                         ? 'bg-white/[0.12] text-white'
                         : 'text-brand-200/80 hover:bg-white/[0.07] hover:text-white'
                     }`
                  }
                >
                  {label}
                </NavLink>
              ))}
            </nav>

            <div className="flex items-center gap-2.5 flex-shrink-0">
              <Avatar user={user} size="sm" tone="dark" />
              <span className="text-sm text-brand-100 hidden sm:inline">{user?.first_name}</span>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs text-brand-200/80 transition-colors hover:bg-white/[0.07] hover:text-white focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-white/25"
              >
                <span>Salir</span>
                <Icon name="logout" className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <main id="contenido" className="max-w-5xl mx-auto py-6 sm:py-8 px-4 sm:px-6 pb-12">
        <Outlet />
      </main>
    </div>
  )
}
