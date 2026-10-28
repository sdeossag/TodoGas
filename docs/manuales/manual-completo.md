# TodoGas CMMS

## Manual de uso completo y detallado

**Versión 1.0 · 28 de octubre de 2026**

Para administradores, supervisores, técnicos y cuentas de hospital.

> [CAPTURA: Pantalla de inicio de sesión de TodoGas CMMS, con el logo, los campos «Correo electrónico» y «Contraseña» y el botón «Iniciar sesión», sin datos escritos — Sin sesión, Web]

---

## Índice

1. [Introducción](#1-introducción)
2. [Conceptos que debe conocer](#2-conceptos-que-debe-conocer)
3. [Administrador y Supervisor](#3-administrador-y-supervisor)
4. [Técnico (app Android)](#4-técnico-app-android)
5. [Cuenta de hospital](#5-cuenta-de-hospital)
6. [Trabajar sin conexión](#6-trabajar-sin-conexión)
7. [Problemas frecuentes](#7-problemas-frecuentes)
8. [Anexo: qué puede hacer cada persona](#8-anexo-qué-puede-hacer-cada-persona)

Cómo leer este manual:

- Los nombres de botones, pestañas y campos van entre comillas «así», tal como aparecen en la pantalla.
- Las instrucciones paso a paso van numeradas.
- Los ejemplos usan datos de demostración («Clínica Demo Norte», «Hospital Demo Sur», la orden «OT-2026-00009»). No son datos reales.
- Cuando vea un recuadro `[CAPTURA: …]`, ahí irá una imagen de la pantalla.
- Para una consulta de dos páginas por perfil, use el **Manual de uso rápido**.

---

## 1. Introducción

### 1.1 Qué es TodoGas CMMS

TodoGas CMMS es el sistema para llevar el mantenimiento de los gases medicinales de los hospitales. Sirve para:

- Registrar los hospitales, sus ubicaciones y sus equipos.
- Definir qué trabajos se le hacen a cada equipo y cada cuánto.
- Programar las visitas y entregárselas a los técnicos.
- Que el técnico llene la revisión, tome las fotos y firme desde el celular, incluso sin señal.
- Que el supervisor revise y apruebe el trabajo.
- Generar el **acta** en PDF y enviarla al hospital.
- Que el hospital consulte sus equipos, su historial, lo que viene y sus actas.

Se usa de dos formas:

- **En el computador**, desde el navegador (Administrador, Supervisor y cuenta de hospital).
- **En el celular**, con la **app Android de TodoGas** (el Técnico). La app es la misma pantalla de la web, con funciones para trabajar sin conexión.

### 1.2 Quién usa el sistema

| Perfil | Quién es | Qué hace | Dónde trabaja |
|---|---|---|---|
| **Administrador** | Responsable del sistema en TodoGas | Todo: configura, planifica, revisa, aprueba y administra usuarios. Es el único que ve «Usuarios», «Formato del acta», «Tipos de tarea» y «Auditoria». Nunca queda limitado a un hospital. | Web |
| **Supervisor** | Planificador o revisor de TodoGas | Planifica visitas, arma las órdenes, revisa y aprueba, decide los hallazgos, gestiona equipos y ubicaciones. No ve «Usuarios», «Formato del acta», «Tipos de tarea» ni «Auditoria». Puede quedar limitado a un hospital o a una parte de él. | Web |
| **Técnico** | Quien hace el trabajo en el hospital | Ve solo las órdenes que tiene asignadas, las ejecuta y las envía a revisión. | App Android (también la web) |
| **Cuenta de hospital** | La persona biomédica o de mantenimiento del hospital | Solo consulta: equipos, historial, próximos mantenimientos, actas, hallazgos y contratos de su hospital. | Web |

Dos aclaraciones importantes:

- **Permisos adicionales.** El Administrador puede darle a un Supervisor o a un Técnico permisos extra (por ejemplo, que un técnico también pueda revisar órdenes). Ese usuario ve entonces las pantallas que le corresponden. Las cuentas de hospital nunca reciben permisos adicionales.
- **Alcance.** El Administrador puede limitar a un usuario a un hospital y, dentro del hospital, a una parte (un piso o un servicio). Esa persona solo ve lo que hay en su alcance, en todas las pantallas.

### 1.3 Cómo entrar

**En la web**

1. Abra el navegador y escriba la dirección que le entregó TodoGas.
2. Escriba su **correo electrónico** y su **contraseña**.
3. Pulse «Iniciar sesión».

El sistema lo lleva a su pantalla de inicio:

| Perfil | Pantalla de inicio |
|---|---|
| Administrador y Supervisor | «Dashboard» |
| Técnico | «Mis órdenes de trabajo» |
| Cuenta de hospital | Panel con el nombre de su hospital |

Si prefiere ver lo que escribe en la contraseña, pulse el botón «Mostrar contraseña» (el ojo). Para ocultarla, «Ocultar contraseña».

**En la app Android**

1. Instale la app de TodoGas en el celular. El archivo de instalación (APK) se lo entrega TodoGas. Requiere Android 7.0 o superior. Si el celular pide permiso para instalar aplicaciones de origen desconocido, acéptelo solo para este archivo.
2. Abra la app «TodoGas».
3. Escriba su correo y su contraseña, y pulse «Iniciar sesión».
4. La primera vez, **entre con señal**. La app descarga sus órdenes, sus listas de revisión y su firma guardada para poder trabajar después sin conexión.

> [CAPTURA: App Android abierta en la pantalla de inicio de sesión, con el teclado cerrado — Técnico, App Android]

**Errores comunes al entrar**

| Mensaje | Qué significa | Qué hacer |
|---|---|---|
| «Ingresa tu correo electrónico.» / «El formato del correo no es válido.» | El correo está vacío o mal escrito. | Revíselo. |
| «Ingresa tu contraseña.» | Falta la contraseña. | Escríbala. |
| «Cuenta bloqueada temporalmente. Intenta de nuevo en 30 minutos.» | Se equivocó 5 veces con el mismo correo. | Espere 30 minutos. No sirve insistir. |
| «Tu cuenta está desactivada. Contacta al administrador.» | El Administrador desactivó la cuenta. | Pídale que la active. |
| «Error de conexión. Verifica tu red e intenta de nuevo.» | No hay internet. | Revise el Wi-Fi o los datos. |
| «Tu sesión ha expirado. Vuelve a iniciar sesión.» | La sesión duró demasiado. | Entre de nuevo. |

Mientras se equivoca, la pantalla le dice cuántos intentos le quedan.

### 1.4 Contraseña temporal y cómo recuperar la contraseña

**Su primera contraseña es temporal.** Cuando el Administrador crea su cuenta, el sistema genera una contraseña temporal y se la envía al correo. Nadie más la conoce, ni el propio Administrador.

1. Entre con el correo y la contraseña temporal.
2. El sistema abre la pantalla «Cambia tu contraseña». No puede seguir sin cambiarla.
3. Escriba la «Contraseña actual» (la temporal).
4. Escriba la «Nueva contraseña» y repítala en «Confirmar nueva contraseña».
5. Pulse «Guardar nueva contraseña».

La contraseña nueva debe tener **mínimo 8 caracteres, una mayúscula, un número y un carácter especial** (por ejemplo `!`, `#` o `$`). Mientras escribe, un medidor le muestra qué tan fuerte es.

> [CAPTURA: Pantalla «Cambia tu contraseña» con el medidor de fortaleza visible y una contraseña de ejemplo escrita (sin mostrar una real) — Cualquier perfil, Web]

**Si olvidó su contraseña**

El sistema no tiene un botón de «Olvidé mi contraseña». El Administrador la restablece:

1. Pídale al Administrador que restablezca su contraseña (se explica en el apartado «Usuarios»).
2. Le llegará al correo una contraseña temporal nueva.
3. Entre con ella y cámbiela, como en los pasos anteriores.

**Si quiere cambiar su contraseña por gusto**, vaya a «Mi perfil» → «Cambiar contrasena» (ver 1.6).

### 1.5 Aviso de privacidad al primer ingreso

La primera vez que entra, y cada vez que TodoGas actualiza el texto del aviso, el sistema muestra una ventana con el **Aviso de privacidad y tratamiento de datos personales** (Ley 1581 de 2012). No puede usar el sistema hasta decidir.

1. Lea el aviso. Dice qué datos se guardan (nombre, correo, teléfono, rol, firma, ubicación GPS de las fotos, dirección IP y su actividad), para qué se usan y cuáles son sus derechos.
2. Si quiere más detalle, pulse «Ver la política completa».
3. Pulse «Acepto» para continuar.
4. Si no desea aceptar, pulse «Cerrar sesión».

Si el sistema no logra guardar su aceptación, muestra «No se pudo registrar tu aceptación. Revisa tu conexión e inténtalo de nuevo.» Revise la señal y pulse «Acepto» otra vez.

Puede volver a leer el aviso cuando quiera: en la pantalla de inicio de sesión, pulse «Aviso de privacidad», o en «Mi perfil» → «Mis datos personales».

> [CAPTURA: Ventana del aviso de privacidad al primer ingreso, con los botones «Ver la política completa», «Cerrar sesión» y «Acepto» — Cualquier perfil, Web]

### 1.6 Mi perfil, firma guardada y mis datos

Abra «Mi perfil» desde el menú. Todos los perfiles lo tienen. Allí ve:

- **Datos de la cuenta:** nombre completo, correo, rol, hospital (si tiene), código de empleado (técnicos) y teléfono. **No puede cambiarlos usted**: si hay un error, pídaselo al Administrador.
- **Mi firma** (Administrador, Supervisor y Técnico).
- **Mis datos personales.**
- **Cambiar contrasena.**

> [CAPTURA: Pantalla «Mi perfil» completa con las secciones «Datos de la cuenta», «Mi firma», «Mis datos personales» y «Cambiar contrasena» — Técnico, Web]

**Registrar su firma guardada**

La firma guardada se dibuja una sola vez y después se usa en sus órdenes sin volver a dibujarla. Es **obligatoria para aprobar órdenes** (Administrador y Supervisor) y muy útil para el Técnico.

1. En «Mi perfil», baje hasta «Mi firma».
2. Dibuje su firma con el dedo (en el celular) o con el mouse, en el recuadro «Dibuja tu firma». Si se equivoca, pulse «Limpiar».
3. Pulse «Guardar mi firma».
4. Aparece «Firma guardada. Ya puedes usarla al firmar tus órdenes.»

Para cambiarla, pulse «Reemplazar» y dibuje otra («Dibuja tu nueva firma»). Para quitarla, pulse «Borrar» y confirme con «Sí, borrar».

Cosas que debe saber:

- **Registrar, reemplazar o borrar la firma necesita conexión.** Hágalo antes de salir a campo. Sin red, la pantalla avisa «Necesitas conexión para registrar tu firma. Hazlo antes de salir a campo.»
- Al firmar una orden, se guarda una **copia** en esa orden. Si después cambia o borra su firma, las actas anteriores **no cambian**.
- Las cuentas de hospital no guardan firma: quien recibe en el hospital firma a mano en cada visita.

> [CAPTURA: Sección «Mi firma» con una firma ya guardada y los botones «Reemplazar» y «Borrar» — Técnico, Web]

**Mis datos personales**

La sección «Mis datos personales» muestra qué datos tiene el sistema sobre usted: nombre, correo, teléfono, alcance, si tiene firma guardada, último acceso, la versión del aviso que aceptó y su actividad.

1. Pulse «Descargar mis datos (JSON)» para guardar una copia en un archivo.
2. Para corregir su nombre, correo o teléfono, o para pedir que se supriman sus datos, escríbale al Administrador.

La supresión no alcanza las actas, firmas, fotos ni registros de auditoría ya generados, porque la normativa sanitaria obliga a conservarlos.

> [CAPTURA: Sección «Mis datos personales» con los datos de la persona de demo y el botón «Descargar mis datos (JSON)» — Técnico, Web]

### 1.7 Cómo se ve el sistema

**Administrador y Supervisor (web).** Arriba hay una barra con el botón de menú (para plegar o abrir el menú lateral), el logo, su nombre y rol, y «Cerrar sesion». A la izquierda, el menú lateral con estos grupos (cada persona ve solo los que le corresponden):

- «Dashboard»
- **Activos:** «Hospitales», «Activos», «Contratos y garantías»
- **Mantenimiento:** «Tareas pendientes», «Hallazgos», «Ordenes de trabajo», «Protocolos», «Calendario»
- **Checklists:** «Checklists»
- **Administracion:** «Inventario», «Usuarios», «Reportes», «Formato del acta», «Tipos de tarea», «Auditoria»
- **Cuenta:** «Mi perfil»

Tres entradas del menú muestran un **globo con número**: «Contratos y garantías» (los que vencen en 60 días), «Hallazgos» (los que esperan decisión) e «Inventario» (los repuestos con poco stock).

**Técnico.** El menú tiene «Mis ordenes» y «Mi perfil». Si el Administrador le dio permisos adicionales, aparece también «Gestión».

**Cuenta de hospital.** Un menú superior con «Dashboard», «Mis activos», «Mis reportes» y «Mi perfil», y el botón «Salir».

**Aviso de conexión.** Cuando se pierde la señal, arriba aparece una franja amarilla: «Sin conexion — Modo offline activo». Se explica en la sección 6.

> [CAPTURA: Pantalla «Dashboard» del Administrador con el menú lateral desplegado y todos sus grupos visibles — Administrador, Web]

**Cerrar sesión.** Pulse «Cerrar sesion» (administración y técnico) o «Salir» (cuenta de hospital). En un celular o un computador compartido, cierre siempre la sesión al terminar.

---

## 2. Conceptos que debe conocer

Estos nombres se repiten en todo el manual. Léalos una vez y todo lo demás será más fácil.

### 2.1 Hospital

Es el cliente o la sede que recibe el servicio. Tiene nombre, código, ciudad, dirección y un **correo de contacto** al que llega el acta de cada visita. Ejemplos de demostración: «Clínica Demo Norte» y «Hospital Demo Sur». Un hospital no se borra: se desactiva y su historial queda.

### 2.2 Árbol de ubicaciones

Es el mapa del hospital: torre, piso, servicio, sala. Se arma una vez y sobre él se colocan los equipos. Sirve para tres cosas: encontrar los equipos como los recorre el técnico, filtrar las listas y limitar el acceso de los usuarios. Ejemplo: «Clínica Demo Norte» → «Piso 1 - Urgencias».

### 2.3 Activo (equipo)

Es cada equipo o punto que se mantiene: un compresor, una alarma, una toma de gases. Tiene código, nombre, tipo, estado, prioridad y ficha técnica (fabricante, modelo, serie, fechas, garantía). Estados:

- **Activo:** en servicio.
- **Fuera de servicio:** no funciona por ahora; no se tocan sus tareas.
- **Dado de baja:** ya no se mantiene; sus tareas pendientes se anulan.

**Una ubicación también puede ser un activo.** Para mantener una sala, un piso o una obra completa (por ejemplo, entregas de obras de instalaciones) se le asigna un protocolo a la ubicación. El sistema crea para ella un activo que la representa, con código `UBI-` seguido de letras y números. Ese activo no aparece entre los equipos, pero su orden y su acta salen igual que las de un equipo, con una etiqueta de ubicación.

### 2.4 Protocolo y sus tareas

El **protocolo** dice qué trabajos se le hacen a un activo y cada cuánto. Ejemplo: «Mant. salidas de gases». Un protocolo tiene **tareas**, y cada tarea tiene:

- Un nombre («Preventivo semestral de salidas»).
- Un **tipo de tarea**.
- Una prioridad y una duración estimada.
- Una **lista de revisión (checklist)** que el técnico llenará.
- **Cuándo se hace:** por fecha («cada 6 meses»), por uso de un medidor («cada 500 horas»), por umbral de una lectura («cuando la presión sea menor que 50 PSI») o por evento (usted la crea cuando ocurre).

Un activo o una ubicación tiene **un solo protocolo**. Un protocolo sin tareas no genera nada. Un protocolo puede ser exclusivo de un hospital.

### 2.5 Tipos de tarea

Cada tarea es de un tipo (por ejemplo «Preventivo», «Correctivo» y los demás del catálogo). Cada tipo **cuenta como** Preventivo, Correctivo u Otro. Eso decide en qué indicador del «Dashboard» entra y los filtros del historial.

### 2.6 Tarea pendiente

Es una tarea que **toca hacer** sobre un activo, con su fecha. Se crea sola a partir del protocolo. Tiene dos fechas:

- **Fecha calculada:** la que sale de la frecuencia.
- **Fecha programada:** la que quedó después de reprogramar. Si nunca se reprogramó, son iguales.

Estados: **Pendiente**, **Programada** (ya está dentro de una orden), **Finalizada** y **Cancelada**.

### 2.7 Orden de trabajo (OT)

Es **una visita a un hospital**. Puede cubrir varios equipos del mismo hospital. Tiene un número como «OT-2026-00009». Se arma agrupando tareas pendientes (o a mano, para un correctivo). **Las órdenes no se crean solas.**

Estados de la OT y quién los mueve:

| Estado | Qué significa | Quién lo cambia |
|---|---|---|
| **Pendiente** | Creada y asignada, sin empezar. | — |
| **En proceso** | El técnico la inició y está trabajando. | La persona asignada, con «Iniciar OT». |
| **En revisión** | Enviada para que la revisen. | La persona asignada, con «Enviar a revision». |
| **Finalizada** | Aprobada y cerrada. Se genera el acta. | Quien revisa, con «Completar». |
| **Cancelada** | No se hizo. Las tareas vuelven a pendientes. | El Administrador (o quien tenga ese permiso), con «Cancelar OT». |

Quien revisa también puede **«Rechazar»**: la OT vuelve a «En proceso» con un motivo. Una OT **Finalizada o Cancelada no se puede modificar**.

### 2.8 Checklist (lista de revisión)

Es el formulario que el técnico llena en cada equipo. Tiene campos de varios tipos:

- Texto corto, texto largo, número.
- **Lectura de medidor** (un número con unidad: PSI, horas, voltaje…).
- **Sí / No**, y si la casilla «Permite N/A (no aplica)» está marcada, también **N/A**.
- Selección única y selección múltiple.
- Fecha, fecha y hora, y localización GPS.

Tres ideas más:

- **Bloques repetibles.** Un grupo de campos que se responde una vez por cada toma, gas o salida (por ejemplo, «Toma»). El protocolo dice cuántas veces va («Toma × 20»). El técnico puede ajustar la cantidad en campo con «Agregar toma» y «Quitar toma (vacía)».
- **Pendiente («no se pudo revisar»).** Si un punto no se pudo revisar (por ejemplo, un cubículo aislado), el técnico lo deja **pendiente** con un motivo. Mientras haya pendientes, la OT no se puede enviar a revisión.
- **Versiones.** Cuando el Administrador cambia un checklist, se publica una versión nueva. Las órdenes que ya empezaron conservan la versión con la que se crearon.

### 2.9 Hallazgo

Es algo que el técnico encuentra en un equipo durante la visita. Tiene severidad (Baja, Media, Alta, Crítica) y puede marcar «El equipo queda fuera de servicio». Puede estar **resuelto en el sitio** (con lo que se hizo) o quedar **pendiente** para que el planificador decida: convertirlo en una tarea correctiva o descartarlo con un motivo. El hospital lo ve en su portal.

### 2.10 Medidor

Es una lectura de un equipo con su unidad (horas, amperios, voltaje, temperatura, presión). Nace con la primera lectura del checklist o a mano en la ficha del equipo. Un medidor puede abrir tareas: «cada N horas de uso» o «cuando la lectura sea mayor (o menor) que un valor».

### 2.11 Acta

Es el **PDF del servicio**. Se genera cuando la OT se aprueba. Lleva los datos de la visita, los equipos, las respuestas del checklist, los hallazgos, las fotos, los materiales y las firmas (**Realizado por**, **Validado por** y **Aceptado por**). Tiene un **código de verificación** en el pie para comprobar que no se alteró, y el aviso de firma electrónica de la Ley 527 de 1999. Se envía por correo al contacto del hospital y queda disponible en el portal.

### 2.12 El ciclo completo

1. El Administrador crea el hospital, sus ubicaciones y sus equipos.
2. Crea el protocolo, con sus tareas, y lo asigna a los equipos (o a las ubicaciones).
3. El sistema genera las **tareas pendientes**.
4. El planificador agrupa las de una misma visita y crea la **OT**, asignada a un técnico.
5. El técnico inicia la OT, llena el checklist, toma fotos, firma y la envía a revisión.
6. El supervisor revisa, corrige si hace falta y **aprueba** con su firma guardada.
7. Se genera el **acta**, que llega al hospital por correo.
8. Cada tarea cerrada crea la siguiente pendiente.

---

## 3. Administrador y Supervisor

Esta sección explica cada pantalla de administración. Donde algo es solo del Administrador, se dice. Donde no se dice nada, ambos perfiles pueden hacerlo.

**Lo que cada perfil hace distinto (resumen)**

| Tarea | Administrador | Supervisor |
|---|---|---|
| Ver «Dashboard», activos, tareas pendientes, hallazgos, órdenes y calendario | Sí | Sí (dentro de su alcance) |
| Crear y editar hospitales | Sí | No |
| Armar ubicaciones, crear y editar activos, dar de baja y reactivar | Sí | Sí |
| Importar desde Fracttal | Sí | No |
| Contratos y garantías | Crear, editar y eliminar | Solo ver |
| Protocolos | Crear, editar, pausar, asignar | Solo ver |
| Checklists | Crear y publicar | Crear y publicar |
| Crear OT desde tareas pendientes, reprogramar y anular | Sí | Sí |
| Crear OT manual | Sí | No |
| Asignar y reasignar técnicos | Sí | Sí |
| Revisar, corregir y aprobar | Sí | Sí |
| Cancelar una OT | Sí | No |
| Decidir hallazgos | Sí | Sí |
| Ver y descargar actas | Sí | Sí |
| Reporte consolidado y reenviar actas | Sí | No |
| Inventario: artículos | Sí | No |
| Inventario: movimientos | Sí | Sí |
| Usuarios, formato del acta, tipos de tarea, auditoría | Sí | No |

Si el Administrador le dio permisos adicionales a otro usuario, esa persona puede tener más botones de los que muestra esta tabla.

### 3.1 Dashboard

**Para qué sirve:** ver de un vistazo cómo va el mantenimiento y qué necesita atención hoy.

**Cómo usarlo**

1. Entre a «Dashboard» (es su pantalla de inicio).
2. Arriba, en «Hospital», elija «Todos los hospitales» o uno solo.
3. En «Periodo», elija «7 dias», «30 dias» o «90 dias».
4. Pulse «Actualizar» para pedir los datos de nuevo.

**Qué muestra**

- **Requiere atención:** cuatro tarjetas que llevan a su lista con un clic: activos con mantenimiento vencido, hallazgos críticos abiertos, OTs vencidas y contratos por atender.
- **Estado de activos:** vencido, por vencer (30 días), al día y sin protocolo. Cada porción lleva a «Activos» ya filtrado.
- **Planificación de tareas:** las tareas abiertas de los próximos 6 meses y las vencidas aparte.
- **Hallazgos abiertos:** por severidad, con el enlace «Ver bandeja».
- **OTs por tipo:** preventivo, correctivo y otros.
- **Cuatro indicadores:** «Cumplimiento de protocolos», «MTTR (tiempo medio de reparacion)», «OTs vencidas» y «OTs completadas este periodo».
- **Gráficas:** «OTs por estado» y «Cumplimiento — ultimos 12 meses».
- **Tablas:** «OTs por tecnico» y «Activos sin mantenimiento reciente».
- **Contratos y garantías**, si hay algo por atender.

**Cómo leer los indicadores**

- **Cumplimiento de protocolos:** de las órdenes preventivas del mes en curso, cuántas se terminaron en su fecha o a lo sumo un día después. Si el mes no tiene órdenes preventivas, muestra 0 %.
- **MTTR:** el tiempo promedio de las órdenes correctivas, desde que se inician hasta que se aprueban (incluye el tiempo en revisión).
- **OTs vencidas:** programadas antes de hoy y sin terminar ni cancelar.

Un Supervisor limitado a un hospital ve los indicadores de ese hospital. Las cifras se guardan unos 5 minutos: si acaba de hacer un cambio y no lo ve, espere un momento y pulse «Actualizar».

> [CAPTURA: «Dashboard» completo con la sección «Requiere atención», «Estado de activos» y los cuatro indicadores, con el filtro «Todos los hospitales» y periodo «30 dias» — Administrador, Web]

### 3.2 Hospitales

**Para qué sirve:** administrar los clientes y sus sedes.

La pantalla «Hospitales» muestra una tabla con «Nombre», «Código», «Ciudad», «Activos», «Contrato», «Estado» y «Acciones». La columna «Contrato» dice «Hasta» y la fecha (con «vence en N días» si está cerca) o «Sin contrato vigente». Puede filtrar por «Todos», «Activos» o «Inactivos» y buscar por nombre o código.

**Crear un hospital (solo Administrador)**

1. Entre a «Hospitales».
2. Pulse «+ Nuevo hospital».
3. Llene «Nombre» y «Código» (obligatorios). Opcionales: NIT, ciudad, departamento y dirección.
4. En «Ubicación en el mapa», busque la dirección y marque el punto. El mapa aparece cuando TodoGas tiene configurada la clave de Google Maps.
5. En «Contacto» escriba el nombre, teléfono y **correo**. Ese correo recibe el acta de cada visita y el aviso de hallazgos graves. **Sin correo, el acta se genera pero no se envía.**
6. Pulse «Crear hospital».

**Otras acciones por fila**

- «Ubicaciones»: abre el árbol del hospital.
- «Ver activos»: abre «Activos» filtrado por ese hospital.
- «Editar» (Administrador): cambia los datos. Pulse «Guardar cambios».
- «Desactivar» / «Activar» (Administrador): cambia el estado. Un hospital inactivo deja de salir en los selectores. El historial no se pierde.
- La columna «Contrato» es un botón que lleva a «Contratos y garantías» de ese hospital.

El Supervisor solo ve su hospital, y no puede crear ni editar.

> [CAPTURA: Tabla «Hospitales» con «Clínica Demo Norte» y «Hospital Demo Sur», la columna «Contrato» y los botones de cada fila — Administrador, Web]

> [CAPTURA: Ventana «Nuevo hospital» con los campos llenos con datos de demo, el mapa y la sección «Contacto» — Administrador, Web]

### 3.3 Ubicaciones del hospital

**Para qué sirve:** armar el árbol del hospital (torre, piso, servicio, sala).

1. En «Hospitales», pulse «Ubicaciones» en la fila del hospital.
2. Pulse «Nueva ubicación» para crear una de primer nivel.
3. En la ventana, escriba «Nombre» (obligatorio) y elija el «Tipo»: «Edificio / Torre», «Piso», «Área / Servicio», «Habitación / Sala» u «Otro».
4. Si es una sububicación, elija en «Ubicada dentro de» a su padre. También sirve para mover una ubicación a otro lugar del árbol.
5. Opcionalmente, «Código», «Orden», «Dirección» y el punto en el mapa.
6. Pulse «Crear ubicación». Si va a crear varias seguidas, pulse «Guardar y crear otra».

**Otras acciones**

- Botón «+» de una fila (*Añadir sububicación en…*): crea una ubicación dentro de esa.
- Lápiz (*Editar…*): cambia nombre, tipo, padre o dirección. Pulse «Guardar cambios».
- *Desactivar… / Activar…*: oculta la ubicación y todo lo que tiene dentro de los formularios. Se ve la marca «Inactiva» u «Oculta». Los equipos que ya estaban allí **conservan su ubicación y su historial**. Se puede reactivar.
- Papelera (*Eliminar ubicación*): borra definitivamente. Solo funciona si la ubicación no tiene sububicaciones ni equipos. Si no, el botón está deshabilitado y explica por qué.
- «Expandir todo» y «Contraer todo» abren o cierran el árbol. El buscador «Buscar por nombre o código...» filtra.
- En cada fila, «N activos» lleva a «Activos» de esa ubicación.

Una ubicación no puede quedar dentro de sí misma ni de sus hijas.

> [CAPTURA: Árbol de ubicaciones de «Clínica Demo Norte» con «Piso 1 - Urgencias» expandido y los botones de cada fila — Administrador, Web]

### 3.4 Activos

**Para qué sirve:** el inventario de equipos por hospital y ubicación, con su semáforo de mantenimiento.

#### Ver y buscar activos

1. Entre a «Activos».
2. A la izquierda, elija el hospital en «Seleccionar hospital». Aparece su árbol de ubicaciones; elija «Todos los activos» o una ubicación.
3. Arriba de la tabla, busque por código, nombre o serie («Buscar código, nombre, serial...») y pulse «Buscar». El filtro «Todos los estados» ofrece «Activo», «Fuera de servicio» y «Dado de baja».

La tabla muestra «Código», «Nombre» (con un punto de color), «Tipo», «Estado», «Prioridad», «Próximo PM» y «Acciones». El punto de color es el semáforo:

- **Verde:** al día.
- **Amarillo:** vence en 30 días o menos.
- **Rojo:** vencido.
- **Gris:** sin protocolo (o con protocolo pausado).

Pulse una fila o «Ver ficha» para abrir el activo. Hay 50 filas por página, con «Anterior» y «Siguiente».

> [CAPTURA: Lista «Activos» con «Clínica Demo Norte» seleccionada, el árbol de ubicaciones a la izquierda y la tabla con el semáforo — Administrador, Web]

#### Crear un activo

1. En «Activos», pulse «+ Nuevo activo».
2. **Paso «Identificación»:** elija el «Hospital» (obligatorio) y la «Ubicación» (si no elige, queda «Sin ubicación específica»). Escriba el «Nombre del activo», el «Modelo» y el «Número de serie». El «Código interno» se escribe o se genera con el botón «Generar». Elija «Tipo de activo», «Estado» y «Prioridad» («Alta», «Media» o «Baja»).
3. Elija el «Protocolo» («Sin protocolo» o uno de la lista). Si elige uno, aparece «Fecha de la primera tarea (opcional)»: déjela vacía para usar la fecha del protocolo o escriba una (puede ser pasada si ya van atrasados).
4. Elija el «Checklist predeterminado» si quiere que se preseleccione al crear órdenes manuales de este equipo.
5. Pulse «Siguiente».
6. **Paso «Ficha técnica»:** «Fabricante», «Proveedor», «Fecha de compra», «Fecha de instalación», «Garantía hasta», «Horas de uso promedio/día» y «Notas».
7. Pulse «Crear activo».

Para corregirlo, abra «Editar» en la fila o en la ficha y pulse «Guardar cambios». Si elige «Dado de baja» al editar, la pantalla avisa qué va a pasar con las tareas antes de guardar. Si cambia el protocolo, avisa que las pendientes del anterior se anulan y las del nuevo conservan la fecha.

> [CAPTURA: Formulario «Registrar activo», paso «Identificación», con datos de demo, el botón «Generar» y la lista «Protocolo» — Administrador, Web]

#### La ficha del activo

Al abrir un activo ve su encabezado (estado, prioridad, nombre, código y ruta de ubicación) y cuatro pestañas:

- **«Información general»:** el «Estado de mantenimiento» (protocolo, próximo y último mantenimiento, y si está al día, próximo a vencer, vencido o sin protocolo), la cobertura (garantía y contrato vigentes), los datos de la ficha técnica y el **código QR**.
- **«Tareas»:** «Próximas» (tarea, cuándo, fecha programada y estado) e «Historial» (tarea, calculada, programada, realización, estado y orden). Si la orden tiene acta, hay un botón «Acta». El historial se filtra con los botones «Todos», «Preventivo», «Correctivo» y «Otro», y cada fila muestra el tipo de tarea. El enlace «Ver todas sus OT» abre la lista de órdenes de ese equipo.
- **«Medidores»:** las lecturas del equipo.
- **«Campos personalizados»:** los datos extra del tipo de activo.

**Descargar la etiqueta QR**

1. En «Información general», busque «Código QR».
2. Pulse «Descargar etiqueta PNG».
3. Imprima la etiqueta y péguela en el equipo.

**Registrar una lectura de medidor**

1. Abra la pestaña «Medidores».
2. Pulse «+ Agregar medidor» para crear uno nuevo, o «Registrar lectura» en uno existente.
3. Escriba la «Lectura», la «Fecha y hora» y una «Nota». En los contadores, marque «El contador se reinició o se cambió» si fue el caso.
4. Pulse «Guardar».

Una lectura registrada a mano se puede borrar solo si no abrió ninguna tarea. Las lecturas que vienen del checklist se corrigen en la respuesta de la OT.

> [CAPTURA: Ficha de un activo de demo, pestaña «Tareas», con «Próximas», «Historial» con los filtros «Todos / Preventivo / Correctivo / Otro» y el botón «Acta» — Administrador, Web]

> [CAPTURA: Ficha de un activo, pestaña «Información general», con el «Código QR» y el botón «Descargar etiqueta PNG» — Administrador, Web]

#### Dar de baja un activo

1. Abra la ficha del activo y pulse «Dar de baja».
2. La ventana «Confirmar baja del activo» explica el efecto: se anulan las tareas pendientes y el equipo no vuelve a entrar en órdenes nuevas.
3. Pulse «Dar de baja».
4. Un resumen indica cuántas tareas se anularon. Si el equipo sigue dentro de una OT abierta, el resumen la nombra: esas tareas no se tocan y, al cerrarse esa OT, **no** se programa la siguiente. Pulse «Entendido».

Nada se borra: las tareas anuladas quedan en el historial. Para volver a ponerlo en servicio, use «Reactivar»: se reabren las tareas de su protocolo.

#### Dar de baja o reactivar varios activos a la vez

1. En «Activos», marque las casillas de las filas (la casilla del encabezado marca todos los visibles).
2. Abajo aparece una barra con «N activos seleccionados» y los botones «Dar de baja», «Reactivar» y «Quitar selección». Puede cambiar hasta **200 activos** a la vez.
3. Pulse «Dar de baja» o «Reactivar».
4. El sistema calcula qué pasará («Calculando qué pasará…») y lo muestra: cuántos cambian, cuántas tareas se anulan o se abren y qué órdenes abiertas conservan tareas.
5. Al reactivar, elija «¿Desde cuándo cuentan sus tareas?»: «Desde hoy (recomendado)» (quedan programadas para hoy) o «Según su último mantenimiento» (cada tarea toma la fecha que le toca, y puede salir vencida).
6. Confirme. Al final, pulse «Entendido».

> [CAPTURA: Lista «Activos» con varias filas marcadas y la barra inferior con «Dar de baja», «Reactivar» y «Quitar selección» — Administrador, Web]

> [CAPTURA: Ventana de reactivación masiva con el resumen de lo que pasará y las opciones «Desde hoy (recomendado)» y «Según su último mantenimiento» — Administrador, Web]

#### Importar desde Fracttal (solo Administrador)

Sirve para traer hospitales, ubicaciones y equipos desde los archivos de Excel que exporta Fracttal.

1. En Fracttal, entre a **Activos → Ubicaciones** (o **Equipos**), abra el menú **⋮** y elija **Exportar**. Se descarga un archivo de Excel (.xlsx). Puede subir uno solo o los dos.
2. En TodoGas, entre a «Activos» y pulse «Importar desde Fracttal».
3. Elija el archivo de «Ubicaciones» y/o el de «Equipos» (.xlsx, máximo 10 MB cada uno). Si se equivoca, pulse «Quitar».
4. Pulse «Revisar archivos». **Todavía no se guarda nada.**
5. Lea el resumen: hospitales nuevos, cuántas ubicaciones y equipos son nuevos y cuántos se actualizan, y los protocolos que se crearán. Los protocolos nuevos quedan **vacíos**: hay que completarles tareas y checklist.
6. Revise la tabla de filas con los filtros «Todas», «Con errores» y «Con avisos». Cada fila dice el archivo, el número de fila, el nombre, la ubicación, la acción y el detalle.
7. Si hay errores, el botón de importar queda deshabilitado y la pantalla dice «Corrige los errores en Fracttal o en el archivo y vuelve a subirlo». Corrija el archivo y empiece de nuevo con «Empezar de nuevo».
8. Si no hay errores, pulse el botón «Importar N equipos y M ubicaciones».
9. Confirme en «¿Importar ahora?» con «Sí, importar».
10. La pantalla «Importación terminada» resume lo hecho y lista los avisos. Pulse «Ir a Activos».

> [CAPTURA: Pantalla «Importar desde Fracttal» con el resumen de la revisión (hospitales, ubicaciones, equipos) y la tabla de filas con el filtro «Con avisos» — Administrador, Web]

### 3.5 Contratos y garantías

**Para qué sirve:** llevar la vigencia de los contratos de mantenimiento y de las garantías de equipos. **Solo avisa**: que un contrato venza no bloquea nada.

La pantalla muestra dos avisos («N por vencer en 60 días» y «N hospitales sin contrato vigente»), las vistas «Vigentes», «Por vencer», «Vencidos», «Próximos» y «Todos», los filtros de tipo, hospital y búsqueda, y una tabla con «Documento», «Cubre», «Vigencia», «Estado» y «Acciones». «Por vencer» significa que faltan 60 días o menos.

**Crear un documento (solo Administrador)**

1. Entre a «Contratos y garantías» y pulse «+ Nuevo documento».
2. Elija el tipo de documento: contrato de mantenimiento o garantía de equipos.
3. Escriba el «Nombre» y, si quiere, la descripción.
4. Elija el hospital.
5. En un contrato, elija qué «Cubre»: «Todo el hospital» o una rama del árbol de ubicaciones.
6. En una garantía, marque los equipos que cubre (puede filtrar por ubicación y buscar por código).
7. Escriba el inicio y el fin de la vigencia. El atajo «Un año desde el inicio» calcula el fin.
8. Adjunte el documento (PDF, Word o imagen, hasta 20 MB).
9. Pulse «Guardar».

Para cambiar uno, pulse «Editar». Si solo terminó, no hace falta borrarlo: queda como vencido en el historial. «Eliminar» lo borra de verdad.

**Avisos automáticos:** cada día a las 6:30 a. m. (hora de Colombia) los administradores reciben **un solo correo** con los documentos que cruzaron el umbral de 60 días, 30 días o vencido. Si no hay nada, no sale. Además, al crear una OT en un hospital sin contrato vigente, aparece un aviso («Puedes crear la OT igual»).

> [CAPTURA: Lista «Contratos y garantías» con la vista «Por vencer» y los dos avisos de arriba, con el contrato por vencer de «Clínica Demo Norte» — Administrador, Web]

### 3.6 Protocolos

**Para qué sirve:** definir qué tareas se le hacen a un equipo y cada cuánto. Es el origen de las tareas pendientes. El Supervisor puede ver todo; solo el Administrador modifica.

**La lista**

La pantalla «Protocolos» muestra «Protocolo», «Tareas» (las dos primeras con su frecuencia, o «Sin tareas: no genera nada»), «Activos», «Próxima fecha», «Cumplimiento del mes», «Estado» y «Acciones». Filtre por «Todos», «Activos» o «Pausados», o busque por nombre.

**Crear un protocolo**

1. Pulse «Nuevo protocolo».
2. Escriba el «Nombre» (por ejemplo, «Salidas de gases 24 tomas») y, si quiere, la descripción.
3. Elija la prioridad por defecto y, si es exclusivo, el hospital en «Solo para el hospital» («Cualquier hospital» lo deja abierto).
4. Pulse «Crear protocolo». El sistema lo lleva a la pestaña de tareas.

**Agregar una tarea al protocolo**

1. En la pestaña «Tareas», pulse «Agregar tarea».
2. Escriba el «Nombre» y elija el tipo, la prioridad y la «Duración estimada» (horas y minutos).
3. Elija el «Checklist» (o «Sin checklist»). Si la plantilla no tiene una versión publicada, la pantalla lo avisa y no deja guardar: publique la plantilla o elija otra.
4. Si el checklist tiene bloques repetibles, aparece «¿Cuántas veces van en esta tarea?». Escriba la cantidad de cada bloque (por ejemplo, 20 tomas). El técnico podrá ajustarla en campo y se le avisará en la OT.
5. En «Cuándo se hace», elija una de tres formas:
   - **«Por fecha (se repite sola)»:** escriba la «Frecuencia» (cada N días, semanas, meses o años) y la «Primera vez».
   - **«Por umbral de una lectura»:** elija el «Medidor» (la unidad), la condición («Cuando la lectura sea…») y el «Umbral». Se abre la tarea cuando la lectura cruza ese valor y se avisa por correo a los administradores. Por ejemplo: presión menor que 50 PSI.
   - **«Por evento (la creas tú cuando ocurre)»:** no se repite sola. Usted la crea con el botón «Crear para un activo».
   Con el medidor también existe la forma «cada N unidades de uso» (por ejemplo, cada 500 horas), solo con unidades que acumulan.
6. En «Repetir», elija «Siempre» o «Solo N veces».
7. La casilla «Programación fija» decide cómo se cuenta la siguiente:
   - **Sin marcar (lo normal):** la siguiente se cuenta desde el día en que **se hizo**.
   - **Marcada:** se cuenta desde la fecha **calculada**; adelantar o aplazar no corre el ciclo.
8. Revise las «Primeras fechas» que muestra la pantalla.
9. Pulse «Agregar tarea».

Para cambiarla, pulse «Editar» en su fila. «Desactivar» la anula en los equipos (las pendientes que ya están en una OT siguen) y conserva su historial; «Activar» la devuelve. Una tarea sin historial se puede eliminar con «Eliminar la tarea».

**Asignar el protocolo a equipos**

1. Abra el protocolo y vaya a la pestaña «Activos».
2. Pulse «Asignar activos».
3. Elija el hospital y, si quiere, una ubicación («Ubicación (incluye lo que tiene dentro)»). Puede buscar por código o nombre, y marcar «Solo activos sin protocolo».
4. Marque los equipos (o «Marcar todos»).
5. En «Fecha de la primera tarea (opcional)» escriba desde cuándo empieza a contar. Vacía, se usa la fecha del protocolo o, si no hay, hoy. Puede ser una fecha pasada si ya van atrasados: la pantalla avisa «La fecha ya pasó: la primera tarea saldrá vencida.»
6. Confirme. El sistema informa «Protocolo asignado a N activos». Si algún equipo tenía otro protocolo, se lista bajo «Cambiaron de protocolo».

Un equipo tiene **un solo protocolo**: asignarle otro quita el anterior, anula las pendientes del anterior y las del nuevo **conservan la fecha**, salvo que usted elija una fecha de inicio.

**Asignar el protocolo a una ubicación**

1. En la pestaña «Activos», pulse «Asignar ubicaciones».
2. Elija el hospital, busque la ubicación («Bloque, piso, sala…») y márquela. Las que ya tienen este protocolo dicen «Ya tiene este protocolo».
3. Opcionalmente escriba la fecha de la primera tarea.
4. Pulse «Asignar a N ubicaciones».

La ubicación aparece en la lista con su etiqueta de ubicación.

**Quitar el protocolo a un equipo:** en la pestaña «Activos», pulse «Quitar» en su fila y confirme con «Quitar protocolo». Se anulan sus pendientes de este protocolo; una tarea que ya esté dentro de una OT se hace igual.

**Pausar y reanudar.** «Pausar» (en el encabezado del protocolo) hace que sus pendientes dejen de salir para planificar; «Reanudar» las repone.

El protocolo no se borra. La pestaña «Cumplimiento» muestra los últimos 12 meses: tareas programadas en cada mes y cuántas se hicieron.

> [CAPTURA: Ventana «Nueva tarea del protocolo» con «Cuándo se hace» en «Por fecha (se repite sola)», frecuencia de 6 meses, el checklist de salidas de gases y las «Primeras fechas» — Administrador, Web]

> [CAPTURA: Protocolo «Mant. salidas de gases», pestaña «Activos», con los equipos y las ubicaciones asignadas y los botones «Asignar ubicaciones» y «Asignar activos» — Administrador, Web]

> [CAPTURA: Ventana «Asignar activos» con el hospital elegido, equipos marcados y el campo «Fecha de la primera tarea (opcional)» — Administrador, Web]

### 3.7 Checklists

**Para qué sirve:** el catálogo de formularios que el técnico llena en campo. Los pueden crear y publicar el Administrador y el Supervisor.

La pantalla «Checklists» lista las plantillas con «Nombre», «Versión actual» (v1, v2…), «Campos», «Estado» y «Acciones». Filtre por «Todas», «Activas» o «Inactivas». Las plantillas no se borran.

**Crear una plantilla**

1. Pulse «+ Nueva plantilla».
2. Escriba el nombre y la descripción.
3. Pulse «Crear y editar». Se abre el editor.

**Armar los campos en el editor**

1. El editor tiene tres pestañas: «Editor», «Vista previa» e «Historial de versiones».
2. En la paleta de tipos de campo, pulse el que necesite: «Texto corto», «Texto largo», «Número», «Lectura de medidor», «Sí / No», «Selección única», «Selección múltiple», «Fecha», «Fecha y hora» o «Localización GPS». El campo se agrega a la lista.
3. Para cada campo, escriba la etiqueta, y si hace falta el «Grupo / Sección», la «Ayuda» y marque «Obligatorio».
4. En «Número» y «Lectura de medidor» puede poner mínimo, máximo y unidad. En «Lectura de medidor» elija además el **medidor**: lo que responda el técnico quedará como lectura del equipo y puede abrir tareas.
5. En «Sí / No», la casilla «Permite N/A (no aplica)» viene **marcada**. Desmárquela si no quiere esa opción. El acta imprime solo la respuesta.
6. Arrastre los campos para cambiar el orden.
7. En «Vista previa» vea cómo quedará el formulario.

**Bloques repetibles.** Para una toma, gas o salida que se responde varias veces: escriba el **mismo** «Grupo / Sección» en todos los campos del bloque (por ejemplo, «Toma») y marque ese grupo en «Grupos que se repiten». Cuántas veces va lo dice la tarea del protocolo.

**Publicar una versión**

1. Pulse «Publicar vN+1» (arriba).
2. Confirme en «Publicar nueva versión» con «Publicar».

Publicar crea una versión nueva y archiva la anterior. Las órdenes que ya empezaron o terminaron **no cambian**: cada tarea queda atada a la versión vigente cuando entró a la orden. En «Historial de versiones» ve cuándo se publicó cada una y quién.

Nota: «Foto» y «Firma» ya no se ofrecen como campos, porque la orden ya tiene sus propias fotos y firmas. Si abre una versión antigua que los tenía, el editor los quita y avisa «Se quitaron N campos de Foto/Firma: ahora van en la OT».

> [CAPTURA: Editor de una plantilla de checklist con la paleta de tipos de campo, un campo «Sí / No» con «Permite N/A (no aplica)» marcada y la sección «Grupos que se repiten» con «Toma» — Administrador, Web]

> [CAPTURA: Pestaña «Historial de versiones» de la plantilla con al menos dos versiones — Administrador, Web]

### 3.8 Tareas pendientes y armado de órdenes

**Para qué sirve:** es el centro de trabajo del planificador. Aquí se ven las tareas que toca hacer, se agrupan las de una misma visita en una OT, y se reprograman o anulan con causa.

**La pantalla**

Los filtros son «Hospital», «Ubicación» (con lo que tiene dentro), «Protocolo», «Buscar activo o tarea», «Desde», «Hasta» y «Solo vencidas». Un contador indica «N pendientes · M vencidas». La tabla muestra la fecha programada («vencida hace…» o «Reprogramada · calc. …»), el activo, la tarea (con su tipo y protocolo), «Cuándo» y la duración. Un botón de historial muestra las fechas y las reprogramaciones.

**Crear una OT desde tareas pendientes**

1. Entre a «Tareas pendientes».
2. Filtre por hospital (y ubicación si quiere).
3. Marque las tareas de **una misma visita**. Deben ser de un solo hospital: si marca tareas de varios, «Crear OT» se deshabilita.
4. En la barra que aparece («N marcadas · duración total · hospital»), pulse «Crear OT».
5. Complete la ventana:
   - «Asignado a»: el técnico (también puede elegir un supervisor o administrador).
   - «Fecha de la visita».
   - «Prioridad».
   - «Ubicación de la visita» (el sistema propone la común).
   - «Título» (el sistema propone uno).
   - «Indicaciones para el técnico».
6. Si el hospital no tiene contrato vigente, aparece un aviso: puede crear la OT igual.
7. Pulse el botón para crear. Aparece «OT creada». Elija «Seguir planificando» o «Ver la OT».

La «Fecha de la visita» **no cambia** la fecha programada de cada tarea. Si una tarea se hará otro día por una causa, reprográmela antes. La OT toma la versión del checklist vigente en ese momento; si la plantilla no tiene versión publicada, entra sin checklist y el sistema avisa.

**Reprogramar tareas**

1. Marque las tareas.
2. Pulse «Reprogramar».
3. Escriba la «Nueva fecha» y elija la «Causa» de la lista (3 VISITAS, ADELANTADO, ANUAL, APLAZADO, GARANTIA, MANTENIMIENTO PUNTUAL, NO DISPONIBLE, PREVENTIVO, PRIMERA VISITA, SOLO 1 VISITA).
4. Opcionalmente, una nota.
5. Confirme.

La fecha calculada no cambia: queda el registro de quién, cuándo y por qué se movió.

**Anular tareas**

1. Marque las tareas y pulse «Anular».
2. Escriba «Por qué se anula» (obligatorio).
3. Confirme.

Anular significa «esta ya no toca»: no se hace ni se crea la siguiente. Si solo se hará otro día, **reprograme**.

Otras reglas: solo se reprograma o anula lo que está **Pendiente** (lo que ya está en una OT hay que sacarlo de la OT primero). Al cambiar un filtro, la selección se **desmarca**, para no meter en una OT algo escondido. «Desmarcar» limpia la selección. Las pendientes de un protocolo pausado no salen en esta lista.

> [CAPTURA: «Tareas pendientes» con dos tareas del «Piso 1 - Urgencias» marcadas y la barra «N marcadas» con «Crear OT», «Reprogramar» y «Anular» — Administrador, Web]

> [CAPTURA: Ventana «Crear OT» con el técnico asignado, fecha de la visita, título propuesto y ubicación común — Administrador, Web]

> [CAPTURA: Ventana «Reprogramar» con la lista «Causa» desplegada — Administrador, Web]

### 3.9 Crear una OT manual (solo Administrador)

Sirve para crear a mano una OT correctiva o de verificación, sin pasar por un protocolo.

1. Entre a «Ordenes de trabajo» y pulse «+ Nueva OT».
2. Elija el «Hospital» y, si quiere, la «Ubicación» (queda como ubicación de la visita).
3. Marque los equipos. Puede buscar por código o nombre, o pulsar «Marcar los N de esta lista». Todos deben ser del mismo hospital.
4. Para cada equipo elija su checklist (de las plantillas con versión publicada) o «Sin checklist». Si el equipo tiene un checklist predeterminado, ya viene elegido.
5. Elija el «Tipo de OT» (por defecto «Correctivo»).
6. Escriba el «Título» (por ejemplo, «Mantenimiento correctivo compresor de oxígeno») y la descripción.
7. Elija la «Prioridad» y la «Fecha límite».
8. Escriba la «Duración estimada» y elija a quién se «Asigna».
9. Pulse «Crear OT».

La OT nace «Pendiente» y sus tareas ya quedan programadas.

> [CAPTURA: Formulario «Nueva orden de trabajo» con un hospital, equipos marcados, tipo «Correctivo» y asignado a un técnico de demo — Administrador, Web]

### 3.10 Lista y detalle de las órdenes; asignar técnicos

**La lista de órdenes**

La pantalla «Ordenes de trabajo» muestra «N órdenes encontradas». Puede buscar por título, número o equipo y filtrar por estado, prioridad, tipo, «Solo vencidas», hospital, ubicación y activo («Quitar filtros de lugar» los limpia). La tabla muestra número, tipo, título, activo, hospital, prioridad, estado, técnico, fecha límite, PDF y «Ver». Las órdenes no se borran.

> [CAPTURA: Lista «Ordenes de trabajo» con el filtro de estado «En revisión» y la OT «OT-2026-00009» o una OT en revisión de demo — Administrador, Web]

**El detalle de una OT**

Pulse «Ver». Arriba aparece el número, el tipo, el estado, la prioridad y los botones que usted puede usar. Debajo hay tarjetas («Activo(s)», «Asignación», «Fechas», «Progreso») y las pestañas:

- «Historial de estados»
- «Checklist» (si la OT tiene varios equipos se llama «Tareas (N)»)
- «Evidencia» (firmas y fotos)
- «Repuestos»
- «Reportes» (el acta)
- «Hallazgos»

La tarjeta «Progreso» muestra «Avance» y calificación, pero hoy no se llenan: el avance real está en la pestaña «Checklist».

**Asignar o reasignar un técnico**

1. En el detalle, en la tarjeta «Asignación», pulse «Reasignar».
2. En la ventana «Reasignar OT», elija a la persona (técnico, supervisor o administrador) en «Seleccionar...».
3. Pulse «Reasignar».

También puede cambiarlo con «Editar». Una OT Finalizada o Cancelada no se puede reasignar.

**Editar los datos de una OT**

1. Pulse «Editar».
2. Cambie título, descripción, prioridad, fecha límite, duración estimada, persona asignada, clasificaciones y notas. El checklist solo se puede cambiar si nadie lo ha respondido y la OT tiene una sola tarea.
3. Pulse «Guardar cambios».

**Agregar o quitar tareas de una OT que no empezó**

1. En la pestaña «Tareas (N)», con la OT en «Pendiente», pulse «Agregar tareas». En «Agregar tareas a la OT» aparecen las pendientes del mismo hospital.
2. Marque las que quiera y confirme.
3. Para sacar una, pulse la «x» de su fila y confirme con «Quitar»: la tarea vuelve a pendientes con su fecha, lista para otra OT.

**Ejecutar la OT usted mismo (Administrador o Supervisor)**

A veces el Administrador o el Supervisor hacen el trabajo (por ejemplo, un informe de instalaciones donde no va un técnico).

1. Abra la OT en «Pendiente» o «En proceso».
2. Pulse «Asignármela».
3. Ahora aparecen los botones del técnico: «Iniciar OT», el checklist, la evidencia y «Enviar a revision». Se usan igual que en la sección 4.
4. Mientras no se la asigne, usted solo revisa; no ejecuta.

**Cancelar una OT (solo Administrador)**

1. Pulse «Cancelar OT».
2. Escriba el motivo en «Motivo de cancelacion...» (obligatorio).
3. Pulse «Confirmar cancelacion». Necesita conexión.

Las tareas de la OT **vuelven a pendientes con la misma fecha**, listas para otra OT. Lo que no se puede deshacer es la cancelación de la OT en sí.

**Cómo quedan los repuestos.** En la pestaña «Repuestos», la persona asignada o el Administrador pulsa «Agregar repuesto» (ventana «Registrar repuesto usado»), busca el artículo, escribe la cantidad y pulsa «Registrar». Se descuenta del inventario. Solo se puede con la OT «En proceso» y con conexión.

> [CAPTURA: Detalle de una OT de demo con las tarjetas «Activo(s)», «Asignación» (botón «Reasignar»), «Fechas» y las seis pestañas — Administrador, Web]

> [CAPTURA: Ventana «Reasignar OT» con la lista de personas desplegada — Administrador, Web]

### 3.11 Revisar, corregir y aprobar

Cuando el técnico envía la OT, queda «En revisión». Quien revisa (Administrador o Supervisor) hace lo siguiente.

**Revisar**

1. Entre a «Ordenes de trabajo» y filtre por «En revisión».
2. Abra la OT.
3. En «Checklist» o «Tareas (N)», revise las respuestas de cada equipo. Si algún punto quedó pendiente, aparece su motivo.
4. En «Evidencia», revise las fotos y las firmas.
5. En «Hallazgos», revise lo reportado.

**Corregir (solo con la OT en revisión)**

- **Respuestas del checklist:** pulse «Corregir respuestas», cambie lo que haga falta (cada cambio se guarda al salir del campo) y pulse «Terminar». Cada respuesta corregida queda marcada «Corregido por» con su nombre; el valor anterior queda en la auditoría.
- **Fotos:** en «Evidencia» puede agregar fotos, cambiar la descripción u **ocultar** una con «Ocultar del acta» (después, «Volver a mostrar en el acta»). Las fotos **no se borran**: quedan en la OT y en la auditoría. El hospital no ve las ocultas.
- **Fecha de intervención:** por defecto sale de lo que registró el técnico (de la primera a la última respuesta, foto o firma). Pulse «Corregir» (o «Cambiar»), escriba la fecha y la hora, y «Guardar fecha». El acta y el correo usan la fecha corregida. «Quitar la corrección» vuelve a la del técnico.

La constancia de las correcciones queda en la OT y en la auditoría, **no** en el acta.

**Rechazar**

1. Pulse «Rechazar».
2. Escriba el «Motivo del rechazo...».
3. Pulse «Confirmar rechazo».

La OT vuelve a «En proceso» y el técnico debe corregir y enviarla otra vez. El motivo queda en el «Historial de estados», que el técnico no puede ver. Avísele por otro medio qué debe corregir.

**Aprobar (firma de validación)**

1. Pulse «Completar».
2. Se abre la ventana «Aprobar orden» («La orden se cierra y queda firmada por ti.»).
3. Si ya tiene firma guardada, verá «Se firmará con tu firma guardada» y su firma en pequeño. Pulse «Aprobar y firmar».
4. Si no tiene firma guardada, la ventana dice «Para aprobar necesitas registrar tu firma». Pulse «Ir a Mi perfil para registrarla», dibuje su firma, vuelva a la OT y repita.
5. La OT pasa a «Finalizada». El sistema genera el acta en segundo plano («Generando reporte…») y la envía por correo.
6. Las tareas pasan a «Finalizada» y cada una crea la siguiente pendiente (si el protocolo lo permite y el equipo sigue «Activo»).

El acta lleva la firma de validación como «Validado por». Si falta la firma guardada, el sistema responde «Registra tu firma en Mi perfil para aprobar esta orden.» con un enlace a «Ir a Mi perfil».

También puede aprobar **sin conexión** si ya abrió la OT con red antes (ver sección 6).

> [CAPTURA: Detalle de una OT «En revisión» con los botones «Completar» y «Rechazar», y el checklist con «Corregir respuestas» — Supervisor, Web]

> [CAPTURA: Ventana «Aprobar orden» con la firma guardada del supervisor en pequeño y el botón «Aprobar y firmar» — Supervisor, Web]

> [CAPTURA: Ventana «Aprobar orden» cuando no hay firma guardada, con el mensaje «Para aprobar necesitas registrar tu firma» y el enlace «Ir a Mi perfil para registrarla» — Supervisor, Web]

> [CAPTURA: Pestaña «Evidencia» en revisión con una foto marcada «Volver a mostrar en el acta» y otra con «Ocultar del acta» — Supervisor, Web]

### 3.12 Hallazgos (bandeja del planificador)

**Para qué sirve:** ver lo que los técnicos encontraron y no resolvieron en el sitio, y decidir qué hacer. Lo deciden el Administrador y el Supervisor.

**La pantalla**

«Hallazgos» muestra el aviso «N críticos o con equipo fuera de servicio» y cuatro pestañas: «Por decidir» (con contador), «Convertidos», «Descartados» y «Resueltos en sitio». Puede filtrar por hospital («Todos los hospitales») y por severidad («Toda severidad»). Cada hallazgo muestra su severidad (y «Fuera de servicio» si aplica), el equipo con su código, el hospital, la ubicación y la OT, la descripción, quién lo reportó, cuándo y cuántas fotos tiene. Los más graves van primero.

**Convertir un hallazgo en tarea correctiva**

1. En «Por decidir», abra el hallazgo y pulse «Convertir en correctivo».
2. Escriba la «Fecha programada» y, si quiere, una nota.
3. Pulse «Crear correctivo».
4. Se crea una tarea correctiva pendiente sobre ese equipo, con prioridad según la severidad (Crítica y Alta quedan en prioridad Alta). La encuentra en «Tareas pendientes» para agruparla en una OT.

**Descartar un hallazgo**

1. Pulse «Descartar».
2. Escriba «Por qué se descarta» (obligatorio). Ejemplo: «ya lo corrigió el hospital».
3. Pulse «Descartar».

**Reglas**

- Solo puede decidir cuando la OT del hallazgo ya está **En revisión** o **Finalizada**. Antes, el técnico todavía puede corregirlo y se ve «La OT sigue en curso».
- El hospital recibe un **correo** cuando se completa la OT si hay hallazgos graves (críticos o con equipo fuera de servicio), y lo ve también en su portal.
- «El equipo queda fuera de servicio» es una **marca del hallazgo**: alimenta el aviso y el acta, pero **no cambia el estado del activo**. Si el equipo debe pasar a «Fuera de servicio», cámbielo en «Editar activo».

> [CAPTURA: Bandeja «Hallazgos» en la pestaña «Por decidir», con el hallazgo crítico del compresor fuera de servicio de demo y los botones «Convertir en correctivo» y «Descartar» — Supervisor, Web]

> [CAPTURA: Ventana «Convertir en correctivo» con la fecha programada y la nota — Supervisor, Web]

### 3.13 Reportes: actas, reenvío y consolidado

**Para qué sirve:** buscar y descargar las **actas** generadas, y reenviarlas por correo. Solo hay actas de órdenes **Finalizadas**.

**Buscar y descargar un acta**

1. Entre a «Reportes».
2. Filtre por «Hospital», «N° OT» (acepta «42» o el código completo), «Desde» y «Hasta», y pulse «Filtrar». «Limpiar» quita los filtros.
3. La tabla muestra la OT, el título, el hospital, cuándo se generó, el código de verificación (SHA-256) y cuántos envíos por correo salieron bien.
4. Pulse «Descargar» para obtener el PDF.

También puede descargar el acta desde la OT: pestaña «Reportes» → «Descargar PDF».

**Reenviar varias actas por correo (solo Administrador)**

1. En la tabla, marque las actas (la casilla del encabezado marca todas las visibles). Puede reenviar hasta **50 actas** a la vez.
2. Abajo aparece la barra con «Reenviar por correo» y «Quitar selección».
3. Pulse «Reenviar por correo». La ventana «Reenviar actas por correo» agrupa las actas por hospital y dice a qué correo irá cada grupo. Los PDF van adjuntos.
4. Si un hospital no tiene correo de contacto, esas actas **no se enviarán**; la ventana lo avisa.
5. Pulse «Reenviar».
6. El resultado se divide en «En camino» (hospital, cuántas actas y a qué correo) y «No se enviaron» (con el motivo). Pulse «Cerrar».

Para reenviar una sola acta también sirve «Reenviar email» en la pestaña «Reportes» de la OT.

**Reporte consolidado (solo Administrador)**

Genera un PDF con todas las órdenes de un periodo.

1. En «Reportes», en el cuadro «Reporte consolidado», elija el «Hospital» (o todos), «Desde», «Hasta» y el «Tipo de OT».
2. Pulse «Generar reporte consolidado».
3. Aparece «Reporte en generacion». Cuando esté listo, le llega por correo a su dirección.

**Verificar que un acta no fue alterada (solo Administrador)**

1. Abra la OT → pestaña «Reportes».
2. Pulse «Verificar integridad del documento».
3. El sistema compara el PDF con su código y dice si coincide.

**Si el acta no se generó.** En la pestaña «Reportes» de la OT aparece «El reporte no se pudo generar.» El Administrador pulsa «Generar reporte de nuevo».

> [CAPTURA: Pantalla «Reportes» con el cuadro «Reporte consolidado», los filtros y la tabla de actas de «Clínica Demo Norte» — Administrador, Web]

> [CAPTURA: Barra inferior «N actas seleccionadas» con «Reenviar por correo» y la ventana «Reenviar actas por correo» con el resumen por hospital — Administrador, Web]

> [CAPTURA: Pestaña «Reportes» de una OT finalizada con «Descargar PDF», el código SHA-256, «Envios por correo» y «Verificar integridad del documento» — Administrador, Web]

### 3.14 Formato del acta (solo Administrador)

**Para qué sirve:** decidir qué imprime el acta, con interruptores. Es **un solo formato para todo el sistema** y se aplica a las actas **nuevas**; las ya generadas no cambian.

**Qué siempre sale (no se puede apagar)**

- Número de orden, tipo y fecha de emisión.
- Hospital.
- La ubicación física (la ruta de la ubicación).
- Los resultados de la revisión (checklist).
- El código de verificación en el pie.
- El aviso de firma electrónica (Ley 527 de 1999).

**Qué se puede prender o apagar**

- **Datos de la visita:** cuántos activos se intervinieron, quién hizo el trabajo, fecha programada, fecha y hora del trabajo (inicio y fin), tiempo que tomó, descripción y notas.
- **Activos:** dónde está el equipo dentro de la ubicación, tipo, fabricante, modelo y serie.
- **Checklist:** nombre de la lista, observaciones de cada resultado, cuándo y quién hizo la revisión, y el mapa de la ubicación tomada con el celular.
- **Hallazgos.**
- **Fotos:** de cada activo, generales de la visita y coordenadas.
- **Materiales.**
- **Firmas:** «Realizado por» (técnico), «Validado por» (aprobación del supervisor) y «Aceptado por» (firma de quien recibe en el hospital).

**Cómo cambiarlo**

1. Entre a «Formato del acta».
2. Prenda o apague los interruptores. Abajo se lee «N cambio(s) sin guardar» o «N campo(s) ocultos en el acta».
3. Pulse «Vista previa» para ver un PDF de ejemplo, sin guardar. Necesita al menos una OT finalizada; si no, dice «Todavía no hay OTs finalizadas para mostrar un acta de ejemplo».
4. Pulse «Guardar cambios». Para olvidar lo que cambió, «Descartar».

«Validado por» sale de quien aprobó la OT. «Aceptado por» es la firma de quien recibe en el hospital; si no se capturó, el acta dice «No registrada».

> [CAPTURA: Pantalla «Formato del acta» con las secciones de interruptores y la barra inferior «Descartar / Vista previa / Guardar cambios» — Administrador, Web]

> [CAPTURA: PDF de un acta de ejemplo abierto desde «Vista previa» con las firmas «Realizado por», «Validado por» y «Aceptado por» — Administrador, Web]

### 3.15 Calendario

**Para qué sirve:** ver las tareas del mes por su fecha programada.

1. Entre a «Calendario».
2. Elija el hospital («Todos los hospitales») y use las flechas para cambiar de mes.
3. Cada día muestra puntos con el número de tareas según su situación: **Vencida** (rojo), **Reprogramada** (ámbar), **Pendiente** (gris), **En OT** (azul) y **Finalizada** (verde). Abajo hay una leyenda.
4. Pulse un día para ver sus tareas (código y nombre del equipo, tarea y protocolo, hospital, ubicación, fecha calculada si fue reprogramada y la OT).
5. Si el día tiene pendientes, pulse «Planificar en Tareas pendientes».

El calendario es de **solo lectura**: no se arrastra para reprogramar. Se reprograma en «Tareas pendientes». No muestra las tareas canceladas.

> [CAPTURA: «Calendario» del mes actual con el panel de un día seleccionado y la leyenda de colores — Administrador, Web]

### 3.16 Inventario

**Para qué sirve:** controlar repuestos y consumibles y descontarlos desde las OT.

La pantalla «Inventario» muestra los artículos con «Nombre» (con la marca «Stock bajo»), «Codigo», «Unidad», «Stock actual», «Stock minimo», «Estado» y «Acciones». Las filas con stock bajo (stock igual o menor al mínimo) van resaltadas, y el globo del menú cuenta cuántas son. Busque por nombre o código y filtre por «Todos», «Solo activos» o «Solo inactivos».

**Crear un artículo (solo Administrador)**

1. Pulse «Nuevo item».
2. Escriba «Nombre» y «Codigo» (obligatorios), descripción, unidad de medida, stock mínimo y costo unitario.
3. Pulse «Crear item».

**Registrar un movimiento (Administrador y Supervisor)**

1. En la fila del artículo, pulse «Ver movimientos».
2. Pulse «Registrar movimiento».
3. Elija el tipo: «Entrada», «Salida» o «Ajuste (establece cantidad exacta)».
4. Escriba la cantidad, una referencia y notas.
5. Guarde.

La pantalla de movimientos muestra el stock actual y mínimo, y una tabla con fecha, tipo, cantidad, OT relacionada, referencia y quién lo registró.

**Reglas**

- El stock **solo cambia por movimientos**. No se edita a mano.
- Una salida mayor al stock se rechaza («Stock insuficiente»).
- El técnico registra **salidas** desde su OT, en la pestaña «Repuestos».
- El inventario es global: no está separado por hospital.

> [CAPTURA: Pantalla «Inventario» con un artículo en «Stock bajo» resaltado — Administrador, Web]

> [CAPTURA: Historial de movimientos de un artículo con una salida ligada a una OT — Administrador, Web]

### 3.17 Tipos de tarea (solo Administrador)

**Para qué sirve:** el catálogo de los tipos que se eligen en las tareas de los protocolos y en las órdenes. «Cuenta como» decide en qué indicador entra cada uno.

**Agregar un tipo**

1. Entre a «Tipos de tarea».
2. Escriba el nombre (por ejemplo, «Revisión de válvulas»).
3. Elija en «Cuenta como»: «Preventivo», «Correctivo» o «Ninguno».
4. Pulse «Agregar».

**Qué significa «Cuenta como»**

- **Preventivo:** entra en el «Cumplimiento de protocolos» del «Dashboard».
- **Correctivo:** entra en el tiempo medio de reparación (MTTR).
- **Ninguno:** no entra en esos indicadores.

**Otras acciones:** «Renombrar» (el código no cambia), cambiar «Cuenta como», activar o desactivar, y «Borrar» (solo si ninguna tarea ni OT lo usa). Un tipo en uso no se borra: se desactiva y deja de ofrecerse, pero lo que ya lo tiene lo conserva. Los tipos del sistema no se desactivan ni se borran.

> [CAPTURA: Pantalla «Tipos de tarea» con la lista de tipos y la columna «Cuenta como» — Administrador, Web]

### 3.18 Usuarios (solo Administrador)

**Para qué sirve:** crear cuentas, ajustar su alcance y permisos, restablecer contraseñas y desactivar usuarios.

La pantalla «Gestión de usuarios» muestra «N de M usuarios», la tabla con «Nombre completo», «Email», «Rol», «Alcance» («Todos» o el hospital y la parte), «Permisos adicionales» y «Estado», y los filtros de búsqueda, rol («Todos los roles») y «Mostrar inactivos».

**Crear un usuario**

1. Pulse «Nuevo usuario».
2. Lea el recordatorio: antes de crear la cuenta, tenga la autorización del titular para tratar sus datos personales (Ley 1581 de 2012).
3. Escriba «Nombre», «Apellido» y «Email». Elija el «Rol» (el rol **no se puede cambiar** después).
4. Defina el alcance:
   - **Cuenta de hospital:** elija el «Hospital» (obligatorio). Sin hospital, esa cuenta no vería nada.
   - **Supervisor o Técnico:** en «Limitar a un hospital» elija uno (o «Todos los hospitales») y, si quiere, la «Parte del hospital» («Todo el hospital» o una ubicación; incluye lo que cuelga de ella).
   - **Técnico:** escriba el «Codigo de empleado» y el «Telefono».
5. Para Supervisor o Técnico, marque en «Permisos adicionales» lo que esa persona puede hacer además de lo que ya trae su rol. Los marcados «Incluido en el rol» ya los tiene. Los permisos suman: nunca quitan, y no amplían el alcance por hospital.
6. Pulse «Crear usuario».
7. El sistema envía por correo una contraseña temporal («Usuario creado. Se envio el correo de bienvenida a …»). La pantalla no la muestra. Si el correo no llegó, restablezca la contraseña.

**Permisos adicionales disponibles**

| Área | Permiso |
|---|---|
| Órdenes de trabajo | Crear órdenes de trabajo · Crear órdenes desde pendientes · Asignar y reasignar · Revisar y aprobar · Cancelar órdenes |
| Planificación | Planificar tareas pendientes · Gestionar protocolos · Gestionar checklists |
| Equipos y contratos | Gestionar equipos y ubicaciones · Gestionar contratos y garantías · Decidir hallazgos |
| Inventario | Gestionar artículos de inventario · Registrar movimientos de inventario |
| Reportes | Ver reportes y actas |

Quedan siempre solo para el Administrador: usuarios, formato del acta, tipos de tarea, hospitales, campos personalizados y auditoría.

**Ver y editar un usuario**

1. En su fila, pulse «Ver».
2. Cambie nombre, apellido, teléfono, código de empleado, alcance o permisos adicionales. Con «Usuario activo» puede activarlo o desactivarlo.
3. Abajo ve «Actividad reciente» (las últimas 5 acciones) y «Ver historial completo», que abre la auditoría ya filtrada por esa persona.
4. Pulse «Guardar cambios».

**Restablecer una contraseña**

1. En la fila, pulse el botón de la llave («Restablecer contrasena»).
2. Confirme: «Se enviara una contrasena temporal al correo del usuario».
3. Pulse «Restablecer». La persona deberá cambiarla al entrar.

**Desactivar o activar**

Pulse «Desactivar» (o «Activar») en la fila y confirme. Usted **no puede desactivar su propia cuenta**.

> [CAPTURA: Pantalla «Gestión de usuarios» con la tabla de los cuatro usuarios de demo y la columna «Permisos adicionales» — Administrador, Web]

> [CAPTURA: Ventana «Nuevo usuario» con el rol «Técnico», el alcance elegido y la sección «Permisos adicionales» con algunas casillas marcadas — Administrador, Web]

### 3.19 Auditoría y exportación a CSV (solo Administrador)

**Para qué sirve:** ver quién hizo qué y cuándo. No se puede borrar nada del registro.

1. Entre a «Auditoria». Verá «Log de auditoria» y el número de registros.
2. Filtre por usuario («Todos los usuarios»), acción («Todas las acciones»), entidad («Todas las entidades»), «Desde» y «Hasta», y pulse «Aplicar filtros». «Limpiar» los quita.
3. Las acciones son: Crear, Actualizar, Eliminar, Cambio de estado, Inicio de sesion, Sincronizacion, Exportacion y Anonimizacion.
4. La tabla muestra fecha y hora, usuario («Sistema» si no hay), acción, entidad, identificador e IP. Pulse una fila para ver el «Detalle de cambios» (valor anterior y nuevo).
5. Hay 50 registros por página; use «Anterior» y «Siguiente».

**Exportar a CSV**

1. Ponga los filtros que quiera.
2. Pulse «Exportar CSV». El archivo trae **todo el resultado del filtro**, no solo la página que está viendo. Si no escribe fechas, exporta los últimos 90 días. El rango máximo por exportación es de 366 días: si pide más, el sistema pide reducirlo.
3. Cada exportación queda registrada en la propia auditoría como «Exportacion».

También se llega aquí desde la ficha de un usuario («Ver historial completo»).

> [CAPTURA: Pantalla «Log de auditoria» con una fila expandida con el «Detalle de cambios» y el botón «Exportar CSV» — Administrador, Web]

### 3.20 Datos personales de los usuarios: exportar y anonimizar (solo Administrador)

Cuando un titular ejerce sus derechos (Ley 1581 de 2012), el Administrador lo atiende desde «Usuarios».

**Exportar los datos de una persona**

1. En «Usuarios», pulse «Exportar datos» en su fila.
2. Se descarga un archivo con sus datos personales.
3. Aparece «Datos personales exportados. Queda constancia en la auditoría.»

**Anonimizar una cuenta**

La anonimización solo se permite con la cuenta **desactivada** y con **más de 2 años sin actividad**. No se puede deshacer.

1. Desactive la cuenta (ver 3.18).
2. Cuando cumpla las condiciones, pulse «Anonimizar» en su fila.
3. Lea la ventana «Anonimizar usuario». Se **borra o reemplaza**: el nombre y apellido (pasan a «Usuario anonimizado» con un código), el correo (se cambia por uno genérico y ya no podrá entrar), el teléfono y el código de empleado (se vacían), la contraseña (se inutiliza) y la firma guardada (se borra).
4. Se **conserva**: las órdenes de trabajo, las firmas de las actas y las fotos de evidencia, el registro de auditoría y la constancia de aceptación del aviso de privacidad. La normativa sanitaria obliga a conservarlos.
5. Pulse «Anonimizar». Aparece «Usuario anonimizado.»

Si la cuenta no cumple las condiciones, el sistema explica por qué y no la anonimiza.

> [CAPTURA: Ventana «Anonimizar usuario» con la lista de lo que se borra y lo que se conserva — Administrador, Web]

---

## 4. Técnico (app Android)

El técnico trabaja desde el celular con la app de TodoGas. Ve **solo las órdenes que tiene asignadas**, sin importar su alcance. Esta sección sigue el trabajo en el orden en que se hace: antes de salir, en el hospital y al terminar.

### 4.1 Antes de salir: prepare el celular

1. Abra la app **con señal** (Wi-Fi o datos).
2. Entre a «Mis ordenes». Al cargar la lista, la app descarga en segundo plano el detalle y las listas de revisión de **todas sus órdenes abiertas** («Pendientes» y «En proceso») y su firma guardada.
3. Verifique que su firma esté guardada: «Mi perfil» → «Mi firma». Si no la tiene, regístrela ahora (necesita señal).
4. Abra la orden que va a hacer (basta con abrirla una vez con señal) para confirmar que quedó en el celular.

Si abre una orden sin señal y no la había descargado, la app avisa: «Esta OT no está descargada en el teléfono. Ábrela con conexión para poder trabajarla sin red.»

Recuerde que la app **envía sola** lo que quedó guardado cuando vuelve la señal: no hay un botón de sincronizar. Lo hace al recuperar la conexión, al abrir la app y cada minuto mientras haya señal.

> [CAPTURA: Pantalla «Mi perfil» en la app Android mostrando la firma guardada, antes de salir a campo — Técnico, App Android]

### 4.2 Ver sus órdenes

1. Entre a «Mis ordenes» (es su pantalla de inicio).
2. Arriba están las pestañas «Pendientes», «En proceso», «En revisión» y «Todas».
3. Cada tarjeta muestra el número, el tipo, la prioridad, el título, el equipo (o «N activos»), el hospital y la ubicación, el estado y la fecha límite («Límite: …» o «Vencida —»). Abajo está el botón que le toca («Iniciar OT» o «Enviar a revision») y «Ver detalle».
4. Si una tarjeta muestra el aviso «Datos pendientes de sincronizar», tiene cosas guardadas en el celular que aún no subieron.

Si no hay órdenes en una pestaña, la pantalla dice «No hay órdenes en esta categoría».

> [CAPTURA: Lista «Mis órdenes de trabajo» en la app, pestaña «Pendientes», con la tarjeta de «OT-2026-00009» de «Clínica Demo Norte» — Técnico, App Android]

### 4.3 Iniciar la orden

1. En «Mis ordenes», pulse «Iniciar OT» en la tarjeta (o entre a «Ver detalle» y púlselo arriba).
2. La orden pasa a «En proceso».

Hasta que inicie la orden, el checklist y la evidencia no se pueden editar: la pantalla dice «Inicia la OT para responder los checklists y adjuntar fotos.» Funciona también sin señal.

### 4.4 Llenar el checklist

1. En el detalle de la orden, abra la pestaña «Checklist». Si la orden tiene varios equipos, la pestaña se llama «Tareas (N)» y muestra una lista con el avance de cada equipo («Sin empezar», «En curso» o «Completo»). Toque el equipo que va a revisar.
2. Pulse «Iniciar checklist». Aparece el nombre de la plantilla y su versión.
3. Responda cada campo. **Cada respuesta se guarda sola al salir del campo** y aparece «guardado».
   - **Sí / No / N/A:** toque el botón. Si el campo no permite N/A, solo hay «Sí» y «No».
   - **Número o lectura de medidor:** escriba el valor con su unidad. Si queda fuera del rango permitido, la pantalla lo señala.
   - **Texto:** escriba la respuesta u observación.
   - **Selección:** elija una o varias opciones.
   - **Localización GPS:** pulse «Capturar» con el celular al aire libre o junto a una ventana.
4. Los campos obligatorios llevan asterisco. La barra de progreso dice «N de M campos completados».
5. Cuando termine todos, pulse «Finalizar checklist». Si falta algún obligatorio, el botón queda desactivado y dice cuántos faltan («N campo(s) obligatorio(s) sin responder»).
6. Al terminar todos los checklists de la orden, aparece «Todos los checklists están completos». La app pregunta «¿Envías la OT a revisión?». Pulse «Enviar a revision», o «Ahora no» si todavía le falta algo (la foto o la firma).

**Equivocarse.** Mientras la orden esté «En proceso» puede cambiar cualquier respuesta, incluso si ya finalizó el checklist: el aviso azul dice «Puedes cambiar cualquier respuesta mientras la OT esté en curso». Si el checklist quedó por finalizar, vuelva a finalizarlo con «Terminar» o «Finalizar checklist».

**Bloques repetibles (tomas).** Cuando el checklist tiene un bloque como «Toma», verá una toma a la vez.

1. Responda todos los campos de la toma 1.
2. Pulse «Siguiente: Toma 2» (o «Siguiente» y «Anterior» para moverse).
3. Si encuentra más tomas de las que dice el protocolo, pulse «Agregar toma». Si sobra una que está vacía, pulse «Quitar toma N (vacía)».
4. Cuando la cantidad no coincide con el protocolo, la pantalla avisa «El protocolo dice N y aquí hay M». El aviso se ve en la OT.

**Dejar un punto pendiente («no se pudo revisar»).** Si un punto o una toma no se pudo revisar (por ejemplo, un cubículo aislado por aerosoles):

1. Pulse «Marcar pendiente» bajo el campo, o «Marcar Toma N como pendiente (no se pudo revisar)» en el bloque.
2. Escriba «¿Por qué no se pudo revisar?» (por ejemplo, «aislado por aerosoles»). Es obligatorio.
3. Pulse «Dejar pendiente».
4. El punto queda con una franja «Pendiente — no se pudo revisar». Arriba de la OT aparece «N pendiente(s) por volver a revisar» con la lista. **Mientras haya pendientes, la orden no se puede enviar a revisión.**
5. Cuando pueda revisarlo, **responda el campo**: el pendiente desaparece solo. O pulse «Quitar» para retirar la marca sin responder.

> [CAPTURA: Checklist de una toma de oxígeno en la app, con un campo «Sí / No / N/A» respondido, una lectura en PSI y el aviso «guardado» — Técnico, App Android]

> [CAPTURA: Bloque repetible «Toma» con los botones «Siguiente: Toma 2», «Agregar toma» y «Quitar toma N (vacía)» — Técnico, App Android]

> [CAPTURA: Un punto marcado como pendiente con la franja «Pendiente — no se pudo revisar» y el aviso «1 pendiente por volver a revisar» arriba de la OT — Técnico, App Android]

### 4.5 Tomar las fotos

Se necesita **al menos una foto** para enviar la orden a revisión. Las fotos se toman en la pestaña «Evidencia».

1. Abra la pestaña «Evidencia» y busque «Agregar foto».
2. Pulse «Tomar foto» (en la app se abre la cámara; en la web el botón dice «Seleccionar foto»). Tome la foto. Permita el uso de la cámara y de la ubicación si el celular lo pide.
3. Elija el momento de la foto con los botones **«Antes»** o **«Después»**.
4. Si la orden tiene varios equipos, en «¿De qué activo es?» elija el equipo, o «De la visita en general».
5. Escriba una descripción si quiere («Descripcion (opcional)»).
6. Pulse «Subir foto» (sin señal dice «Guardar foto»).

Sobre las fotos:

- La app anota solita la ubicación GPS y la hora. Si no consigue la ubicación, avisa «No se pudo obtener la ubicacion. La foto se subira sin coordenadas GPS.» y la foto sube igual. **La foto es obligatoria; el GPS, no.**
- Si la foto pesa más de 10 MB, la app la reduce sola.
- Sin señal aparece «Foto guardada. Se sincronizara al reconectar.»
- Las fotos no se borran. Si una foto quedó mala, tome otra: quien revisa puede ocultar la que no sirva.

> [CAPTURA: Pestaña «Evidencia» en la app, sección «Agregar foto» con una foto tomada, los botones «Antes» y «Después» y «Subir foto» — Técnico, App Android]

> [CAPTURA: Galería de fotos de la OT con una foto «Antes» y una «Después» — Técnico, App Android]

### 4.6 Firmar: la suya y la de quien recibe

Se necesitan **firmas** para enviar la orden a revisión. En la pestaña «Evidencia», sección «Agregar firma», hay dos paneles.

**Su firma («Firma del técnico»)**

1. Si tiene firma guardada, aparece su firma con los botones «Usar mi firma guardada» y «Dibujar a mano».
2. Pulse «Usar mi firma guardada». Aparece «Firma guardada correctamente.» Se firma con su nombre y su cargo.
3. Si prefiere dibujarla, pulse «Dibujar a mano», firme en el recuadro, escriba el «Nombre del firmante» (obligatorio) y el «Cargo», y pulse «Guardar firma». Si se equivoca, pulse «Limpiar».

**La firma de quien recibe en el hospital («Firma de quien recibe en el hospital»)**

Esta firma **siempre se dibuja a mano** en cada visita.

1. Pásele el celular a la persona del hospital que recibe el trabajo.
2. Que firme en el recuadro con el dedo.
3. Escriba su «Nombre del firmante» (obligatorio) y su «Cargo».
4. Debajo del recuadro hay una línea: «Al firmar autoriza el tratamiento de su nombre, cargo y firma para el acta de servicio, según el aviso de privacidad…». Pulse «Ver aviso de privacidad» si la persona quiere leerlo.
5. Pulse «Guardar firma». El acta lo imprime como «Aceptado por».

Si intenta guardar sin firmar, la pantalla dice «Por favor firme en el area antes de guardar». Si falta el nombre: «El nombre del firmante es requerido».

Solo se puede firmar mientras la orden está en progreso. Sin señal, la firma queda guardada en el celular y sube al reconectar.

> [CAPTURA: Sección «Agregar firma» con los dos paneles «Firma del técnico» (con «Usar mi firma guardada») y «Firma de quien recibe en el hospital» con la línea de autorización — Técnico, App Android]

### 4.7 Reportar un hallazgo

Si encuentra algo en un equipo:

1. Abra la pestaña «Hallazgos» de la orden.
2. Pulse «Reportar hallazgo».
3. Si la orden tiene varios equipos, elija el «Equipo».
4. Escriba «Qué encontraste» (por ejemplo, «fuga en la válvula de oxígeno del cubículo 4»).
5. Elija la «Severidad»: «Baja», «Media», «Alta» o «Crítica».
6. Si el equipo no puede seguir funcionando, marque «El equipo queda fuera de servicio».
7. Si lo arregló ahí mismo, marque «Lo resolví aquí mismo» y escriba «Qué hiciste».
8. Pulse «Reportar».

Un hallazgo sin resolver llega al planificador, que lo convierte en una tarea correctiva o lo descarta. Los hallazgos salen en el acta. Mientras la orden esté en curso puede tocar «Editar» para corregir un hallazgo. Funciona también sin señal.

> [CAPTURA: Ventana «Reportar hallazgo» con la descripción escrita, severidad «Crítica» y «El equipo queda fuera de servicio» marcada — Técnico, App Android]

### 4.8 Registrar repuestos usados

Si usó materiales del inventario:

1. Abra la pestaña «Repuestos».
2. Pulse «Agregar repuesto».
3. En «Registrar repuesto usado», busque el artículo en «Buscar item» (por nombre o código), escriba la «Cantidad» y, si quiere, «Notas».
4. Pulse «Registrar». Se descuenta del inventario.

Esto necesita **señal**. Hágalo cuando tenga conexión, mientras la orden esté «En proceso».

### 4.9 Enviar a revisión

1. Revise que no falte nada. Si falta algo, bajo los botones de la orden aparece «Para enviar a revisión falta: …» con la lista, y el botón «Enviar a revision» está desactivado. Lo que se exige:
   - Los checklists completos (sin puntos pendientes).
   - Al menos una foto que no esté oculta.
   - Al menos una firma.
2. Pulse «Enviar a revision» (arriba, en el detalle de la orden, o en la tarjeta de «Mis ordenes»).
3. La orden pasa a «En revisión». Ya no puede cambiar nada. Si el revisor la rechaza, vuelve a «En proceso» y usted la corrige.

Sin señal, el botón funciona igual: la app guarda el cambio («Estado guardado. Se sincronizara al reconectar.») y lo envía al volver la señal, después de enviar las respuestas, fotos y firmas.

> [CAPTURA: Detalle de una orden «En proceso» con el mensaje «Para enviar a revisión falta: …» y el botón «Enviar a revision» desactivado — Técnico, App Android]

> [CAPTURA: Detalle de la orden con todos los requisitos cumplidos, el botón «Enviar a revision» activo y el diálogo «Todos los checklists están completos» — Técnico, App Android]

### 4.10 Si le dieron permisos adicionales

Si el Administrador le sumó permisos (por ejemplo, revisar o asignar órdenes), en el menú aparece «Gestión». Ve las órdenes de su alcance y no solo las suyas, y tiene los botones que correspondan a sus permisos. Todo se usa como se explica en la sección 3.

---

## 5. Cuenta de hospital

La cuenta de hospital es **solo de consulta**. Ve únicamente lo de su hospital (o de su parte del hospital, si el Administrador la limitó). Nunca ve órdenes en curso: solo las **finalizadas**. Tampoco ve fotos ocultas ni tareas canceladas.

Entre por la web con su correo y contraseña (sección 1.3). Su menú superior tiene «Dashboard», «Mis activos», «Mis reportes» y «Mi perfil».

### 5.1 Dashboard del hospital

Es su pantalla de inicio. Muestra el nombre y la dirección del hospital y:

- **Tarjetas** con el total de activos y cuántos hay en cada estado («Activo», «Fuera de servicio», «Dado de baja»).
- **Cumplimiento** de los últimos 12 meses: cuántos mantenimientos se realizaron, cuántos a tiempo y cuántos están vencidos.
- **Próximos mantenimientos:** los más cercanos, con «Vencido» si ya pasó la fecha.
- **Hallazgos:** los más recientes con su estado: «Resuelto», «Corrección programada» (con fecha), «Pendiente de corrección» o «Descartado».
- **Contratos y garantías:** vigencia, qué cubren y el documento.
- **Ultimas ordenes de trabajo** (con «Ver mis activos») y **Reportes recientes** (con «Descargar»).

Para ir a un detalle, pulse el equipo, la orden o el reporte.

> [CAPTURA: «Dashboard» del hospital «Clínica Demo Norte» con las tarjetas de activos, «Cumplimiento» y «Próximos mantenimientos» — Cuenta de hospital, Web]

> [CAPTURA: Parte baja del «Dashboard» del hospital con «Hallazgos», «Contratos y garantías», «Ultimas ordenes de trabajo» y «Reportes recientes» — Cuenta de hospital, Web]

### 5.2 Mis activos y la ficha de cada equipo

1. Entre a «Mis activos». Verá los equipos de su hospital.
2. Busque por nombre, código, marca o modelo («Buscar por nombre, codigo, marca o modelo...»).
3. Pulse «Ver historial» en un equipo.

La ficha del equipo muestra:

- Los datos del equipo: ubicación, tipo, marca, modelo y serie.
- **Cobertura:** garantía y contrato vigentes.
- **Próximos mantenimientos.**
- **Hallazgos** del equipo.
- **Historial:** qué se hizo, cuándo se programó y cuándo se realizó, con el **tipo** (preventivo, correctivo u otro) y el botón del acta. Los botones «Todos», «Preventivo», «Correctivo» y «Otro» filtran el historial.

Pulse la orden de una fila para abrirla, o el botón del acta para descargarla.

> [CAPTURA: Ficha de un equipo del hospital con «Próximos mantenimientos» e «Historial» con los filtros por tipo y el botón del acta — Cuenta de hospital, Web]

### 5.3 Una visita ya cerrada

Al abrir una orden finalizada ve:

- El número, el tipo, la fecha de cierre, el título y el botón del acta.
- «Equipos intervenidos (N)», cada uno con «Ver checklist» u «Ocultar checklist» (las respuestas, solo lectura).
- Los hallazgos, con su estado.
- Las fotos (sin las ocultas) y las firmas.

No ve el historial de estados, los repuestos ni los costos.

> [CAPTURA: Orden finalizada vista desde el hospital con «Equipos intervenidos» y un checklist desplegado con «Ver checklist» — Cuenta de hospital, Web]

### 5.4 Actas

1. Entre a «Mis reportes». Verá una lista con el título, el número de la orden, la fecha y el código de verificación abreviado.
2. Pulse «Descargar PDF».

Si no hay ninguna, dice «Aun no hay reportes disponibles». Además de verlas aquí, recibe cada acta por correo, en el contacto del hospital, cuando se aprueba la orden. También puede descargar un acta desde «Reportes recientes» del «Dashboard» o desde el historial de un equipo.

> [CAPTURA: Pantalla «Mis reportes» con las actas de «Clínica Demo Norte» y el botón «Descargar PDF» — Cuenta de hospital, Web]

### 5.5 Hallazgos y contratos

- **Hallazgos:** aparecen en el «Dashboard» y en la ficha de cada equipo. Si un hallazgo es grave (crítico o con equipo fuera de servicio), el contacto del hospital recibe además un correo cuando se aprueba la orden.
- **Contratos y garantías:** aparecen en el «Dashboard», con su vigencia, qué cubren y el documento adjunto. En la ficha de cada equipo se ve su cobertura.

### 5.6 Mi perfil

Igual que los demás perfiles (sección 1.6), menos la firma guardada: quien recibe en el hospital firma a mano en cada visita. Allí puede cambiar su contraseña y descargar «Mis datos personales».

---

## 6. Trabajar sin conexión

La app Android del técnico sigue funcionando cuando se pierde la señal. Lo que usted hace queda **guardado en el celular** y se envía solo cuando vuelve la señal. Nada se pierde.

### 6.1 Cómo saber si hay conexión

Arriba de la pantalla aparece una franja:

- **Amarilla, «Sin conexion — Modo offline activo»:** no hay señal. Dice «Los cambios se sincronizaran al recuperar la conexion» y cuántos elementos esperan («N elementos en cola»).
- **Azul, «Sincronizando…»:** volvió la señal y la app está enviando lo guardado. Muestra cuántos elementos faltan.
- **Sin franja:** hay conexión y no hay nada por enviar.

Cuando guarda algo sin señal, aparece una confirmación verde: «Foto guardada. Se sincronizara al reconectar.», «Firma guardada. Se sincronizara al reconectar.» o «Estado guardado. Se sincronizara al reconectar.»

> [CAPTURA: App en modo avión con la franja «Sin conexion — Modo offline activo» y la confirmación «Foto guardada. Se sincronizara al reconectar.» — Técnico, App Android]

### 6.2 Qué se puede hacer sin señal

| Sí se puede | No se puede |
|---|---|
| Ver las órdenes y los checklists que ya descargó | Abrir una orden que nunca descargó con señal |
| Iniciar la orden («Iniciar OT») | Cancelar una orden |
| Responder los campos y finalizar el checklist | Corregir respuestas de otra persona en revisión |
| Cambiar la cantidad de tomas y dejar puntos pendientes | Registrar repuestos usados |
| Tomar fotos («Guardar foto») | Registrar, reemplazar o borrar su firma guardada |
| Firmar (usar su firma guardada o dibujar) | Descargar actas |
| Reportar y editar hallazgos | Usar las pantallas de administración |
| Enviar la orden a revisión («Enviar a revision») | |
| Aprobar una orden en revisión (quien revisa, si tiene firma guardada y ya abrió la OT con señal) | |

### 6.3 Qué debe hacer antes de salir

1. Abra la app con señal y entre a «Mis ordenes».
2. Espere unos segundos a que se descarguen las órdenes abiertas.
3. Compruebe que su firma esté guardada («Mi perfil»).
4. Abra la orden del día para confirmar que quedó en el celular.

La app descarga las órdenes que están «Pendientes» o «En proceso». Para una orden «En revisión» que quiera aprobar sin señal, ábrala antes con señal.

### 6.4 Cuando vuelve la señal

La app envía lo guardado **en orden**: primero las respuestas del checklist, las fotos, las firmas y los hallazgos, y al final el cambio de estado de la orden (por ejemplo, «Enviar a revision»). Así el sistema nunca recibe una orden «completa» sin su evidencia.

Si el envío falla por la señal o por un problema temporal, la app **reintenta sola**, esperando cada vez más (hasta 30 minutos). Solo hay que mantener la app instalada y abrirla de vez en cuando con señal.

### 6.5 Aviso «Hay N elementos que no se pudieron enviar»

Si el sistema **rechaza** algo (por ejemplo, un valor que no es válido), la app no lo reintenta sola. Aparece un aviso que no se puede cerrar: «Hay 1 elemento que no se pudo enviar» (o «Hay N elementos que no se pudieron enviar»), con el texto «Siguen guardados en este teléfono; no se pierde nada.»

1. Lea cada elemento: dice qué es (una respuesta, una foto, una firma, un hallazgo…), de qué orden y el motivo («El servidor dice: …»).
2. Corrija lo que haga falta en la orden (por ejemplo, un valor fuera de rango).
3. Pulse «Reintentar» en ese elemento, o «Reintentar todo» si son varios.
4. Si sale «Listo, se envió.», quedó resuelto. Si sigue sin enviarse, la pantalla lo dice («Sigue sin enviarse: 1. Revisa el mensaje del servidor.»).
5. Si es el cambio de estado de la orden que el servidor rechazó, la orden vuelve a su estado anterior y el aviso tiene el botón «Entendido».

Si pulsa «Reintentar» sin señal, dice «Sin conexión. Se enviará cuando vuelva la señal.»

> [CAPTURA: Aviso «Hay 1 elemento que no se pudo enviar» con el motivo «El servidor dice: …» y los botones «Reintentar» y «Reintentar todo» — Técnico, App Android]

---

## 7. Problemas frecuentes

| Problema | Causa probable | Qué hacer |
|---|---|---|
| «Cuenta bloqueada temporalmente. Intenta de nuevo en 30 minutos.» | Cinco intentos fallidos con el mismo correo. | Espere 30 minutos y entre con la contraseña correcta. Si no la recuerda, pida al Administrador que la restablezca. |
| No recuerdo mi contraseña | No hay recuperación automática. | Pídale al Administrador que la restablezca; llegará una temporal al correo. |
| No me llegó el correo con la contraseña temporal | El correo falló o está en spam. | Revise la carpeta de spam. Pida al Administrador que restablezca la contraseña de nuevo y confirme que su correo esté bien escrito. |
| «Tu cuenta está desactivada» | El Administrador la desactivó. | Pídale que la active. |
| No veo el menú o la pantalla que necesito | Su perfil no tiene ese permiso o su alcance no incluye ese hospital. | Pídale al Administrador que revise su rol, su alcance y sus permisos adicionales. |
| Mi hospital no ve nada | La cuenta no tiene hospital asignado, o aún no hay órdenes finalizadas. | Pida al Administrador que revise el hospital de la cuenta. Recuerde que solo se ven órdenes finalizadas. |
| Al aprobar dice «Para aprobar necesitas registrar tu firma» o «Registra tu firma en Mi perfil para aprobar esta orden» | Quien aprueba no tiene firma guardada. | Pulse «Ir a Mi perfil», dibuje su firma en «Mi firma» y vuelva a aprobar. Para registrarla necesita conexión. |
| «Enviar a revision» está desactivado | Falta un checklist, una foto o una firma, o hay puntos pendientes. | Lea «Para enviar a revisión falta: …» y complete lo que diga. |
| No puedo editar el checklist ni subir fotos | La orden no está «En proceso», o no es suya. | Pulse «Iniciar OT». Solo quien tiene asignada la orden la ejecuta. Un Administrador o Supervisor debe pulsar antes «Asignármela». |
| Una foto no se sube | Foto muy pesada, sin señal o la sesión caducó. | Con señal, espere: la app la envía sola. Si aparece el aviso «Hay N elementos que no se pudieron enviar», pulse «Reintentar». La foto sin GPS sube igual. |
| La foto salió mala | — | Tome otra. Quien revisa puede ocultar la mala; las fotos no se borran. |
| «Hay N elementos que no se pudieron enviar» | El sistema rechazó algo guardado en el celular. | Siga el apartado 6.5. Nada se pierde. |
| «Esta OT no está descargada en el teléfono» | Abrió una orden sin señal que nunca descargó. | Abra «Mis ordenes» con señal, espere la descarga y abra la orden. |
| No puedo cancelar una orden sin señal | Cancelar necesita conexión. | Hágalo cuando tenga señal. |
| Cancelé una OT por error | La cancelación no se deshace. | Las tareas volvieron a pendientes con su misma fecha: cree una OT nueva desde «Tareas pendientes». |
| El acta no aparece o dice «El reporte no se pudo generar» | Falló la generación del PDF. | El Administrador pulsa «Generar reporte de nuevo» en la pestaña «Reportes» de la OT. |
| El hospital dice que no recibió el acta | El hospital no tiene correo de contacto, o el correo es incorrecto. | Revise el correo en «Hospitales» → «Editar». Luego reenvíe el acta (ver 3.13). |
| No puedo crear una OT con varias tareas | Hay tareas de más de un hospital. | Una OT es de un solo hospital. Marque solo las de uno. |
| No puedo reprogramar ni anular una tarea | La tarea ya está dentro de una OT. | Saque la tarea de la OT primero (en la OT pendiente, pulse la «x» de su fila). |
| La importación de Fracttal no deja importar | El archivo tiene errores. | Use el filtro «Con errores», corrija en Fracttal o en el archivo y vuelva a subirlo. |
| Un protocolo no genera tareas | No tiene tareas, o está pausado. | Agréguele tareas con «Agregar tarea», o pulse «Reanudar». |
| El «Dashboard» no refleja un cambio reciente | Las cifras se guardan unos 5 minutos. | Espere un momento y pulse «Actualizar». |
| No puedo anonimizar un usuario | La cuenta debe estar desactivada y con más de 2 años sin actividad. | Desactívela y espere a que se cumpla el plazo. |
| «Esta acción no se puede deshacer» al cancelar | Es el aviso normal de la cancelación. | Confirme solo si está seguro. |

**Si nada de esto resuelve el problema**, anote el mensaje exacto que aparece en pantalla, la orden o el equipo, y repórtelo a TodoGas.

---

## 8. Anexo: qué puede hacer cada persona

«Sí» significa que el perfil lo puede hacer con los permisos normales de su rol. Un Administrador puede darle más permisos a un Supervisor o a un Técnico.

| Acción | Admin | Super. | Téc. | Hosp. |
|---|---|---|---|---|
| Ver «Dashboard» de administración | Sí | Sí | No | No |
| Ver «Dashboard» y activos de su hospital | — | — | — | Sí |
| Crear y editar hospitales | Sí | No | No | No |
| Armar ubicaciones | Sí | Sí | No | No |
| Crear, editar y dar de baja activos | Sí | Sí | No | No |
| Importar desde Fracttal | Sí | No | No | No |
| Crear y editar contratos y garantías | Sí | No | No | No |
| Crear, editar y asignar protocolos | Sí | No | No | No |
| Crear y publicar checklists | Sí | Sí | No | No |
| Crear OT desde tareas pendientes | Sí | Sí | No | No |
| Reprogramar y anular tareas | Sí | Sí | No | No |
| Crear OT manual | Sí | No | No | No |
| Asignar y reasignar | Sí | Sí | No | No |
| Ejecutar una OT (si está asignada) | Sí | Sí | Sí | No |
| Revisar, corregir y aprobar | Sí | Sí | No | No |
| Cancelar una OT | Sí | No | No | No |
| Reportar hallazgos | Sí | Sí | Sí | No |
| Decidir hallazgos | Sí | Sí | No | No |
| Ver y descargar actas | Sí | Sí | No | Sí |
| Reenviar actas y reporte consolidado | Sí | No | No | No |
| Formato del acta, tipos de tarea, usuarios, auditoría | Sí | No | No | No |
| Inventario: crear artículos | Sí | No | No | No |
| Inventario: registrar movimientos | Sí | Sí | Solo salidas, en su OT | No |
| Firma guardada | Sí | Sí | Sí | No |

