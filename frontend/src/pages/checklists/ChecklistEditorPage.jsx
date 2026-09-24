import { useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useChecklistTemplate, usePublishVersion } from '../../api/checklists'
import FormBuilder from '../../components/checklists/FormBuilder'
import ChecklistPreview from '../../components/checklists/ChecklistPreview'
import Icon from '../../components/ui/Icon'
import useModalDismiss from '../../hooks/useModalDismiss'
import Spinner from '../../components/ui/Spinner'

const TOAST_TONES = {
  success: 'bg-green-700 text-white',
  warning: 'bg-amber-600 text-white',
  danger: 'bg-red-700 text-white',
}

const TOAST_ICONS = {
  success: 'checkCircle',
  warning: 'warning',
  danger: 'xCircle',
}


export default function ChecklistEditorPage() {
  const { id } = useParams()
  const navigate = useNavigate()

  const { data: template, isLoading, isError, refetch } = useChecklistTemplate(id)
  const publishMut = usePublishVersion(id)

  const [tab, setTab] = useState(0)
  const [editorFields, setEditorFields] = useState(null)
  // Grupos que se repiten (null = los de la version actual, sin tocar).
  const [repeatable, setRepeatable] = useState(null)
  const [showConfirm, setShowConfirm] = useState(false)
  // { message, tone }. Antes solo servia para el exito y los fallos se
  // quedaban en la consola o salian por window.alert.
  const [toast, setToast] = useState(null)

  const notify = useCallback((message, tone = 'success') => {
    setToast({ message, tone })
    setTimeout(() => setToast(null), 4000)
  }, [])

  const closeConfirm = useCallback(() => setShowConfirm(false), [])
  useModalDismiss(showConfirm ? closeConfirm : null)

  const currentVersion = template?.versions?.find((v) => v.is_current)
  const currentFields = currentVersion?.checklist_fields ?? []
  const nextVersionNumber = (currentVersion?.version_number ?? 0) + 1
  const repeatableGroups = repeatable ?? currentVersion?.repeatable_groups ?? []

  const handleFieldsChange = useCallback((fields) => {
    setEditorFields(fields)
  }, [])

  async function handlePublish() {
    const fields = editorFields ?? currentFields
    if (!fields.length) return

    const payload = {
      checklist_fields: fields.map((f) => ({
        label: f.label,
        field_type: f.field_type,
        group: f.group || '',
        is_required: !!f.is_required,
        sort_order: f.sort_order ?? 0,
        options_json: f.options_json ?? [],
        help_text: f.help_text || '',
      })),
      // Solo grupos que siguen teniendo campos: el servidor rechaza el resto.
      repeatable_groups: repeatableGroups.filter((g) => fields.some((f) => (f.group || '') === g)),
    }

    try {
      await publishMut.mutateAsync(payload)
      setShowConfirm(false)
      setEditorFields(null)
      setRepeatable(null)
      notify(`Versión v${nextVersionNumber} publicada`)
      refetch()
    } catch (err) {
      console.error('[ChecklistEditor] publish error:', err?.response?.data)
      setShowConfirm(false)
      notify('No se pudo publicar la versión. Intenta de nuevo.', 'danger')
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner />
      </div>
    )
  }

  if (isError || !template) {
    return (
      <div className="text-center py-20 text-gray-500">
        <Icon name="warning" className="w-10 h-10 mx-auto mb-3 text-amber-500" />
        <p>No se encontró la plantilla</p>
        <button
          onClick={() => navigate('/checklists')}
          className="mt-3 text-sm text-brand hover:underline"
        >
          Volver
        </button>
      </div>
    )
  }

  const displayFields = editorFields ?? currentFields

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/checklists')}
            className="p-1.5 -ml-1.5 rounded-lg text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/25"
            aria-label="Volver a checklists"
          >
            <Icon name="arrowLeft" className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-gray-900">{template.name}</h1>
            <p className="text-xs text-gray-500 mt-0.5">
              {currentVersion
                ? `Versión actual: v${currentVersion.version_number} · ${currentFields.length} campos`
                : 'Sin versiones publicadas'}
            </p>
          </div>
        </div>

        <button
          onClick={() => {
            if ((editorFields ?? currentFields).length === 0) {
              notify('Agrega al menos un campo antes de publicar.', 'warning')
              return
            }
            setShowConfirm(true)
          }}
          className="btn-primary"
        >
          Publicar v{nextVersionNumber}
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <div className="flex gap-0">
          {['Editor', 'Vista previa', 'Historial de versiones'].map((label, i) => (
            <button
              key={label}
              onClick={() => setTab(i)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                tab === i
                  ? 'border-brand text-brand'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {tab === 0 && (
        <>
          <RepeatableGroups
            fields={displayFields}
            value={repeatableGroups}
            onChange={setRepeatable}
          />
          <FormBuilder
            key={currentVersion?.id ?? 'empty'}
            initialFields={currentFields}
            onFieldsChange={handleFieldsChange}
            readOnly={false}
          />
        </>
      )}
      {tab === 1 && <ChecklistPreview fields={displayFields} repeatableGroups={repeatableGroups} />}
      {tab === 2 && <VersionHistory template={template} />}

      {/* Confirm modal */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 backdrop-blur-[2px]">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4 space-y-4">
            <h3 className="text-lg font-semibold text-gray-800">Publicar nueva versión</h3>
            <p className="text-sm text-gray-600">
              Se creará la <strong>versión v{nextVersionNumber}</strong> con{' '}
              {(editorFields ?? currentFields).length} campos. La versión anterior quedará
              archivada. Las OTs ya completadas no se ven afectadas.
            </p>
            {publishMut.isError && (
              <p className="text-sm text-red-700">
                Error al publicar. Verifica que todos los campos tengan etiqueta.
              </p>
            )}
            <div className="flex justify-end gap-3 pt-1">
              <button onClick={() => setShowConfirm(false)} className="btn-ghost">
                Cancelar
              </button>
              <button
                onClick={handlePublish}
                disabled={publishMut.isPending}
                className="btn-primary"
              >
                {publishMut.isPending ? 'Publicando...' : 'Publicar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div
          role="status"
          className={`fixed bottom-6 right-6 z-50 flex items-center gap-2.5 text-sm font-medium
            px-4 py-3 rounded-xl shadow-xl animate-rise ${TOAST_TONES[toast.tone] ?? TOAST_TONES.success}`}
        >
          <Icon name={TOAST_ICONS[toast.tone] ?? TOAST_ICONS.success} className="w-4 h-4 flex-shrink-0" />
          {toast.message}
        </div>
      )}
    </div>
  )
}

// ── Grupos repetibles ────────────────────────────────────────────────────────

/**
 * Qué grupos se repiten. El bloque "Toma" se define una vez y la tarea del plan
 * dice cuántas veces va ("MANT. SALIDAS 20 TOMAS" → Toma × 20). En Fracttal ese
 * bloque se escribe a mano tantas veces como tomas haya.
 */
function RepeatableGroups({ fields, value, onChange }) {
  const grupos = [...new Set(fields.map((f) => f.group || '').filter(Boolean))]

  function toggle(grupo) {
    onChange(value.includes(grupo) ? value.filter((g) => g !== grupo) : [...value, grupo])
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-2">
      <div>
        <p className="text-sm font-medium text-gray-800">Grupos que se repiten</p>
        <p className="text-xs text-gray-500">
          Un grupo repetible se responde una vez por toma, gas o salida. Cuántas veces lo dice la
          tarea del protocolo, y el técnico puede ajustarlo en campo.
        </p>
      </div>
      {grupos.length === 0 ? (
        <p className="text-xs text-gray-500">
          Ningún campo tiene grupo. Escribe el mismo «Grupo / Sección» en los campos del bloque
          (por ejemplo «Toma») para poder repetirlo.
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {grupos.map((g) => (
            <label key={g}
              className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm cursor-pointer ${
                value.includes(g) ? 'border-brand bg-brand/5 text-brand' : 'border-gray-200 text-gray-600'
              }`}>
              <input type="checkbox" checked={value.includes(g)} onChange={() => toggle(g)} />
              {g}
              <span className="text-xs text-gray-500">
                ({fields.filter((f) => (f.group || '') === g).length} campos)
              </span>
            </label>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Version history tab ──────────────────────────────────────────────────────

function VersionHistory({ template }) {
  const versions = template?.versions ?? []

  return (
    <div className="space-y-3 max-w-2xl">
      {versions.length === 0 ? (
        <p className="text-sm text-gray-500 text-center py-10">Sin versiones publicadas aún</p>
      ) : (
        versions.map((v) => (
          <div
            key={v.id}
            className={`bg-white rounded-xl border p-4 ${v.is_current ? 'border-brand' : 'border-gray-200'}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gray-800">v{v.version_number}</span>
                  {v.is_current && (
                    <span className="text-xs px-2 py-0.5 bg-brand/10 text-brand rounded-full font-medium">
                      Actual
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {new Date(v.published_at).toLocaleString('es-CO')}
                  {v.published_by_name && ` · ${v.published_by_name}`}
                  {' · '}
                  {v.checklist_fields?.length ?? 0} campos
                </p>
              </div>
            </div>

            {/* Field list summary */}
            {v.checklist_fields && v.checklist_fields.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {v.checklist_fields.slice(0, 8).map((f) => (
                  <span
                    key={f.id}
                    className="text-xs px-2 py-0.5 bg-gray-100 text-gray-500 rounded"
                  >
                    {f.label}
                    {f.is_required && <span className="text-red-400 ml-0.5">*</span>}
                  </span>
                ))}
                {v.checklist_fields.length > 8 && (
                  <span className="text-xs text-gray-500">
                    +{v.checklist_fields.length - 8} más
                  </span>
                )}
              </div>
            )}
          </div>
        ))
      )}
    </div>
  )
}
