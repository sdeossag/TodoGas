# ADR-003: Manejo de estado en React

**Fecha:** 2026-08-10
**Estado:** Aceptado
**Decidido por:** Samuel Deossa (desarrollo)

---

## Contexto

La aplicacion web necesita manejar dos tipos de estado:

1. **Estado del servidor:** datos que vienen del API (activos, OTs,
   checklists, hospitales). Requieren cache, invalidacion, loading
   states, y refetch automatico.

2. **Estado global de UI:** usuario autenticado, filtros activos en
   listados, notificaciones in-app, preferencias de la sesion.

Las opciones evaluadas fueron: React Query + Zustand, Redux Toolkit,
y Context API puro.

## Decision

**React Query para estado del servidor + Zustand para estado de UI**

## Justificacion

**React Query:**
- Elimina el 80% del codigo de fetch manual (loading, error, retry,
  cache, stale-while-revalidate).
- Los hooks son declarativos y faciles de leer: useQuery, useMutation.
- Invalida el cache automaticamente cuando se hace una mutacion,
  manteniendo la UI sincronizada con el servidor sin logica adicional.
- Facilita explicarle a Codex exactamente que hacer: "crea un hook
  useWorkOrders que use useQuery con endpoint /api/work-orders/".

**Zustand:**
- Minimalista y sin boilerplate. Un store se define en 10 lineas.
- No requiere Provider ni wrappers en el arbol de componentes.
- Facil de serializar para depuracion.
- Apropiado para el volumen de estado global que tiene este proyecto.

## Consecuencias

- Los hooks de React Query viven en frontend/src/api/ (uno por modulo).
- El store de Zustand vive en frontend/src/store/index.js.
- No se usa Context API para estado global (solo para temas o config
  estatica que no cambia en la sesion).

## Alternativas descartadas

**Redux Toolkit:** Estandar de la industria pero con boilerplate
excesivo para el tamano de este proyecto. Ademas, Codex tiende a
generar codigo Redux innecesariamente verboso. Descartado.

**Context API puro:** Causa re-renders innecesarios en componentes
que no consumen el contexto modificado. No escala bien con el volumen
de datos del sistema (3940 activos, listados de OTs). Descartado.
