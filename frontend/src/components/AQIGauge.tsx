import { getAQIInfo } from '../lib/aqi'

interface Props {
  aqi:   number
  pm25:  number
  size?: number   // SVG diameter px
}

export function AQIGauge({ aqi, pm25, size = 220 }: Props) {
  const info = getAQIInfo(aqi)
  const cx = size / 2
  const cy = size / 2
  const r  = size * 0.38
  const stroke = size * 0.09

  // Arc: 135° → 405° (270° total sweep), value maps aqi 0→500
  const startAngle = 135
  const sweep      = 270
  const pct        = Math.min(aqi / 500, 1)
  const endDeg     = startAngle + sweep * pct

  const toRad = (d: number) => (d * Math.PI) / 180
  const arcX  = (deg: number) => cx + r * Math.cos(toRad(deg))
  const arcY  = (deg: number) => cy + r * Math.sin(toRad(deg))

  // Background arc path
  const bgPath = describeArc(cx, cy, r, startAngle, startAngle + sweep)
  // Value arc path
  const valPath = pct > 0 ? describeArc(cx, cy, r, startAngle, endDeg) : ''

  // Tick marks for AQI levels: 25, 50, 100, 200, 500
  const ticks = [25, 50, 100, 200, 500].map((v) => ({
    deg: startAngle + (v / 500) * sweep,
    label: v.toString(),
  }))

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Background track */}
        <path d={bgPath} fill="none" stroke="#1e293b" strokeWidth={stroke} strokeLinecap="round" />

        {/* Coloured value arc */}
        {valPath && (
          <path
            d={valPath}
            fill="none"
            stroke={info.ring}
            strokeWidth={stroke}
            strokeLinecap="round"
            style={{ filter: `drop-shadow(0 0 ${size * 0.04}px ${info.ring}88)` }}
          />
        )}

        {/* Tick marks */}
        {ticks.map((t) => {
          const inner = r - stroke * 0.6
          const outer = r + stroke * 0.6
          return (
            <line
              key={t.label}
              x1={cx + inner * Math.cos(toRad(t.deg))}
              y1={cy + inner * Math.sin(toRad(t.deg))}
              x2={cx + outer * Math.cos(toRad(t.deg))}
              y2={cy + outer * Math.sin(toRad(t.deg))}
              stroke="#475569"
              strokeWidth={1.5}
            />
          )
        })}

        {/* Center content */}
        <text x={cx} y={cy - size * 0.08} textAnchor="middle" fill={info.ring} fontSize={size * 0.2} fontWeight="700">
          {aqi}
        </text>
        <text x={cx} y={cy + size * 0.04} textAnchor="middle" fill="#94a3b8" fontSize={size * 0.065}>
          AQI
        </text>
        <text x={cx} y={cy + size * 0.14} textAnchor="middle" fill="#cbd5e1" fontSize={size * 0.075} fontWeight="600">
          {info.level}
        </text>
        <text x={cx} y={cy + size * 0.23} textAnchor="middle" fill="#64748b" fontSize={size * 0.055}>
          PM2.5: {pm25.toFixed(1)} µg/m³
        </text>

        {/* Emoji indicator */}
        <text x={cx} y={cy + size * 0.36} textAnchor="middle" fontSize={size * 0.1}>
          {info.emoji}
        </text>
      </svg>

      {/* Legend */}
      <div className="flex gap-2 flex-wrap justify-center text-xs">
        {[
          { label: 'ดีมาก',              color: '#00b050', range: '0–25'   },
          { label: 'ดี',                 color: '#92d050', range: '26–50'  },
          { label: 'ปานกลาง',            color: '#ffcc00', range: '51–100' },
          { label: 'เริ่มมีผล',           color: '#ff9900', range: '101–200'},
          { label: 'มีผลต่อสุขภาพ',       color: '#ff0000', range: '201+'  },
        ].map((l) => (
          <span key={l.label} className="flex items-center gap-1 text-slate-400">
            <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: l.color }} />
            {l.label}
          </span>
        ))}
      </div>
    </div>
  )
}

// ── SVG arc helpers ──────────────────────────────────────────────────────────
function describeArc(cx: number, cy: number, r: number, startDeg: number, endDeg: number) {
  const toRad  = (d: number) => (d * Math.PI) / 180
  const start  = { x: cx + r * Math.cos(toRad(startDeg)), y: cy + r * Math.sin(toRad(startDeg)) }
  const end    = { x: cx + r * Math.cos(toRad(endDeg)),   y: cy + r * Math.sin(toRad(endDeg))   }
  const largeArc = endDeg - startDeg > 180 ? 1 : 0
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`
}
