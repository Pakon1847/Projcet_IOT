import { useEffect, useState } from 'react'
import { useStore }            from '../store/useStore'
import { sensorApi }           from '../api/sensor'
import { PM25Chart }           from '../components/PM25Chart'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from 'recharts'
import type { SensorReading, DailyAvg } from '../api/sensor'
import { PM25_STANDARD_24H }  from '../lib/aqi'

const RANGE_OPTIONS = [
  { label: '3h',  hours: 3   },
  { label: '6h',  hours: 6   },
  { label: '24h', hours: 24  },
  { label: '48h', hours: 48  },
  { label: '7d',  hours: 168 },
]

export function HistoryPage() {
  const deviceId = useStore((s) => s.deviceId)
  const [hours,   setHours]   = useState(24)
  const [history, setHistory] = useState<SensorReading[]>([])
  const [daily,   setDaily]   = useState<DailyAvg[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [h, d] = await Promise.all([
          sensorApi.history(deviceId, hours),
          sensorApi.dailyAvg(deviceId, 14),
        ])
        setHistory((h.data as any).data ?? h.data)
        setDaily((d.data as any).data ?? d.data)
      } catch { /* ignore */ }
      finally { setLoading(false) }
    }
    load()
  }, [deviceId, hours])

  // Stats summary
  const pm25Values = history.map((r) => r.pm25)
  const avg   = pm25Values.length ? pm25Values.reduce((a, b) => a + b, 0) / pm25Values.length : 0
  const max   = pm25Values.length ? Math.max(...pm25Values) : 0
  const min   = pm25Values.length ? Math.min(...pm25Values) : 0
  const exceed = pm25Values.filter((v) => v > PM25_STANDARD_24H).length
  const exceedPct = pm25Values.length ? Math.round((exceed / pm25Values.length) * 100) : 0

  return (
    <main className="page pt-16 pb-28 md:pb-10">
      <h1 className="text-lg font-bold mb-4">ประวัติข้อมูล</h1>

      {/* Range selector */}
      <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
        {RANGE_OPTIONS.map((o) => (
          <button
            key={o.hours}
            onClick={() => setHours(o.hours)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition ${
              hours === o.hours
                ? 'bg-sky-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-slate-500 text-sm text-center py-12 animate-pulse">กำลังโหลด...</div>
      ) : (
        <>
          {/* Summary stats */}
          <div className="grid grid-cols-4 gap-2 mb-4">
            {[
              { label: 'ค่าเฉลี่ย', value: avg.toFixed(1),  color: 'text-sky-400' },
              { label: 'สูงสุด',   value: max.toFixed(1),  color: 'text-red-400'  },
              { label: 'ต่ำสุด',   value: min.toFixed(1),  color: 'text-green-400'},
              { label: 'เกินมาตรฐาน', value: `${exceedPct}%`, color: exceedPct > 0 ? 'text-orange-400' : 'text-slate-400' },
            ].map((s) => (
              <div key={s.label} className="card text-center py-3">
                <div className={`text-lg font-bold ${s.color}`}>{s.value}</div>
                <div className="text-xs text-slate-500 mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>

          {/* Area chart */}
          <div className="card mb-4">
            <h2 className="text-sm font-semibold text-slate-300 mb-3">PM2.5 (µg/m³)</h2>
            {history.length > 1 ? (
              <PM25Chart data={history} height={220} showAQI />
            ) : (
              <p className="text-slate-500 text-xs text-center py-8">ไม่มีข้อมูลในช่วงนี้</p>
            )}
          </div>

          {/* Daily avg bar chart */}
          {daily.length > 0 && (
            <div className="card">
              <h2 className="text-sm font-semibold text-slate-300 mb-3">ค่าเฉลี่ยรายวัน — 14 วัน</h2>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={daily} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: '#64748b', fontSize: 10 }}
                    tickLine={false}
                    axisLine={{ stroke: '#334155' }}
                  />
                  <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
                    labelStyle={{ color: '#94a3b8' }}
                  />
                  <ReferenceLine y={PM25_STANDARD_24H} stroke="#f97316" strokeDasharray="4 2" />
                  <Bar dataKey="pm25" name="PM2.5" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </main>
  )
}
