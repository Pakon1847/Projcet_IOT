import { useEffect, useState } from 'react'
import { useStore } from '../store/useStore'
import { useCountUp } from '../hooks/useCountUp'

/* ── types ────────────────────────────────────────────────────────────────── */
interface NodePos { x: number; y: number }
interface NodeDef extends NodePos {
  id: string; icon: string; label: string; sublabel: string
  color: string; value?: string; pulse?: boolean
}
interface ArrowDef {
  x1:number; y1:number; x2:number; y2:number
  color:string; label?:string; animated?:boolean; dur?:number
}
interface DeviceSpec {
  icon: string; name: string; category: string; color: string
  specs: { key: string; val: string }[]
  liveKeys?: string[]   // keys to highlight when live
}

const NW = 92; const NH = 76

const COLORS: Record<string,string> = {
  sky:'#0ea5e9', cyan:'#06b6d4', violet:'#8b5cf6',
  purple:'#a78bfa', amber:'#f59e0b', emerald:'#10b981',
  slate:'#475569', orange:'#f97316', pink:'#ec4899', gray:'#64748b',
}

/* ── device encyclopedia ─────────────────────────────────────────────────── */
const DEVICE_INFO: Record<string, DeviceSpec> = {
  pms: {
    icon:'🌫️', name:'PMS5003', category:'Sensor', color:COLORS.sky,
    specs:[
      { key:'ประเภท',       val:'Laser Particle Counter' },
      { key:'Interface',    val:'UART 9600 baud' },
      { key:'วัดได้',       val:'PM1.0 · PM2.5 · PM10' },
      { key:'Range',        val:'0 – 500 µg/m³' },
      { key:'Response time',val:'< 1 วินาที' },
      { key:'Power',        val:'5 V · ~100 mA' },
      { key:'Protocol',     val:'Passive / Active mode' },
    ],
    liveKeys:['PM2.5 ปัจจุบัน'],
  },
  bme: {
    icon:'🌡️', name:'BME280', category:'Sensor', color:COLORS.cyan,
    specs:[
      { key:'ประเภท',       val:'Environmental Sensor' },
      { key:'Interface',    val:'I2C addr 0x76' },
      { key:'Temp range',   val:'-40 ~ 85 °C (±1°C)' },
      { key:'Humidity',     val:'0 – 100 % RH (±3%)' },
      { key:'Pressure',     val:'300 – 1100 hPa' },
      { key:'Power',        val:'3.3 V · 2 µA sleep' },
    ],
  },
  pi: {
    icon:'🖥️', name:'Raspberry Pi 4 (4 GB)', category:'Compute', color:COLORS.purple,
    specs:[
      { key:'CPU',    val:'BCM2711 · 4× ARM Cortex-A72 @ 1.8 GHz' },
      { key:'RAM',    val:'4 GB LPDDR4-3200' },
      { key:'OS',     val:'Raspberry Pi OS 64-bit (Bookworm)' },
      { key:'Python', val:'3.11 + paho-mqtt + TFLite runtime' },
      { key:'GPIO',   val:'40-pin · PWM fan via pin 12' },
      { key:'I2C',    val:'SDA=2 SCL=3 (BME280 + OLED)' },
      { key:'UART',   val:'GPIO14/15 → PMS5003' },
    ],
  },
  mqtt: {
    icon:'📡', name:'Mosquitto MQTT Broker', category:'Middleware', color:COLORS.violet,
    specs:[
      { key:'Version',   val:'Mosquitto 2.x' },
      { key:'Port',      val:'1883 (MQTT) · 9001 (WS)' },
      { key:'Protocol',  val:'MQTT v3.1.1 / v5' },
      { key:'Topic ส่ง', val:'airguard/{device}/sensor' },
      { key:'Topic รับ', val:'airguard/{device}/fan/set' },
      { key:'QoS',       val:'0 (sensor) · 1 (fan command)' },
      { key:'Retain',    val:'Last-value retain on sensor topic' },
    ],
  },
  oled: {
    icon:'🖵', name:'OLED SSD1306', category:'Display', color:COLORS.slate,
    specs:[
      { key:'Model',      val:'SSD1306' },
      { key:'Size',       val:'0.96" · 128 × 64 pixels' },
      { key:'Interface',  val:'I2C addr 0x3C' },
      { key:'แสดงผล',     val:'AQI · PM2.5 · Temp · Humidity' },
      { key:'Refresh',    val:'ทุก 2 วินาที' },
      { key:'Library',    val:'luma.oled (Python)' },
    ],
  },
  fan: {
    icon:'🌀', name:'DC Fan (IRF520 MOSFET)', category:'Actuator', color:COLORS.amber,
    specs:[
      { key:'Driver',     val:'IRF520 N-channel MOSFET' },
      { key:'Control',    val:'PWM via Raspberry Pi GPIO 12' },
      { key:'Frequency',  val:'1 kHz PWM' },
      { key:'Speed',      val:'0 – 100 % (duty cycle)' },
      { key:'Auto mode',  val:'PM2.5 > 37.5 → speed up' },
      { key:'Logic',      val:'สั่งผ่าน MQTT airguard/fan/set' },
    ],
  },
  be: {
    icon:'⚡', name:'FastAPI Backend', category:'Backend', color:COLORS.emerald,
    specs:[
      { key:'Framework',  val:'FastAPI 0.111 (Python 3.11)' },
      { key:'Port',       val:'8000' },
      { key:'Auth',       val:'JWT Bearer (HS256 · 7d expire)' },
      { key:'WebSocket',  val:'/api/ws/{device_id}' },
      { key:'MQTT',       val:'Subscribe sensor · Publish fan/set' },
      { key:'Routers',    val:'auth · sensor · fan · alert · ai' },
      { key:'DB',         val:'InfluxDB (time-series) + SQLite (meta)' },
    ],
  },
  inf: {
    icon:'📊', name:'InfluxDB', category:'Database', color:COLORS.emerald,
    specs:[
      { key:'Version',    val:'InfluxDB 2.7' },
      { key:'Port',       val:'8086' },
      { key:'Bucket',     val:'airguard (retention 30 วัน)' },
      { key:'Org',        val:'airguard_org' },
      { key:'Measurement',val:'sensor_data' },
      { key:'Fields',     val:'pm25 · temp · humidity · aqi · fan_speed' },
      { key:'Query',      val:'Flux query language' },
    ],
  },
  sq: {
    icon:'🗄️', name:'SQLite', category:'Database', color:COLORS.gray,
    specs:[
      { key:'ไฟล์',       val:'airguard.db' },
      { key:'ORM',        val:'SQLAlchemy 2.x' },
      { key:'ตาราง',      val:'users · alert_rules · devices' },
      { key:'Users',      val:'id · username · email · hashed_password' },
      { key:'Alert rules',val:'threshold · level · notify_channel' },
    ],
  },
  gra: {
    icon:'📈', name:'Grafana', category:'Monitoring', color:COLORS.orange,
    specs:[
      { key:'Version',    val:'Grafana 10.x' },
      { key:'Port',       val:'3001' },
      { key:'DataSource', val:'InfluxDB (Flux)' },
      { key:'Dashboard',  val:'PM2.5 trend · AQI gauge · Fan speed' },
      { key:'Alerts',     val:'Grafana alerting → webhook' },
      { key:'Auth',       val:'admin / airguard (default)' },
    ],
  },
  dash: {
    icon:'💻', name:'React Dashboard (PWA)', category:'Frontend', color:COLORS.sky,
    specs:[
      { key:'Framework',  val:'React 18 + Vite + TypeScript' },
      { key:'UI',         val:'Tailwind CSS + Recharts' },
      { key:'State',      val:'Zustand' },
      { key:'Port',       val:'5173 (dev) · 80 (prod via Nginx)' },
      { key:'Real-time',  val:'WebSocket → live PM2.5/AQI/Fan' },
      { key:'PWA',        val:'Installable · Offline fallback' },
      { key:'หน้า',       val:'Dashboard · History · Fan · Alerts · AI · System' },
    ],
  },
  notif: {
    icon:'🔔', name:'Notification Service', category:'Output', color:COLORS.pink,
    specs:[
      { key:'ช่องทาง',    val:'Line Notify · Telegram Bot' },
      { key:'Trigger',    val:'PM2.5 เกิน threshold' },
      { key:'Payload',    val:'AQI level · PM2.5 value · timestamp' },
      { key:'Cooldown',   val:'5 นาที ต่อ alert' },
      { key:'Config',     val:'ตั้งค่าใน Alert Rules (/alerts)' },
    ],
  },
}

