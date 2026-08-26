import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import Icon from '../components/ui/Icon'
import OfflineBanner from '../components/ui/OfflineBanner'

const NAV_LINKS = [
  { to: '/mis-ordenes', label: 'Mis Órdenes', icon: 'wrench' },
  { to: '/mi-perfil', label: 'Mi Perfil', icon: 'profile' },
]

export default function TechnicianLayout() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const [showLogo, setShowLogo] = useState(true)

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex h-screen bg-gray-100">
      <aside className="w-56 flex-shrink-0 bg-brand flex flex-col">
        <div className="h-20 flex items-center px-4 border-b border-white/10">
          {showLogo ? (
            <img
              src="/logo-invertido-.png"
              alt="TodoGas CMMS"
              className="h-10 w-auto"
              onError={() => setShowLogo(false)}
            />
          ) : (
            <span className="text-white font-bold text-lg">TodoGas</span>
          )}
        </div>
        <nav className="flex-1 py-4">
          {NAV_LINKS.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-5 py-2.5 text-sm font-medium transition-colors
                 ${isActive ? 'bg-white/15 text-white' : 'text-brand-100 hover:bg-white/10 hover:text-white'}`
              }
            >
              <Icon name={icon} className="w-[18px] h-[18px] flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-brand-dark">
          <p className="text-brand-200 text-xs truncate">{user?.email}</p>
        </div>
      </aside>

      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-20 bg-white border-b border-gray-200 shadow-sm flex items-center justify-between px-6 flex-shrink-0">
          <span className="text-gray-700 font-medium">
            {user?.first_name} {user?.last_name}
          </span>
          <button
            onClick={handleLogout}
            className="text-sm text-gray-500 hover:text-red-600 transition-colors flex items-center gap-1"
          >
            Cerrar sesión
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h6a2 2 0 012 2v1" />
            </svg>
          </button>
        </header>

        <OfflineBanner />

        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
