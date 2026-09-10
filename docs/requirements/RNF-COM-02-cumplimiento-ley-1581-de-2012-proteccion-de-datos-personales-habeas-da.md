---
id: RNF-COM-02
issue: 79
titulo: "Cumplimiento Ley 1581 de 2012 (Protección de Datos Personales — Habeas Data)"
tipo: non-functional
prioridad: must-have
modulo: cumplimiento-legal
estado: OPEN
etiquetas: ['priority: must-have', 'type: non-functional', 'mod: cumplimiento-legal']
---

# RNF-COM-02 - Cumplimiento Ley 1581 de 2012 (Protección de Datos Personales — Habeas Data)

### RNF-COM-02: Cumplimiento Ley 1581 de 2012 (Protección de Datos Personales — Habeas Data)
**Prioridad:** M

**Descripción:**
El sistema cumple con la Ley 1581 de 2012 y el Decreto 1377 de 2013 de Colombia en el tratamiento de los datos personales de empleados, técnicos, y representantes de hospitales que están registrados en el sistema.

**Marco normativo aplicable:**
- **Ley 1581 de 2012**: Régimen General de Protección de Datos Personales de Colombia.
- **Decreto 1377 de 2013**: reglamenta la Ley 1581, especialmente en lo relativo al aviso de privacidad, autorización de tratamiento, y derechos de los titulares.
- **Supervisión:** la Superintendencia de Industria y Comercio (SIC) es la autoridad de control.

**Criterios de aceptación:**
- Los datos personales almacenados en el sistema están **identificados y documentados** en un inventario de tratamiento de datos (quién, qué datos, para qué fin, por cuánto tiempo). La empresa debe registrar este inventario ante la SIC.
- Al crear un usuario en el sistema, el ADMIN tiene la obligación de haber obtenido el consentimiento del titular previamente (el sistema no captura directamente el consentimiento, pero el proceso de onboarding de la empresa debe contemplarlo). El sistema incluye un texto informativo al ADMIN al crear usuarios advirtiendo esta responsabilidad.
- Los usuarios del sistema (especialmente técnicos y representantes de hospitales) pueden solicitar al ADMIN: acceso a sus datos personales almacenados, corrección de datos incorrectos, y supresión de datos si ya no hay justificación legal para conservarlos.
- El sistema soporta la **supresión de datos personales de un usuario** (anonimización): el ADMIN puede anonimizar un usuario inactivo reemplazando nombre, correo, y teléfono con valores genéricos (ej: "Usuario Anonimizado #123"), preservando el resto del historial de actividad para la trazabilidad regulatoria de las OTs. Esta función está disponible solo para usuarios con más de 2 años de inactividad.
- Los datos personales de representantes de hospitales (nombre + cargo del firmante en OTs) no pueden anonimizarse si están vinculados a registros de mantenimiento auditables, dada la superposición con el requisito regulatorio de GMP. Se documenta esta tensión en la política de privacidad de la empresa.
- En caso de un **incidente de seguridad** que comprometa datos personales, el sistema tiene un procedimiento documentado para notificar a la SIC dentro de los **15 días hábiles** siguientes al conocimiento del incidente (requisito del Art. 17 de la Ley 1581). El sistema facilita esto manteniendo logs de acceso que permiten determinar el alcance de una brecha.
- La política de privacidad de la empresa (documento externo al CMMS) debe mencionar el uso del CMMS como herramienta de tratamiento de datos y ser accesible a los titulares.
