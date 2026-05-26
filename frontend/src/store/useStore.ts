import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { SensorReading } from '../api/sensor'
import type { UserInfo } from '../api/auth'

interface AppState {
  // Auth
  token:    string | null
  user:     UserInfo | null
  setToken: (token: string | null) => void
  setUser:  (user: UserInfo | null) => void
  logout:   () => void

  // Active device
  deviceId:    string
  setDeviceId: (id: string) => void

  // Live sensor reading (from WebSocket)
  liveReading:    SensorReading | null
  setLiveReading: (r: SensorReading) => void
}

export const useStore = create<AppState>()(
  persist(
    (set) => ({
      // ── Auth ──────────────────────────────────────────────────────────────
      token:    null,
      user:     null,
      setToken: (token) => set({ token }),
      setUser:  (user)  => set({ user }),
      logout:   () => {
        localStorage.removeItem('token')
        set({ token: null, user: null })
      },

      // ── Device ────────────────────────────────────────────────────────────
      deviceId:    'pi-001',
      setDeviceId: (id) => set({ deviceId: id }),

      // ── Live data ─────────────────────────────────────────────────────────
      liveReading:    null,
      setLiveReading: (r) => set({ liveReading: r }),
    }),
    {
      name: 'airguard-store',
      partialize: (s) => ({ token: s.token, user: s.user, deviceId: s.deviceId }),
    },
  ),
)
