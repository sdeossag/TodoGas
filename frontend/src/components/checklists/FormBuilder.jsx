import { useState, useRef, useEffect } from 'react'
import { FIELD_TYPES, getFieldType } from '../../constants/checklistFields'
import Icon from '../ui/Icon'

function uid() {
  return Math.random().toString(36).slice(2, 9) + Date.now().toString(36)
}

function normalizeOptionsJson(field) {
  const ft = FIELD_TYPES.find((f) => f.value === field.field_type)
  if (!ft) return []
  if (ft.hasMinMax) {
    const oj = field.options_json
    return typeof oj === 'object' && !Array.isArray(oj) && oj !== null ? oj : {}
  }
  if (ft.hasOptions) return Array.isArray(field.options_json) ? field.options_json : []
  return []
}

export default function FormBuilder({
  initialFields = [],
  onSave,
  onFieldsChange,
  readOnly = false,
}) {
  const [fields, setFields] = useState(() =>
    initialFields.map((f) => ({
      ...f,
      _id: uid(),
      _expanded: false,
      options_json: normalizeOptionsJson(f),
    }))
  )
  const [visualDrag, setVisualDrag] = useState({ dragIndex: null, hoverIndex: null })
  const dragRef = useRef({ isDragging: false, dragIndex: null, hoverIndex: null })
  const itemRefs = useRef([])

  useEffect(() => {
    onFieldsChange?.(fields)
  }, [fields]) // eslint-disable-line react-hooks/exhaustive-deps

  function addField(ft) {
    if (readOnly) return
    setFields((prev) => [
      ...prev,
      {
        _id: uid(),
        label: `Nuevo ${ft.label.toLowerCase()}`,
        field_type: ft.value,
        group: '',
        is_required: false,
        sort_order: prev.length,
        options_json: ft.hasMinMax ? {} : ft.hasOptions ? ['Opción 1'] : [],
        help_text: '',
        _expanded: true,
      },
    ])
  }

  function updateField(_id, updates) {
    setFields((prev) => prev.map((f) => (f._id === _id ? { ...f, ...updates } : f)))
  }

  function removeField(_id) {
    setFields((prev) => prev.filter((f) => f._id !== _id))
  }

  function handleMouseDown(e, index) {
    if (readOnly) return
    e.preventDefault()
    dragRef.current = { isDragging: true, dragIndex: index, hoverIndex: index }
    setVisualDrag({ dragIndex: index, hoverIndex: index })

    function onMouseMove(e) {
      const refs = itemRefs.current
      for (let i = 0; i < refs.length; i++) {
        if (!refs[i]) continue
        const rect = refs[i].getBoundingClientRect()
        if (e.clientY < rect.top + rect.height / 2) {
          if (dragRef.current.hoverIndex !== i) {
            dragRef.current.hoverIndex = i
            setVisualDrag((v) => ({ ...v, hoverIndex: i }))
          }
          return
        }
      }
      const last = refs.length - 1
      if (dragRef.current.hoverIndex !== last) {
        dragRef.current.hoverIndex = last
        setVisualDrag((v) => ({ ...v, hoverIndex: last }))
      }
    }

    function onMouseUp() {
      const { dragIndex, hoverIndex } = dragRef.current
      dragRef.current = { isDragging: false, dragIndex: null, hoverIndex: null }
      setVisualDrag({ dragIndex: null, hoverIndex: null })

      if (dragIndex !== null && hoverIndex !== null && dragIndex !== hoverIndex) {
        setFields((prev) => {
          const next = [...prev]
          const [moved] = next.splice(dragIndex, 1)
          next.splice(hoverIndex, 0, moved)
          return next.map((f, i) => ({ ...f, sort_order: i }))
        })
      }

      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  }

  function handleSave() {
    const payload = fields.map((f, i) => {
      const { _id, _expanded, ...rest } = f
      return { ...rest, sort_order: i }
    })
    onSave?.(payload)
  }

  return (
    <div className="flex gap-4">
      {/* Left: type palette */}
      {!readOnly && (
        <div className="w-52 shrink-0 bg-gray-50 rounded-xl border border-gray-200 p-3 self-start">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3 px-1">
            Tipos de campo
          </p>
          <div className="space-y-0.5">
            {FIELD_TYPES.map((ft) => (
              <button
                key={ft.value}
                onClick={() => addField(ft)}
                className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left text-sm hover:bg-brand/10 transition-colors group"
              >
                <Icon name={ft.icon} className="w-4 h-4 text-gray-500 group-hover:text-brand flex-shrink-0" />
                <span className="text-gray-600 group-hover:text-brand text-xs">{ft.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Right: fields list */}
      <div className={`${readOnly ? 'w-full' : 'flex-1'} space-y-2`}>
        {fields.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-14 border-2 border-dashed border-gray-200 rounded-xl text-gray-500">
            <Icon name="checklist" className="w-10 h-10 mb-3 text-gray-400" />
            <p className="text-sm">
              {readOnly
                ? 'Esta versión no tiene campos'
                : 'Haz clic en un tipo de campo para agregarlo'}
            </p>
          </div>
        ) : (
          fields.map((field, index) => (
            <FieldCard
              key={field._id}
              field={field}
              isDragging={visualDrag.dragIndex === index}
              isDropTarget={
                visualDrag.hoverIndex === index &&
                visualDrag.dragIndex !== null &&
                visualDrag.dragIndex !== index
              }
              onMouseDown={(e) => handleMouseDown(e, index)}
              onChange={(updates) => updateField(field._id, updates)}
              onRemove={() => removeField(field._id)}
              readOnly={readOnly}
              itemRef={(el) => { itemRefs.current[index] = el }}
            />
          ))
        )}

        {!readOnly && onSave && (
          <div className="flex justify-end pt-2">
            <button
              onClick={handleSave}
              className="px-5 py-2 bg-brand text-white text-sm font-medium rounded-lg hover:bg-brand-light transition-colors"
            >
              Guardar cambios
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Field card ───────────────────────────────────────────────────────────────

function FieldCard({
  field,
  isDragging,
  isDropTarget,
  onMouseDown,
  onChange,
  onRemove,
  readOnly,
  itemRef,
}) {
  const ft = getFieldType(field.field_type)
  const [editLabel, setEditLabel] = useState(false)
  const [labelDraft, setLabelDraft] = useState(field.label)

  function commitLabel() {
    onChange({ label: labelDraft })
    setEditLabel(false)
  }

  return (
    <div
      ref={itemRef}
      className={[
        'bg-white rounded-lg border p-3 transition-all select-none',
        isDragging ? 'opacity-40' : '',
        isDropTarget ? 'border-brand border-2 shadow-md' : 'border-gray-200',
      ].join(' ')}
    >
      {/* Header row */}
      <div className="flex items-center gap-2">
        {/* Drag handle */}
        {!readOnly && (
          <div
            className="cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-500 px-1 py-1 flex flex-col gap-0.5"
            onMouseDown={onMouseDown}
          >
            {[0, 1].map((r) => (
              <div key={r} className="flex gap-0.5">
                {[0, 1].map((c) => (
                  <div key={c} className="w-1 h-1 rounded-full bg-current" />
                ))}
              </div>
            ))}
          </div>
        )}

        {/* Label */}
        <div className="flex-1 min-w-0">
          {editLabel && !readOnly ? (
            <input
              autoFocus
              value={labelDraft}
              onChange={(e) => setLabelDraft(e.target.value)}
              onBlur={commitLabel}
              onKeyDown={(e) => e.key === 'Enter' && commitLabel()}
              className="w-full border-b border-brand outline-none text-sm font-medium text-gray-800 bg-transparent"
            />
          ) : (
            <p
              onClick={() => !readOnly && setEditLabel(true)}
              className={`text-sm font-medium text-gray-800 truncate ${!readOnly ? 'cursor-text' : ''}`}
            >
              {field.label}
              {field.is_required && <span className="text-red-500 ml-0.5">*</span>}
            </p>
          )}
        </div>

        {/* Type badge */}
        <span className="shrink-0 inline-flex items-center gap-1 text-xs px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full whitespace-nowrap">
          <Icon name={ft.icon} className="w-3.5 h-3.5" />
          {ft.label}
        </span>

        {!readOnly && (
          <>
            <button
              onClick={() => onChange({ _expanded: !field._expanded })}
              className={`p-1 rounded text-sm transition-colors ${field._expanded ? 'text-brand' : 'text-gray-500 hover:text-brand'}`}
              title="Configurar"
            >
              <Icon name="settings" className="w-4 h-4" />
            </button>
            <button
              onClick={onRemove}
              className="p-1 rounded text-gray-400 hover:text-red-500 transition-colors"
              title="Eliminar"
            >
              <Icon name="close" className="w-4 h-4" />
            </button>
          </>
        )}
      </div>

      {/* Expanded config */}
      {!readOnly && field._expanded && (
        <div className="mt-3 pt-3 border-t border-gray-100 space-y-3">
          {/* Group */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-500 w-24 shrink-0">Grupo / Sección</span>
            <input
              value={field.group}
              onChange={(e) => onChange({ group: e.target.value })}
              placeholder="Sin grupo"
              className="flex-1 border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-brand/30"
            />
          </div>

          {/* Required toggle */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-500 w-24 shrink-0">Obligatorio</span>
            <button
              type="button"
              onClick={() => onChange({ is_required: !field.is_required })}
              className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${field.is_required ? 'bg-brand' : 'bg-gray-200'}`}
            >
              <span
                className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${field.is_required ? 'translate-x-4' : 'translate-x-0.5'}`}
              />
            </button>
          </div>

          {/* Help text */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-500 w-24 shrink-0">Ayuda</span>
            <input
              value={field.help_text}
              onChange={(e) => onChange({ help_text: e.target.value })}
              placeholder="Instrucción para el técnico..."
              className="flex-1 border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-brand/30"
            />
          </div>

          {/* NUMBER / METER: range + unit */}
          {ft.hasMinMax && (
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-xs text-gray-500 w-24 shrink-0">Rango / Unidad</span>
              <div className="flex gap-2 items-center flex-wrap">
                <input
                  type="number"
                  placeholder="Min"
                  value={field.options_json?.min ?? ''}
                  onChange={(e) =>
                    onChange({
                      options_json: {
                        ...field.options_json,
                        min: e.target.value !== '' ? Number(e.target.value) : undefined,
                      },
                    })
                  }
                  className="w-20 border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none"
                />
                <span className="text-xs text-gray-500">—</span>
                <input
                  type="number"
                  placeholder="Max"
                  value={field.options_json?.max ?? ''}
                  onChange={(e) =>
                    onChange({
                      options_json: {
                        ...field.options_json,
                        max: e.target.value !== '' ? Number(e.target.value) : undefined,
                      },
                    })
                  }
                  className="w-20 border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none"
                />
                <input
                  placeholder="Unidad (°C, bar…)"
                  value={field.options_json?.unit ?? ''}
                  onChange={(e) =>
                    onChange({ options_json: { ...field.options_json, unit: e.target.value } })
                  }
                  className="w-28 border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none"
                />
              </div>
            </div>
          )}

          {/* SELECT / MULTI_SELECT: options */}
          {ft.hasOptions && (
            <div className="space-y-2">
              <p className="text-xs text-gray-500">Opciones de selección</p>
              {(Array.isArray(field.options_json) ? field.options_json : []).map((opt, i) => (
                <div key={i} className="flex gap-1.5 items-center">
                  <input
                    value={opt}
                    onChange={(e) => {
                      const opts = [...(field.options_json || [])]
                      opts[i] = e.target.value
                      onChange({ options_json: opts })
                    }}
                    placeholder={`Opción ${i + 1}`}
                    className="flex-1 border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none"
                  />
                  <button
                    onClick={() =>
                      onChange({ options_json: field.options_json.filter((_, j) => j !== i) })
                    }
                    className="text-gray-400 hover:text-red-500 px-1"
                  >
                    <Icon name="close" className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
              <button
                onClick={() =>
                  onChange({
                    options_json: [
                      ...(Array.isArray(field.options_json) ? field.options_json : []),
                      '',
                    ],
                  })
                }
                className="text-xs text-brand hover:underline"
              >
                + Agregar opción
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
