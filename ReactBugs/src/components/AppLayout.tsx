import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import type { ReactNode } from 'react'

export default function AppLayout({ children }: { children: ReactNode }) {
  const { logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `text-sm font-medium transition-colors ${
      isActive ? 'text-white' : 'text-gray-300 hover:text-white'
    }`

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="bg-gray-900 px-4 py-3 flex items-center gap-6 shrink-0">
        <span className="text-white font-bold text-base tracking-tight">RxBugs</span>
        <nav className="flex items-center gap-4">
          <NavLink to="/bugs" className={linkClass}>Bugs</NavLink>
          <NavLink to="/admin" className={linkClass}>Admin</NavLink>
        </nav>
        <button
          onClick={handleLogout}
          className="ml-auto text-xs text-gray-400 hover:text-white transition-colors"
        >
          Sign out
        </button>
      </header>
      <main className="flex-1">{children}</main>
    </div>
  )
}
