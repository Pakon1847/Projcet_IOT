import { api } from './client'

export interface FanSchedule {
  id:         number
  name:       string
  days:       string   // "1111111" — ตำแหน่ง 0=จันทร์ ... 6=อาทิตย์
  start_time: string   // "HH:MM"
  end_time:   string   // "HH:MM"
  fan_speed:  number   // 0–100
  is_active:  boolean
}

export type ScheduleCreate = Omit<FanSchedule, 'id'>

export const scheduleApi = {
  list: () =>
    api.get<FanSchedule[]>('/api/schedule/'),

  create: (body: ScheduleCreate) =>
    api.post<FanSchedule>('/api/schedule/', body),

  update: (id: number, body: Partial<ScheduleCreate>) =>
    api.put<FanSchedule>(`/api/schedule/${id}`, body),

  remove: (id: number) =>
    api.delete(`/api/schedule/${id}`),

  toggle: (id: number) =>
    api.patch<FanSchedule>(`/api/schedule/${id}/toggle`),
}

// ──────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────

export const DAY_LABELS = ['จ', 'อ', 'พ', 'พฤ', 'ศ', 'ส', 'อา']
export const DAY_LABELS_FULL = ['จันทร์', 'อังคาร', 'พุธ', 'พฤหัส', 'ศุกร์', 'เสาร์', 'อาทิตย์']

/** แปลง "1111100" เป็น "จ อ พ พฤ ศ" */
export function formatDays(days: string): string {
  return DAY_LABELS.filter((_, i) => days[i] === '1').join(' ')
}

/** แปลง "1111100" เป็น label สั้น เช่น "ทุกวัน" / "วันธรรมดา" */
export function daysLabel(days: string): string {
  if (days === '1111111') return 'ทุกวัน'
  if (days === '1111100') return 'วันธรรมดา'
  if (days === '0000011') return 'เสาร์-อาทิตย์'
  return formatDays(days)
}
