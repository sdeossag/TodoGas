import { getFieldType } from '../../constants/checklistFields'
import Icon from '../ui/Icon'

function groupFields(fields) {
  const groups = []
  const map = {}
  for (const f of fields) {
    const key = f.group || ''
    if (!map[key]) {
      map[key] = { name: key, fields: [] }
      groups.push(map[key])
    }
    map[key].fields.push(f)
  }
  return groups
}

export default function ChecklistPreview({ fields = [] }) {
  if (fields.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-14 text-gray-500">
        <Icon name="eye" className="w-10 h-10 mb-3 text-gray-400" />
        <p className="text-sm">Agrega campos en el editor para ver la vista previa</p>
      </div>
    )
  }

  const groups = groupFields(fields)

  return (
    <div className="max-w-lg mx-auto space-y-8">
      {groups.map((group, gi) => (
        <div key={gi} className="space-y-5">
          {group.name && (
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide border-b border-gray-200 pb-2">
              {group.name}
            </h3>
          )}
          {group.fields.map((field, fi) => (
            <FieldPreview key={fi} field={field} />
          ))}
        </div>
      ))}
    </div>
  )
}

function FieldPreview({ field }) {
  const ft = getFieldType(field.field_type)
  const opts = Array.isArray(field.options_json) ? field.options_json : []
  const minMax =
    typeof field.options_json === 'object' && !Array.isArray(field.options_json) && field.options_json !== null
      ? field.options_json
      : {}

  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-gray-700">
        {field.label}
        {field.is_required && <span className="text-red-500 ml-0.5">*</span>}
        {field.help_text && (
          <span className="text-xs font-normal text-gray-500 ml-2">({field.help_text})</span>
        )}
      </label>

      {field.field_type === 'TEXT' && (
        <input
          type="text"
          disabled
          placeholder="Respuesta de texto corto..."
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-500"
        />
      )}

      {field.field_type === 'TEXTAREA' && (
        <textarea
          disabled
          rows={3}
          placeholder="Respuesta de texto largo..."
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-500 resize-none"
        />
      )}

      {(field.field_type === 'NUMBER' || field.field_type === 'METER') && (
        <div className="flex items-center gap-3">
          <input
            type="number"
            disabled
            placeholder="0"
            className="w-32 border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-500"
          />
          {minMax.unit && <span className="text-sm text-gray-500">{minMax.unit}</span>}
          {(minMax.min !== undefined || minMax.max !== undefined) && (
            <span className="text-xs text-gray-500">
              [{minMax.min ?? '—'} — {minMax.max ?? '—'}]
            </span>
          )}
        </div>
      )}

      {field.field_type === 'BOOLEAN' && (
        <div className="flex gap-2">
          <button
            disabled
            className="px-5 py-2 border border-gray-200 rounded-lg text-sm text-gray-500 bg-gray-50"
          >
            Sí
          </button>
          <button
            disabled
            className="px-5 py-2 border border-gray-200 rounded-lg text-sm text-gray-500 bg-gray-50"
          >
            No
          </button>
        </div>
      )}

      {field.field_type === 'SELECT' && (
        <select
          disabled
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-500"
        >
          <option value="">Seleccionar...</option>
          {opts.filter(Boolean).map((o, i) => (
            <option key={i}>{o}</option>
          ))}
        </select>
      )}

      {field.field_type === 'MULTI_SELECT' && (
        <div className="space-y-1.5">
          {opts.filter(Boolean).map((o, i) => (
            <label key={i} className="flex items-center gap-2 text-sm text-gray-500 cursor-default">
              <input type="checkbox" disabled className="rounded" />
              {o}
            </label>
          ))}
          {opts.length === 0 && (
            <p className="text-xs text-gray-500 italic">Sin opciones configuradas</p>
          )}
        </div>
      )}

      {field.field_type === 'DATE' && (
        <input
          type="date"
          disabled
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-500"
        />
      )}

      {field.field_type === 'DATETIME' && (
        <input
          type="datetime-local"
          disabled
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-500"
        />
      )}

      {field.field_type === 'GPS' && (
        <div className="flex items-center gap-2 px-3 py-2.5 border border-gray-200 rounded-lg bg-gray-50">
          <Icon name="area" className="w-4 h-4 text-gray-500" />
          <span className="text-sm text-gray-500">Capturar ubicación GPS</span>
        </div>
      )}

      {field.field_type === 'PHOTO' && (
        <div className="flex items-center gap-2 px-3 py-2.5 border border-gray-200 rounded-lg bg-gray-50">
          <Icon name="camera" className="w-4 h-4 text-gray-500" />
          <span className="text-sm text-gray-500">Tomar fotografía</span>
        </div>
      )}

      {field.field_type === 'SIGNATURE' && (
        <div className="flex items-center gap-2 px-3 py-2.5 border border-gray-200 rounded-lg bg-gray-50">
          <Icon name="signature" className="w-4 h-4 text-gray-500" />
          <span className="text-sm text-gray-500">Capturar firma</span>
        </div>
      )}
    </div>
  )
}
