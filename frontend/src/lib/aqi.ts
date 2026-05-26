// Thai AQI helpers — mirrors backend/firmware logic in TypeScript

export interface AQIInfo {
  level:    string      // Thai label
  levelEn:  string
  color:    string      // Tailwind bg class
  textColor:string      // Tailwind text class
  ring:     string      // hex for SVG
  emoji:    string
}

export function getAQIInfo(aqi: number): AQIInfo {
  if (aqi <= 25)  return { level: 'ดีมาก',              levelEn: 'Very Good',               color: 'bg-green-500',  textColor: 'text-green-400',  ring: '#00b050', emoji: '😊' }
  if (aqi <= 50)  return { level: 'ดี',                 levelEn: 'Good',                    color: 'bg-lime-400',   textColor: 'text-lime-400',   ring: '#92d050', emoji: '🙂' }
  if (aqi <= 100) return { level: 'ปานกลาง',            levelEn: 'Moderate',                color: 'bg-yellow-400', textColor: 'text-yellow-400', ring: '#ffcc00', emoji: '😐' }
  if (aqi <= 200) return { level: 'เริ่มมีผลต่อสุขภาพ', levelEn: 'Unhealthy for Sensitive', color: 'bg-orange-500', textColor: 'text-orange-400', ring: '#ff9900', emoji: '😷' }
  return            { level: 'มีผลต่อสุขภาพ',           levelEn: 'Unhealthy',               color: 'bg-red-600',    textColor: 'text-red-400',    ring: '#ff0000', emoji: '🚨' }
}

/** แปลง PM2.5 (µg/m³) → Thai AQI (linear interpolation) */
export function pm25ToAQI(pm25: number): number {
  const bp: [number, number, number, number][] = [
    [0.0,  15.0,   0,  25],
    [15.1, 25.0,  26,  50],
    [25.1, 37.5,  51, 100],
    [37.6, 75.0, 101, 200],
    [75.1, 999,  201, 500],
  ]
  for (const [cLo, cHi, iLo, iHi] of bp) {
    if (pm25 >= cLo && pm25 <= cHi) {
      return Math.round(((iHi - iLo) / (cHi - cLo)) * (pm25 - cLo) + iLo)
    }
  }
  return 500
}

export const PM25_STANDARD_24H  = 37.5
export const PM25_STANDARD_YEAR = 15.0
