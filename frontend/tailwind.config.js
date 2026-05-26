/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Thai AQI palette
        aqi: {
          great:    '#00b050',   // ดีมาก   0-25
          good:     '#92d050',   // ดี       26-50
          moderate: '#ffff00',   // ปานกลาง 51-100
          sensitive:'#ff9900',   // เริ่มมีผล 101-200
          unhealthy:'#ff0000',   // มีผลต่อสุขภาพ 201-500
        },
        navy: {
          900: '#0f172a',
          800: '#1e293b',
          700: '#334155',
          600: '#475569',
        },
      },
      fontFamily: {
        sans: ['Inter', 'Noto Sans Thai', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow':  'spin 8s linear infinite',
      },
    },
  },
  plugins: [],
}
