# Política de Tratamiento de Información (plantilla)

> Plantilla para revisión del asesor legal del cliente. Reemplazar los marcadores y las notas «A confirmar» antes de publicar. Fundamento: Ley 1581 de 2012, Decreto 1377 de 2013 (compilado en el Decreto 1074 de 2015), Ley 527 de 1999.

Versión: `[VERSIÓN]`  Vigente desde: `[FECHA]`

## 1. Responsable del tratamiento

| | |
|---|---|
| Razón social | `[RAZÓN SOCIAL]` |
| NIT | `[NIT]` |
| Dirección | `[DIRECCIÓN]`, `[CIUDAD]` |
| Correo | `[CORREO DE CONTACTO]` |
| Teléfono | `[TELÉFONO]` |

## 2. Alcance y definiciones

Esta política aplica a los datos personales tratados en el CMMS TodoGas, la plataforma web y la app móvil con que `[RAZÓN SOCIAL]` gestiona el mantenimiento de redes de gases medicinales en hospitales. Titular es la persona a quien corresponden los datos; tratamiento es cualquier operación sobre ellos (recolección, almacenamiento, uso, circulación o supresión).

Titulares: personal administrativo y supervisores, técnicos, usuarios de cuentas de hospitales clientes, personas del hospital que reciben y firman las actas, y contactos de hospitales y contratos.

## 3. Datos tratados y finalidades

Datos: nombre, correo, teléfono, cédula o código de empleado, cargo, rol, firma manuscrita digitalizada, ubicación (GPS) de fotos y firmas, dirección IP y datos del dispositivo, fotos de evidencia de mantenimiento.

Finalidades:

1. Crear y administrar cuentas de acceso y controlar permisos.
2. Programar, ejecutar, evidenciar, revisar y aprobar órdenes de trabajo de mantenimiento.
3. Emitir actas de servicio con firma del técnico, del supervisor y del receptor del hospital.
4. Cumplir las obligaciones de conservación de registros de mantenimiento de la normativa sanitaria (INVIMA) y atender auditorías de hospitales.
5. Mantener la trazabilidad y la seguridad del sistema (registro de auditoría).
6. Enviar avisos operativos por correo y notificaciones (hallazgos críticos, vencimiento de contratos y garantías, órdenes asignadas) y enviar actas y reportes a los contactos del hospital.
7. Atender consultas, peticiones, reclamos e incidentes de seguridad.

El tratamiento no se usa para publicidad ni se vende a terceros.

## 4. Datos de especial cuidado

El sistema no recoge datos sensibles en el sentido del artículo 5 de la Ley 1581 (salud, orientación política, datos biométricos de identificación, etc.). La firma manuscrita digitalizada y la ubicación GPS se tratan con medidas reforzadas de acceso y solo para las finalidades 2 a 5. El titular no está obligado a autorizar tratamiento de datos sensibles. `A confirmar con el asesor legal: clasificación de la firma digitalizada.`

## 5. Autorización

El tratamiento se basa en la autorización previa, expresa e informada del titular, que se obtiene en el proceso de vinculación o de creación de usuario y queda soportada (`A confirmar: forma de soporte`). Para el receptor que firma un acta, la autorización se informa en el momento de la firma. No se requiere autorización para el tratamiento de datos de naturaleza pública ni cuando una norma lo exija (por ejemplo, la conservación de registros sanitarios).

## 6. Derechos del titular

El titular puede:

- Conocer, actualizar y rectificar sus datos.
- Solicitar prueba de la autorización otorgada.
- Ser informado del uso dado a sus datos.
- Presentar quejas ante la Superintendencia de Industria y Comercio (SIC) por infracciones al régimen de protección de datos, una vez agotado el trámite de consulta o reclamo ante el responsable.
- Revocar la autorización y solicitar la supresión de los datos cuando no se respeten los principios, derechos y garantías, o cuando no exista deber legal o contractual de conservarlos.
- Acceder gratuitamente a sus datos personales.

La revocación y la supresión no proceden mientras exista deber legal o contractual de conservar el dato (sección 12).

## 7. Área responsable de peticiones, consultas y reclamos

`[CARGO DEL RESPONSABLE]`, correo `[CORREO DE CONTACTO]`, teléfono `[TELÉFONO]`, dirección `[DIRECCIÓN]`, `[CIUDAD]`.

## 8. Procedimiento de consultas y reclamos

**Consultas** (acceder a la información personal). Se atienden en máximo diez (10) días hábiles contados desde la fecha de recibo. Si no es posible, se informa al interesado los motivos y la nueva fecha, que no puede superar cinco (5) días hábiles adicionales (Ley 1581, art. 14).

