---
id: RF-OT-05
issue: 12
titulo: "Ejecución de OT por el técnico (app Android)"
tipo: functional
prioridad: must-have
modulo: ordenes-trabajo
estado: CLOSED
etiquetas: ['priority: must-have', 'type: functional', 'mod: ordenes-trabajo']
---

# RF-OT-05 - Ejecución de OT por el técnico (app Android)

### RF-OT-05: Ejecución de OT por el técnico (app Android)
**Prioridad:** M

**Descripción:**
El flujo de ejecución de una OT por parte del técnico está completamente disponible en la app Android, diseñado para uso en campo con conectividad intermitente y condiciones físicas adversas.

**Criterios de aceptación:**
- El `TEC` ve el detalle completo de su OT: activo afectado (con acceso a su ficha), descripción de la falla/trabajo, checklist asociado, fecha límite, prioridad, y observaciones del ADMIN.
- El botón "Iniciar OT" es explícito y prominente; al pulsarlo cambia el estado a "En Progreso" y registra la hora de inicio.
- El técnico completa el checklist asociado campo por campo (ver módulo CK para detalles del flujo).
- El técnico puede añadir hasta 20 fotos de evidencia general (adicionales a las fotos de campos específicos del checklist).
- El técnico puede registrar los repuestos/materiales usados durante la ejecución seleccionándolos del catálogo de inventario.
- El técnico puede añadir observaciones de texto libre sin límite.
- Al finalizar el trabajo, el técnico captura su firma digital (ver módulo FD).
- El técnico tiene la opción de capturar la firma del receptor/cliente del hospital (opcional).
- El botón "Enviar para revisión" valida en tiempo real que todos los requisitos estén cumplidos antes de habilitarse; si falta algo, muestra una lista específica de elementos pendientes.
- La interfaz usa fuente mínima de 16px, áreas de toque mínimas de 48px, y colores de alto contraste para legibilidad en exteriores.
