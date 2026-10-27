import { useState } from 'react'
import { Link } from 'react-router-dom'
import Spinner from '../../components/ui/Spinner'
import Modal from '../../components/ui/Modal'
import Icon from '../../components/ui/Icon'
import { usePreviewFracttalImport, useImportFracttal } from '../../api/assets'
import { apiErrorMessage } from '../../utils/apiError'
import {
  FILTROS_FILAS, MENSAJE_CORREGIR, contarFilas, errorDeArchivo, filtrarFilas, hayArchivos,
  nombreArchivo, puedeImportar, textoBotonImportar, textoProtocolos, textoResultado,
} from '../../utils/importacionFracttal'

const ACCION = {
  create: { label: 'Nuevo', cls: 'bg-green-100 text-green-700' },
  update: { label: 'Se actualiza', cls: 'bg-blue-100 text-blue-700' },
  error: { label: 'Error', cls: 'bg-red-100 text-red-700' },
}

export default function ImportFracttalPage() {
  const [archivos, setArchivos] = useState({ ubicaciones: null, equipos: null })
  const [resumen, setResumen] = useState(null)
  const [resultado, setResultado] = useState(null)
  const [confirmar, setConfirmar] = useState(false)
  const [filtro, setFiltro] = useState('todas')
  const [errorLocal, setErrorLocal] = useState('')

  const preview = usePreviewFracttalImport()
  const importar = useImportFracttal()

  const errorArchivos = errorDeArchivo(archivos.ubicaciones) || errorDeArchivo(archivos.equipos)

  function elegir(clave, file) {
    setArchivos((a) => ({ ...a, [clave]: file ?? null }))
    setErrorLocal('')
    preview.reset()
  }

  function revisar() {
    setErrorLocal('')
    preview.mutate(archivos, {
      onSuccess: (data) => { setResumen(data); setFiltro('todas') },
    })
  }

  function aplicar() {
    importar.mutate(archivos, {
      onSuccess: (data) => { setConfirmar(false); setResultado(data) },
      onError: (err) => {
        setConfirmar(false)
        const data = err?.response?.data
        if (err?.response?.status === 400 && data?.rows) {
          setResumen(data)
          setFiltro(data.errors_count > 0 ? 'errores' : 'todas')
        } else {
          setErrorLocal(apiErrorMessage(err))
        }
      },
    })
  }

  function empezarDeNuevo() {
    setArchivos({ ubicaciones: null, equipos: null })
    setResumen(null)
    setResultado(null)
    setConfirmar(false)
    setErrorLocal('')
    preview.reset()
    importar.reset()
  }

  return (
    <div className="space-y-4 max-w-5xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tightest text-gray-900">
            Importar desde Fracttal
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">Trae hospitales, ubicaciones y equipos desde las exportaciones a Excel</p>
        </div>
        <Link to="/activos" className="text-sm text-brand hover:underline whitespace-nowrap pt-2">Volver a Activos</Link>
      </div>

      {resultado ? (
        <Resultado resumen={resultado} onReiniciar={empezarDeNuevo} />
      ) : resumen ? (
        <Vista
          resumen={resumen}
          filtro={filtro}
          onFiltro={setFiltro}
          onImportar={() => setConfirmar(true)}
          onReiniciar={empezarDeNuevo}
          error={errorLocal}
        />
      ) : (
        <PasoArchivos
          archivos={archivos}
          onElegir={elegir}
          onRevisar={revisar}
          cargando={preview.isPending}
          error={errorArchivos || errorLocal || (preview.isError ? apiErrorMessage(preview.error) : '')}
          deshabilitado={!hayArchivos(archivos) || Boolean(errorArchivos) || preview.isPending}
        />
      )}

      {confirmar && resumen && (
        <Modal title="¿Importar ahora?" onClose={() => !importar.isPending && setConfirmar(false)} width="max-w-md">
          <p className="text-sm text-gray-600">
            Se va a guardar en el sistema: {textoResultado(resumen).join(', ') || 'sin cambios'}.
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

function PasoArchivos({ archivos, onElegir, onRevisar, cargando, error, deshabilitado }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-card p-4 sm:p-6 space-y-5">
      <div className="rounded-lg bg-gray-50 border border-gray-100 p-3 text-sm text-gray-600">
        <p className="font-medium text-gray-800 mb-1">Cómo exportar desde Fracttal</p>
        <p>
          Entra a <b>Activos → Ubicaciones</b> (o <b>Equipos</b>), abre el menú <b>⋮</b> y elige <b>Exportar</b>.
          Se descarga un archivo de Excel (.xlsx). Puedes subir uno solo o los dos.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Selector clave="ubicaciones" titulo="Ubicaciones" archivo={archivos.ubicaciones} onElegir={onElegir} />
        <Selector clave="equipos" titulo="Equipos" archivo={archivos.equipos} onElegir={onElegir} />
      </div>

      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}

      <div className="flex justify-end">
        <button type="button" disabled={deshabilitado} onClick={onRevisar}
          className="w-full sm:w-auto px-5 py-2.5 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2">
          {cargando && <Spinner className="h-4 w-4 text-white" />}
          {cargando ? 'Revisando…' : 'Revisar archivos'}
        </button>
      </div>
    </div>
  )
}

function Selector({ clave, titulo, archivo, onElegir }) {
  const id = `fracttal-${clave}`
  return (
    <div className="rounded-lg border border-dashed border-gray-300 p-4">
      <label htmlFor={id} className="block text-sm font-medium text-gray-800">{titulo}</label>
      <p className="text-xs text-gray-500 mb-2">Archivo .xlsx, máximo 10 MB</p>
      <input id={id} type="file"
        accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        onChange={(e) => onElegir(clave, e.target.files?.[0])}
        className="block w-full text-sm text-gray-600 file:mr-3 file:px-3 file:py-2 file:rounded-lg file:border-0 file:bg-brand/10 file:text-brand file:text-sm file:font-medium hover:file:bg-brand/20" />
      {archivo && (
        <div className="mt-2 flex items-center justify-between gap-2 text-xs text-gray-600">
          <span className="truncate">{archivo.name}</span>
          <button type="button" onClick={() => { document.getElementById(id).value = ''; onElegir(clave, null) }}
            className="text-gray-500 hover:text-red-600 flex-shrink-0">Quitar</button>
        </div>
      )}
    </div>
  )
}

function Tarjeta({ titulo, children, destacado }) {
  return (
    <div className={`rounded-xl border bg-white shadow-card p-4 ${destacado ? 'border-brand/30' : 'border-gray-200'}`}>
      <p className="text-xs font-medium text-gray-500">{titulo}</p>
      {children}
    </div>
  )
}

function Conteo({ creados, actualizados }) {
  return (
    <div className="mt-1 text-sm text-gray-600">
      <p><span className="text-2xl font-semibold text-gray-900">{creados}</span> nuevas</p>
      <p><span className="font-semibold text-gray-800">{actualizados}</span> se actualizan</p>
    </div>
  )
}

function Vista({ resumen, filtro, onFiltro, onImportar, onReiniciar, error }) {
  const conteo = contarFilas(resumen.rows)
  const filas = filtrarFilas(resumen.rows, filtro)
  const hospitalesNuevos = resumen.hospitals?.create ?? []
  const hospitalesExistentes = resumen.hospitals?.existing ?? []
  const protocolosNuevos = resumen.plans?.create ?? []
  const hayErrores = (resumen.errors_count ?? 0) > 0

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <Tarjeta titulo="Hospitales" destacado={hospitalesNuevos.length > 0}>
          <p className="mt-1 text-sm text-gray-600">
            <span className="text-2xl font-semibold text-gray-900">{hospitalesNuevos.length}</span> nuevos
          </p>
          {hospitalesNuevos.length > 0 && (
            <ul className="mt-1 text-xs text-gray-700 list-disc pl-4">
              {hospitalesNuevos.map((h) => <li key={h}>{h}</li>)}
            </ul>
          )}
          {hospitalesExistentes.length > 0 && (
            <p className="mt-1 text-xs text-gray-500">Ya existen: {hospitalesExistentes.join(', ')}</p>
          )}
        </Tarjeta>
        <Tarjeta titulo="Ubicaciones">
          <Conteo creados={resumen.locations?.create ?? 0} actualizados={resumen.locations?.update ?? 0} />
        </Tarjeta>
        <Tarjeta titulo="Equipos">
          <Conteo creados={resumen.assets?.create ?? 0} actualizados={resumen.assets?.update ?? 0} />
        </Tarjeta>
      </div>

      {protocolosNuevos.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-medium text-amber-800">
            Se crearán {textoProtocolos(protocolosNuevos.length)} nuevos
          </p>
          <p className="text-xs text-amber-700 mb-2">
            Quedan vacíos: hay que completarles tareas y checklist.
          </p>
          <ul className="text-xs text-amber-900 list-disc pl-4 columns-1 sm:columns-2 gap-6">
            {protocolosNuevos.map((p) => <li key={p}>{p}</li>)}
          </ul>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 shadow-card overflow-hidden">
        <div className="p-3 border-b flex flex-wrap gap-2">
          {FILTROS_FILAS.map((f) => (
            <button key={f.id} type="button" onClick={() => onFiltro(f.id)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium ${
                filtro === f.id ? 'bg-brand text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
              {f.label} ({conteo[f.id]})
            </button>
          ))}
        </div>
        <div className="overflow-x-auto">
          {filas.length === 0 ? (
            <p className="text-center text-sm text-gray-500 py-10">No hay filas en este filtro</p>
          ) : (
            <table className="w-full text-sm min-w-[44rem]">
              <thead className="bg-gray-50">
                <tr className="text-left text-xs font-medium text-gray-500">
                  <th className="px-4 py-3">Archivo</th>
                  <th className="px-4 py-3">Fila</th>
                  <th className="px-4 py-3">Nombre</th>
                  <th className="px-4 py-3">Ubicación</th>
                  <th className="px-4 py-3">Acción</th>
                  <th className="px-4 py-3">Detalle</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 align-top">
                {filas.map((r, i) => {
                  const a = ACCION[r.action] ?? { label: r.action, cls: 'bg-gray-100 text-gray-600' }
                  return (
                    <tr key={`${r.file}-${r.row}-${i}`}>
                      <td className="px-4 py-3 text-gray-500">{nombreArchivo(r.file)}</td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-500">{r.row}</td>
                      <td className="px-4 py-3 font-medium text-gray-800">{r.name}</td>
                      <td className="px-4 py-3 text-gray-500">{r.location || '—'}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${a.cls}`}>{a.label}</span>
                      </td>
                      <td className="px-4 py-3 text-xs">
                        {r.errors?.map((e, k) => <p key={`e${k}`} className="text-red-600">{e}</p>)}
                        {r.warnings?.map((w, k) => <p key={`w${k}`} className="text-amber-600">{w}</p>)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}

      <div className="flex flex-col-reverse sm:flex-row sm:items-center sm:justify-between gap-3">
        <button type="button" onClick={onReiniciar}
          className="px-4 py-2 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50">
          Empezar de nuevo
        </button>
        <div className="flex flex-col sm:items-end gap-1">
          <button type="button" disabled={!puedeImportar(resumen)} onClick={onImportar}
            className="px-5 py-2.5 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light disabled:opacity-50 disabled:cursor-not-allowed">
            {textoBotonImportar(resumen)}
          </button>
          {hayErrores && <p className="text-xs text-red-600">{MENSAJE_CORREGIR}</p>}
        </div>
      </div>
    </div>
  )
}

function Resultado({ resumen, onReiniciar }) {
  const partes = textoResultado(resumen)
  const avisos = (resumen.rows ?? []).filter((r) => r.warnings?.length > 0)
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-card p-4 sm:p-6 space-y-4">
      <div className="flex items-center gap-2 text-green-700">
        <Icon name="check" className="w-5 h-5" />
        <h2 className="text-lg font-semibold">Importación terminada</h2>
      </div>
      {partes.length > 0 ? (
        <ul className="text-sm text-gray-700 list-disc pl-5">
          {partes.map((p) => <li key={p}>{p}</li>)}
        </ul>
      ) : (
        <p className="text-sm text-gray-600">No hubo cambios.</p>
      )}
      {avisos.length > 0 && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 p-3">
          <p className="text-sm font-medium text-amber-800 mb-1">Avisos ({avisos.length})</p>
          <ul className="text-xs text-amber-900 space-y-0.5 max-h-48 overflow-y-auto">
            {avisos.map((r, i) => (
              <li key={i}>{nombreArchivo(r.file)}, fila {r.row} ({r.name}): {r.warnings.join(' · ')}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="flex flex-col sm:flex-row gap-2">
        <Link to="/activos"
          className="px-5 py-2.5 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light text-center">
          Ir a Activos
        </Link>
        <button type="button" onClick={onReiniciar}
          className="px-4 py-2.5 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50">
          Empezar de nuevo
        </button>
      </div>
    </div>
  )
}
