---
id: RNF-AND-02
issue: 83
titulo: "Tamaños de pantalla y resoluciones"
tipo: non-functional
prioridad: must-have
modulo: android
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: android']
---

# RNF-AND-02 - Tamaños de pantalla y resoluciones

### RNF-AND-02: Tamaños de pantalla y resoluciones
**Prioridad:** M

**Descripción:**
La app es usable en los tamaños de pantalla más comunes de los smartphones Android de gama media usados en Colombia.

**Criterios de aceptación:**
- La app está optimizada para pantallas de **5.0" a 6.7"** de diagonal, resolución mínima de 720 × 1280 px (HD).
- Los layouts usan dimensiones en `dp` (density-independent pixels) y textos en `sp` (scale-independent pixels), adaptándose automáticamente a diferentes densidades de pantalla (mdpi, hdpi, xhdpi, xxhdpi).
- La interfaz funciona correctamente tanto en orientación **vertical (portrait)** como horizontal (landscape), aunque la orientación principal es portrait. Las vistas críticas (checklist, captura de firma) se diseñan primero para portrait.
- En pantallas de 720p (HD) el texto es legible sin zoom manual.
- La app no tiene layouts que se rompan (texto cortado, elementos superpuestos) en ninguno de los tamaños de pantalla objetivo. Esto se verifica en emuladores de Android Studio con múltiples resoluciones antes de cada release.
