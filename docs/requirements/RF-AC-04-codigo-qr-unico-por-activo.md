---
id: RF-AC-04
issue: 4
titulo: "Código QR único por activo"
tipo: functional
prioridad: must-have
modulo: activos
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: activos']
---

# RF-AC-04 - Código QR único por activo

### RF-AC-04: Código QR único por activo
**Prioridad:** M

**Descripción:**
Cada activo en nivel "Equipo" recibe un código QR único generado automáticamente, que permite al técnico identificar y acceder al activo instantáneamente desde la app Android sin búsqueda manual.

**Criterios de aceptación:**
- El código QR se genera automáticamente al crear el activo; no requiere acción adicional del ADMIN.
- El QR codifica una URL interna única basada en UUID del activo (ej: `https://app.cmms.com/activos/{uuid}`). El UUID no es predecible ni secuencial.
- Desde la app Android, el técnico escanea el QR con la cámara del dispositivo; la app abre directamente la ficha del activo correspondiente en ≤ 2 segundos.
- El código QR nunca cambia aunque se edite cualquier dato del activo.
- Desde la ficha del activo en la web, el ADMIN o SUP puede descargar un PDF de etiqueta para impresión. La etiqueta contiene: código QR imprimible, nombre del activo, código interno, hospital al que pertenece, y una instrucción de texto "Escanear para ver ficha técnica".
- El PDF de etiqueta está optimizado para impresión en formato 5x5 cm (etiqueta adhesiva estándar).
