import { useState } from 'react'
import { fanApi } from '../api/fan'

interface Props {
  deviceId:     string
  currentSpeed: number
  currentMode:  string
  onUpdated?:   () => void
}

export function FanControl({ deviceId, currentSpeed, currentMode, onUpdated }: Props) {
  const [speed,   setSpeed]   = useState(currentSpeed)
  const [loading, setLoading] = useState(false)
  const [mode,    setMode]    = useState<'auto' | 'manual'>(
    currentMode === 'auto' ? 'auto' : 'manual',
  )

  const apply = async () => {
    setLoading(true)
    try {
      await fanApi.set(deviceId, { speed, mode })
      onUpdated?.()
    } finally {
      setLoading(false)
    }
  }

  const setAuto = async () => {
    setLoading(true)
    try {
      await fanApi.setAuto(deviceId)
      setMode('auto')
      onUpdated?.()
    } finally {
      setLoading(false)
    }
  }

  const setOff = async () => {
    setLoading(true)
    try {
      await fanApi.setOff(deviceId)
      setSpeed(0)
      setMode('manual')
      onUpdated?.()
    } finally {
      setLoading(false)
    }
  }

  // Fan blade visual (rotates with speed)
  const animDuration = speed > 0 ? `${Math.max(0.3, 3 - speed * 0.025)}s` : '0s'

  return (
    <div className="flex flex-col items-center gap-5">

      {/* Fan icon */}
      <div className="relative w-28 h-28 flex items-center justify-center">
        <div
          className="w-24 h-24 text-6xl select-none"
          style={{
            animation: speed > 0 ? `spin ${animDuration} linear infinite` : 'none',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          🌀
        </div>
        <span
          className="absolute bottom-0 right-0 text-xs font-bold px-2 py-0.5 rounded-full"
          style={{ background: speed > 0 ? '#0ea5e9' : '#334155', color: '#fff' }}
        >
          {speed}%
        </span>
      </div>

      {/* Mode badge */}
      <div className="flex gap-2">
        <span
          className={`px-3 py-1 rounded-full text-xs font-semibold border ${
            mode === 'auto'
              ? 'bg-sky-900 border-sky-500 text-sky-300'
              : 'bg-slate-800 border-slate-600 text-slate-400'
          }`}
        >
          {mode === 'auto' ? '🤖 Auto' : '🖐 Manual'}
        </span>
      </div>

      {/* Speed slider (manual only) */}
      <div className="w-full px-2">
        <label className="flex justify-between text-xs text-slate-400 mb-1">
          <span>ความเร็ว</span>
          <span className="font-bold text-white">{speed}%</span>
        </label>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={speed}
          onChange={(e) => { setSpeed(+e.target.value); setMode('manual') }}
          className="w-full accent-sky-500"
        />
        <div className="flex justify-between text-xs text-slate-600 mt-0.5">
          <span>ปิด</span>
          <span>ต่ำ</span>
          <span>กลาง</span>
          <span>สูง</span>
          <span>Max</span>
        </div>
      </div>

      {/* Preset buttons */}
      <div className="flex flex-wrap gap-2 justify-center">
        {[
          { label: 'ปิด',  speed: 0,   mode: 'manual' as const },
          { label: '25%',  speed: 25,  mode: 'manual' as const },
          { label: '50%',  speed: 50,  mode: 'manual' as const },
          { label: '75%',  speed: 75,  mode: 'manual' as const },
          { label: '100%', speed: 100, mode: 'manual' as const },
        ].map((p) => (
          <button
            key={p.label}
            onClick={() => { setSpeed(p.speed); setMode(p.mode) }}
            className="px-3 py-1 text-xs rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 transition"
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 w-full">
        <button
          onClick={setAuto}
          disabled={loading}
          className="flex-1 py-2 rounded-xl text-sm font-semibold bg-emerald-700 hover:bg-emerald-600 text-white transition disabled:opacity-50"
        >
          🤖 Auto
        </button>
        <button
          onClick={apply}
          disabled={loading}
          className="flex-1 py-2 rounded-xl text-sm font-semibold bg-sky-600 hover:bg-sky-500 text-white transition disabled:opacity-50"
        >
          {loading ? '...' : '✓ Apply'}
        </button>
        <button
          onClick={setOff}
          disabled={loading}
          className="flex-1 py-2 rounded-xl text-sm font-semibold bg-slate-700 hover:bg-slate-600 text-white transition disabled:opacity-50"
        >
          ⏹ Off
        </button>
      </div>
    </div>
  )
}
