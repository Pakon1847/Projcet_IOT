import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, Legend,
} from 'recharts'
import { format, parseISO } from 'date-fns'
import { th } from 'date-fns/locale'
import type { SensorReading } from '../api/sensor'
import { PM25_STANDARD_24H } from '../lib/aqi'

interface Props {
  data:     SensorReading[]
  height?:  number
  showAQI?: boolean
}

// Custom tooltip
const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-navy-800 border border-slate-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ color: p.color }} className="font-semibold">
          {p.name}: {typeof p.value === 'number' ? p.value.toFixed(1) : p.value}
          {p.dataKey === 'pm25' ? ' µg/m³' : p.dataKey === 'aqi' ? '' : ''}
        </p>
      ))}
    </div>
  )
}

export function PM25Chart({ data, height = 260, showAQI = false }: Props) {
  const chartData = data.map((r) => ({
    time:  format(parseISO(r.timestamp), 'HH:mm', { locale: th }),
    pm25:  +r.pm25.toFixed(1),
    aqi:   r.aqi,
    temp:  +r.temperature.toFixed(1),
    hum:   +r.humidity.toFixed(1),
  }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="pm25Grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#0ea5e9" stopOpacity={0.4} />
            <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0}   />
          </linearGradient>
          {showAQI && (
            <linearGradient id="aqiGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#f59e0b" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}   />
            </linearGradient>
          )}
        </defs>

        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis
          dataKey="time"
          tick={{ fill: '#64748b', fontSize: 11 }}
          interval="preserveStartEnd"
          tickLine={false}
          axisLine={{ stroke: '#334155' }}
        />
        <YAxis
          tick={{ fill: '#64748b', fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          domain={['auto', 'auto']}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 12, color: '#94a3b8', paddingTop: 8 }}
        />

        {/* มาตรฐาน 24 ชั่วโมง (37.5 µg/m³) */}
        <ReferenceLine
          y={PM25_STANDARD_24H}
          stroke="#f97316"
          strokeDasharray="4 2"
          label={{ value: 'มาตรฐาน 37.5', position: 'insideTopRight', fill: '#f97316', fontSize: 10 }}
        />

        <Area
          type="monotone"
          dataKey="pm25"
          name="PM2.5 (µg/m³)"
          stroke="#0ea5e9"
          strokeWidth={2}
          fill="url(#pm25Grad)"
          dot={false}
          activeDot={{ r: 4, fill: '#0ea5e9' }}
        />

        {showAQI && (
          <Area
            type="monotone"
            dataKey="aqi"
            name="AQI"
            stroke="#f59e0b"
            strokeWidth={2}
            fill="url(#aqiGrad)"
            dot={false}
            activeDot={{ r: 4, fill: '#f59e0b' }}
          />
        )}
      </AreaChart>
    </ResponsiveContainer>
  )
}
