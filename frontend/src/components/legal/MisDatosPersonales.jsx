import { Link } from 'react-router-dom'

import { descargarJson, useMyPersonalData } from '../../api/privacy'
import { nombreArchivoDatos } from '../../utils/consentimiento'
import { puedeTenerFirmaGuardada } from '../../utils/firmaGuardada'
import useAuthStore from '../../store/authStore'

function fecha(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' })
}

function Fila({ label, children }) {
  return (
    <div>
      <p className="text-xs font-medium text-gray-500 mb-0.5">{label}</p>
      <div className="text-sm text-gray-800">{children}</div>
    </div>
  )
}

/** "Mis datos personales" en Mi perfil: derecho de acceso de la Ley 1581 de 2012. */
export default function MisDatosPersonales() {
  const role = useAuthStore((s) => s.user?.role)
  const { data, isLoading, isError } = useMyPersonalData()

  return (
    <section className="bg-white rounded-xl border border-gray-200 shadow-card p-5">
      <h2 className="text-xs font-semibold text-gray-500 border-b border-gray-200 pb-2 mb-4">
        Mis datos personales
      </h2>

      {isLoading && <p className="text-sm text-gray-500">Cargando...</p>}
      {isError && (
        <p className="text-sm text-red-600">No se pudieron cargar tus datos. Inténtalo de nuevo.</p>
      )}

      {data && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Fila label="Nombre">{`${data.perfil.nombre} ${data.perfil.apellido}`.trim()}</Fila>
            <Fila label="Correo">{data.perfil.correo}</Fila>
            <Fila label="Teléfono">{data.perfil.telefono || '—'}</Fila>
            <Fila label="Alcance">
              {data.perfil.hospital
                ? `${data.perfil.hospital}${data.perfil.alcance ? ` · ${data.perfil.alcance}` : ''}`
                : 'Todos'}
            </Fila>
            <Fila label="Firma guardada">{data.firma_guardada.tiene ? 'Sí' : 'No'}</Fila>
            <Fila label="Último acceso">{fecha(data.ultimo_acceso)}</Fila>
            <Fila label="Aviso de privacidad aceptado">
              {data.consentimientos.length
                ? data.consentimientos.map((c) => `${c.version} (${fecha(c.aceptado)})`).join(', ')
                : '—'}
            </Fila>
            <Fila label="Tu actividad">
              {data.actividad.ot_ejecutadas} OT ejecutadas · {data.actividad.firmas_en_actas} firmas ·{' '}
              {data.actividad.fotos} fotos
            </Fila>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => descargarJson(data, nombreArchivoDatos())}
              className="px-4 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand/90 transition-colors"
            >
              Descargar mis datos (JSON)
            </button>
            <Link to="/privacidad" className="text-sm text-gray-500 hover:text-gray-700 underline">
              Aviso de privacidad
            </Link>
          </div>

          <p className="text-xs text-gray-500">
            Para corregir tu nombre, correo o teléfono, o para solicitar la supresión de tus datos,
            contacta a un administrador.
            {puedeTenerFirmaGuardada(role) && (
              <>
                {' '}
                Tu firma guardada la puedes reemplazar o borrar tú mismo en{' '}
                <a href="#mi-firma" className="underline">
                  Mi firma
                </a>
                .
              </>
            )}
          </p>
        </div>
      )}
    </section>
  )
}
