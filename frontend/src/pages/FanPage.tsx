import { useEffect, useState } from 'react'
import { useStore }            from '../store/useStore'
import { useWebSocket }        from '../hooks/useWebSocket'
import { FanControl }          from '../components/FanControl'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts'
import { sensorApi }      from '../api/sensor'
import type { SensorReading } from '../api/sensor'
import { format, parseISO }   from 'date-fns'

export function FanPage() {
  const deviceId    = useStore((s) => s.deviceId)
  const liveReading = useStore((s) => s.liveReading)
  const [history, setHistory] = useState<SensorReading[]>([])

  useWebSocket(deviceId)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await sensorApi.history(deviceId, 3)
        setHistory((res.data as any).data ?? res.data)
      } catch { /* ignore */ }
    }
    load()
    const id = setInterval(load, 30_000)
    return () => clearInterval(id)
  }, [deviceId])

  const currentSpeed = liveReading?.fan_speed ?? 0
  const currentMode  = 'auto'   // TODO: persist mode from backend

  const chartData = history.map((r) => ({
    time:  format(parseISO(r.timestamp), 'HH:mm'),
    speed: r.fan_speed,
    pm25:  +r.pm25.toFixed(1),
  }))

  return (
    <main className="page pt-16 pb-28 md:pb-10">
      <h1 className="text-lg font-bold mb-4">ควบคุมพัดลม</h1>

      {/* Fan control widget */}
      <div className="card mb-4">
        <FanControl
          deviceId={deviceId}
          currentSpeed={currentSpeed}
          currentMode={currentMode}
          onUpdated={() => {}}
        />
      </div>

      {/* Info cards */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="card text-center">
          <div className="text-2xl font-bold text-violet-400">{currentSpeed}%</div>
          <div className="text-xs text-slate-500 mt-1">ความเร็วปัจจุบัน</div>
        </div>
        <div className="card text-center">
          <div className="text-2xl font-bold text-sky-400">
            {liveReading?.pm25.toFixed(1) ?? '—'}
          </div>
          <div className="text-xs text-slate-500 mt-1">PM2.5 µg/m³</div>
        </div>
      </div>

      {/* Speed history chart */}
      {chartData.length > 1 && (
        <div className="card">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">ความเร็วพัดลม vs PM2.5 (3h)</h2>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis
                dataKey="time"
                tick={{ fill: '#64748b', fontSize: 10 }}
                tickLine={false}
                axisLine={{ stroke: '#334155' }}
                interval="preserveStartEnd"
              />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: '#94a3b8' }}
              />
              <Line type="monotone" dataKey="speed" name="ความเร็ว (%)" stroke="#a78bfa" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="pm25"  name="PM2.5"        stroke="#0ea5e9" strokeWidth={2} dot={false} strokeDasharray="4 2" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Tips */}
      <div className="mt-4 card text-xs text-slate-500 space-y-1.5">
        <p className="font-semibold text-slate-400">💡 เกี่ยวกับ Auto Mode</p>
        <p>• PM2.5 ≤ 15 µg/m³ → พัดลม 0% (ปิด)</p>
        <p>• PM2.5 15–37.5 µg/m³ → พัดลม 20–60%</p>
        <p>• PM2.5 37.5–75 µg/m³ → พัดลม 60–90%</p>
        <p>• PM2.5 &gt; 75 µg/m³ → พัดลม 100% (สูงสุด)</p>
        <p className="text-slate-600">ความเร็วต่ำสุดที่พัดลมจะหมุนได้: 20%</p>
      </div>
    </main>
  )
}
