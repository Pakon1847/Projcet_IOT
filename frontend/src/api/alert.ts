import { api } from './client'

export interface AlertRule {
  id?:          number
  device_id:    string
  metric:       string   // 'pm25' | 'aqi' | 'temperature' | 'humidity'
  operator:     string   // 'gt' | 'lt' | 'gte' | 'lte'
  threshold:    number
  channel:      string   // 'line' | 'telegram'
  cooldown_min: number
  is_active:    boolean
}

export interface AlertLog {
  id:         number
  rule_id:    number
  device_id:  string
  metric:     string
  value:      number
  message:    string
  channel:    string
  sent_ok:    boolean
  created_at: string
}

export const alertApi = {
  listRules: () => api.get<AlertRule[]>('/api/alert/rules'),
  createRule: (rule: AlertRule) => api.post<AlertRule>('/api/alert/rules', rule),
  deleteRule: (id: number) => api.delete(`/api/alert/rules/${id}`),
  logs: (deviceId: string) => api.get<AlertLog[]>(`/api/alert/logs/${deviceId}`),
}