/* ── Device detail panel ─────────────────────────────────────────────────── */
function DevicePanel({
  id, liveReading, onClose,
}: {
  id: string
  liveReading: any
  onClose: () => void
}) {
  const info = DEVICE_INFO[id]
  if (!info) return null

  // extra live rows
  const liveRows: { key: string; val: string }[] = []
  if (liveReading) {
    if (id === 'pms')  liveRows.push({ key:'PM2.5 ปัจจุบัน',   val:`${liveReading.pm25.toFixed(1)} µg/m³` })
    if (id === 'bme')  liveRows.push(
      { key:'Temp ปัจจุบัน',    val:`${liveReading.temperature.toFixed(1)} °C` },
      { key:'Humidity ปัจจุบัน',val:`${liveReading.humidity.toFixed(0)} %` },
    )
    if (id === 'pi')   liveRows.push({ key:'AQI ปัจจุบัน', val:`${liveReading.aqi}` })
    if (id === 'fan')  liveRows.push({ key:'Speed ปัจจุบัน', val:`${liveReading.fan_speed} %` })
    if (id === 'be')   liveRows.push({ key:'Status', val:'🟢 Running' })
    if (id === 'dash') liveRows.push({ key:'Status', val:'🟢 Connected (WebSocket)' })
  }

  return (
    /* backdrop */
    <div
      className="fixed inset-0 z-50 flex items-end md:items-center justify-center
                 bg-black/60 backdrop-blur-sm px-4 pb-4 md:pb-0"
      onClick={onClose}
    >
      {/* panel */}
      <div
        className="w-full max-w-md bg-[#0f172a] rounded-2xl border border-slate-700/80
                   shadow-2xl overflow-hidden animate-fade-slide-up"
        style={{ boxShadow: `0 0 40px ${info.color}22` }}
        onClick={e => e.stopPropagation()}
      >
        {/* header */}
        <div className="relative px-5 pt-5 pb-4"
             style={{ background: `linear-gradient(135deg, ${info.color}18 0%, transparent 60%)` }}>
          <div className="flex items-start gap-3">
            <div className="text-4xl mt-0.5">{info.icon}</div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium uppercase tracking-wider mb-0.5"
                   style={{ color: info.color }}>
                {info.category}
              </div>
              <h2 className="text-base font-bold text-white leading-tight">{info.name}</h2>
            </div>
            <button
              onClick={onClose}
              className="w-7 h-7 flex items-center justify-center rounded-lg
                         bg-slate-800 text-slate-400 hover:bg-slate-700
                         hover:text-slate-200 transition-all duration-150 text-sm flex-shrink-0"
            >✕</button>
          </div>
          {/* colour bar */}
          <div className="absolute bottom-0 left-0 right-0 h-px"
               style={{ background: `linear-gradient(90deg, ${info.color}60, transparent)` }}/>
        </div>

        {/* spec table */}
        <div className="px-5 pb-5 max-h-72 overflow-y-auto space-y-1.5 mt-2">
          {info.specs.map(({ key, val }) => (
            <div key={key} className="flex items-start gap-3 text-sm">
              <span className="text-slate-500 shrink-0 w-28 text-xs pt-0.5">{key}</span>
              <span className="text-slate-200 text-xs font-medium leading-relaxed">{val}</span>
            </div>
          ))}

          {/* live data */}
          {liveRows.length > 0 && (
            <>
              <div className="flex items-center gap-2 mt-3 mb-1">
                <div className="h-px flex-1 bg-slate-800"/>
                <span className="text-xs text-emerald-500 font-medium flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse inline-block"/>
                  Live
                </span>
                <div className="h-px flex-1 bg-slate-800"/>
              </div>
              {liveRows.map(({ key, val }) => (
                <div key={key} className="flex items-start gap-3 text-sm">
                  <span className="text-slate-500 shrink-0 w-28 text-xs pt-0.5">{key}</span>
                  <span className="text-xs font-bold leading-relaxed"
                        style={{ color: info.color }}>{val}</span>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

/* ── FlowNode (clickable) ───────────────────────────────────────────────── */
function FlowNode({ x, y, id, icon, label, sublabel, color, value, pulse, onSelect }: NodeDef & { onSelect:(id:string)=>void }) {
  return (
    <g transform={`translate(${x},${y})`}
       style={{ cursor:'pointer' }}
       onClick={() => onSelect(id)}>
      {/* hover area (bigger hit target) */}
      <rect x={-4} y={-4} width={NW+8} height={NH+8} rx={18} fill="transparent"/>

      {/* animated halo */}
      {pulse && (
        <rect x={-6} y={-6} width={NW+12} height={NH+12} rx={20}
          fill="none" stroke={color} strokeWidth={1.5} opacity={0.25}>
          <animate attributeName="opacity" values="0.25;0.55;0.25" dur="1.8s" repeatCount="indefinite"/>
          <animate attributeName="x"      values="-6;-9;-6"        dur="1.8s" repeatCount="indefinite"/>
          <animate attributeName="y"      values="-6;-9;-6"        dur="1.8s" repeatCount="indefinite"/>
          <animate attributeName="width"  values={`${NW+12};${NW+18};${NW+12}`} dur="1.8s" repeatCount="indefinite"/>
          <animate attributeName="height" values={`${NH+12};${NH+18};${NH+12}`} dur="1.8s" repeatCount="indefinite"/>
        </rect>
      )}

      <defs>
        <linearGradient id={`bg-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor={color} stopOpacity="0.18"/>
          <stop offset="100%" stopColor={color} stopOpacity="0.04"/>
        </linearGradient>
        <filter id={`gf-${id}`} x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="5" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>

      <g style={pulse ? { filter:`url(#gf-${id})` } : undefined}>
        <rect width={NW} height={NH} rx={16}
          fill={`url(#bg-${id})`}
          stroke={color} strokeWidth={pulse ? 1.8 : 1.2}
          strokeOpacity={pulse ? 0.9 : 0.5}/>
        <rect width={NW} height={3} rx={3} fill={color} opacity={0.9}/>
        <text x={NW/2} y={32} textAnchor="middle" fontSize={22}>{icon}</text>
        <text x={NW/2} y={50} textAnchor="middle" fontSize={10}
          fontWeight="700" fill="#f1f5f9">{label}</text>
        <text x={NW/2} y={65} textAnchor="middle" fontSize={8.5}
          fill={value ? color : '#64748b'} fontWeight={value ? '600' : '400'}>
          {value ?? sublabel}
        </text>
      </g>

      {/* click hint dot */}
      <circle cx={NW-8} cy={8} r={4} fill={color} opacity={0.55}>
        <animate attributeName="opacity" values="0.55;0.9;0.55" dur="2.5s" repeatCount="indefinite"/>
      </circle>
    </g>
  )
}

/* ── Arrow ──────────────────────────────────────────────────────────────── */
function Arrow({ x1, y1, x2, y2, color, label, animated, dur=2 }: ArrowDef) {
  const mx=(x1+x2)/2; const my=(y1+y2)/2
  const id=`arr-${x1}-${y1}-${x2}-${y2}`.replace(/\./g,'')
  const path=`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`
  return (
    <g>
      <defs>
        <marker id={`hd-${id}`} markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
          <polygon points="0,0 7,3.5 0,7" fill={color} opacity={0.7}/>
        </marker>
      </defs>
      <path d={path} fill="none" stroke={color} strokeWidth={3} strokeOpacity={0.07} strokeLinecap="round"/>
      <path d={path} fill="none" stroke={color} strokeWidth={1.5}
        strokeOpacity={animated ? 0.5 : 0.2} strokeDasharray={animated ? 'none' : '5 4'}
        strokeLinecap="round" markerEnd={`url(#hd-${id})`}/>
      {animated && (<>
        <circle r={3.5} fill={color} opacity={0.95}>
          <animateMotion dur={`${dur}s`} repeatCount="indefinite" path={path}/>
        </circle>
        <circle r={2.5} fill={color} opacity={0.6}>
          <animateMotion dur={`${dur}s`} begin={`${dur*0.45}s`} repeatCount="indefinite" path={path}/>
        </circle>
      </>)}
      {label && (
        <text x={mx} y={my-7} textAnchor="middle" fontSize={8}
          fill={color} opacity={0.8} fontWeight="600">{label}</text>
      )}
    </g>
  )
}

/* ── Live stat card ─────────────────────────────────────────────────────── */
function LiveCard({ icon, label, value, unit, color }: {
  icon:string; label:string; value:number; unit:string; color:string
}) {
  const dec = value%1!==0?1:0
  const d   = useCountUp(value, 700, dec)
  return (
    <div className="card card-hover text-center py-3 border-slate-700/50
                    hover:border-slate-600/60 transition-all duration-300">
      <div className="text-xl mb-1">{icon}</div>
      <div className={`text-lg font-bold tabular-nums ${color}`}>
        {dec>0?d.toFixed(1):d}
        <span className="text-xs font-normal text-slate-400 ml-1">{unit}</span>
      </div>
      <div className="text-xs text-slate-500 mt-0.5">{label}</div>
    </div>
  )
}

/* ── Page ────────────────────────────────────────────────────────────────── */
export function SystemFlowPage() {
  const liveReading  = useStore((s) => s.liveReading)
  const [,setTick]   = useState(0)
  const [selected, setSelected] = useState<string|null>(null)

  useEffect(() => {
    const id = setInterval(()=>setTick(t=>t+1), 3000)
    return ()=>clearInterval(id)
  },[])

  // close on Escape
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key==='Escape') setSelected(null) }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  },[])

  const pm25  = liveReading?.pm25           ?? 0
  const temp  = liveReading?.temperature    ?? 0
  const hum   = liveReading?.humidity       ?? 0
  const aqi   = liveReading?.aqi            ?? 0
  const fanS  = liveReading?.fan_speed      ?? 0
  const isLive= !!liveReading

  const pm25s = liveReading ? `${pm25.toFixed(1)} µg/m³` : undefined
  const bmes  = liveReading ? `${temp.toFixed(1)}°C ${hum.toFixed(0)}%` : undefined
  const aqis  = liveReading ? `AQI ${aqi}` : undefined
  const fans  = liveReading ? `${fanS}%` : undefined

  const PMS  ={x:40, y:55};  const BME  ={x:40, y:180}
  const PI   ={x:215,y:115}; const MQTT ={x:385,y:35}
  const OLED ={x:215,y:278}; const FAN  ={x:215,y:388}
  const BE   ={x:535,y:115}; const INF  ={x:705,y:35}
  const SQ   ={x:705,y:158}; const GRA  ={x:705,y:278}
  const DASH ={x:705,y:390}; const NOTIF={x:705,y:492}
  const cx=(n:NodePos)=>n.x+NW/2; const cy=(n:NodePos)=>n.y+NH/2

  const sel = (id:string) => setSelected(id)

  const legend=[
    {c:COLORS.sky,    l:'Sensor data'},
    {c:COLORS.violet, l:'MQTT'},
    {c:COLORS.emerald,l:'Storage'},
    {c:COLORS.amber,  l:'Fan control'},
    {c:COLORS.pink,   l:'Notification'},
  ]

  return (
    <main className="page pt-16 pb-28 md:pb-10">
      {/* header */}
      <div className="flex items-center justify-between mb-4 animate-fade-slide-up">
        <div>
          <h1 className="text-lg font-bold bg-gradient-to-r from-sky-400 to-violet-400
                         bg-clip-text text-transparent">System Flow</h1>
          <p className="text-xs text-slate-500">คลิกที่อุปกรณ์เพื่อดูรายละเอียด</p>
        </div>
        <div className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border
                         transition-all duration-300 ${
          isLive
            ? 'bg-emerald-900/30 border-emerald-700/50 text-emerald-400'
            : 'bg-slate-800/50  border-slate-700/50  text-slate-500'
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${isLive?'bg-emerald-400 animate-pulse':'bg-slate-600'}`}/>
          {isLive ? 'Live data' : 'No data'}
        </div>
      </div>

      {/* SVG diagram */}
      <div className="card overflow-x-auto animate-fade-slide-up delay-75
                      hover:shadow-xl hover:shadow-sky-950/30 transition-all duration-300
                      p-3 border-slate-700/60">
        <svg viewBox="0 0 820 595" width="100%" style={{minWidth:580}}>
          <defs>
            <pattern id="grid" x="0" y="0" width="30" height="30" patternUnits="userSpaceOnUse">
              <circle cx="15" cy="15" r="1" fill="#1e293b"/>
            </pattern>
          </defs>
          <rect width="820" height="595" fill="url(#grid)" opacity={0.6}/>

          {/* arrows */}
          <Arrow x1={PMS.x+NW}  y1={cy(PMS)}     x2={PI.x}        y2={PI.y+28}      color={COLORS.sky}    label="UART"      animated={isLive} dur={1.8}/>
          <Arrow x1={BME.x+NW}  y1={cy(BME)}      x2={PI.x}        y2={PI.y+48}      color={COLORS.cyan}   label="I2C"       animated={isLive} dur={2.1}/>
          <Arrow x1={PI.x+NW}   y1={PI.y+22}      x2={MQTT.x}      y2={cy(MQTT)}     color={COLORS.violet} label="publish"   animated={isLive} dur={1.6}/>
          <Arrow x1={cx(PI)}    y1={PI.y+NH}      x2={cx(OLED)}    y2={OLED.y}       color={COLORS.slate}  label="I2C"       animated={false}/>
          <Arrow x1={MQTT.x+NW} y1={cy(MQTT)}     x2={BE.x}        y2={BE.y+20}      color={COLORS.violet} label="subscribe" animated={isLive} dur={1.5}/>
          <Arrow x1={BE.x}      y1={BE.y+50}      x2={MQTT.x+NW}   y2={cy(MQTT)-12}  color={COLORS.amber}  label="fan/set"   animated={false}/>
          <Arrow x1={MQTT.x}    y1={cy(MQTT)+12}  x2={PI.x+NW}     y2={PI.y+56}      color={COLORS.amber}                    animated={false}/>
          <Arrow x1={cx(PI)}    y1={PI.y+NH}      x2={cx(FAN)}     y2={FAN.y}        color={COLORS.amber}  label="PWM"       animated={false}/>
          <Arrow x1={BE.x+NW}   y1={BE.y+18}      x2={INF.x}       y2={cy(INF)}      color={COLORS.emerald}label="write"     animated={isLive} dur={1.7}/>
          <Arrow x1={BE.x+NW}   y1={BE.y+40}      x2={SQ.x}        y2={cy(SQ)}       color={COLORS.gray}   label="ORM"       animated={false}/>
          <Arrow x1={BE.x+NW}   y1={BE.y+56}      x2={DASH.x}      y2={cy(DASH)}     color={COLORS.sky}    label="WS"        animated={isLive} dur={1.4}/>
          <Arrow x1={cx(INF)}   y1={INF.y+NH}     x2={cx(GRA)}     y2={GRA.y}        color={COLORS.orange} label="query"     animated={false}/>
          <Arrow x1={BE.x+NW}   y1={BE.y+66}      x2={NOTIF.x}     y2={cy(NOTIF)}    color={COLORS.pink}   label="alert"     animated={false}/>

          {/* nodes */}
          <FlowNode {...PMS}  id="pms"  icon="🌫️" label="PMS5003"    sublabel="PM2.5 Sensor"   color={COLORS.sky}    value={pm25s} pulse={isLive} onSelect={sel}/>
          <FlowNode {...BME}  id="bme"  icon="🌡️" label="BME280"     sublabel="Temp/Hum/Press" color={COLORS.cyan}   value={bmes}  pulse={isLive} onSelect={sel}/>
          <FlowNode {...PI}   id="pi"   icon="🖥️" label="Pi 4 (4GB)" sublabel="Controller"     color={COLORS.purple} value={aqis}  pulse={isLive} onSelect={sel}/>
          <FlowNode {...MQTT} id="mqtt" icon="📡" label="Mosquitto"   sublabel="MQTT Broker"    color={COLORS.violet} value="1883"               onSelect={sel}/>
          <FlowNode {...OLED} id="oled" icon="🖵" label="OLED"        sublabel="SSD1306 128×64" color={COLORS.slate}                             onSelect={sel}/>
          <FlowNode {...FAN}  id="fan"  icon="🌀" label="DC Fan"      sublabel="IRF520 MOSFET"  color={COLORS.amber}  value={fans}  pulse={isLive} onSelect={sel}/>
          <FlowNode {...BE}   id="be"   icon="⚡" label="FastAPI"     sublabel="Backend :8000"  color={COLORS.emerald}value="port 8000" pulse={isLive} onSelect={sel}/>
          <FlowNode {...INF}  id="inf"  icon="📊" label="InfluxDB"    sublabel="Time-series DB" color={COLORS.emerald}value="port 8086"           onSelect={sel}/>
          <FlowNode {...SQ}   id="sq"   icon="🗄️" label="SQLite"     sublabel="Users/Rules"    color={COLORS.gray}                              onSelect={sel}/>
          <FlowNode {...GRA}  id="gra"  icon="📈" label="Grafana"     sublabel="Monitoring"     color={COLORS.orange} value="port 3001"           onSelect={sel}/>
          <FlowNode {...DASH} id="dash" icon="💻" label="Dashboard"   sublabel="React + PWA"    color={COLORS.sky}    value="port 5173" pulse={isLive} onSelect={sel}/>
          <FlowNode {...NOTIF}id="notif"icon="🔔" label="แจ้งเตือน"   sublabel="Line/Telegram"  color={COLORS.pink}                              onSelect={sel}/>

          {/* legend */}
          <g transform="translate(18,556)">
            {legend.map((l,i)=>(
              <g key={l.l} transform={`translate(${i*145},0)`}>
                <rect x={0} y={0} width={18} height={8} rx={4} fill={l.c} opacity={0.85}/>
                <text x={24} y={8} fontSize={9} fill="#94a3b8" fontWeight="500">{l.l}</text>
              </g>
            ))}
          </g>
        </svg>
      </div>

      {/* live stats */}
      {isLive && (
        <div className="grid grid-cols-4 gap-2 mt-4 animate-fade-slide-up delay-150">
          <LiveCard icon="🌫️" label="PM2.5"    value={pm25} unit="µg/m³" color="text-sky-400"/>
          <LiveCard icon="🌡️" label="Temp"     value={temp} unit="°C"    color="text-orange-400"/>
          <LiveCard icon="💧" label="Humidity" value={hum}  unit="%"     color="text-cyan-400"/>
          <LiveCard icon="🌀" label="Fan"      value={fanS} unit="%"     color="text-violet-400"/>
        </div>
      )}

      {/* device detail panel */}
      {selected && (
        <DevicePanel
          id={selected}
          liveReading={liveReading}
          onClose={() => setSelected(null)}
        />
      )}
    </main>
  )
}
