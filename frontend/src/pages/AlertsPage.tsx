import { useEffect, useState, FormEvent } from 'react'
import { useStore }   from '../store/useStore'
import { alertApi }   from '../api/alert'
import type { AlertRule, AlertLog } from '../api/alert'
import { format, parseISO } from 'date-fns'

const METRICS   = ['pm25', 'aqi', 'temperature', 'humidity']
const OPERATORS = [
  { value: 'gt',  label: '> มากกว่า'      },
  { value: 'gte', label: '≥ มากกว่าหรือเท่า'},
  { value: 'lt',  label: '< น้อยกว่า'     },
  { value: 'lte', label: '≤ น้อยกว่าหรือเท่า'},
]
const CHANNELS = ['line', 'telegram']

export function AlertsPage() {
  const deviceId = useStore((s) => s.deviceId)
  const [rules,   setRules]   = useState<AlertRule[]>([])
  const [logs,    setLogs]    = useState<AlertLog[]>([])
  const [tab,     setTab]     = useState<'rules' | 'logs'>('rules')
  const [loading, setLoading] = useState(true)

  // New rule form
  const [metric,      setMetric]      = useState('pm25')
  const [operator,    setOperator]    = useState('gt')
  const [threshold,   setThreshold]   = useState('37.5')
  const [channel,     setChannel]     = useState('line')
  const [cooldown,    setCooldown]    = useState('60')
  const [saving,      setSaving]      = useState(false)
  const [formError,   setFormError]   = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const [r, l] = await Promise.all([
        alertApi.listRules(),
        alertApi.logs(deviceId),
      ])
      setRules(r.data)
      setLogs(l.data)
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [deviceId])

  const createRule = async (e: FormEvent) => {
    e.preventDefault()
    setFormError('')
    setSaving(true)
    try {
      await alertApi.createRule({
        device_id:    deviceId,
        metric,
        operator,
        threshold:    parseFloat(threshold),
        channel,
        cooldown_min: parseInt(cooldown, 10),
        is_active:    true,
      })
      await load()
    } catch (err: any) {
      setFormError(err.response?.data?.detail ?? 'เกิดข้อผิดพลาด')
    } finally {
      setSaving(false)
    }
  }

  const deleteRule = async (id: number) => {
    if (!confirm('ลบกฎนี้?')) return
    try { await alertApi.deleteRule(id); await load() } catch { /* ignore */ }
  }

  return (
    <main className="page pt-16 pb-28 md:pb-10">
      <h1 className="text-lg font-bold mb-4">การแจ้งเตือน</h1>

      {/* Tabs */}
      <div className="flex bg-slate-900 rounded-xl p-1 mb-4">
        {(['rules', 'logs'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-1.5 rounded-lg text-sm font-medium transition ${
              tab === t ? 'bg-sky-700 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {t === 'rules' ? '🔔 กฎแจ้งเตือน' : '📋 ประวัติ'}
          </button>
        ))}
      </div>

      {tab === 'rules' ? (
        <>
          {/* Add rule form */}
          <div className="card mb-4">
            <h2 className="text-sm font-semibold text-slate-300 mb-3">เพิ่มกฎใหม่</h2>
            <form onSubmit={createRule} className="flex flex-col gap-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">ตัวชี้วัด</label>
                  <select className="input" value={metric} onChange={(e) => setMetric(e.target.value)}>
                    {METRICS.map((m) => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">เงื่อนไข</label>
                  <select className="input" value={operator} onChange={(e) => setOperator(e.target.value)}>
                    {OPERATORS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">ค่า threshold</label>
                  <input
                    className="input"
                    type="number"
                    step="0.1"
                    value={threshold}
                    onChange={(e) => setThreshold(e.target.value)}
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">ช่องทาง</label>
                  <select className="input" value={channel} onChange={(e) => setChannel(e.target.value)}>
                    {CHANNELS.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">Cooldown (นาที)</label>
                <input
                  className="input"
                  type="number"
                  min={1}
                  value={cooldown}
                  onChange={(e) => setCooldown(e.target.value)}
                  required
                />
              </div>

              {formError && (
                <p className="text-xs text-red-400 bg-red-900/30 rounded-lg px-3 py-2">{formError}</p>
              )}
              <button type="submit" disabled={saving} className="btn-primary">
                {saving ? '...' : '+ เพิ่มกฎ'}
              </button>
            </form>
          </div>

          {/* Rule list */}
          {loading ? (
            <p className="text-slate-500 text-sm text-center py-8 animate-pulse">กำลังโหลด...</p>
          ) : rules.length === 0 ? (
            <div className="card text-center py-8 text-slate-500">
              <p className="text-3xl mb-2">🔕</p>
              <p className="text-sm">ยังไม่มีกฎแจ้งเตือน</p>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {rules.map((r) => (
                <div key={r.id} className="card flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-white">
                      {r.metric} {OPERATORS.find((o) => o.value === r.operator)?.label.split(' ')[0]} {r.threshold}
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {r.channel} · cooldown {r.cooldown_min} นาที ·
                      <span className={r.is_active ? ' text-emerald-400' : ' text-slate-600'}>
                        {r.is_active ? ' เปิดใช้งาน' : ' ปิดใช้งาน'}
                      </span>
                    </p>
                  </div>
                  <button
                    onClick={() => deleteRule(r.id!)}
                    className="text-slate-600 hover:text-red-400 text-lg leading-none transition flex-shrink-0"
                    title="ลบ"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        /* Logs tab */
        loading ? (
          <p className="text-slate-500 text-sm text-center py-8 animate-pulse">กำลังโหลด...</p>
        ) : logs.length === 0 ? (
          <div className="card text-center py-8 text-slate-500">
            <p className="text-3xl mb-2">📭</p>
            <p className="text-sm">ยังไม่มีประวัติการแจ้งเตือน</p>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {logs.map((l) => (
              <div key={l.id} className="card">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-white">{l.metric} = {l.value}</span>
                  <span className={`text-xs ${l.sent_ok ? 'text-emerald-400' : 'text-red-400'}`}>
                    {l.sent_ok ? '✓ ส่งแล้ว' : '✗ ส่งไม่สำเร็จ'}
                  </span>
                </div>
                <p className="text-xs text-slate-400">{l.message}</p>
                <p className="text-xs text-slate-600 mt-1">
                  {format(parseISO(l.created_at), 'dd/MM/yyyy HH:mm')} · {l.channel}
                </p>
              </div>
            ))}
          </div>
        )
      )}
    </main>
  )
}