**Reclamos** (corrección, actualización, supresión, revocación o presunto incumplimiento). El titular presenta solicitud con su identificación, la descripción de los hechos, la dirección de respuesta y los documentos que quiera aportar. Si está incompleta, se le pide subsanar dentro de los cinco (5) días siguientes; pasados dos (2) meses sin respuesta se entiende desistido. El reclamo se resuelve en máximo quince (15) días hábiles desde el día siguiente a su recibo; si no es posible, se informa el motivo y la nueva fecha, que no puede superar ocho (8) días hábiles adicionales (Ley 1581, art. 15). Mientras se resuelve, el dato se marca «reclamo en trámite» (`A confirmar: forma de marcarlo`).

El titular solo puede acudir a la SIC después de agotar este trámite.

## 9. Transferencias y transmisiones

- **Transmisión a encargados**: para operar el sistema, los datos se alojan y procesan con **Amazon Web Services** (base de datos, almacenamiento de evidencia, correo transaccional, registros) en la región `[REGIÓN DE AWS]`, lo que puede implicar tratamiento fuera de Colombia. Se rige por contrato de encargo que obliga al proveedor a las medidas de seguridad y confidencialidad (Decreto 1377, art. 25, compilado en el Decreto 1074 de 2015). `A confirmar: país de la región y si requiere declaración de conformidad de la SIC para transferencias internacionales (Ley 1581, art. 26) o si basta la transmisión con contrato.`
- **Monitoreo de errores**: si se activa, el proveedor recibe información técnica sin datos de usuario, IP, cookies ni cabeceras. `A confirmar: proveedor.`
- **Hospitales clientes**: ven las actas, hallazgos y datos del personal que intervino en su alcance, como parte del servicio.
- No se transfieren datos a otros terceros salvo orden de autoridad competente.

## 10. Medidas de seguridad

Cifrado en tránsito (HTTPS) y en reposo (base de datos y bucket cifrados), control de acceso por rol y por hospital/ubicación, contraseñas almacenadas con hash, registro de auditoría inmutable de acciones e IP, firmas y actas protegidas contra modificación, copias de seguridad, acceso del personal limitado y confidencialidad contractual. Los incidentes se gestionan según el procedimiento interno de incidentes y se notifican a la SIC cuando corresponda.

## 11. Datos en el teléfono

La app puede funcionar sin red y guarda temporalmente en el teléfono respuestas, fotos y firmas pendientes de sincronizar, y la firma guardada del usuario. El técnico debe proteger su teléfono con bloqueo de pantalla y avisar de inmediato su pérdida para cerrar sesiones.

## 12. Conservación y supresión: tensión con los registros sanitarios

| Dato | Conservación | Supresión |
|---|---|---|
| Actas, firmas en actas (incluida la del receptor con nombre y cargo), fotos, órdenes de trabajo | Mínimo 5 años por la normativa sanitaria y las auditorías de hospitales | No se suprimen ni anonimizan durante ese plazo |
| Registro de auditoría | 5 años (evidencia de medidas de seguridad y trazabilidad) | No se modifica ni borra |
| Cuenta y datos de usuarios activos | Vigencia de la relación + 2 años | Al terminar la relación se desactiva la cuenta |
| Usuarios inactivos | 2 años desde la desactivación | Anonimización de nombre, correo y teléfono; el historial de actividad se conserva con un identificador genérico |
| Copias de seguridad | 30 días rodantes (`A confirmar`: dumps semanales) | Se sobrescriben por rotación |

El derecho del titular a la supresión (Ley 1581, art. 8 y art. 15) no es absoluto: no procede cuando exista un deber legal o contractual de conservar el dato. Los registros de mantenimiento de gases medicinales son documentos que debe conservarse y que pueden ser exigidos por INVIMA o por el hospital, y la firma y el nombre del firmante son parte de su integridad y autenticidad (Ley 527 de 1999). Por eso, frente a una solicitud de supresión: (1) se anonimiza la cuenta cuando proceda; (2) se conservan, bloqueados para usos distintos a la trazabilidad, los datos vinculados a registros auditables hasta el vencimiento del plazo; (3) se informa por escrito al titular el motivo; (4) al vencer el plazo, y con decisión del administrador y del responsable legal, se suprimen o anonimizan. `A confirmar: plazo exacto exigido por el sistema de calidad y el asesor legal.`

## 13. Vigencia y cambios

Esta política rige desde `[FECHA]` y mientras `[RAZÓN SOCIAL]` realice el tratamiento. Los cambios sustanciales se comunican a los titulares por la app o por correo antes de aplicarse (Decreto 1377, art. 13, compilado en el Decreto 1074 de 2015). Las versiones anteriores se archivan.

## 14. Registro Nacional de Bases de Datos

Cuando corresponda, las bases de datos del CMMS se inscriben en el RNBD de la SIC y se actualizan en los plazos que fije la norma. `A confirmar: obligación de registro.`
