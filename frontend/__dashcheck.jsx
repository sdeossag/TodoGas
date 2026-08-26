/* Harness temporal: renderiza DashboardPage en jsdom con datos simulados. */
import { JSDOM } from 'jsdom'

const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', {
  url: 'http://localhost/dashboard',
  pretendToBeVisual: true,
})
global.window = dom.window
global.document = dom.window.document
Object.defineProperty(global, 'navigator', { value: dom.window.navigator, configurable: true })
global.HTMLElement = dom.window.HTMLElement
global.Element = dom.window.Element
global.Node = dom.window.Node
global.SVGElement = dom.window.SVGElement
global.getComputedStyle = dom.window.getComputedStyle
global.localStorage = dom.window.localStorage
global.location = dom.window.location
global.requestAnimationFrame = (cb) => setTimeout(() => cb(Date.now()), 0)
global.cancelAnimationFrame = (id) => clearTimeout(id)
global.IS_REACT_ACT_ENVIRONMENT = true

// ResponsiveContainer mide con ResizeObserver — le damos un tamano fijo.
const W = 560
const H = 260
class RO {
  constructor(cb) { this.cb = cb }
  observe(el) {
    setTimeout(() => this.cb([{ target: el, contentRect: { width: W, height: H } }]), 0)
  }
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = RO
dom.window.ResizeObserver = RO
Object.defineProperty(dom.window.HTMLElement.prototype, 'offsetWidth', { get: () => W })
Object.defineProperty(dom.window.HTMLElement.prototype, 'offsetHeight', { get: () => H })
// Solo los contenedores HTML miden; los <text> del SVG se dejan sin medida
// para no disparar el descarte de ticks por colision de recharts.
dom.window.HTMLElement.prototype.getBoundingClientRect = () => ({
  width: W, height: H, top: 0, left: 0, bottom: H, right: W, x: 0, y: 0, toJSON() {},
})

async function main() {
  const React = (await import('react')).default
  const { createRoot } = await import('react-dom/client')
  const { act } = await import('react')
  const { QueryClient, QueryClientProvider } = await import('@tanstack/react-query')
  const { MemoryRouter } = await import('react-router-dom')
  const apiClient = (await import('./src/api/client.js')).default
  const DashboardPage = (await import('./src/pages/dashboard/DashboardPage.jsx')).default

  // ── Datos simulados con las formas exactas del backend ──────────────────────
  const MOCKS = {
    '/api/dashboard/': {
      compliance: { percentage: 91.7, completed: 11, generated: 12, month: '2026-08' },
      mttr: { mttr_hours: 4.25, sample_size: 8 },
      overdue: { count: 3, critical: 1 },
      ots_by_status: {
        PENDING: 5, IN_PROGRESS: 2, IN_REVIEW: 1, COMPLETED: 12, CANCELLED: 1,
      },
      ots_by_technician: [
        { technician_id: 't1', technician_name: 'Ana Ruiz', assigned: 9, completed: 7, overdue: 2 },
        { technician_id: 't2', technician_name: 'Luis Paz', assigned: 6, completed: 6, overdue: 0 },
      ],
      assets_without_maintenance: [
        { asset_id: 'a1', asset_name: 'Central de oxigeno', asset_code: 'OX-01',
          hospital_name: 'Hospital San Juan', days_since_last_pm: 143 },
        { asset_id: 'a2', asset_name: 'Compresor aire medicinal', asset_code: 'AM-02',
          hospital_name: 'Clinica Norte', days_since_last_pm: null },
      ],
    },
    '/api/dashboard/compliance-history/': [
      { percentage: 91.7, completed: 11, generated: 12, month: '2025-09' },
      { percentage: 0.0, completed: 0, generated: 0, month: '2025-10' },
      { percentage: 42.0, completed: 4, generated: 10, month: '2025-11' },
      { percentage: 66.7, completed: 6, generated: 9, month: '2025-12' },
      { percentage: 100.0, completed: 5, generated: 5, month: '2026-01' },
      { percentage: 80.0, completed: 8, generated: 10, month: '2026-02' },
      { percentage: 55.0, completed: 11, generated: 20, month: '2026-03' },
      { percentage: 30.0, completed: 3, generated: 10, month: '2026-04' },
      { percentage: 95.0, completed: 19, generated: 20, month: '2026-05' },
      { percentage: 0.0, completed: 0, generated: 0, month: '2026-06' },
      { percentage: 72.0, completed: 18, generated: 25, month: '2026-07' },
      { percentage: 91.7, completed: 11, generated: 12, month: '2026-08' },
    ],
    '/api/dashboard/assets-status/': { on_time: 34, due_soon: 7, overdue: 4, no_plan: 12, total: 57 },
    '/api/hospitals/': [
      { id: 'h1', name: 'Hospital San Juan' },
      { id: 'h2', name: 'Clinica Norte' },
    ],
  }

  apiClient.defaults.adapter = async (config) => {
    const data = MOCKS[config.url]
    if (data === undefined) throw new Error(`URL sin mock: ${config.url}`)
    return { data, status: 200, statusText: 'OK', headers: {}, config }
  }

  try {
    const probe = await apiClient.get('/api/dashboard/', { params: { days: 30 } })
    console.log('PROBE OK, compliance =', JSON.stringify(probe.data.compliance))
  } catch (e) {
    console.log('PROBE FALLO:', e.message)
  }

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const root = createRoot(document.getElementById('root'))

  await act(async () => {
    root.render(
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(MemoryRouter, null, React.createElement(DashboardPage))
      )
    )
  })
  // Dejar correr fetches + ResizeObserver + relayout de recharts
  for (let i = 0; i < 6; i++) {
    await act(async () => { await new Promise((r) => setTimeout(r, 60)) })
  }

