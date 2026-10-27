---
id: RF-OF-03
issue: 48
titulo: "Sincronización automática al recuperar conexión"
tipo: functional
prioridad: must-have
modulo: offline
estado: OPEN
etiquetas: ['priority: must-have', 'type: functional', 'mod: offline']
---

# RF-OF-03 - Sincronización automática al recuperar conexión

### RF-OF-03: Sincronización automática al recuperar conexión
**Prioridad:** M

**Descripción:**
Al recuperar la conexión a internet, la app sincroniza automáticamente toda la información capturada offline sin intervención del técnico y sin riesgo de pérdida ni duplicación de datos.

**Criterios de aceptación:**
- La app detecta la recuperación de conexión y comienza la sincronización automáticamente dentro de los 10 segundos siguientes.
- **Orden de sincronización:** (1) primero sube las fotos (las más pesadas; proceso en background), (2) luego los datos de checklists, firmas y observaciones, (3) finalmente los cambios de estado de la OT.
- El técnico ve el progreso de sincronización con un indicador visible (ej: "Sincronizando: 3 de 5 fotos subidas...").
- Si la sincronización se interrumpe (nueva pérdida de conexión a mitad), continúa automáticamente desde donde quedó al recuperar conexión sin duplicar los datos ya subidos (idempotencia).
- Una vez completada la sincronización exitosa, el botón "Enviar para revisión" se habilita para que el técnico lo use conscientemente.
- El técnico recibe una confirmación visual de "Sincronización completada ✓" cuando todo está subido.
- **Resolución de conflictos:** dado que solo un técnico puede estar asignado a una OT a la vez, los conflictos reales son improbables. Si el servidor detecta una inconsistencia (ej: el ADMIN canceló la OT mientras el técnico trabajaba offline), la app notifica al técnico con el detalle del conflicto y el ADMIN recibe una alerta para decidir cómo proceder con los datos capturados offline.

---

## MÓDULO CL — Portal del Cliente

---

---

**Metadatos de importacion**
- Repositorio destino: `sdeossag/TodoGas`
- Modulo: `OF - Modo Offline (App Android)`
- Prioridad: `M`
- Fuente: `CMMS_Fase1_Requisitos_Funcionales.md`

**Implementación (revisión del 2026-10-27):**
- [x] Sincroniza sola al volver la red, en menos de 10 s — networkStatusChange dispara triggerSync al instante; además reintento cada 60 s.
- [ ] ~~Orden: fotos, luego datos, luego estados~~ (ya no aplica: Orden distinto y deliberado: datos, hallazgos, fotos, firmas y al final el estado, porque el servidor valida lo anterior al cambiar el estado.)
- [x] Indicador de progreso — Banner Sincronizando con elementos pendientes (no dice 3 de 5 fotos).
- [x] Continuar sin duplicar tras un corte — offline_uuid único, sync_state con reintentos y espera creciente.
- [ ] ~~Botón Enviar para revisión se habilita al terminar~~ (ya no aplica: Superado: se puede enviar a revisión sin red.)
- [ ] Confirmación visual Sincronización completada — Al terminar el banner solo desaparece; no hay mensaje de éxito.
- [ ] Conflictos: avisar al técnico y alerta al ADMIN — Un rechazo devuelve la OT a su estado con aviso al técnico (SyncAttentionNotice), pero no hay alerta al ADMIN.

Commits: f57ddb2, 0a360e0, b065c1d
Archivos: `frontend/src/sync/syncEngine.js`, `frontend/src/store/networkStore.js`, `frontend/src/components/ui/OfflineBanner.jsx`
