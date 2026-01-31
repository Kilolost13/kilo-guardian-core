/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'zombie-green': '#00ff41',
        'terminal-green': '#00cc33',
        'dark-bg': '#0a0e0f',
        'zombie-dark': '#0a0e0f', // Alias for dark-bg
        'dark-card': '#1a1f20',
        'dark-border': '#2a3f3f',
        'neon-blue': '#00d9ff',
        'neon-purple': '#b842ff',
        'neon-pink': '#ff006e',
        'blood-red': '#ff0033',
      },
      fontFamily: {
        'mono': ['Courier New', 'monospace'],
        'terminal': ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { textShadow: '0 0 5px #00ff41, 0 0 10px #00ff41' },
          '100%': { textShadow: '0 0 10px #00ff41, 0 0 20px #00ff41, 0 0 30px #00ff41' },
        }
      },
      backgroundImage: {
        'zombie-gradient': 'linear-gradient(135deg, #0a0e0f 0%, #1a1f20 50%, #0a0e0f 100%)',
        'terminal-gradient': 'linear-gradient(to bottom, #0a0e0f, #1a2f1f)',
      },
    },
  },
  plugins: [],
}
