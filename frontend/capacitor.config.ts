import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'com.todogas.cmms',
  appName: 'TodoGas',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
  },
}

export default config
