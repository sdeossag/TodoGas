---
id: RNF-REN-04
issue: 62
titulo: "Rendimiento de la sincronización offline"
tipo: non-functional
prioridad: should-have
modulo: rendimiento
estado: CLOSED
etiquetas: ['priority: should-have', 'type: non-functional', 'mod: rendimiento']
---

# RNF-REN-04 - Rendimiento de la sincronización offline

### RNF-REN-04: Rendimiento de la sincronización offline
**Prioridad:** M

**Descripción:**
El proceso de sincronización de datos offline → online debe completarse en tiempos aceptables para no bloquear al técnico más de lo necesario al recuperar conexión.

**Criterios de aceptación:**
- **Descarga inicial de datos al dispositivo** (hasta 20 OTs con checklists y metadatos, sin fotos): ≤ 30 segundos en conexión 4G.
- **Subida de una OT completada offline** (checklist + hasta 10 fotos comprimidas + firmas): ≤ 60 segundos en conexión 4G con buena señal (≥ 10 Mbps upload).
- **Subida de una OT completada offline en conexión 3G** (mínimo 1 Mbps upload): ≤ 5 minutos para las mismas 10 fotos. El proceso continúa en background sin bloquear la UI del técnico.
- La sincronización no bloquea la interfaz del usuario: el técnico puede seguir navegando por otras OTs mientras se suben los datos en background.
- Si una foto individual falla al subir, el sistema reintenta esa foto específica sin reiniciar toda la sincronización.

---

## RNF-DIS — Disponibilidad y Confiabilidad
