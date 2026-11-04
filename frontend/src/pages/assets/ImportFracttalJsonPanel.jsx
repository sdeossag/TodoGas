import { useState } from 'react'
import { Link } from 'react-router-dom'
import Spinner from '../../components/ui/Spinner'
import Modal from '../../components/ui/Modal'
import Icon from '../../components/ui/Icon'
import { usePreviewFracttalJsonImport, useImportFracttalJson } from '../../api/assets'
import { apiErrorMessage } from '../../utils/apiError'
import {
  LIMITE_JSON_MB, errorDeArchivoJson, puedeImportarJson, textoResultadoJson,
} from '../../utils/importacionFracttalJson'

function Tarjeta({ titulo, children }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-card p-4">
      <p className="text-xs font-medium text-gray-500">{titulo}</p>
      {children}
    </div>
  )
}

function Numeros({ lineas }) {
  return (
    <div className="mt-1 text-sm text-gray-600 space-y-0.5">
      {lineas.map(([n, texto]) => (
        <p key={texto}><span className="font-semibold text-gray-900">{n}</span> {texto}</p>
      ))}
    </div>
  )
}

function Avisos({ avisos }) {
  if (!avisos?.length) return null
  return (
    <div className="rounded-lg bg-amber-50 border border-amber-200 p-3">
      <p className="text-sm font-medium text-amber-800 mb-1">Avisos ({avisos.reduce((n, a) => n + a.cantidad, 0)})</p>
      <ul className="text-xs text-amber-900 space-y-1 max-h-64 overflow-y-auto">
        {avisos.map((a) => (
          <li key={a.mensaje}>
            <b>{a.cantidad}×</b> {a.mensaje}
            {a.ejemplos?.length > 0 && <span className="text-amber-700"> (ej.: {a.ejemplos.join('; ')})</span>}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function ImportFracttalJsonPanel() {
  const [archivo, setArchivo] = useState(null)
  const [resumen, setResumen] = useState(null)
  const [resultado, setResultado] = useState(null)
  const [confirmar, setConfirmar] = useState(false)
  const [errorLocal, setErrorLocal] = useState('')

  const preview = usePreviewFracttalJsonImport()
  const importar = useImportFracttalJson()
  const errorArchivo = errorDeArchivoJson(archivo)

  function elegir(file) {
    setArchivo(file ?? null)
    setErrorLocal('')
    preview.reset()
  }

  function reiniciar() {
    setArchivo(null); setResumen(null); setResultado(null); setConfirmar(false); setErrorLocal('')
    preview.reset(); importar.reset()
  }

  function aplicar() {
    importar.mutate(archivo, {
      onSuccess: (data) => { setConfirmar(false); setResultado(data) },
      onError: (err) => {
        setConfirmar(false)
        const data = err?.response?.data
        if (err?.response?.status === 400 && data?.warnings) setResumen(data)
        else setErrorLocal(apiErrorMessage(err))
      },
    })
  }

  if (resultado) {
    const c = resultado.applied_counts ?? {}
    return (
      <div className="bg-white rounded-xl border border-gray-200 shadow-card p-4 sm:p-6 space-y-4">
        <div className="flex items-center gap-2 text-green-700">
          <Icon name="check" className="w-5 h-5" />
          <h2 className="text-lg font-semibold">Importación terminada</h2>
        </div>
        <ul className="text-sm text-gray-700 list-disc pl-5">
          <li>{c.locations_created ?? 0} ubicaciones nuevas, {c.assets_created ?? 0} equipos nuevos ({c.assets_updated ?? 0} actualizados)</li>
          <li>{c.plans_created ?? 0} protocolos nuevos con {c.plan_tasks_created ?? 0} tareas</li>
          <li>{c.work_orders_created ?? 0} OT históricas con {c.responses_created ?? 0} respuestas de checklist</li>
          <li>{c.pending_tasks_created ?? 0} tareas pendientes programadas</li>
          <li>{c.photos_pending ?? 0} fotos quedan pendientes de descargar de Fracttal</li>
        </ul>
        <Avisos avisos={resultado.warnings} />
        <div className="flex flex-col sm:flex-row gap-2">
          <Link to="/activos" className="px-5 py-2.5 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light text-center">
            Ir a Activos
          </Link>
          <button type="button" onClick={reiniciar}
            className="px-4 py-2.5 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50">
            Empezar de nuevo
          </button>
        </div>
      </div>
    )
  }

  if (resumen) {
    const o = resumen.work_orders ?? {}
    return (
      <div className="space-y-4">
        <p className="text-sm text-gray-600">Sede: <b>{resumen.sede}</b></p>
        <div className="grid gap-3 sm:grid-cols-3">
          <Tarjeta titulo="Hospital y ubicaciones">
            <Numeros lineas={[
              [resumen.hospitals?.create?.length ?? 0, 'hospitales nuevos'],
              [resumen.locations?.create ?? 0, 'ubicaciones nuevas'],
              [resumen.locations?.update ?? 0, 'ubicaciones se actualizan'],
            ]} />
          </Tarjeta>
          <Tarjeta titulo="Equipos">
            <Numeros lineas={[[resumen.assets?.create ?? 0, 'nuevos'], [resumen.assets?.update ?? 0, 'se actualizan']]} />
          </Tarjeta>
          <Tarjeta titulo="Protocolos">
            <Numeros lineas={[
              [resumen.plans?.create ?? 0, 'nuevos'], [resumen.plans?.update ?? 0, 'existentes'],
              [resumen.plan_tasks?.create ?? 0, 'tareas nuevas'], [resumen.checklist_fields ?? 0, 'campos de checklist'],
            ]} />
          </Tarjeta>
          <Tarjeta titulo="Historial de OT">
            <Numeros lineas={[
              [o.create ?? 0, `a crear (${o.completed ?? 0} finalizadas, ${o.cancelled ?? 0} canceladas)`],
              [o.existing ?? 0, 'ya importadas'], [resumen.tasks ?? 0, 'tareas'], [resumen.responses ?? 0, 'respuestas'],
            ]} />
          </Tarjeta>
          <Tarjeta titulo="Evidencia">
            <Numeros lineas={[[resumen.signatures ?? 0, 'OT con firma del técnico'], [resumen.photos_pending ?? 0, 'fotos pendientes de descargar']]} />
          </Tarjeta>
          <Tarjeta titulo="Activadores">
            <div className="mt-1 text-sm text-gray-600">
              {Object.entries(resumen.triggers ?? {}).map(([k, v]) => <p key={k}><b className="text-gray-900">{v}</b> {k}</p>)}
            </div>
          </Tarjeta>
        </div>

        {resumen.errors?.length > 0 && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
            {resumen.errors.map((e) => <p key={e}>{e}</p>)}
          </div>
        )}
        <Avisos avisos={resumen.warnings} />
        {errorLocal && <p role="alert" className="text-sm text-red-600">{errorLocal}</p>}

        <div className="flex flex-col-reverse sm:flex-row sm:items-center sm:justify-between gap-3">
          <button type="button" onClick={reiniciar}
            className="px-4 py-2 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50">
            Empezar de nuevo
          </button>
          <button type="button" disabled={!puedeImportarJson(resumen)} onClick={() => setConfirmar(true)}
            className="px-5 py-2.5 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light disabled:opacity-50 disabled:cursor-not-allowed">
            Importar
          </button>
        </div>

        {confirmar && (
          <Modal title="¿Importar ahora?" onClose={() => !importar.isPending && setConfirmar(false)} width="max-w-md">
            <p className="text-sm text-gray-600">
              Se va a guardar en el sistema: {textoResultadoJson(resumen).join(', ') || 'sin cambios'}.
              El historial de OT queda como histórico: sin actas ni correos.
            </p>
            <div className="flex justify-end gap-2 mt-5">
              <button type="button" disabled={importar.isPending} onClick={() => setConfirmar(false)}
                className="px-4 py-2 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50">
                Cancelar
              </button>
              <button type="button" disabled={importar.isPending} onClick={aplicar}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-brand text-white hover:bg-brand-light disabled:opacity-60 inline-flex items-center gap-2">
                {importar.isPending && <Spinner className="h-4 w-4 text-white" />}
                Sí, importar
              </button>
            </div>
          </Modal>
        )}
      </div>
    )
  }

  const error = errorArchivo || errorLocal || (preview.isError ? apiErrorMessage(preview.error) : '')
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-card p-4 sm:p-6 space-y-5">
      <div className="rounded-lg bg-gray-50 border border-gray-100 p-3 text-sm text-gray-600">
        <p className="font-medium text-gray-800 mb-1">Cómo obtener el archivo</p>
        <p>
          Con el extractor de Fracttal (docs/fracttal/extractor-fracttal.js) se descarga un archivo .json
          con la sede completa: ubicaciones, equipos, protocolos con su checklist y el historial de OT.
        </p>
      </div>
      <div className="rounded-lg border border-dashed border-gray-300 p-4">
        <label htmlFor="fracttal-json" className="block text-sm font-medium text-gray-800">Archivo del extractor</label>
        <p className="text-xs text-gray-500 mb-2">Archivo .json, máximo {LIMITE_JSON_MB} MB</p>
        <input id="fracttal-json" type="file" accept=".json,application/json"
          onChange={(e) => elegir(e.target.files?.[0])}
          className="block w-full text-sm text-gray-600 file:mr-3 file:px-3 file:py-2 file:rounded-lg file:border-0 file:bg-brand/10 file:text-brand file:text-sm file:font-medium hover:file:bg-brand/20" />
        {archivo && <p className="mt-2 text-xs text-gray-600 truncate">{archivo.name}</p>}
      </div>
      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
      <div className="flex justify-end">
        <button type="button" disabled={!archivo || Boolean(errorArchivo) || preview.isPending}
          onClick={() => preview.mutate(archivo, { onSuccess: setResumen })}
          className="w-full sm:w-auto px-5 py-2.5 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2">
          {preview.isPending && <Spinner className="h-4 w-4 text-white" />}
          {preview.isPending ? 'Revisando…' : 'Revisar archivo'}
        </button>
      </div>
    </div>
  )
}
