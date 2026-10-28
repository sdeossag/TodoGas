# Manuales de usuario de TodoGas CMMS

Esta carpeta guarda la fuente de los dos manuales que se entregan con el sistema (issues #151 y #152). Están escritos en Markdown, en español, tratando al lector de «usted», con los textos de botones tal como aparecen en la interfaz. Los ejemplos usan solo datos de la demostración («Clínica Demo Norte», «OT-2026-00009»): el repositorio es público y no lleva datos reales del cliente ni de sus hospitales.

Versión 1.0 · 28 de octubre de 2026.

## Qué contiene

| Archivo | Para qué sirve |
|---|---|
| `manual-completo.md` | Manual de uso completo y detallado (issue #151). Portada, índice, introducción, conceptos, una sección por perfil (Administrador y Supervisor, Técnico, Cuenta de hospital), trabajo sin conexión, problemas frecuentes y un anexo de permisos. |
| `manual-rapido.md` | Manual de uso rápido (issue #152). Una sección por perfil, de 1 a 2 páginas, con las tareas del día a día en pasos cortos. Usa los mismos nombres que el manual completo. |
| `capturas-pendientes.md` | Lista numerada de todas las capturas de pantalla marcadas en los dos manuales: archivo destino, rol con el que se toma, pantalla, datos de la demo y plataforma (web o app Android). |
| `capturas/` | Carpeta donde irán las imágenes PNG (se crea cuando se tomen). |

## Cómo está escrito

- Donde irá una captura hay un marcador con este formato:
  `> [CAPTURA: <pantalla y estado exacto a capturar> — <rol>, <Web o App Android>]`
- Cada marcador tiene su fila en `capturas-pendientes.md`, en el mismo orden en que aparece (primero el manual completo y luego el rápido).
- Los nombres de pantallas, botones y mensajes salen del código de la interfaz (`frontend/src`). Si cambia un texto de la interfaz, hay que cambiarlo también en los manuales.
- Las funciones y permisos descritos corresponden a la versión del sistema de la fecha de la portada.

## Cómo se tomarán las capturas

1. Cargar la base de demostración (ver `docs/DEMO.md`).
2. Con cada cuenta de demo, abrir la pantalla indicada en `capturas-pendientes.md` y dejarla en el estado que describe la fila.
3. Guardar la imagen en `docs/manuales/capturas/` con el nombre sugerido.
4. Marcar la fila como hecha (agregar una columna «Hecha» o tachar la fila).

## Cómo se generarán el Word y el PDF

Al final, con todas las capturas tomadas, la fuente Markdown se convierte a los formatos que se entregan:

1. **Reemplazar los marcadores por imágenes.** Un paso automático recorre cada `> [CAPTURA: …]`, busca su archivo en `capturas/` según el número de `capturas-pendientes.md` y lo cambia por `![texto](capturas/NN-nombre.png)` con el texto del marcador como pie de imagen.
2. **Word (.docx).** Con Pandoc, a partir del Markdown ya con imágenes y con una plantilla de Word (`--reference-doc`) que lleva el **logo de TodoGas** (`frontend/public/logo-mejorado-.png`) en el encabezado, los colores de la marca y la tabla de contenido:
   `pandoc manual-completo.md -o manual-completo.docx --toc --reference-doc=plantilla-todogas.docx`
3. **PDF.** Con Pandoc y WeasyPrint (la misma herramienta que genera las actas), usando una hoja de estilos con el logo y los colores de TodoGas:
   `pandoc manual-completo.md -o manual-completo.pdf --toc --pdf-engine=weasyprint --css=estilo-todogas.css`
4. Repetir para `manual-rapido.md`.
5. Revisar los dos formatos: portada, índice, tablas y que no quede ningún marcador `[CAPTURA: …]` sin imagen.

La plantilla de Word y la hoja de estilos se crean en ese momento; no forman parte de esta carpeta todavía.

## Cómo mantenerlos

- Si cambia la versión del sistema, actualizar la versión y la fecha de la portada de los dos manuales.
- Si cambia una pantalla, revisar el manual completo, el rápido y las capturas afectadas.
- Para el detalle de lo que hace cada pantalla del sistema, la fuente interna es `docs/GUIA-SECCIONES.md`.
