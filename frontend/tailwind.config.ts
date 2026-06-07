/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Design System — Dark Navy Palette
        bg: {
          primary: '#0A0E1A',
          surface: '#111827',
          elevated: '#1C2537',
        },
        border: {
          subtle: '#2D3748',
          accent: 'rgba(99,102,241,0.3)',
        },
        brand: {
          DEFAULT: '#6366F1',   // indigo-500
          hover:   '#4F46E5',   // indigo-600
          glow:    'rgba(99,102,241,0.15)',
          light:   '#818CF8',   // indigo-400
        },
        success: '#10B981',     // emerald-500 — present
        warning: '#F59E0B',     // amber-500 — at risk
        danger:  '#EF4444',     // red-500 — absent/fraud
        muted:   '#475569',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      backgroundImage: {
        'gradient-brand': 'linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)',
        'gradient-success': 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
        'gradient-card': 'linear-gradient(145deg, rgba(28,37,55,0.8) 0%, rgba(17,24,39,0.9) 100%)',
      },
      boxShadow: {
        'glow-brand': '0 0 40px rgba(99,102,241,0.2)',
        'glow-success': '0 0 30px rgba(16,185,129,0.2)',
        'card': '0 8px 32px rgba(0,0,0,0.4)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};
