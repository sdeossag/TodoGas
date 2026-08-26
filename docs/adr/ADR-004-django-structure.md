# ADR-004: Estructura de apps Django y monorepo

**Fecha:** 2026-08-10
**Estado:** Aceptado
**Decidido por:** Samuel Deossa (desarrollo)

---

## Contexto

El proyecto necesita una estructura de repositorio y una division
interna del backend Django que sea mantenible, facil de explicarle
a herramientas de IA (Codex, Claude Code), y que soporte el
crecimiento del sistema durante los 14 sprints del proyecto.

Las decisiones a tomar eran:
1. Monorepo vs repos separados (backend / frontend / android)
2. Django: una app grande vs apps separadas por dominio

## Decision

**Monorepo unico + Django dividido en apps por dominio de negocio**

## Estructura adoptada

```
todogas/
├── backend/
│   ├── config/          (settings, urls, celery, wsgi)
│   └── apps/
│       ├── users/       (autenticacion, roles, perfiles)
│       ├── assets/      (hospitales, jerarquia, activos)
│       ├── checklists/  (templates, versiones, respuestas)
│       ├── work_orders/ (OTs, estados, historial)
│       ├── maintenance/ (planes PM, ejecuciones)
│       ├── evidence/    (fotos con GPS, firmas digitales)
│       ├── inventory/   (repuestos, movimientos de stock)
│       ├── audit/       (log inmutable, trazabilidad)
│       ├── reports/     (PDFs generados, envios)
│       └── notifications/ (log de notificaciones)
├── frontend/            (React + Vite + Tailwind)
├── docs/
│   └── adr/             (este archivo y los demas ADRs)
├── docker-compose.yml
└── .env.example
```

## Justificacion del monorepo

- Un solo repositorio simplifica el CI/CD: un PR puede cruzar cambios
  de backend y frontend simultaneamente.
- Codex y Claude Code tienen contexto completo del proyecto en cada
  sesion sin necesidad de cambiar de repositorio.
- El proyecto es desarrollado por un solo desarrollador principal.
  La complejidad de sincronizar multiples repos no aporta valor.
- La app Android se genera desde el frontend con Capacitor, no es
  un proyecto separado.

## Justificacion de apps por dominio

- Cada app tiene su propio models.py, admin.py, y tests/. Cuando
  Codex trabaja en ordenes de trabajo, solo toca work_orders/.
- Las dependencias entre apps son explicitas via ForeignKey con
  strings ('assets.Asset') en lugar de imports directos.
- Facilita el crecimiento: agregar una nueva funcionalidad es
  agregar una nueva app sin tocar las existentes.
- El AuditLog en su propia app audit/ garantiza que ningun otro
  modulo puede modificar o eliminar registros de auditoria.

## Consecuencias

- Los ForeignKey entre apps usan referencias en string, nunca imports
  directos, para evitar dependencias circulares.
- Cada app tiene su propio archivo de migraciones independiente.
- El orden de makemigrations debe respetar dependencias:
  users -> assets -> checklists -> work_orders -> maintenance
  -> evidence -> inventory -> audit -> reports -> notifications.

## Alternativas descartadas

**Repos separados:** Complejidad de sincronizacion innecesaria para
un equipo de un desarrollador. Descartado.

**Una sola app Django:** Un models.py con 21 modelos y un views.py
con todos los endpoints es imposible de mantener y de explicarle
a herramientas de IA con contexto limitado. Descartado.
