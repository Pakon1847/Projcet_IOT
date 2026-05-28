import { useEffect, useState } from 'react'
import { useStore }            from '../store/useStore'
import { useWebSocket }        from '../hooks/useWebSocket'
import { sensorApi }           from '../api/sensor'
import { AQIGauge }            from '../components/AQIGauge'
import { PM25Chart }           from '../components/PM25Chart'
import { StatCard }            from '../components/StatCard'
import { OutdoorCard }         from '../components/OutdoorCard'
import { getAQIInfo, PM25_STANDARD_24H } from '../lib/aqi'
import type { SensorReading }  from '../api/sensor'
import { formatDistanceToNow, parseISO } from 'date-fns'
import { th } from 'date-fns/locale'

export function DashboardPage() {
  const deviceId    = useStore((s) => s.deviceId)
  const liveReading = useStore((s) => s.liveReading)
  const [history,   setHistory]   = useState<SensorReading[]>([])
  const [loading,   setLoading]   = useState(true)
  const [anomaly,   setAnomaly]   = useState<{ message: string; type: string } | null>(null)

  useWebSocket(deviceId, (msg) => {
    if (msg.anomaly) {
      setAnomaly(msg.anomaly)
      // auto-dismiss หลัง 30 วินาที
      setTimeout(() => setAnomaly(null), 30_000)
    }
  })

  useEffect(() => {
    const load = async () => {
      try {
        const res = await sensorApi.history(deviceId, 3)
        setHistory((res.data as any).data ?? res.data)
      } catch { /* offline */ }
      finally { setLoading(false) }
    }
    load()
    const id = setInterval(load, 60_000)
    return () => clearInterval(id)
  }, [deviceId])

  const reading = liveReading ?? history[history.length - 1]
  const info    = reading ? getAQIInfo(reading.aqi) : null
  const ago     = reading
    ? formatDistanceToNow(parseISO(reading.timestamp), { addSuffix: true, locale: th })
    : '—'

  if (loading) {
    return (
      <main className="page flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <svg className="animate-spin w-8 h-8 text-sky-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
          <span className="text-slate-500 text-sm">กำลังโหลด...</span>
        </div>
      </main>
    )
  }

  return (
    <main className="page pt-16 pb-28 md:pb-10">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 animate-fade-slide-up">
        <div>
          <h1 className="text-lg font-bold text-white">Dashboard</h1>
          <p className="text-xs text-slate-500">{deviceId} · อัปเดต {ago}</p>
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          <span className={`w-2 h-2 rounded-full transition-colors ${
            liveReading ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'
          }`} />
          <span className={liveReading ? 'text-emerald-400' : 'text-slate-500'}>
            {liveReading ? 'Live' : 'Offline'}
          </span>
        </div>
      </div>

      {reading ? (
        <>
          {/* AQI Gauge */}
          <div className="card flex justify-center mb-4 animate-fade-slide-up delay-75
                          hover:shadow-lg hover:shadow-sky-950/40 transition-all duration-300">
            <AQIGauge aqi={reading.aqi} pm25={reading.pm25} size={230} />
          </div>

          {/* Anomaly alert banner */}
          {anomaly && (
            <div className={`animate-fade-slide-up delay-100 rounded-xl px-4 py-3 mb-4
                            text-sm flex items-start gap-2 shadow-lg
                            ${anomaly.type === 'critical'
                              ? 'bg-red-900/40 border border-red-600/60 text-red-200 shadow-red-950/30'
                              : 'bg-amber-900/30 border border-amber-600/60 text-amber-200 shadow-amber-950/30'
                            }`}>
              <span className="mt-0.5 shrink-0">{anomaly.type === 'critical' ? '🚨' : '⚠️'}</span>
              <span className="leading-relaxed whitespace-pre-line">{anomaly.message}</span>
              <button
                onClick={() => setAnomaly(null)}
                className="ml-auto shrink-0 opacity-60 hover:opacity-100 transition-opacity text-base"
              >✕</button>
            </div>
          )}

          {/* PM2.5 standard alert banner */}
          {!anomaly && reading.pm25 > PM25_STANDARD_24H && (
            <div className="animate-fade-slide-up delay-150
                            bg-red-900/30 border border-red-700/60 rounded-xl
                            px-4 py-3 mb-4 text-sm text-red-300
                            flex items-center gap-2 shadow-lg shadow-red-950/30">
              <span>🚨</span>
              <span>PM2.5 เกินมาตรฐาน 24 ชั่วโมง ({PM25_STANDARD_24H} µg/m³) — ควรสวมหน้ากาก N95</span>
            </div>
          )}

          {/* Stat cards */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="animate-fade-slide-up delay-150">
              <StatCard icon="🌫️" label="PM2.5"
                value={reading.pm25} unit="µg/m³"
                color={info?.textColor ?? 'text-white'}
                highlight={reading.pm25 > PM25_STANDARD_24H} />
            </div>
            <div className="animate-fade-slide-up delay-225">
              <StatCard icon="🌡️" label="อุณหภูมิ"
                value={reading.temperature} unit="°C"
                color="text-orange-400" />
            </div>
            <div className="animate-fade-slide-up delay-300">
              <StatCard icon="💧" label="ความชื้น"
                value={reading.humidity} unit="%"
                color="text-sky-400" />
            </div>
            <div className="animate-fade-slide-up" style={{ animationDelay: '350ms' }}>
              <StatCard icon="🌀" label="พัดลม"
                value={reading.fan_speed} unit="%"
                color="text-violet-400"
                sub={reading.fan_speed > 0 ? 'กำลังทำงาน' : 'ปิดอยู่'} />
            </div>
          </div>

          {/* Outdoor Card */}
          <OutdoorCard indoorPm25={reading.pm25} />

          {/* Chart */}
          <div className="card animate-fade-slide-up hover:shadow-lg
                          hover:shadow-slate-900/50 transition-all duration-300"
               style={{ animationDelay: '400ms' }}>
            <h2 className="text-sm font-semibold text-slate-300 mb-3">
              PM2.5 — 3 ชั่วโมงล่าสุด
            </h2>
            {history.length > 1 ? (
              <PM25Chart data={history} height={180} />
            ) : (
              <p className="text-slate-500 text-xs text-center py-8">ยังไม่มีข้อมูลประวัติ</p>
            )}
          </div>
        </>
      ) : (
        <div className="card flex flex-col items-center gap-3 py-12 text-slate-500
                        animate-fade-slide-up delay-150">
          <span className="text-4xl animate-float">📡</span>
          <p className="text-sm">ไม่มีข้อมูลจากอุปกรณ์</p>
          <p className="text-xs text-slate-600">รัน mock_sensor.py เพื่อทดสอบ</p>
        </div>
      )}
    </main>
  )
}
