import { api } from './client'

export interface OutdoorStation {
  station_id: string
  name_th:    string
  name_en:    string
  area_th:    string
  lat:        number
  lon:        number
  pm25:       number | null
  aqi:        number | null
  color:      string
  updated_at: string
}

export interface VentilationAdvice {
  action: 'open' | 'optional' | 'close' | 'unknown'
  icon:   string
  title:  string
  detail: string
  color:  string
}

export interface AdviceResponse {
  advice:      VentilationAdvice
  station:     OutdoorStation | null
  indoor_pm25: number
}

export const outdoorApi = {
  nearest: (lat: number, lon: number) =>
    api.get<{ station: OutdoorStation | null }>(`/api/outdoor/nearest?lat=${lat}&lon=${lon}`),

  advice: (indoor_pm25: number, lat: number, lon: number) =>
    api.get<AdviceResponse>(
      `/api/outdoor/advice?indoor_pm25=${indoor_pm25}&lat=${lat}&lon=${lon}`
    ),

  stations: () =>
    api.get<{ count: number; stations: OutdoorStation[] }>('/api/outdoor/stations'),
}