  const html = document.getElementById('root').innerHTML
  const text = document.getElementById('root').textContent

  const svgs = document.querySelectorAll('svg.recharts-surface')
  const sectors = document.querySelectorAll('.recharts-pie-sector path, .recharts-sector')
  const bars = document.querySelectorAll('.recharts-bar-rectangle path, .recharts-rectangle')
  const xTicks = [...document.querySelectorAll('.recharts-xAxis .recharts-cartesian-axis-tick-value')]
    .map((t) => t.textContent)
  const yTicks = [...document.querySelectorAll('.recharts-yAxis .recharts-cartesian-axis-tick-value')]
    .map((t) => t.textContent)
  const fills = [...new Set([...sectors, ...bars].map((n) => n.getAttribute('fill')))]

  console.log('--- recharts ---')
  console.log('superficies svg:', svgs.length)
  console.log('sectores dona  :', sectors.length)
  console.log('barras         :', bars.length)
  console.log('eje X          :', xTicks.join(' '))
  console.log('eje Y          :', yTicks.join(' '))
  console.log('colores usados :', fills.join(' '))
  console.log('--- contenido ---')
  console.log('skeletons pendientes:', document.querySelectorAll('.animate-pulse').length)
  for (const needle of [
    '91.7%', '11/12 OTs', '4.3h', 'Basado en 8 OTs correctivas', '3', '1 criticas',
    '12', 'De 21 ordenes', 'Ana Ruiz', 'Central de oxigeno', '143 dias', 'Nunca',
    'Al dia', '34', '12',
  ]) {
    console.log(`  ${text.includes(needle) ? 'OK ' : 'FALTA'}  "${needle}"`)
  }
  console.log('--- orden tecnicos (por vencidas desc) ---')
  console.log([...document.querySelectorAll('tbody tr')].map((r) => r.textContent).join(' | '))
  console.log('--- ejes (sondeo) ---')
  console.log('tick groups   :', document.querySelectorAll('.recharts-cartesian-axis-tick').length)
  console.log('textos en svg :',
    [...document.querySelectorAll('svg text')].map((t) => t.textContent).join('|'))
  const bar = document.querySelector('.recharts-bar')
  console.log('clases de eje :',
    [...new Set([...document.querySelectorAll('svg *')].map((n) => n.getAttribute('class')).filter(Boolean))]
      .filter((c) => c.includes('axis')).join(' / '))
  console.log('--- longitud html:', html.length)

}

main().catch((e) => { console.error(e); process.exit(1) })
