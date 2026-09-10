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

        // Los neutros se redefinen sobre el mismo tono 214 de la marca. Antes
        // convivian el gray de Tailwind (frio, tono 220) con hexes slate
        // sueltos en las graficas: dos familias de gris en la misma pantalla.
        // Al reescribir la escala, todas las clases gray-* ya existentes
        // quedan alineadas con el navy sin tocar una sola vista.
        gray: {
          50: '#f8fafc',
          100: '#f1f4f8',
          200: '#e2e7ee',
          300: '#cbd2dc',
          400: '#9ba7b5',
          500: '#6b7b8e',
          600: '#505f71',
          700: '#3b4859',
          800: '#293442',
          900: '#19222e',
          950: '#0d131c',
        },
      },

      fontFamily: {
        sans: ['Geist', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        // Codigos de activo, IDs, horas y contadores: cifras de ancho fijo
        // para que las columnas numericas no bailen entre filas.
        mono: ['"Geist Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },

      letterSpacing: {
        tightest: '-0.035em',
      },

      // Sombras tenidas con el navy de fondo en lugar de negro puro: sobre un
      // lienzo frio, el negro al 10% se lee gris sucio.
      boxShadow: {
        sm: '0 1px 2px 0 rgb(20 35 56 / 0.05)',
        DEFAULT: '0 1px 2px 0 rgb(20 35 56 / 0.05), 0 1px 3px 0 rgb(20 35 56 / 0.07)',
        md: '0 2px 4px -2px rgb(20 35 56 / 0.06), 0 4px 10px -2px rgb(20 35 56 / 0.10)',
        lg: '0 4px 6px -4px rgb(20 35 56 / 0.07), 0 10px 20px -6px rgb(20 35 56 / 0.12)',
        xl: '0 8px 12px -8px rgb(20 35 56 / 0.10), 0 24px 48px -16px rgb(20 35 56 / 0.20)',
        '2xl': '0 32px 64px -20px rgb(20 35 56 / 0.28)',
        // Reposo y elevacion de tarjeta, para que el hover tenga a donde subir.
        card: '0 1px 2px 0 rgb(20 35 56 / 0.04), 0 1px 3px -1px rgb(20 35 56 / 0.06)',
        lift: '0 2px 4px -2px rgb(20 35 56 / 0.06), 0 12px 24px -10px rgb(20 35 56 / 0.16)',
        inset: 'inset 0 1px 0 0 rgb(255 255 255 / 0.06)',
      },

      keyframes: {
        rise: {
          from: { opacity: '0', transform: 'translate3d(0, 10px, 0)' },
          to: { opacity: '1', transform: 'translate3d(0, 0, 0)' },
        },
        fade: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
      },

      animation: {
        rise: 'rise 340ms cubic-bezier(0.22, 1, 0.36, 1) both',
        fade: 'fade 240ms ease-out both',
      },

      transitionTimingFunction: {
        // Salida tipo muelle, sin rebote: peso sin aparatosidad.
        spring: 'cubic-bezier(0.22, 1, 0.36, 1)',
      },
    },
  },
  plugins: [],
}
