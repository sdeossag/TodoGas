/**
 * Utilidades del árbol de ubicaciones (AssetNode) de un hospital.
 *
 * El backend guarda las ubicaciones como lista autorreferencial (`parent`). El
 * editor pide la lista plana con conteos y aquí se arma el árbol; los
 * selectores de los formularios reciben ya el árbol de /tree/ y solo necesitan
 * aplanarlo con sangría.
 */

// Tipos de AssetNode.NodeType, en el orden en que se recorre un hospital:
// bloque → piso → servicio → sala.
export const NODE_TYPES = [
  { value: 'BUILDING', label: 'Edificio / Torre', icon: 'building' },
  { value: 'FLOOR', label: 'Piso', icon: 'floor' },
  { value: 'AREA', label: 'Área / Servicio', icon: 'area' },
  { value: 'ROOM', label: 'Habitación / Sala', icon: 'room' },
  { value: 'OTHER', label: 'Otro', icon: 'folder' },
]

const TYPE_BY_VALUE = Object.fromEntries(NODE_TYPES.map((t) => [t.value, t]))

export function nodeTypeLabel(value) {
  return TYPE_BY_VALUE[value]?.label ?? 'Otro'
}

export function nodeTypeIcon(value) {
  return TYPE_BY_VALUE[value]?.icon ?? 'folder'
}

/**
 * Tipo sugerido para una ubicación nueva según dónde se crea. Es solo el
 * valor inicial del selector: un hospital sin torres empieza por pisos y el
 * usuario lo cambia.
 */
export function suggestedChildType(parentType) {
  const next = { BUILDING: 'FLOOR', FLOOR: 'AREA', AREA: 'ROOM', ROOM: 'OTHER' }
  if (!parentType) return 'BUILDING'
  return next[parentType] ?? 'OTHER'
}

// Orden natural: "Piso 2" antes que "Piso 10". El backend ordena por
// sort_order y luego por nombre como texto, que pone el 10 antes que el 2.
const collator = new Intl.Collator('es', { numeric: true, sensitivity: 'base' })

export function compareNodes(a, b) {
  const byOrder = (a.sort_order ?? 0) - (b.sort_order ?? 0)
  return byOrder !== 0 ? byOrder : collator.compare(a.name, b.name)
}

/**
 * Arma el árbol a partir de la lista plana del endpoint /api/asset-nodes/.
 *
 * Devuelve { roots, byId }. Cada nodo del árbol conserva los campos de la API
 * y añade `children` (ordenados) y `depth`. Si un nodo apunta a un padre que no
 * vino en la lista, se trata como raíz en vez de perderlo.
 */
export function buildTree(flatNodes) {
  const byId = new Map()
  for (const n of flatNodes) byId.set(n.id, { ...n, children: [] })

  const roots = []
  for (const node of byId.values()) {
    const parentId = node.parent?.id
    const parent = parentId ? byId.get(parentId) : null
    if (parent) parent.children.push(node)
    else roots.push(node)
  }

  function finish(nodes, depth) {
    nodes.sort(compareNodes)
    for (const n of nodes) {
      n.depth = depth
      finish(n.children, depth + 1)
    }
  }
  finish(roots, 0)

  return { roots, byId }
}

/** Ids de un nodo y todos sus descendientes. */
export function subtreeIds(node) {
  const ids = new Set()
  const stack = [node]
  while (stack.length) {
    const current = stack.pop()
    ids.add(current.id)
    stack.push(...current.children)
  }
  return ids
}

/**
 * Recorre el árbol en orden de lectura y devuelve los nodos en una lista con
 * su `depth`. Sirve para un <select>: el árbol de /tree/ llega ya anidado pero
 * sin ordenar de forma natural, así que se reordena aquí también.
 */
export function flattenTree(nodes, depth = 0) {
  const result = []
  for (const node of [...nodes].sort(compareNodes)) {
    result.push({ ...node, depth })
    if (node.children?.length) result.push(...flattenTree(node.children, depth + 1))
  }
  return result
}

/**
 * Texto de una opción de <select> con sangría visible. Los espacios normales
 * dentro de <option> se colapsan al pintar, por eso la jerarquía nunca se veía
 * en el selector del formulario de activos; con espacios de no separación sí.
 */
export function indentedLabel(name, depth) {
  return `${'    '.repeat(depth)}${depth > 0 ? '└ ' : ''}${name}`
}

/** Mapa id → id del padre (null en las raíces), recorriendo el árbol de /tree/. */
export function parentMap(roots) {
  const map = new Map()
  const stack = (roots ?? []).map((n) => [n, null])
  while (stack.length) {
    const [node, parent] = stack.pop()
    map.set(node.id, parent)
    for (const child of node.children ?? []) stack.push([child, node.id])
  }
  return map
}

/**
 * La ubicación más profunda que contiene a todas las dadas: si las tareas son
 * de habitaciones del Piso 3, el Piso 3. null si alguna no tiene ubicación (o
 * está inactiva y no vino en el árbol) o no comparten ninguna.
 */
export function commonAncestor(nodeIds, parents) {
  if (!nodeIds.length || nodeIds.some((id) => !id || !parents.has(id))) return null
  const chain = (id) => {
    const out = []
    for (let current = id; current; current = parents.get(current)) out.push(current)
    return out
  }
  const [first, ...rest] = nodeIds.map(chain)
  const others = rest.map((c) => new Set(c))
  return first.find((id) => others.every((s) => s.has(id))) ?? null
}
