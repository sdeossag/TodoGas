# ADR-001: Libreria de generacion de PDF

**Fecha:** 2026-08-10
**Estado:** Aceptado
**Decidido por:** Samuel Deossa (desarrollo)

---

## Contexto

El sistema necesita generar PDFs de reportes de servicio al completar
una OT. Cada reporte incluye: datos del activo, checklist completado
con respuestas, galeria de fotos con metadata GPS, firma digital del
tecnico y del cliente, y pie de pagina con hash de integridad.

Las opciones evaluadas fueron WeasyPrint y ReportLab.

## Decision

**WeasyPrint**

## Justificacion

- El template del reporte de servicio tiene layout complejo: fotos
  incrustadas, tablas de checklist, cabecera y pie de pagina repetidos
  en cada pagina, y estilos visuales definidos por la empresa.
- WeasyPrint renderiza HTML + CSS a PDF, lo que permite disenar el
  template como una pagina web y reutilizar conocimiento existente
  del stack (Jinja2 o Django templates).
- ReportLab usa una API programatica donde cada elemento del layout
  se posiciona con coordenadas. Para un layout con fotos y tablas
  dinamicas, el tiempo de desarrollo es 3x mayor.
- La empresa ya tiene PDFs existentes con formato definido. Replicar
  ese formato en HTML/CSS es directo; en ReportLab requeriria calculo
  manual de posiciones.

## Consecuencias

- El Dockerfile del backend debe incluir las dependencias de sistema
  de WeasyPrint: libpango, libcairo, libffi.
- La generacion de PDF corre en un worker de Celery separado para
  no bloquear el worker principal.
- Los templates HTML de los reportes viven en
  backend/apps/reports/templates/reports/.

## Alternativas descartadas

**ReportLab:** API programatica potente pero verbosa. Disenar una
tabla con fotos tarda significativamente mas que con HTML/CSS.
Descartado por costo de desarrollo en el plazo disponible.
