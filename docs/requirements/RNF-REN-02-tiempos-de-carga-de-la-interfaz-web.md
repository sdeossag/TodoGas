---
id: RNF-REN-02
issue: 60
titulo: "Tiempos de carga de la interfaz web"
tipo: non-functional
prioridad: must-have
modulo: rendimiento
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: rendimiento']
---

# RNF-REN-02 - Tiempos de carga de la interfaz web

### RNF-REN-02: Tiempos de carga de la interfaz web
**Prioridad:** M

**Descripción:**
La aplicación web debe cargar y ser interactiva en tiempos razonables para usuarios con conexión a internet estándar en Colombia (4G o banda ancha fija).

**Criterios de aceptación:**
- **First Contentful Paint (FCP):** ≤ 1.5 segundos en conexión 4G (simulada en Lighthouse: 10 Mbps down, 4G latency).
- **Largest Contentful Paint (LCP):** ≤ 3 segundos en conexión 4G.
- **Time to Interactive (TTI):** ≤ 4 segundos en primera carga.
- **Navegación entre vistas** (rutas ya cargadas, sin recarga completa): ≤ 300 ms (React Router client-side navigation).
- El bundle de JavaScript de producción no supera los **400 KB gzip** (excluyendo las librerías CDN). Se aplica code splitting por ruta.
- Los assets estáticos (JS, CSS, imágenes de UI) se sirven desde **CloudFront** con caché de largo plazo (cache-control: max-age=31536000, immutable para assets con hash en el nombre).
- Las puntuaciones de **Lighthouse en producción** deben ser: Performance ≥ 75, Accessibility ≥ 85, Best Practices ≥ 90. Se mide mensualmente.

---

---

**Metadatos de importacion**
- Tipo: `Requisito no funcional`
- Fase: `2`
- Repositorio destino: `sdeossag/TodoGas`
- Categoria: `REN - Rendimiento`
- Prioridad: `M`
- Fuente: `CMMS Gases Medicinales - Fase 2: Requisitos No Funcionales`

**Implementación (revisión del 2026-10-27):**
- [ ] FCP/LCP/TTI en 4G y Lighthouse en producción — Sin mediciones; sin despliegue
- [ ] Paquete menor a 400 KB gzip con code splitting por ruta — No se usa React.lazy; todo va en un solo paquete
- [x] Assets desde CloudFront con caché larga — CloudFront con CachingOptimized y OAC (escrito, no desplegado)
- [x] Cabeceras de seguridad en el sitio web — Política gestionada de CloudFront

Commits: 45090aa
Archivos: `infra/terraform/web.tf`, `frontend/vite.config.js`
