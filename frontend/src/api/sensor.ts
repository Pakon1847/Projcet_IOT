import { api } from './client'

export interface SensorReading {
  device_id:   string
  pm25:        number
  pm10:        number
  temperature: number
  humidity:    number
  pressure:    number
  aqi:         number
  aqi_level:   string
  aqi_level_en:string
  fan_speed:   number
  timestamp:   string   // ISO 8601
}

export interface DailyAvg {
  date:   string
  pm25:   number
  aqi:    number
}

export const sensorApi = {
  latest: (deviceId: string) =>
    api.get<SensorReading>(`/api/sensor/latest/${deviceId}`),

  history: (deviceId: string, hours = 24) =>
    api.get<SensorReading[]>(`/api/sensor/history/${deviceId}`, { params: { hours } }),

  dailyAvg: (deviceId: string, days = 7) =>
    api.get<DailyAvg[]>(`/api/sensor/daily-avg/${deviceId}`, { params: { days } }),
}
