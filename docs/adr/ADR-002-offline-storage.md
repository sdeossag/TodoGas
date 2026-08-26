# ADR-002: Estrategia de almacenamiento offline en Capacitor

**Fecha:** 2026-08-10
**Estado:** Aceptado
**Decidido por:** Samuel Deossa (desarrollo)

---

## Contexto

La app Android para tecnicos de campo debe funcionar completamente
sin internet. Los tecnicos trabajan en hospitales con cobertura
intermitente o nula. Las acciones que deben funcionar offline son:

- Ver OTs asignadas
- Completar checklist
- Capturar fotos con GPS
- Capturar firma digital
- Registrar repuestos usados

Al recuperar conexion, todo se sincroniza automaticamente con el servidor.

Las opciones evaluadas fueron @capacitor-community/sqlite y WatermelonDB.

## Decision

**@capacitor-community/sqlite**

## Justificacion

- El caso de uso es concreto y acotado: guardar OTs, respuestas de
  checklist, fotos pendientes de subir, y firmas. No se necesita
  un ORM mobil complejo.
- WatermelonDB es mas potente pero tiene una curva de aprendizaje
  significativa y fricciones documentadas en su integracion con
  Capacitor en Windows.
- Con SQLite directo, la logica de sincronizacion es explicita y
  controlable: el desarrollador decide exactamente que sube, en que
  orden, y como manejar conflictos.
- WatermelonDB hace magia por debajo que es dificil de depurar cuando
  falla en produccion con datos reales.
- El esquema SQLite local es simple: tablas planas de WorkOrder,
  ChecklistFieldResponse, Photo, y Signature con un campo synced_at.

## Consecuencias

- La sincronizacion offline -> online se implementa manualmente en
  el frontend: primero fotos, luego datos de checklist, luego estado.
- Cada entidad tiene un campo offline_uuid generado por la app antes
  de sincronizar, para evitar duplicados si el tecnico sincroniza
  dos veces.
- El esquema SQLite local se define en frontend/src/db/schema.js.

## Alternativas descartadas

**WatermelonDB:** ORM reactivo para React Native / Capacitor. Mas
potente pero innecesariamente complejo para el caso de uso. La
integracion con Capacitor en entornos Windows tiene problemas
documentados de compilacion. Descartado por complejidad y riesgo.
