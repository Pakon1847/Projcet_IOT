import { NavLink, useNavigate } from 'react-router-dom'
import { useStore } from '../store/useStore'

const links = [
  { to: '/',        icon: '📊', label: 'Dashboard' },
  { to: '/history', icon: '📈', label: 'ประวัติ'    },
  { to: '/fan',     icon: '🌀', label: 'พัดลม'      },
  { to: '/alerts',  icon: '🔔', label: 'แจ้งเตือน'  },
  { to: '/ai',      icon: '🤖', label: 'AI Chat'    },
  { to: '/system',  icon: '🔗', label: 'System'     },
]

export function NavBar() {
  const { user, logout } = useStore()
  const navigate = useNavigate()

  const handleLogout = () => { logout(); navigate('/login') }

  return (
    <>
      {/* Desktop top bar */}
      <header className="hidden md:flex fixed top-0 inset-x-0 z-50 h-14
                         items-center justify-between px-6
                         bg-[#0f172a]/80 backdrop-blur-md
                         border-b border-slate-800/80 shadow-sm">
        <div className="flex items-center gap-2 font-bold text-sky-400 text-lg">
          <span className="animate-float inline-block">💨</span>
          <span>AirGuard Pi</span>
        </div>

        <nav className="flex gap-0.5">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === '/'}
              className={({ isActive }) =>
                `px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-sky-900/60 text-sky-300 shadow-sm shadow-sky-950'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/70'
                }`
              }
            >
              {l.icon} {l.label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-3 text-sm">
          <span className="text-slate-400">{user?.username}</span>
          <button
            onClick={handleLogout}
            className="px-3 py-1 rounded-lg bg-slate-800/80 text-slate-400
                       hover:bg-slate-700 hover:text-slate-200
                       active:scale-95 transition-all duration-200 text-xs"
          >
            ออกจากระบบ
          </button>
        </div>
      </header>

      {/* Mobile bottom tab bar */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-50 flex
                      bg-[#0f172a]/90 backdrop-blur-md
                      border-t border-slate-800/80 pb-safe">
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.to === '/'}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center py-2 gap-0.5 text-xs
               transition-all duration-200 ${
                isActive
                  ? 'text-sky-400 scale-105'
                  : 'text-slate-500 hover:text-slate-300'
              }`
            }
          >
            <span className="text-xl">{l.icon}</span>
            <span>{l.label}</span>
          </NavLink>
        ))}
      </nav>
    </>
  )
}
