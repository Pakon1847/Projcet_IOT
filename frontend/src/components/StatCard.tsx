import { useCountUp } from '../hooks/useCountUp'

interface Props {
  icon:       string
  label:      string
  value:      string | number
  unit?:      string
  sub?:       string
  color?:     string
  highlight?: boolean
}

// extract glow color from tailwind text class
function glowColor(color: string) {
  if (color.includes('sky'))    return 'hover:shadow-sky-500/20'
  if (color.includes('orange')) return 'hover:shadow-orange-500/20'
  if (color.includes('cyan'))   return 'hover:shadow-cyan-500/20'
  if (color.includes('violet')) return 'hover:shadow-violet-500/20'
  if (color.includes('emerald'))return 'hover:shadow-emerald-500/20'
  if (color.includes('red'))    return 'hover:shadow-red-500/20'
  return 'hover:shadow-slate-500/20'
}

function AnimatedNumber({ value, color }: { value: number; color: string }) {
  const decimals = value % 1 !== 0 ? 1 : 0
  const display  = useCountUp(value, 700, decimals)
  return (
    <span className={`text-2xl font-bold ${color} tabular-nums`}>
      {decimals > 0 ? display.toFixed(1) : display}
    </span>
  )
}

export function StatCard({ icon, label, value, unit, sub, color = 'text-white', highlight }: Props) {
  const isNumber = typeof value === 'number'
  const glow     = highlight ? 'hover:shadow-red-500/30' : glowColor(color)

  return (
    <div
      className={`
        bg-[#1e293b] rounded-2xl p-4 flex flex-col gap-1
        border transition-all duration-300 ease-out
        hover:-translate-y-0.5 hover:shadow-lg
        ${glow}
        ${highlight
          ? 'border-red-600/60 shadow-red-900/40 shadow-lg'
          : 'border-slate-700/50 hover:border-slate-600/70'}
      `}
    >
      <div className="flex items-center gap-2 text-slate-400 text-xs">
        <span>{icon}</span>
        <span>{label}</span>
      </div>

      <div className="flex items-baseline gap-1">
        {isNumber
          ? <AnimatedNumber value={value as number} color={color} />
          : <span className={`text-2xl font-bold ${color} tabular-nums`}>{value}</span>
        }
        {unit && <span className="text-sm font-normal text-slate-400">{unit}</span>}
      </div>

      {sub && <div className="text-xs text-slate-500">{sub}</div>}
    </div>
  )
}
