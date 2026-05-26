import { useState, useRef, useEffect, FormEvent } from 'react'
import { useStore }  from '../store/useStore'
import { aiApi }     from '../api/ai'
import type { ChatMessage } from '../api/ai'
import { aiApi as predict } from '../api/ai'
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer,
} from 'recharts'

export function AIChatPage() {
  const deviceId = useStore((s) => s.deviceId)

  const [messages,    setMessages]    = useState<ChatMessage[]>([
    {
      role:    'assistant',
      content: 'สวัสดีครับ 👋 ผม AirGuard AI ขับเคลื่อนด้วย Phi-3 Mini ทำงานบน Raspberry Pi ถามเรื่องคุณภาพอากาศ, PM2.5, หรือสุขภาพได้เลยครับ',
    },
  ])
  const [input,       setInput]       = useState('')
  const [loading,     setLoading]     = useState(false)
  const [predictions, setPredictions] = useState<{ hour: number; pm25: number }[]>([])
  const [predLoading, setPredLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const send = async (e: FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    const userMsg: ChatMessage = { role: 'user', content: text }
    setMessages((m) => [...m, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await aiApi.chat({
        device_id: deviceId,
        message:   text,
        history:   messages.slice(-10),   // last 10 messages for context
      })
      setMessages((m) => [...m, { role: 'assistant', content: res.data.reply }])
    } catch {
      setMessages((m) => [...m, { role: 'assistant', content: '⚠️ ไม่สามารถเชื่อมต่อ Ollama ได้ กรุณาตรวจสอบว่าเปิด Ollama ไว้บน host แล้ว' }])
    } finally {
      setLoading(false)
    }
  }

  const loadPredictions = async () => {
    setPredLoading(true)
    try {
      const res = await predict.predict(deviceId)
      setPredictions(res.data.predictions)
    } catch { /* ignore */ }
    finally { setPredLoading(false) }
  }

  // Quick prompt suggestions
  const suggestions = [
    'ตอนนี้คุณภาพอากาศเป็นอย่างไร?',
    'ควรสวมหน้ากากตอนไหน?',
    'PM2.5 มีผลต่อสุขภาพอย่างไร?',
    'วิธีดูแลเครื่องกรองอากาศ',
  ]

  return (
    <main className="page pt-16 pb-28 md:pb-10 flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h1 className="text-lg font-bold">AI Chat</h1>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Phi-3 Mini · Local</span>
          <span className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
        </div>
      </div>

      {/* Prediction chart */}
      <div className="card mb-3">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-slate-300">🔮 พยากรณ์ PM2.5 (6 ชั่วโมง)</h2>
          <button
            onClick={loadPredictions}
            disabled={predLoading}
            className="text-xs text-sky-400 hover:text-sky-300 transition"
          >
            {predLoading ? '...' : '🔄 โหลด'}
          </button>
        </div>
        {predictions.length > 0 ? (
          <ResponsiveContainer width="100%" height={120}>
            <LineChart data={predictions} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis
                dataKey="hour"
                tickFormatter={(v) => `+${v}h`}
                tick={{ fill: '#64748b', fontSize: 10 }}
                tickLine={false}
                axisLine={{ stroke: '#334155' }}
              />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
                labelFormatter={(v) => `+${v}h`}
                labelStyle={{ color: '#94a3b8' }}
              />
              <Line type="monotone" dataKey="pm25" name="PM2.5" stroke="#a78bfa" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-xs text-slate-600 text-center py-4">กด 🔄 โหลด เพื่อดูการพยากรณ์</p>
        )}
      </div>

      {/* Chat messages */}
      <div className="card flex-1 min-h-0 overflow-y-auto flex flex-col gap-3 mb-3 max-h-[40vh]">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] px-3 py-2 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                m.role === 'user'
                  ? 'bg-sky-700 text-white rounded-br-sm'
                  : 'bg-slate-800 text-slate-200 rounded-bl-sm'
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-800 px-3 py-2 rounded-2xl rounded-bl-sm">
              <span className="text-slate-500 text-sm animate-pulse">กำลังคิด...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quick suggestions */}
      {messages.length <= 1 && (
        <div className="flex gap-2 flex-wrap mb-3">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => setInput(s)}
              className="px-3 py-1.5 text-xs rounded-full bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200 transition border border-slate-700"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <form onSubmit={send} className="flex gap-2">
        <input
          className="input flex-1"
          placeholder="ถามเรื่องคุณภาพอากาศ..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="btn-primary px-4"
        >
          ➤
        </button>
      </form>
    </main>
  )
}
