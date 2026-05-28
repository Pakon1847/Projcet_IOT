/**
 * OutdoorCard — แสดง PM2.5 นอกบ้าน + คำแนะนำการระบายอากาศ
 * ใช้ใน DashboardPage
 */

import { useEffect, useState } from 'react'
import { outdoorApi }          from '../api/outdoor'
import type { AdviceResponse } from '../api/outdoor'

// ค่า lat/lon เริ่มต้น (กทม.) — ในอนาคตสามารถอ่านจาก settings ได้
const DEFAULT_LAT = 13.756
const DEFAULT_LON = 100.501

const colorMap: Record<string, string> = {
  emerald: 'border-emerald-500/40 bg-emerald-900/20 text-emerald-300',
  sky:     'border-sky-500/40     bg-sky-900/20     text-sky-300',
  red:     'border-red-500/40     bg-red-900/20     text-red-300',
  slate:   'border-slate-600/40   bg-slate-800/20   text-slate-400',
}

interface Props {
  indoorPm25: number
}

export function OutdoorCard({ indoorPm25 }: Props) {
  const [data,    setData]    = useState<AdviceResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    const fetchAdvice = async () => {
      try {
        const res = await outdoorApi.advice(indoorPm25, DEFAULT_LAT, DEFAULT_LON)
        if (!cancelled) setData(res.data)
      } catch {
        // silently skip if outdoor API unavailable
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchAdvice()
    // รีเฟรชทุก 30 นาที (match server cache TTL)
    const id = setInterval(fetchAdvice, 30 * 60 * 1000)
    return () => { cancelled = true; clearInterval(id) }
  }, [indoorPm25])

  if (loading) {
    return (
      <div className="card animate-pulse">
        <div className="h-4 w-32 bg-slate-700 rounded mb-2" />
        <div className="h-3 w-48 bg-slate-800 rounded" />
      </div>
    )
  }

  if (!data) return null

  const { advice, station, indoor_pm25 } = data
  const cardClass = colorMap[advice.color] ?? colorMap.slate

  return (
    <div className={`card border animate-fade-slide-up ${cardClass}`}
         style={{ animationDelay: '450ms' }}>

      {/* Header row */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xl">{advice.icon}</span>
          <span className="font-semibold text-sm">{advice.title}</span>
        </div>
        <span className="text-xs opacity-60">อากาศนอกบ้าน</span>
      </div>

      {/* Detail */}
      <p className="text-xs opacity-80 mb-3 leading-relaxed">{advice.detail}</p>

      {/* PM2.5 comparison row */}
      {station && (
        <div className="flex gap-3">
          <div className="flex-1 rounded-lg bg-black/20 px-3 py-2 text-center">
            <p className="text-[10px] opacity-60 mb-0.5">ในบ้าน</p>
            <p className="text-lg font-bold">{indoor_pm25.toFixed(1)}</p>
            <p className="text-[10px] opacity-50">µg/m³</p>
          </div>
          <div className="flex items-center text-xl opacity-40">→</div>
          <div className="flex-1 rounded-lg bg-black/20 px-3 py-2 text-center">
            <p className="text-[10px] opacity-60 mb-0.5">นอกบ้าน</p>
            <p className="text-lg font-bold">
              {station.pm25 != null ? station.pm25.toFixed(1) : '—'}
            </p>
            <p className="text-[10px] opacity-50">µg/m³</p>
          </div>
        </div>
      )}

      {/* Station name */}
      {station && (
        <p className="text-[10px] opacity-40 mt-2 text-right truncate">
          📍 {station.name_th || station.name_en}
        </p>
      )}
    </div>
  )
}
