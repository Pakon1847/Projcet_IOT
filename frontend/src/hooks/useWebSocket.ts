import { useEffect, useRef, useCallback } from 'react'
import { useStore } from '../store/useStore'

const WS_BASE = import.meta.env.VITE_WS_URL ?? ''   // '' → same host

export function useWebSocket(
  deviceId:  string,
  onMessage?: (data: Record<string, any>) => void,
) {
  const setLiveReading = useStore((s) => s.setLiveReading)
  const wsRef    = useRef<WebSocket | null>(null)
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const cbRef    = useRef(onMessage)
  cbRef.current  = onMessage   // keep latest callback without re-connecting

  const connect = useCallback(() => {
    const token = localStorage.getItem('token')
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host  = WS_BASE || `${proto}://${window.location.host}`
    const url   = `${host}/api/sensor/ws/${deviceId}?token=${token ?? ''}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen    = () => console.log('[WS] connected', deviceId)
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        // ถ้า payload มี sensor fields → update live reading
        if (data.pm2_5 !== undefined || data.pm25 !== undefined) {
          setLiveReading(data)
        }
        // เรียก callback เสมอ (anomaly, etc.)
        cbRef.current?.(data)
      } catch { /* ignore parse errors */ }
    }
    ws.onclose = (e) => {
      console.log('[WS] closed', e.code)
      if (e.code !== 1000) {
        retryRef.current = setTimeout(connect, 3000)
      }
    }
    ws.onerror = () => ws.close()
  }, [deviceId, setLiveReading])

  useEffect(() => {
    connect()
    return () => {
      if (retryRef.current) clearTimeout(retryRef.current)
      wsRef.current?.close(1000)
    }
  }, [connect])
}
