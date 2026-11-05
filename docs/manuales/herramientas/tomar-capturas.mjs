// Toma las capturas web de los manuales con Playwright.
// Uso: node tomar-capturas.mjs [--solo 1,8,10] [--base http://localhost:5197]
// Ver README.md y capturas.json (cada entrada documenta sus pasos).
import { chromium } from 'playwright'
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const aqui = path.dirname(fileURLToPath(import.meta.url))
const raiz = path.resolve(aqui, '..', '..', '..')

const args = process.argv.slice(2)
const arg = (nombre, def) => {
  const i = args.indexOf(nombre)
  return i >= 0 && args[i + 1] ? args[i + 1] : def
}
const BASE = arg('--base', 'http://localhost:5197').replace(/\/$/, '')
const solo = arg('--solo', '') ? arg('--solo', '').split(',').map((s) => Number(s.trim())) : null
const DB_NAME = arg('--db', 'todogas_manual_demo')

// Cuentas de la demo local (docs/DEMO.md), leidas del archivo, mas las que
// crea preparar_datos_capturas.py (todas con el dominio de la demo).
function leerCuentas() {
  const md = fs.readFileSync(path.join(raiz, 'docs', 'DEMO.md'), 'utf8')
  const roles = { admin: 'Administrador', supervisor: 'Supervisor', tecnico: 'Técnico', biomedica: 'Biomédica' }
  const cuentas = {}
  for (const linea of md.split('\n')) {
    const celdas = linea.split('|').map((c) => c.replace(/`/g, '').trim())
    if (celdas.length < 5) continue
    for (const [rol, prefijo] of Object.entries(roles)) {
      if (celdas[1].startsWith(prefijo)) cuentas[rol] = { correo: celdas[2], clave: celdas[3] }
    }
  }
  const extra = (n, c) => ({ correo: `${n}@demo.todogas.local`, clave: c })
  cuentas.revisor = extra('revisor', 'TgDemo-Revisor-2026') // supervisor sin firma guardada
  cuentas.nuevo = extra('nuevo', 'TgDemo-Nuevo-2026') // debe cambiar la contrasena
  cuentas.aviso = extra('aviso', 'TgDemo-Aviso-2026') // nunca acepto el aviso de privacidad
  return cuentas
}

const cuentas = leerCuentas()
const { capturas: todas } = JSON.parse(fs.readFileSync(path.join(aqui, 'capturas.json'), 'utf8'))
const porN = Object.fromEntries(todas.map((c) => [c.n, c]))
// `como: N` hereda rol, ruta, pasos y viewport de la entrada N (recortes del manual rapido).
const resolver = (c) => {
  if (!c.como) return c
  const base = resolver(porN[c.como])
  // `mas` agrega pasos a los heredados; `pasos` los reemplaza.
  const pasos = c.pasos ?? [...(base.pasos ?? []), ...(c.mas ?? [])]
  const { elemento, clip, fullPage, omitir, motivo, ...heredable } = base
  const mezcla = { ...heredable, ...c, pasos }
  return mezcla
}
// `soloEnCopia`: la captura escribe en la base (p. ej. aplicar una importacion). Solo corre si
// se indica otra base con --db (una copia); con la base principal se omite para no alterarla.
const lista = todas
  .filter((c) => !c.omitir && !(c.soloEnCopia && DB_NAME === 'todogas_manual_demo') && (!solo || solo.includes(c.n)))
  .map(resolver)
const dirSesiones = path.join(aqui, '.sesiones')
fs.mkdirSync(dirSesiones, { recursive: true })

const VIEWPORT = { width: 1366, height: 768 }

async function aceptarAviso(page) {
  const boton = page.getByRole('button', { name: 'Acepto', exact: true })
  if (await boton.isVisible().catch(() => false)) {
    await boton.click()
    await page.waitForTimeout(800)
  }
}

async function entrar(page, cuenta, { aceptar = true } = {}) {
  await page.goto(`${BASE}/login`)
  await page.fill('#email', cuenta.correo)
  await page.fill('#password', cuenta.clave)
  await page.click('button[type=submit]')
  await page.waitForTimeout(2500)
  if (aceptar) await aceptarAviso(page)
}

async function iniciarSesion(browser, rol) {
  const estado = path.join(dirSesiones, `${rol}.json`)
  const cuenta = cuentas[rol]
  if (!cuenta) throw new Error(`No hay cuenta de demo para el rol "${rol}"`)
  const ctx = await browser.newContext({ viewport: VIEWPORT, deviceScaleFactor: 1 })
  const page = await ctx.newPage()
  await entrar(page, cuenta)
  if (page.url().includes('/cambiar-contrasena')) {
    throw new Error(`La cuenta ${rol} pide cambiar la contraseña; ajusta la demo (must_change_password).`)
  }
  await page.waitForLoadState('networkidle').catch(() => {})
  await ctx.storageState({ path: estado })
  await ctx.close()
  return estado
}

// Enlace de restablecimiento de contrasena valido para el usuario "restablecer"
// (sin tocar su contrasena). El token dura 1 hora.
function enlaceRestablecer() {
  const codigo =
    "from django.contrib.auth.tokens import default_token_generator as g;" +
    "from django.utils.http import urlsafe_base64_encode as e;from django.utils.encoding import force_bytes as f;" +
    "from apps.users.models import User;u=User.objects.get(email='restablecer@demo.todogas.local');" +
    "print('ENLACE|'+e(f(u.pk))+'|'+g.make_token(u))"
  const salida = execFileSync(
    path.join(raiz, 'backend', '.venv', 'Scripts', 'python.exe'),
    [path.join(raiz, 'backend', 'manage.py'), 'shell', '-c', codigo],
    { env: { ...process.env, DB_NAME, PYTHONIOENCODING: 'utf-8' }, encoding: 'utf8' },
  )
  const m = salida.match(/ENLACE\|([^|\s]+)\|(\S+)/)
  if (!m) throw new Error('No se pudo generar el enlace de restablecimiento')
  return `/restablecer-contrasena?uid=${m[1]}&token=${m[2]}`
}

function localizar(page, sel) {
  return sel.startsWith('css=') || /^[#.\[]/.test(sel)
    ? page.locator(sel.replace(/^css=/, '')).first()
    : page.getByText(sel, { exact: false }).first()
}

async function ejecutarPasos(page, pasos = [], ctx) {
  for (const p of pasos) {
    if (p.esperar) await page.waitForTimeout(p.esperar)
    else if (p.esperarTexto) await page.getByText(p.esperarTexto).first().waitFor({ timeout: 15000 })
    else if (p.ir) {
      await page.goto(`${BASE}${p.ir === 'ENLACE' ? enlaceRestablecer() : p.ir}`)
      await page.waitForLoadState('networkidle').catch(() => {})
    } else if (p.click) await localizar(page, p.click).click()
    else if (p.boton) await page.getByRole('button', { name: p.boton, exact: !!p.exacto }).first().click()
    else if (p.enlace) await page.getByRole('link', { name: p.enlace, exact: !!p.exacto }).first().click()
    else if (p.pestana) await page.getByRole('tab', { name: p.pestana }).or(page.getByRole('button', { name: p.pestana })).first().click()
    else if (p.fila) await page.locator('tr', { hasText: p.fila }).first().click()
    else if (p.botonEnFila) await page.locator('tr', { hasText: p.botonEnFila[0] }).first().getByRole('button', { name: p.botonEnFila[1] }).first().click()
    else if (p.marcar) await page.getByLabel(p.marcar).first().check()
    else if (p.marcarFila) await page.locator('tr', { hasText: p.marcarFila }).first().locator('input[type=checkbox]').first().check()
    else if (p.rellenar) await page.fill(p.rellenar[0], p.rellenar[1])
    else if (p.escribir) await page.getByLabel(p.escribir[0]).first().fill(p.escribir[1])
    else if (p.seleccionar) await page.selectOption(p.seleccionar[0], p.seleccionar[1])
    else if (p.hover) await localizar(page, p.hover).hover()
    else if (p.tecla) await page.keyboard.press(p.tecla)
    else if (p.scroll !== undefined) await page.mouse.wheel(0, p.scroll)
    else if (p.scrollElemento) await page.locator(p.scrollElemento).first().scrollIntoViewIfNeeded()
    else if (p.js) await page.evaluate(p.js)
    else if (p.subir) await page.setInputFiles(p.subir[0], path.join(aqui, p.subir[1]))
    else if (p.pdfVista) {
      // «Vista previa» del formato del acta: el navegador sin cabeza no pinta PDF en un iframe,
      // asi que se toma el PDF de la respuesta, se convierte a PNG (pypdfium2) y se pone
      // en lugar del iframe. Se ve la ventana real con las paginas del acta.
      const [resp] = await Promise.all([
        page.waitForResponse((r) => r.url().includes('report-settings/preview')),
        page.getByRole('button', { name: 'Vista previa' }).first().click(),
      ])
      const pdf = path.join(dirSesiones, 'vista.pdf')
      fs.writeFileSync(pdf, await resp.body())
      const prefijo = path.join(dirSesiones, 'vista')
      const n = Number(execFileSync(path.join(raiz, 'backend', '.venv', 'Scripts', 'python.exe'),
        [path.join(aqui, 'render_pdf.py'), pdf, prefijo, String(p.pdfVista.escala ?? 1.1)], { encoding: 'utf8' }).trim())
      const paginas = (p.pdfVista.paginas ?? [1]).filter((k) => k <= n)
      const imgs = paginas.map((k) => 'data:image/png;base64,' + fs.readFileSync(`${prefijo}-${k}.png`).toString('base64'))
      await page.waitForSelector('iframe[title="Vista previa del acta"]')
      await page.evaluate((srcs) => {
        const f = document.querySelector('iframe[title="Vista previa del acta"]')
        const d = document.createElement('div')
        d.className = f.className
        d.style.cssText = 'overflow:auto;background:#e5e7eb;display:flex;gap:12px;padding:8px;justify-content:center'
        d.innerHTML = srcs.map((s) => `<img src="${s}" style="height:100%;width:auto;box-shadow:0 1px 4px rgba(0,0,0,.3)"/>`).join('')
        f.replaceWith(d)
        // La ventana por defecto es angosta para dos paginas: se ensancha para que se lean.
        for (let a = d.parentElement; a && a !== document.body; a = a.parentElement) {
          if (/max-w-/.test(a.className || '')) { a.style.maxWidth = '1180px'; break }
        }
        d.querySelectorAll('img').forEach((i) => { i.style.height = 'auto'; i.style.width = '49%'; i.style.alignSelf = 'flex-start' })
      }, imgs)
    } else if (p.firma) {
      const caja = await page.locator(p.firma).first().boundingBox()
      await page.mouse.move(caja.x + 30, caja.y + caja.height / 2)
      await page.mouse.down()
      for (let i = 1; i <= 14; i++) {
        await page.mouse.move(caja.x + 30 + i * (caja.width - 60) / 14, caja.y + caja.height / 2 + (i % 2 ? -28 : 28), { steps: 3 })
      }
      await page.mouse.up()
    }
    await page.waitForLoadState('networkidle').catch(() => {})
    await page.waitForTimeout(p.despues ?? 400)
  }
}

const browser = await chromium.launch()
const sesiones = {}
let fallos = 0
for (const c of lista) {
  const t0 = Date.now()
  let ctx
  try {
    const viewport = c.viewport ?? VIEWPORT
    let storageState
    if (c.cuenta) {
      // Entra con una cuenta propia en un contexto efimero (no se guarda la sesion).
    } else if (c.rol && c.rol !== 'ninguno') {
      sesiones[c.rol] ??= await iniciarSesion(browser, c.rol)
      storageState = sesiones[c.rol]
    }
    ctx = await browser.newContext({ viewport, deviceScaleFactor: 1, storageState, acceptDownloads: true })
    const page = await ctx.newPage()
    if (c.cuenta) await entrar(page, cuentas[c.cuenta], { aceptar: !c.sinAceptarAviso })
    if (c.ruta) {
      await page.goto(`${BASE}${c.ruta}`)
      await page.waitForLoadState('networkidle').catch(() => {})
    }
    if (!c.sinAceptarAviso) await aceptarAviso(page)
    await ejecutarPasos(page, c.pasos, ctx)
    const destino = path.join(raiz, c.archivo)
    fs.mkdirSync(path.dirname(destino), { recursive: true })
    const opc = { path: destino, type: 'png' }
    if (c.fullPage) opc.fullPage = true
    if (c.clip) opc.clip = c.clip
    if (c.elemento) await page.locator(c.elemento).first().screenshot({ path: destino, type: 'png' })
    else await page.screenshot(opc)
    console.log(`OK   #${c.n} ${c.archivo} (${((Date.now() - t0) / 1000).toFixed(1)} s)`)
  } catch (e) {
    fallos++
    console.error(`FALLO #${c.n}: ${e.message.split('\n').slice(0, 3).join(' | ').slice(0, 300)}`)
  } finally {
    await ctx?.close().catch(() => {})
  }
}
await browser.close()
fs.rmSync(dirSesiones, { recursive: true, force: true })
process.exit(fallos ? 1 : 0)
