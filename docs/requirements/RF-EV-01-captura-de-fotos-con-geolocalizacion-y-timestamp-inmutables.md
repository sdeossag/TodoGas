---
id: RF-EV-01
issue: 24
titulo: "Captura de fotos con geolocalización y timestamp inmutables"
tipo: functional
prioridad: must-have
modulo: evidencia
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: evidencia']
---

# RF-EV-01 - Captura de fotos con geolocalización y timestamp inmutables

### RF-EV-01: Captura de fotos con geolocalización y timestamp inmutables
**Prioridad:** M

**Descripción:**
El técnico captura fotos desde la app Android vinculadas a una OT. La geolocalización y timestamp son capturados automáticamente por el sistema y no pueden ser modificados por el técnico, garantizando la autenticidad de la evidencia para efectos probatorios y regulatorios.

**Criterios de aceptación:**
- El técnico captura fotos únicamente usando la cámara integrada de la app (acceso directo a cámara nativa). **No se permite importar fotos desde la galería del dispositivo** para garantizar autenticidad.
- Al momento de capturar la foto, el sistema registra automáticamente y de forma no editable: coordenadas GPS (latitud, longitud, precisión en metros según el GPS del dispositivo), timestamp en UTC y hora local del dispositivo, nombre completo del técnico (del perfil autenticado), y el ID de la OT a la que pertenece.
- Si el GPS del dispositivo no tiene señal al capturar la foto: la foto se guarda igualmente, pero se le asigna la marca **"GPS no disponible en el momento de captura"** en sus metadatos. El sistema no bloquea la captura por falta de GPS.
- Las fotos se comprimen automáticamente al capturarlas: calidad JPEG 80%, ancho máximo 1,920px (la dimensión menor se escala proporcionalmente). Los metadatos EXIF originales del dispositivo se conservan antes de la compresión.
- Se permiten hasta **20 fotos por OT** (combinando fotos de campos de checklist y fotos de evidencia general).
- Las fotos se almacenan en AWS S3 en una ruta organizada: `evidencias/{año}/{mes}/{ot_id}/{uuid_foto}.jpg`. El acceso a las fotos se realiza mediante URLs pre-firmadas con expiración de 24 horas (no son URLs públicas permanentes).
- El técnico no puede eliminar fotos una vez capturadas; solo el `ADMIN` puede eliminar fotos de OTs que aún no estén completadas, con registro en el log de trazabilidad.
