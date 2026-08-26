/**
 * Notificaciones push (FCM).
 *
 * Solo corre en Android: en el navegador el plugin no existe y initFCM()
 * sale sin hacer nada, para que App.jsx pueda llamarlo sin condicionar.
 *
 * Requiere android/app/google-services.json real. Con el placeholder que hay
 * ahora el APK compila pero no recibe notificaciones.
 */

import { Capacitor } from '@capacitor/core'
import { PushNotifications } from '@capacitor/push-notifications'

let initialized = false

export async function initFCM(onNotification) {
  if (!Capacitor.isNativePlatform()) return

  // React monta los efectos dos veces en desarrollo: sin esto quedarian
  // listeners duplicados y cada notificacion navegaria dos veces.
  if (initialized) return
  initialized = true

  try {
    // Solicitar permiso
    const result = await PushNotifications.requestPermissions()
    if (result.receive !== 'granted') {
      initialized = false
      return
    }

    // Registrar con FCM
    await PushNotifications.register()

    // Listener: token registrado
    await PushNotifications.addListener('registration', (token) => {
      console.info('FCM token:', token.value)
      // En Sprint 13: enviar token al backend
      // POST /api/users/me/fcm-token/
      // con {token: token.value}
    })

    await PushNotifications.addListener('registrationError', (error) => {
      console.warn('[fcm] fallo el registro:', error?.error ?? error)
    })

    // Listener: notificacion recibida en primer plano
    await PushNotifications.addListener('pushNotificationReceived', (notification) => {
      onNotification?.(notification)
    })

    // Listener: usuario toca la notificacion
    await PushNotifications.addListener('pushNotificationActionPerformed', (action) => {
      const data = action.notification.data
      if (data?.work_order_id) {
        // Navegar a la OT correspondiente
        window.location.href = '/mis-ordenes/' + data.work_order_id
      }
    })
  } catch (error) {
    // Sin google-services.json valido el registro falla. No es motivo para
    // tumbar el arranque de la app: el resto funciona sin push.
    initialized = false
    console.warn('[fcm] no se pudo inicializar:', error?.message ?? error)
  }
}

/** Suelta todos los listeners. Util al cerrar sesion. */
export async function stopFCM() {
  if (!Capacitor.isNativePlatform() || !initialized) return
  try {
    await PushNotifications.removeAllListeners()
  } catch {
    // los handles ya pueden estar sueltos
  }
  initialized = false
}
