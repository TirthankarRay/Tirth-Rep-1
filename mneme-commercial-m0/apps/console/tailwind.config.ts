import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        mneme: {
          bg: '#0a0d18',
          surface: '#161b2b',
          surface2: '#1f2538',
          line: '#2a3148',
          text: '#dde2f0',
          dim: '#8a93a9',
          accent: '#d4a045',
          good: '#5fb37a',
          warn: '#d4a045',
          bad: '#d4685f',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
        display: ['Fraunces', 'Inter', 'serif'],
      },
    },
  },
  plugins: [],
} satisfies Config;
