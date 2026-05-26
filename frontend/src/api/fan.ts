import { api } from './client'

export interface FanCommand {
  speed: number        // 0–100
  mode:  'manual' | 'auto'
}

export interface FanStatus {
  device_id: string
  speed:     number
  mode:      string
  ok:        boolean
}

export const fanApi = {
  set: (deviceId: string, cmd: FanCommand) =>
    api.post<FanStatus>(`/api/fan/set/${deviceId}`, cmd),

  setAuto: (deviceId: string) =>
    api.post<FanStatus>(`/api/fan/auto/${deviceId}`),

  setOff: (deviceId: string) =>
    api.post<FanStatus>(`/api/fan/off/${deviceId}`),
}
