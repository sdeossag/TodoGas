export const FIELD_TYPES = [
  { value: 'TEXT',         label: 'Texto corto',          icon: 'text', hasOptions: false, hasMinMax: false, hasUnit: false },
  { value: 'TEXTAREA',     label: 'Texto largo',           icon: 'paragraph', hasOptions: false, hasMinMax: false, hasUnit: false },
  { value: 'NUMBER',       label: 'Número',                icon: 'number', hasOptions: false, hasMinMax: true,  hasUnit: true  },
  { value: 'METER',        label: 'Lectura de medidor',    icon: 'gauge', hasOptions: false, hasMinMax: true,  hasUnit: true  },
  { value: 'BOOLEAN',      label: 'Sí / No',               icon: 'toggle', hasOptions: false, hasMinMax: false, hasUnit: false },
  { value: 'SELECT',       label: 'Selección única',       icon: 'radio', hasOptions: true,  hasMinMax: false, hasUnit: false },
  { value: 'MULTI_SELECT', label: 'Selección múltiple',    icon: 'multiSelect',  hasOptions: true,  hasMinMax: false, hasUnit: false },
  { value: 'DATE',         label: 'Fecha',                 icon: 'calendar', hasOptions: false, hasMinMax: false, hasUnit: false },
  { value: 'DATETIME',     label: 'Fecha y hora',          icon: 'clock', hasOptions: false, hasMinMax: false, hasUnit: false },
  { value: 'GPS',          label: 'Localización GPS',      icon: 'area', hasOptions: false, hasMinMax: false, hasUnit: false },
  { value: 'PHOTO',        label: 'Fotografía',            icon: 'camera', hasOptions: false, hasMinMax: false, hasUnit: false },
  { value: 'SIGNATURE',    label: 'Firma digital',         icon: 'signature',  hasOptions: false, hasMinMax: false, hasUnit: false },
]

// Foto y Firma ya no se ofrecen en campos nuevos (audio3 05:10): la OT ya tiene
// fotos de evidencia y firmas. Siguen existiendo en las versiones publicadas,
// así que FIELD_TYPES las conserva (getFieldType, vista previa, ejecución) y la
// paleta del constructor usa NEW_FIELD_TYPES. El servidor rechaza publicar una
// versión nueva que los traiga.
export const RETIRED_FIELD_TYPES = ['PHOTO', 'SIGNATURE']
export const NEW_FIELD_TYPES = FIELD_TYPES.filter((ft) => !RETIRED_FIELD_TYPES.includes(ft.value))

/** Separa los campos que ya no se pueden publicar de los que sí. */
export function withoutRetiredFields(fields) {
  const kept = fields.filter((f) => !RETIRED_FIELD_TYPES.includes(f.field_type))
  return { kept, removed: fields.length - kept.length }
}

// Sí/No/N/A (decisión del 2026-09-24): el N/A es una opción del Sí/No y el
// campo guarda 'true', 'false' o 'na'.
export function allowsNa(field) {
  const o = field?.options_json
  return field?.field_type === 'BOOLEAN' && !!o && !Array.isArray(o) && !!o.allow_na
}

export function booleanOptions(field) {
  return allowsNa(field) ? ['true', 'false', 'na'] : ['true', 'false']
}

export function booleanLabel(value) {
  return { true: 'Sí', false: 'No', na: 'N/A' }[value] ?? value
}

export function getFieldType(value) {
  return FIELD_TYPES.find((ft) => ft.value === value) ?? FIELD_TYPES[0]
}
