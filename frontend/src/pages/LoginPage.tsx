import { useState, FormEvent } from 'react'
import { useNavigate }         from 'react-router-dom'
import { authApi }             from '../api/auth'
import { useStore }            from '../store/useStore'
import { ParticleBackground }  from '../components/ParticleBackground'

type Mode = 'login' | 'register'

export function LoginPage() {
  const navigate   = useNavigate()
  const setToken   = useStore((s) => s.setToken)
  const setUser    = useStore((s) => s.setUser)

  const [mode,     setMode]     = useState<Mode>('login')
  const [username, setUsername] = useState('')
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') {
        const res = await authApi.login({ username, password })
        const tok = res.data.access_token
        localStorage.setItem('token', tok)
        setToken(tok)
        const me = await authApi.me()
        setUser(me.data)
        navigate('/')
      } else {
        await authApi.register({ username, email, password })
        setMode('login')
        setError('สมัครสมาชิกสำเร็จ กรุณาเข้าสู่ระบบ')
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'เกิดข้อผิดพลาด กรุณาลองใหม่')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-[#0f172a] overflow-hidden relative">

      {/* Particle network background */}
      <ParticleBackground />

      {/* Gradient blobs */}
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="animate-blob absolute -top-32 -left-32 w-96 h-96 rounded-full
                        bg-sky-600/10 blur-3xl" />
        <div className="animate-blob delay-300 absolute top-1/2 -right-40 w-80 h-80 rounded-full
                        bg-violet-600/10 blur-3xl" />
        <div className="animate-blob delay-150 absolute -bottom-20 left-1/4 w-72 h-72 rounded-full
                        bg-cyan-500/8 blur-3xl" />
      </div>

      {/* Card */}
      <div className="w-full max-w-sm relative z-10 animate-scale-in">

        {/* Logo */}
        <div className="text-center mb-8 animate-fade-slide-up">
          <div className="text-6xl mb-3 animate-float inline-block">💨</div>
          <h1 className="text-2xl font-bold text-white tracking-tight">AirGuard Pi</h1>
          <p className="text-slate-400 text-sm mt-1">PM2.5 Smart Air Purifier</p>
        </div>

        <div className="card animate-fade-slide-up delay-75
                        shadow-2xl shadow-sky-950/50 border-slate-700/80
                        backdrop-blur-sm bg-[#1e293b]/90">

          {/* Tab switcher */}
          <div className="flex bg-slate-900/80 rounded-xl p-1 mb-5">
            {(['login', 'register'] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setError('') }}
                className={`flex-1 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                  mode === m
                    ? 'bg-sky-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {m === 'login' ? 'เข้าสู่ระบบ' : 'สมัครสมาชิก'}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="flex flex-col gap-3">
            <div className="animate-fade-slide-up delay-150">
              <label className="block text-xs text-slate-400 mb-1">ชื่อผู้ใช้</label>
              <input
                className="input"
                placeholder="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoComplete="username"
              />
            </div>

            {mode === 'register' && (
              <div className="animate-fade-slide-up">
                <label className="block text-xs text-slate-400 mb-1">Email</label>
                <input
                  className="input"
                  type="email"
                  placeholder="email@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            )}

            <div className="animate-fade-slide-up delay-225">
              <label className="block text-xs text-slate-400 mb-1">รหัสผ่าน</label>
              <input
                className="input"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />
            </div>

            {error && (
              <p className={`text-xs px-3 py-2 rounded-lg animate-fade-in ${
                error.includes('สำเร็จ')
                  ? 'bg-emerald-900/40 text-emerald-400 border border-emerald-800/50'
                  : 'bg-red-900/40 text-red-400 border border-red-800/50'
              }`}>
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn-primary mt-1 animate-fade-slide-up delay-300"
            >
              {loading
                ? <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                      <path className="opacity-75" fill="currentColor"
                        d="M4 12a8 8 0 018-8v8H4z"/>
                    </svg>
                    กำลังเข้าสู่ระบบ...
                  </span>
                : mode === 'login' ? 'เข้าสู่ระบบ' : 'สมัครสมาชิก'
              }
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-slate-600 mt-6">
          AirGuard Pi v1.0 · Thai PCD PM2.5 Standard
        </p>
      </div>
    </div>
  )
}
