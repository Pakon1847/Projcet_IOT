/**
 * SchedulePage — จัดการตาราง schedule พัดลม
 * - ดูรายการ schedule ทั้งหมด
 * - เพิ่ม / แก้ไข / ลบ / toggle เปิด-ปิด
 */

import { useEffect, useState } from 'react'
import { scheduleApi, daysLabel, DAY_LABELS }  from '../api/schedule'
import type { FanSchedule, ScheduleCreate }    from '../api/schedule'

const EMPTY_FORM: ScheduleCreate = {
  name:       '',
  days:       '1111111',
  start_time: '22:00',
  end_time:   '06:00',
  fan_speed:  80,
  is_active:  true,
}

export function SchedulePage() {
  const [schedules, setSchedules] = useState<FanSchedule[]>([])
  const [loading,   setLoading]   = useState(true)
  const [showForm,  setShowForm]  = useState(false)
  const [editId,    setEditId]    = useState<number | null>(null)
  const [form,      setForm]      = useState<ScheduleCreate>(EMPTY_FORM)
  const [saving,    setSaving]    = useState(false)

  const load = async () => {
    try {
      const res = await scheduleApi.list()
      setSchedules(res.data)
    } catch { /* offline */ }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  // ── Form helpers ──────────────────────────────────────────────────

  const openAdd = () => {
    setEditId(null)
    setForm(EMPTY_FORM)
    setShowForm(true)
  }

  const openEdit = (s: FanSchedule) => {
    setEditId(s.id)
    setForm({ name: s.name, days: s.days, start_time: s.start_time,
              end_time: s.end_time, fan_speed: s.fan_speed, is_active: s.is_active })
    setShowForm(true)
  }

  const toggleDay = (i: number) => {
    const d = form.days.split('')
    d[i] = d[i] === '1' ? '0' : '1'
    setForm({ ...form, days: d.join('') })
  }

  const handleSave = async () => {
    if (!form.name.trim()) return
    setSaving(true)
    try {
      if (editId !== null) {
        await scheduleApi.update(editId, form)
      } else {
        await scheduleApi.create(form)
      }
      setShowForm(false)
      await load()
    } catch (e: any) {
      alert(e?.response?.data?.detail ?? 'เกิดข้อผิดพลาด')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('ลบ schedule นี้?')) return
    await scheduleApi.remove(id)
    setSchedules((prev) => prev.filter((s) => s.id !== id))
  }

  const handleToggle = async (id: number) => {
    const res = await scheduleApi.toggle(id)
    setSchedules((prev) => prev.map((s) => s.id === id ? res.data : s))
  }

  // ── Render ─────────────────────────────────────────────────────────

  return (
    <main className="page pt-16 pb-28 md:pb-10">

      {/* Header */}
      <div className="flex items-center justify-between mb-5 animate-fade-slide-up">
        <div>
          <h1 className="text-lg font-bold text-white">⏰ ตั้งเวลาพัดลม</h1>
          <p className="text-xs text-slate-500">พัดลมจะทำงานอัตโนมัติตามเวลาที่กำหนด</p>
        </div>
        <button
          onClick={openAdd}
          className="px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500
                     text-white text-sm font-medium active:scale-95 transition-all"
        >
          + เพิ่ม
        </button>
      </div>

      {/* List */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2].map((n) => (
            <div key={n} className="card animate-pulse h-20 bg-slate-800/60" />
          ))}
        </div>
      ) : schedules.length === 0 ? (
        <div className="card flex flex-col items-center gap-3 py-12 text-slate-500
                        animate-fade-slide-up">
          <span className="text-4xl animate-float">⏰</span>
          <p className="text-sm">ยังไม่มี schedule</p>
          <p className="text-xs text-slate-600">กด "+ เพิ่ม" เพื่อสร้าง schedule แรก</p>
        </div>
      ) : (
        <div className="space-y-3">
          {schedules.map((s, i) => (
            <div
              key={s.id}
              className={`card animate-fade-slide-up transition-all duration-300
                          ${s.is_active ? '' : 'opacity-50'}`}
              style={{ animationDelay: `${i * 75}ms` }}
            >
              <div className="flex items-start justify-between gap-3">
                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-white text-sm truncate">{s.name}</span>
                    {s.is_active ? (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full
                                       bg-emerald-900/40 text-emerald-400 border border-emerald-700/40">
                        เปิด
                      </span>
                    ) : (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full
                                       bg-slate-800/60 text-slate-500 border border-slate-700/40">
                        ปิด
                      </span>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-400">
                    <span>🕐 {s.start_time} – {s.end_time}</span>
                    <span>🌀 {s.fan_speed}%</span>
                    <span>📅 {daysLabel(s.days)}</span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1.5 shrink-0">
                  {/* Toggle */}
                  <button
                    onClick={() => handleToggle(s.id)}
                    className={`w-10 h-6 rounded-full transition-all duration-300 relative
                                ${s.is_active ? 'bg-sky-600' : 'bg-slate-700'}`}
                    title={s.is_active ? 'ปิด' : 'เปิด'}
                  >
                    <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow
                                      transition-all duration-300
                                      ${s.is_active ? 'left-[calc(100%-1.375rem)]' : 'left-0.5'}`} />
                  </button>

                  <button
                    onClick={() => openEdit(s)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-sky-300
                               hover:bg-slate-800 transition-all text-sm"
                    title="แก้ไข"
                  >
                    ✏️
                  </button>
                  <button
                    onClick={() => handleDelete(s.id)}
                    className="p-1.5 rounded-lg text-slate-500 hover:text-red-400
                               hover:bg-slate-800 transition-all text-sm"
                    title="ลบ"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Modal Form ──────────────────────────────────────────────── */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center
                        bg-black/60 backdrop-blur-sm"
             onClick={(e) => { if (e.target === e.currentTarget) setShowForm(false) }}>
          <div className="w-full max-w-md bg-[#1e293b] rounded-t-2xl md:rounded-2xl
                          border border-slate-700/60 p-5 shadow-2xl animate-fade-slide-up">

            <h2 className="text-base font-bold text-white mb-4">
              {editId !== null ? '✏️ แก้ไข Schedule' : '➕ เพิ่ม Schedule'}
            </h2>

            <div className="space-y-4">
              {/* Name */}
              <div>
                <label className="text-xs text-slate-400 mb-1 block">ชื่อ Schedule</label>
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="เช่น กลางคืน, เช้า"
                  className="w-full bg-slate-800/60 border border-slate-700/60 rounded-lg
                             px-3 py-2 text-sm text-white placeholder:text-slate-600
                             focus:outline-none focus:border-sky-500 transition-colors"
                />
              </div>

              {/* Days */}
              <div>
                <label className="text-xs text-slate-400 mb-2 block">วันที่ทำงาน</label>
                <div className="flex gap-1.5">
                  {DAY_LABELS.map((d, i) => (
                    <button
                      key={i}
                      onClick={() => toggleDay(i)}
                      className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all
                                  ${form.days[i] === '1'
                                    ? 'bg-sky-600 text-white'
                                    : 'bg-slate-800 text-slate-500 hover:bg-slate-700'
                                  }`}
                    >
                      {d}
                    </button>
                  ))}
                </div>
              </div>

              {/* Time range */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">เริ่ม</label>
                  <input
                    type="time"
                    value={form.start_time}
                    onChange={(e) => setForm({ ...form, start_time: e.target.value })}
                    className="w-full bg-slate-800/60 border border-slate-700/60 rounded-lg
                               px-3 py-2 text-sm text-white
                               focus:outline-none focus:border-sky-500 transition-colors"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">สิ้นสุด</label>
                  <input
                    type="time"
                    value={form.end_time}
                    onChange={(e) => setForm({ ...form, end_time: e.target.value })}
                    className="w-full bg-slate-800/60 border border-slate-700/60 rounded-lg
                               px-3 py-2 text-sm text-white
                               focus:outline-none focus:border-sky-500 transition-colors"
                  />
                </div>
              </div>

              {/* Fan speed */}
              <div>
                <label className="text-xs text-slate-400 mb-1 block">
                  ความเร็วพัดลม — <span className="text-sky-400 font-semibold">{form.fan_speed}%</span>
                </label>
                <input
                  type="range"
                  min={0} max={100} step={5}
                  value={form.fan_speed}
                  onChange={(e) => setForm({ ...form, fan_speed: Number(e.target.value) })}
                  className="w-full accent-sky-500"
                />
                <div className="flex justify-between text-[10px] text-slate-600 mt-1">
                  <span>ปิด (0%)</span>
                  <span>เต็ม (100%)</span>
                </div>
              </div>

              {/* Active toggle */}
              <label className="flex items-center gap-3 cursor-pointer">
                <div
                  onClick={() => setForm({ ...form, is_active: !form.is_active })}
                  className={`w-10 h-6 rounded-full transition-all duration-300 relative cursor-pointer
                              ${form.is_active ? 'bg-sky-600' : 'bg-slate-700'}`}
                >
                  <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow
                                    transition-all duration-300
                                    ${form.is_active ? 'left-[calc(100%-1.375rem)]' : 'left-0.5'}`} />
                </div>
                <span className="text-sm text-slate-300">เปิดใช้งานทันที</span>
              </label>
            </div>

            {/* Buttons */}
            <div className="flex gap-3 mt-5">
              <button
                onClick={() => setShowForm(false)}
                className="flex-1 py-2 rounded-lg bg-slate-800 text-slate-400
                           hover:bg-slate-700 text-sm transition-all"
              >
                ยกเลิก
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !form.name.trim()}
                className="flex-1 py-2 rounded-lg bg-sky-600 hover:bg-sky-500
                           text-white text-sm font-medium transition-all
                           disabled:opacity-50 disabled:cursor-not-allowed active:scale-95"
              >
                {saving ? 'กำลังบันทึก...' : 'บันทึก'}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
