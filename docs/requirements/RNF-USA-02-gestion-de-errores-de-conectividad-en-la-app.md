---
id: RNF-USA-02
issue: 75
titulo: "Gestión de errores de conectividad en la app"
tipo: non-functional
prioridad: must-have
modulo: usabilidad
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: usabilidad']
---

# RNF-USA-02 - Gestión de errores de conectividad en la app

### RNF-USA-02: Gestión de errores de conectividad en la app
**Prioridad:** M

**Descripción:**
La app maneja explícitamente los escenarios de pérdida y recuperación de conexión para que el técnico nunca pierda trabajo realizado.

**Criterios de aceptación:**
- La app detecta el cambio de estado de la conexión (conectado ↔ desconectado) en tiempo real usando la API de red de Android/Capacitor.
- Al perder la conexión durante la ejecución de una OT, la app guarda automáticamente el progreso localmente (SQLite) en los siguientes 5 segundos y notifica al usuario: "Conexión perdida. Tu progreso está guardado localmente."
- La app no muestra pantallas de "Error de red" ni pantallas en blanco al perder conexión. En su lugar, entra al modo offline mostrando los datos ya descargados.
- Al recuperar la conexión, la app notifica al usuario: "Conexión recuperada. Sincronizando..." y comienza la sincronización en background.
- Si el técnico intenta realizar una acción que requiere conexión (enviar OT a revisión) estando offline, el sistema muestra un mensaje claro explicando por qué no puede hacerlo y qué debe hacer (esperar conexión).

---

---

**Metadatos de importacion**
- Tipo: `Requisito no funcional`
- Fase: `2`
- Repositorio destino: `sdeossag/TodoGas`
- Categoria: `USA - Usabilidad en Campo`
- Prioridad: `M`
- Fuente: `CMMS Gases Medicinales - Fase 2: Requisitos No Funcionales`

**Implementación (revisión del 2026-10-27):**
- [x] Detecta cambios de conexión en tiempo real — networkStore con el plugin de red de Capacitor
- [ ] Guarda el progreso local y avisa 'Conexión perdida...' — Guarda local en SQLite; no se encontró el aviso con ese texto
- [x] Sin pantallas de error al perder conexión — Modo offline con datos descargados
- [ ] Aviso 'Conexión recuperada. Sincronizando...' — No se encontró el texto
- [x] Acciones que exigen red explican el motivo — Mensajes sin conexión en firma y fotos; rechazo al sincronizar con motivo

Commits: f57ddb2, 9267bfa
Archivos: `frontend/src/store/networkStore.js`, `frontend/src/hooks/useOfflineWorkOrders.js`, `frontend/src/components/ui/OfflineBanner.jsx`
