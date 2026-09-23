import { useTaskTypes } from '../../api/taskTypes'
import { taskTypeLabel } from '../../constants/labels'

/**
 * Selector de tipo de tarea con el catálogo. En formularios ofrece solo los
 * activos, más el valor actual aunque se haya desactivado (no se pierde al
 * editar). Como filtro (`emptyLabel`), ofrece todos.
 */
export default function TaskTypeSelect({ value, onChange, emptyLabel, className = 'input-field', ...rest }) {
  const filtro = emptyLabel !== undefined
  const { data: tipos = [] } = useTaskTypes({ active: !filtro })
  const faltaActual = value && !tipos.some((t) => t.code === value)
  return (
    <select value={value} onChange={onChange} className={className} {...rest}>
      {filtro && <option value="">{emptyLabel}</option>}
      {faltaActual && <option value={value}>{taskTypeLabel(value)}</option>}
      {tipos.map((t) => <option key={t.code} value={t.code}>{t.name}</option>)}
    </select>
  )
}
