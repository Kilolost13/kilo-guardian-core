/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  theme: {
    extend: {
      colors: {
        'kilo-green': '#39FF14',
        'kilo-black': '#050505',
      },
      fontFamily: {
        'header': ['Orbitron', 'sans-serif'],
        'mono': ['Share Tech Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
