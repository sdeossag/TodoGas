/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Escala unica de marca, tono 214 constante. brand-800 es el navy
        // corporativo (#1e3a5f); DEFAULT/light/dark se mantienen como alias
        // para no romper los usos existentes de bg-brand / bg-brand-light.
        brand: {
          50: '#f3f7fc',
          100: '#e3ecf7',
          200: '#c5d6ed',
          300: '#9db8dd',
          400: '#6b93c7',
          500: '#4070b0',
          600: '#2f588e',
          700: '#254774',
          800: '#1e3a5f',
          900: '#162d4b',
          950: '#0e1c2f',
          DEFAULT: '#1e3a5f',
          light: '#2f588e',
          dark: '#162d4b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
