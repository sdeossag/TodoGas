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

export function getFieldType(value) {
  return FIELD_TYPES.find((ft) => ft.value === value) ?? FIELD_TYPES[0]
}
