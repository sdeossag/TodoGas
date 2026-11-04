import { useEffect, useMemo, useState } from 'react'

import {
  usePreviewReportSettings,
  useReportSettings,
  useSaveReportSettings,
} from '../../api/reports'
import Icon from '../../components/ui/Icon'
import Modal from '../../components/ui/Modal'

/**
 * Qué imprime el acta de servicio (#107). Un solo formato con interruptores,
 * como las "Opciones de Impresión" de Fracttal: aplica a las actas nuevas y
 * las ya generadas no cambian. Lo que prueba el servicio no se puede apagar.
 */
export default function ReportSettingsPage() {
  const { data, isLoading, error } = useReportSettings()
  const guardar = useSaveReportSettings()
  const previa = usePreviewReportSettings()

  const [opciones, setOpciones] = useState(null)
  // Razón social y NIT del encabezado del acta (vacíos: el encabezado no los muestra).
  const [empresa, setEmpresa] = useState(null) // { company_name, company_tax_id }
  const [pdf, setPdf] = useState(null) // { url, workOrder }
  const [aviso, setAviso] = useState('')

  useEffect(() => {
    if (data && opciones === null) {
      setOpciones(data.options)
      setEmpresa({ company_name: data.company_name ?? '', company_tax_id: data.company_tax_id ?? '' })
    }
  }, [data, opciones])

  // El PDF de la vista previa vive en memoria del navegador: se suelta al cerrar.
  useEffect(() => () => pdf && URL.revokeObjectURL(pdf.url), [pdf])

  const secciones = useMemo(() => {
    const porSeccion = new Map()
    for (const item of data?.catalog ?? []) {
      if (!porSeccion.has(item.section)) porSeccion.set(item.section, [])
      porSeccion.get(item.section).push(item)
    }
    return [...porSeccion]
  }, [data])

  const cambios = useMemo(() => {
    if (!data || !opciones) return {}
    return Object.fromEntries(
      Object.entries(opciones).filter(([k, v]) => data.options[k] !== v)
    )
  }, [data, opciones])
  const cambiosEmpresa = useMemo(() => {
    if (!data || !empresa) return {}
    return Object.fromEntries(
      Object.entries(empresa).filter(([k, v]) => (data[k] ?? '') !== v.trim())
    )
  }, [data, empresa])
  const nCambios = Object.keys(cambios).length + Object.keys(cambiosEmpresa).length
  const hayCambios = nCambios > 0
  const apagadas = opciones ? Object.values(opciones).filter((v) => !v).length : 0

  if (isLoading || !opciones || !empresa) {
    return <p className="text-sm text-gray-500">{error ? 'No se pudo cargar la configuración del acta.' : 'Cargando…'}</p>
  }

  const cambiar = (clave) => setOpciones((o) => ({ ...o, [clave]: !o[clave] }))

  function verPrevia() {
    previa.mutate({ options: opciones, ...empresa }, {
      onSuccess: ({ blob, workOrder }) => setPdf({ url: URL.createObjectURL(blob), workOrder }),
    })
  }

  function guardarCambios() {
    const envio = { ...cambiosEmpresa }
    if (Object.keys(cambios).length) envio.options = cambios
    guardar.mutate(envio, {
      onSuccess: (nuevo) => {
        setOpciones(nuevo.options)
        setEmpresa({ company_name: nuevo.company_name ?? '', company_tax_id: nuevo.company_tax_id ?? '' })
        setAviso('Guardado. Las próximas actas saldrán con este formato.')
        setTimeout(() => setAviso(''), 5000)
      },
    })
  }

  const errorPrevia = previa.error?.response?.status === 404
    ? 'Todavía no hay OTs finalizadas para mostrar un acta de ejemplo.'
    : previa.error && 'No se pudo generar la vista previa.'

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">Formato del acta</h1>
        <p className="text-sm text-gray-500 mt-0.5 max-w-2xl">
          Qué imprime el acta de servicio. Aplica a las actas que se generen desde ahora; las ya
          generadas no cambian.
          {data.updated_by_name && (
            <> Último cambio: {data.updated_by_name} ({new Date(data.updated_at).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' })})</>
          )}
        </p>
      </div>

      <section className="bg-white rounded-xl border border-gray-200 shadow-card p-5">
        <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
          <Icon name="key" className="w-4 h-4 text-gray-400" /> Siempre incluidos
        </h2>
        <p className="text-xs text-gray-500 mt-1">
          Es lo que prueba el servicio, por eso no se puede quitar.
        </p>
        <ul className="mt-3 flex flex-wrap gap-2">
          {data.always_included.map((x) => (
            <li key={x} className="text-xs text-gray-600 bg-gray-50 border border-gray-200 rounded-full px-3 py-1">{x}</li>
          ))}
        </ul>
      </section>

      <section className="bg-white rounded-xl border border-gray-200 shadow-card p-5">
        <h2 className="text-sm font-semibold text-gray-700">Encabezado del acta</h2>
        <p className="text-xs text-gray-500 mt-1">
          Salen en el centro del encabezado, bajo el logo. Si los dejas vacíos, el acta no los muestra.
        </p>
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <label className="block text-sm text-gray-700">
            Razón social
            <input
              type="text"
              value={empresa.company_name}
              maxLength={200}
              onChange={(e) => setEmpresa((x) => ({ ...x, company_name: e.target.value }))}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="block text-sm text-gray-700">
            NIT
            <input
              type="text"
              value={empresa.company_tax_id}
              maxLength={50}
              onChange={(e) => setEmpresa((x) => ({ ...x, company_tax_id: e.target.value }))}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
        </div>
      </section>

      <div className="grid gap-5 lg:grid-cols-2">
        {secciones.map(([seccion, items]) => (
          <section key={seccion} className="bg-white rounded-xl border border-gray-200 shadow-card p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">{seccion}</h2>
            <ul className="divide-y divide-gray-100">
              {items.map(({ key, label }) => (
                <li key={key}>
                  <label className="flex items-center justify-between gap-4 py-2.5 cursor-pointer">
                    <span className={`text-sm ${opciones[key] ? 'text-gray-800' : 'text-gray-400 line-through'}`}>
                      {label}
                    </span>
                    <input
                      type="checkbox"
                      role="switch"
                      checked={opciones[key]}
                      onChange={() => cambiar(key)}
                      aria-label={label}
                      className="sr-only peer"
                    />
                    <span aria-hidden="true"
                      className="relative shrink-0 w-10 h-6 rounded-full bg-gray-300 transition-colors peer-checked:bg-brand peer-focus-visible:ring-2 peer-focus-visible:ring-brand/40 after:absolute after:top-0.5 after:left-0.5 after:w-5 after:h-5 after:rounded-full after:bg-white after:shadow after:transition-transform peer-checked:after:translate-x-4" />
                  </label>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      {/* Barra pegada al pie del contenido (no de la ventana: taparía el menú). */}
      <div className="sticky bottom-4 z-20 bg-white/95 backdrop-blur border border-gray-200 rounded-xl shadow-card">
        <div className="px-4 py-3 flex flex-wrap items-center gap-3 justify-end">
          <p className="text-xs text-gray-500 mr-auto" role="status">
            {aviso || errorPrevia || guardar.error?.response?.data?.options
              || guardar.error?.response?.data?.company_name || guardar.error?.response?.data?.company_tax_id || (
              hayCambios
                ? `${nCambios} cambio(s) sin guardar`
                : apagadas ? `${apagadas} campo(s) ocultos en el acta` : 'El acta imprime todo'
            )}
          </p>
          {hayCambios && (
            <button
              type="button"
              onClick={() => {
                setOpciones(data.options)
                setEmpresa({ company_name: data.company_name ?? '', company_tax_id: data.company_tax_id ?? '' })
              }}
              className="btn-secondary"
            >
              Descartar
            </button>
          )}
          <button type="button" onClick={verPrevia} disabled={previa.isPending} className="btn-secondary">
            <Icon name="eye" className="w-4 h-4" /> {previa.isPending ? 'Generando…' : 'Vista previa'}
          </button>
          <button type="button" onClick={guardarCambios} disabled={!hayCambios || guardar.isPending} className="btn-primary">
            {guardar.isPending ? 'Guardando…' : 'Guardar cambios'}
          </button>
        </div>
      </div>

      {pdf && (
        <Modal
          title="Vista previa del acta"
          subtitle={`Con los interruptores de esta pantalla${pdf.workOrder ? `, sobre la ${pdf.workOrder}` : ''}. No se guarda.`}
          onClose={() => setPdf(null)}
          width="max-w-4xl"
        >
          <iframe title="Vista previa del acta" src={pdf.url} className="w-full h-[70vh] rounded border border-gray-200" />
        </Modal>
      )}
    </div>
  )
}
