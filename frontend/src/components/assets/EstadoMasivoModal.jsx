import { useEffect, useState } from 'react'
import Modal from '../ui/Modal'
import { useBulkAssetStatus, useBulkAssetStatusPreview } from '../../api/assets'
import {
  ACCION_BAJA,
  ACCION_REACTIVAR,
  INICIO_HOY,
  OPCIONES_INICIO,
  textoCambian,
  textoOts,
  textoResultado,
  textoTareas,
  textoTareasHechas,
  tituloAccion,
  validarSeleccion,
} from '../../utils/estadoMasivo'

/**
 * Dar de baja o reactivar uno o varios activos: pide la vista previa, muestra
 * qué pasará, y al confirmar aplica el cambio y muestra el resultado.
 * Lo usan la lista de activos (varios) y la ficha de un activo dado de baja (uno).
 */
export default function EstadoMasivoModal({ accion, assetIds, onClose, onDone }) {
  const [inicio, setInicio] = useState(INICIO_HOY)
  const previewMut = useBulkAssetStatusPreview()
  const applyMut = useBulkAssetStatus()
  const [resultado, setResultado] = useState(null)

  const reactivar = accion === ACCION_REACTIVAR
  const motivo = validarSeleccion(assetIds.length)
  const clave = assetIds.join(',')
  const cuerpo = { asset_ids: assetIds, status: accion, ...(reactivar && { start: inicio }) }

  const { mutate: pedirPreview } = previewMut
  useEffect(() => {
    if (!motivo) pedirPreview({ asset_ids: assetIds, status: accion, ...(reactivar && { start: inicio }) })
    // assetIds se resume en `clave`: evita repetir la petición por una lista nueva igual.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clave, accion, inicio, motivo, reactivar, pedirPreview])

  async function aplicar() {
    try {
      setResultado(await applyMut.mutateAsync(cuerpo))
    } catch {
      // el error se muestra en el modal
    }
  }

  function cerrar() {
    const hecho = resultado !== null
    onClose()
    if (hecho) onDone?.(resultado)
  }

  const preview = previewMut.data
  const enBaja = accion === ACCION_BAJA
  const errorDetalle = (mut, defecto) => mut.error?.response?.data?.detail ?? defecto
  const cargando = previewMut.isPending
  const sinCambios = preview && preview.changed === 0
  const ots = preview ? textoOts(preview) : null

  return (
    <Modal
      title={resultado ? (enBaja ? 'Activos dados de baja' : 'Activos reactivados') : tituloAccion(accion)}
      subtitle={`${assetIds.length} ${assetIds.length === 1 ? 'activo' : 'activos'}`}
      onClose={cerrar}
      width="max-w-md"
    >
      {resultado ? (
        <div className="space-y-3">
          <p className="text-sm text-gray-700">{textoResultado(resultado, accion)}</p>
          <p className="text-sm text-gray-600">{textoTareasHechas(resultado, accion, inicio)}</p>
          {textoOts(resultado) && (
            <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              {textoOts(resultado)}
            </p>
          )}
          <div className="flex justify-end pt-2">
            <button type="button" onClick={cerrar}
              className="px-5 py-2 bg-brand text-white text-sm rounded-lg hover:bg-brand-light">
              Entendido
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {motivo && <p className="text-sm text-red-600">{motivo}</p>}

          {reactivar && (
            <fieldset className="space-y-2">
              <legend className="text-sm font-medium text-gray-700 mb-1">¿Desde cuándo cuentan sus tareas?</legend>
              {OPCIONES_INICIO.map((o) => (
                <label key={o.value} className="flex items-start gap-2 text-sm cursor-pointer">
                  <input type="radio" name="inicio-reactivacion" value={o.value}
                    checked={inicio === o.value} onChange={() => setInicio(o.value)}
                    className="mt-1" />
                  <span>
                    <span className="font-medium text-gray-800">{o.label}</span>
                    <span className="block text-xs text-gray-500">{o.ayuda}</span>
                  </span>
                </label>
              ))}
            </fieldset>
          )}

          <div className="text-sm text-gray-700 space-y-2" aria-live="polite">
            {cargando && <p className="text-gray-500">Calculando qué pasará…</p>}
            {previewMut.isError && (
              <p className="text-red-600">{errorDetalle(previewMut, 'No se pudo calcular el efecto.')}</p>
            )}
            {preview && !cargando && (
              <>
                <p className="font-medium text-gray-800">{textoCambian(preview, accion)}</p>
                {!sinCambios && <p>{textoTareas(preview, accion, inicio)}</p>}
                {ots && (
                  <p className="text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">{ots}</p>
                )}
              </>
            )}
          </div>

          {applyMut.isError && (
            <p className="text-sm text-red-600">{errorDetalle(applyMut, 'No se pudo aplicar el cambio.')}</p>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={cerrar} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
              Cancelar
            </button>
            <button type="button" onClick={aplicar}
              disabled={Boolean(motivo) || cargando || !preview || sinCambios || applyMut.isPending}
              className={`px-5 py-2 text-white text-sm rounded-lg disabled:opacity-50 disabled:cursor-not-allowed ${
                enBaja ? 'bg-red-600 hover:bg-red-700' : 'bg-brand hover:bg-brand-light'}`}>
              {applyMut.isPending ? 'Aplicando…' : tituloAccion(accion)}
            </button>
          </div>
        </div>
      )}
    </Modal>
  )
}
