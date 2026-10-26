# Guía de secciones de TodoGas CMMS

Definición pantalla por pantalla de lo que el sistema hace **hoy**. Está escrita leyendo el código (router, layouts, páginas, permisos y vistas del backend), no los requisitos. Lo que no pude confirmar con el código va marcado **(sin confirmar)**.

Cómo se usa: lee primero el mapa, el glosario y las reglas transversales (secciones 1 a 3). Después, ve a la pantalla que vas a mostrar. Cada pantalla tiene el mismo formato: *Para qué sirve, Quién la ve, Qué se ve, Qué se puede hacer, Reglas importantes, Se conecta con, Para la demo*.

Roles: **ADMIN** (Administrador), **SUP** (Supervisor), **TEC** (Técnico), **CLI** (Cliente: la biomédica o cuenta de un hospital).

Documentos hermanos: `docs/DEMO.md` (cuentas y datos de demo), `docs/PRUEBAS-DEMO.md` (lista de pruebas) y `docs/GUIA-PRESENTADOR.md`.

---

## 1. Mapa del sistema

### 1.1 Qué rol usa qué

| Rol | Entra a | Pantallas que ve |
|---|---|---|
| **ADMIN** | Web, `/dashboard` | Todo el menú de administración. Es el único que ve Usuarios, Formato del acta, Tipos de tarea y Auditoría. Nunca queda limitado por alcance. |
| **SUP** | Web, `/dashboard` | El menú de administración **menos** Usuarios, Formato del acta, Tipos de tarea y Auditoría. Puede quedar limitado a un hospital o a una parte de su árbol de ubicaciones. |
| **TEC** | App Android (o web), `/mis-ordenes` | Solo dos entradas de menú: **Mis ordenes** y **Mi perfil**. Ve únicamente las OT que tiene asignadas. |
| **CLI** | Portal del hospital, `/mis-dashboard` | **Dashboard, Mis activos, Mis reportes, Mi perfil**. Solo lectura, y solo lo finalizado de su hospital (o de su parte del hospital). |

La app Android es el mismo frontend React empaquetado con Capacitor: la cámara y el GPS usan las funciones nativas del teléfono, y el resto es idéntico a la web.

### 1.2 El ciclo completo

```
Protocolo ──(se asigna a activos)──▶ Tarea pendiente por activo ──(el planificador las agrupa)──▶ OT (una visita a un hospital)
   │                                         │ reprogramar (con causa) / anular (con motivo)              │
   │                                         ▼                                                            ▼
   │                               Calendario y Dashboard                    Técnico: Iniciar OT ▶ checklist por activo + fotos + firma
   │                                                                                                      │ Enviar a revisión
   │                                                                                                      ▼
   │                                                        ADMIN/SUP en "En revisión": corregir respuestas, ocultar fotos,
   │                                                        corregir fecha de intervención ▶ Completar  (o Rechazar ▶ vuelve a "En proceso")
   │                                                                                                      │ Completar
   │                                                                                                      ▼
   │         Las tareas pasan a "Finalizada" y cada una crea la siguiente pendiente ◀── se genera el acta PDF con hash SHA-256 y sale por correo al hospital
   │                                                                                                      │
   └───────────────────────────────────────────────────────────────────────────────────────────────────▶ Portal del hospital: OT finalizada, checklist, fotos, firmas, acta
```

Dos cosas que conviene tener claras al explicarlo:

- **Las OT no se crean solas.** La opción de generar OT automáticamente por fecha está apagada (`MAINTENANCE_AUTO_CREATE_WORK_ORDERS = False`). El proceso diario (6:00 a. m. hora Colombia) solo repone las tareas pendientes que falten. El planificador (ADMIN o SUP) arma las OT desde **Tareas pendientes**.
- **Los hallazgos son un ciclo paralelo.** El técnico los reporta en la OT. El planificador los convierte en una tarea correctiva pendiente (que entra de nuevo al ciclo) o los descarta con motivo. El hospital los ve en su portal.

---

## 2. Glosario

- **Protocolo** (en el código y en las URL: *plan*, `/planes-pm`). Define qué tareas se le hacen a un activo y cada cuánto. Tiene tareas (cada una con su tipo, checklist, frecuencia y disparador). Un activo tiene **un solo** protocolo. Un protocolo puede ser exclusivo de un hospital.
- **Tarea pendiente.** Ocurrencia de una tarea de un protocolo sobre **un activo**, con su fecha. Hay dos fechas: la **calculada** (la que sale de la frecuencia) y la **programada** (la que quedó después de reprogramar). Estados: Pendiente, Programada (ya está dentro de una OT), Finalizada y Cancelada.
- **OT (orden de trabajo).** Una **visita a un hospital** que puede cubrir varios activos del mismo hospital. Tiene número legible tipo `OT-2026-00009`. Cada activo de la OT es una tarea con su propio checklist. Estados: Pendiente, En proceso, En revisión, Finalizada, Cancelada.
- **Hallazgo.** Lo que el técnico encuentra en un equipo durante la OT. Tiene severidad (Baja, Media, Alta, Crítica), puede marcar "El equipo queda fuera de servicio" y puede quedar **resuelto en sitio** (con lo que se hizo). Los que no se resuelven en sitio quedan **Pendientes** para el planificador. Un hallazgo es *grave* si es Crítico o deja un equipo fuera de servicio.
- **Acta.** El PDF del servicio, que se genera al completar la OT. Lleva el hash SHA-256 en el pie para verificar que no se alteró. Qué imprime lo define **Formato del acta**.
- **Toma o bloque repetible.** Un grupo de campos del checklist (por ejemplo «Toma») que se responde una vez por cada toma, gas o salida. El checklist define el grupo una sola vez. La tarea del protocolo dice cuántas veces va («Toma × 20»). El técnico puede ajustar la cantidad en campo con **Agregar toma** o **Quitar toma (vacía)**.
- **Medidor y activador.** Un **medidor** es una lectura de un equipo con una unidad (horas, amperios, voltaje, temperatura, presión). Se crea con la primera lectura o a mano. Un **activador** es la regla de una tarea del protocolo que usa un medidor:
  - **Cada**: «cada N horas de uso» (solo con unidades que acumulan, como horas).
  - **Cuando**: «cuando la lectura sea mayor que X» (umbral). Abre la tarea y manda correo a los administradores.
- **Alcance.** A qué se limita un usuario: un hospital y, dentro de él, una parte del árbol (piso, servicio). Aplica a SUP, TEC y CLI. Al ADMIN nunca. Un CLI sin hospital no ve nada.
- **Tipo de tarea.** Catálogo editable (Preventivo, Correctivo y los del cliente en Fracttal). Cada tipo **cuenta como** Preventivo, Correctivo o Ninguno. Eso decide en qué indicador del Dashboard entra.

---

## 3. Reglas transversales

**Alcance por hospital y por árbol** (`apps/users/scope.py`). Todas las vistas filtran por él: hospitales, ubicaciones, activos, tareas, OT, contratos, protocolos, hallazgos, reportes, medidores y movimientos de inventario ligados a una OT. Una OT se ve si es del hospital y, con un nodo, si alguna de sus tareas es de un activo de esa parte. Una OT **asignada** a un SUP o TEC se ve aunque quede fuera de su alcance. Los Protocolos son un catálogo compartido: se ve todo salvo lo restringido a otro hospital.

**Nada importante se borra.** Los hospitales y los activos no tienen borrado (el servidor responde 405). Las OT tampoco. Las fotos se **ocultan**, no se borran. Las tareas se **anulan** con nota. Lo que se borra de verdad: ubicaciones vacías, tareas de protocolo sin historial, tipos de tarea sin uso, contratos y lecturas manuales de medidor. Todas las claves foráneas son `PROTECT`.

**OT cerrada = registro inmutable.** Una OT Finalizada o Cancelada no admite modificaciones (el servidor responde 403 con ese mensaje). Esto cubre la edición y la reasignación.

**Estados de la OT y quién los mueve.**

| Cambio | Quién | Condición |
|---|---|---|
| Pendiente → En proceso (**Iniciar OT**) | La **persona asignada** (TEC, o ADMIN/SUP si se la asignó) | Ninguna |
| En proceso → En revisión (**Enviar a revision**) | La persona asignada | Checklists completos, al menos 1 foto no oculta y la firma |
| En revisión → Finalizada (**Completar**) | ADMIN o SUP | Ninguna |
| En revisión → En proceso (**Rechazar**) | ADMIN o SUP | Motivo obligatorio |
| Pendiente / En proceso / En revisión → Cancelada (**Cancelar OT**) | **Solo ADMIN** | Motivo obligatorio. Necesita red. |

**Qué pasa con las tareas.**
- *Completar*: las tareas pasan a Finalizada y cada una genera la siguiente pendiente (si el protocolo lo permite y el equipo sigue Activo).
- *Cancelar*: las tareas quedan como canceladas y **se reemiten como pendientes con la misma fecha**, listas para agruparse en otra OT. No se pierde el preventivo.

**Auditoría.** Casi todo cambio por API queda en el log (usuario, acción, entidad, IP, y el valor anterior en las correcciones). Solo el ADMIN lo ve.

**Sin red.** Solo el técnico trabaja sin red de forma completa. Ver la sección 7.

**Notificaciones.** El servicio de push es un **placeholder**: escribe un registro y una línea en la consola, no manda nada al teléfono. La campana de la barra superior de administración llama a `/api/notifications/`, que **no existe**, así que la campana no aparece. Lo que sí sale son los **correos**: acta al hospital, hallazgo grave, vencimiento de contratos y umbral de medidor.

---

## 4. Pantallas de acceso

### 4.1 Inicio de sesión (`/login`)

- **Para qué sirve:** entrar al sistema. Cada rol aterriza en su pantalla de inicio.
- **Quién la ve:** todos, sin sesión.
- **Qué se ve:** «Entrar al sistema», campos *Correo electrónico* y *Contraseña* (con botón para mostrarla) y el botón **Iniciar sesión**. Debajo, la nota «¿No puedes entrar? El administrador de tu organización puede restablecer tu contraseña desde el módulo de usuarios».
- **Qué se puede hacer:** entrar. ADMIN y SUP van a `/dashboard`, TEC a `/mis-ordenes` y CLI a `/mis-dashboard`. Si la cuenta tiene la contraseña temporal, pasa primero a *Cambia tu contraseña*.
- **Reglas importantes:**
  - Tras **5 intentos fallidos** de un correo, la cuenta se bloquea **30 minutos**: «Cuenta bloqueada temporalmente».
  - Una cuenta desactivada muestra «Tu cuenta está desactivada. Contacta al administrador».
  - Todo intento (exitoso o no) queda en la auditoría.
- **Se conecta con:** Usuarios (donde el ADMIN crea la cuenta y restablece la contraseña).
- **Para la demo:** nada que mostrar aquí más allá de entrar con cada rol.
  - *Pregunta probable: «¿Se bloquea si se equivocan?»* Sí, a los 5 intentos, 30 minutos.

### 4.2 Cambia tu contraseña (`/cambiar-contrasena`)

- **Para qué sirve:** forzar la contraseña propia cuando se entra con una temporal (cuenta nueva o restablecida).
- **Quién la ve:** cualquier usuario con `must_change_password`.
- **Qué se ve:** *Contraseña actual*, *Nueva contraseña* (con medidor de fortaleza), *Confirmar nueva contraseña* y **Guardar nueva contraseña**.
- **Qué se puede hacer:** cambiarla. Luego va a la pantalla de inicio de su rol.
- **Reglas importantes:** mínimo 8 caracteres, una mayúscula, un número y un carácter especial (lo valida el servidor; en esta pantalla el cliente solo exige 8 y que coincidan).
- **Se conecta con:** Inicio de sesión y Usuarios.
- **Para la demo:** no se muestra. *Pregunta probable: «¿El admin sabe la contraseña de los demás?»* No. La temporal se genera y viaja solo por correo.

### 4.3 Página no encontrada

Sin sesión, una ruta desconocida lleva al login. Con sesión, muestra el 404 con un enlace de vuelta al inicio del rol.

---

## 5. Menú de administración (ADMIN y SUP)

La barra superior lleva el botón de menú (se pliega y recuerda su estado en escritorio), el logo, el nombre y rol del usuario y **Cerrar sesion**. Debajo, un aviso permanente de conexión (`OfflineBanner`). El menú lateral tiene los grupos *(Dashboard)*, **Activos**, **Mantenimiento**, **Checklists**, **Administracion** y **Cuenta**.

Tres entradas llevan **globo con número**:
- *Contratos y garantías*: los que vencen en 60 días.
- *Hallazgos*: los pendientes de decisión.
- *Inventario*: los items con stock bajo.

### 5.1 Dashboard (`/dashboard`)

- **Para qué sirve:** ver de un vistazo cómo va el mantenimiento y qué requiere acción hoy.
- **Quién la ve:** ADMIN y SUP. Un SUP limitado a un hospital ve los indicadores de **ese hospital** (los indicadores van por hospital, no por piso).
- **Qué se ve:**
  - **Filtros:** *Hospital* (Todos los hospitales), *Periodo* (7 dias, 30 dias, 90 dias) y **Actualizar**.
  - **Requiere atención** (4 tarjetas que enlazan a su lista):
    - *Activos con mantenimiento vencido*, que lleva a Activos filtrado.
    - *Hallazgos críticos abiertos*, que lleva a Hallazgos con `status=PENDING&severity=CRITICAL`.
    - *OTs vencidas*, que lleva a `/ordenes` **sin** filtro de vencidas.
    - *Contratos por atender*: por vencer más hospitales sin contrato.
  - **Estado de activos:** Vencido, Por vencer (30 días), Al día, Sin protocolo. Cada porción enlaza a Activos filtrado por ese estado.
  - **Planificación de tareas:** tareas abiertas de los próximos 6 meses más las vencidas aparte. Cada barra enlaza a Tareas pendientes.
  - **Hallazgos abiertos:** por severidad, y **Ver bandeja**.
  - **OTs por tipo:** Preventivo, Correctivo y Otros, del periodo.
  - **Cuatro indicadores:**
    - *Cumplimiento de protocolos*
    - *MTTR (tiempo medio de reparacion)*
    - *OTs vencidas*
    - *OTs completadas este periodo*
  - **Gráficas:** *OTs por estado* (dona con leyenda) y *Cumplimiento — ultimos 12 meses* (barras).
  - **Tablas:** *OTs por tecnico* (Tecnico, Asignadas, Completadas, Vencidas) y *Activos sin mantenimiento reciente* (los 10 con más días; «Nunca» si no tienen ninguna).
  - **Contratos y garantías**, solo si hay algo por atender.
- **Qué se puede hacer:** filtrar, actualizar y navegar a las listas con un clic.
- **Reglas importantes (cómo se calcula cada cifra):**
  - **Cumplimiento de protocolos:** de las OT con tipo que cuenta como *Preventivo* y fecha programada en el **mes en curso**, cuántas se completaron a más tardar **un día después** de su fecha programada. El filtro de periodo **no** lo afecta.
  - **MTTR:** promedio de `completada − iniciada` de las OT con tipo *Correctivo* completadas en el periodo. Como `completada` es el momento en que el supervisor aprueba, **incluye el tiempo que la OT estuvo en revisión**.
  - **OTs vencidas:** programadas antes de hoy y no finalizadas ni canceladas; «críticas» son las de prioridad Alta.
  - **OTs por estado:** cuenta por fecha de **creación** de la OT, dentro del periodo.
  - **OTs por técnico:** lista a **todos** los técnicos activos, también para un SUP limitado a un hospital.
  - **Activos sin mantenimiento reciente:** activos en servicio con protocolo activo y sin tarea hecha en los últimos 90 días.
  - El servidor **guarda en caché 5 minutos** los indicadores. **Actualizar** vuelve a pedir los datos, pero no salta esa caché.
- **Se conecta con:** todo se alimenta de Tareas pendientes, OT, Hallazgos, Activos y Contratos. Lleva a esas mismas pantallas.
- **Para la demo (20–30 s):** abre con *Requiere atención*, haz clic en *Hallazgos críticos abiertos* y llegas a la bandeja ya filtrada. Después muestra *Estado de activos*.
  - *Pregunta probable: «¿Cómo se calcula el cumplimiento?»* Por mes: OT preventivas del mes terminadas en su fecha o un día después, sobre las que tocaban ese mes.
  - Si el mes no tiene OT preventivas, la tarjeta dice **0%** en rojo (no «sin datos»). Ten a mano la explicación.

### 5.2 Hospitales (`/hospitales`)

- **Para qué sirve:** administrar los clientes y sus sedes, y entrar a sus ubicaciones, activos y contratos.
- **Quién la ve:** ADMIN y SUP. El SUP solo ve su hospital (por alcance). **Solo el ADMIN** crea, edita y activa o desactiva.
- **Qué se ve:**
  - Título «Hospitales — Gestión de clientes y sedes».
  - Botón **+ Nuevo hospital** (ADMIN).
  - Filtros *Todos / Activos / Inactivos* y búsqueda «Buscar por nombre o código...».
  - Tabla: *Nombre, Código, Ciudad, Activos* (cantidad), *Contrato*, *Estado* y *Acciones*.
  - La columna *Contrato* muestra «Hasta {fecha}» (con «vence en N días» si está por vencer) o «Sin contrato vigente». Es un botón que lleva a Contratos de ese hospital.
- **Qué se puede hacer:**
  - **Ubicaciones:** abre el árbol del hospital.
  - **Ver activos:** abre Activos filtrado por el hospital.
  - **Editar** (ADMIN): modal *Nuevo hospital / Editar hospital*. Campos: Nombre\*, Código\*, NIT, Ciudad, Departamento, Dirección, *Ubicación en el mapa* (con buscador) y Contacto (Nombre, Teléfono, Email). Botones *Crear hospital* o *Guardar cambios*.
  - **Desactivar / Activar** (ADMIN): cambia el estado. No pide confirmación.
- **Reglas importantes:**
  - **El hospital no se borra** (405).
  - El **email de contacto** es el destinatario del acta y del aviso de hallazgo grave. Sin email, el acta se genera pero el correo se omite.
  - El mapa solo aparece si está configurada la clave de Google Maps; si no, la pantalla lo avisa.
  - Un hospital inactivo deja de salir en los selectores. El efecto sobre sus usuarios y OT ya existentes **(sin confirmar)**.
- **Se conecta con:** Ubicaciones, Activos, Contratos y Usuarios (la cuenta CLI se liga a un hospital). El contacto alimenta el envío del acta.
- **Para la demo:** muestra la tabla con la columna *Contrato* (el hospital con contrato por vencer salta a la vista).
  - *Pregunta probable: «¿Podemos eliminar un hospital?»* No. Se desactiva y su historial queda.

### 5.3 Ubicaciones del hospital (`/hospitales/:id/ubicaciones`)

- **Para qué sirve:** armar el árbol del hospital (torre → piso → servicio → sala) tal como lo recorre el técnico. Sobre ese árbol se asignan activos, se filtran listas y se limita el acceso de usuarios.
- **Quién la ve:** ADMIN y SUP, **ambos pueden crear, editar y borrar** ubicaciones (el servidor lo permite a los dos). El SUP limitado solo ve su rama.
- **Qué se ve:**
  - «Ubicaciones», el nombre y el código del hospital (con «Hospital inactivo» si aplica).
  - Botón **Nueva ubicación**.
  - Buscador «Buscar por nombre o código...».
  - **Expandir todo / Contraer todo**.
  - Contador «N ubicaciones · M inactivas · K activos asignados».
  - Árbol: en cada fila van el tipo (Edificio / Torre, Piso, Área / Servicio, Habitación / Sala, Otro), el nombre, el código, un pin a Google Maps si tiene coordenadas, las marcas *Inactiva* u *Oculta*, y «N activos» (enlace a Activos de esa ubicación) o «Sin activos».
- **Qué se puede hacer:**
  - Botones de icono por fila (con su texto en el tooltip):
    - *Añadir sububicación en…*
    - *Editar…*
    - *Desactivar… / Activar…*
    - Papelera (*Eliminar ubicación*)
  - Modal *Nueva ubicación / Nueva sububicación en X / Editar ubicación*. Campos: Nombre\*, Tipo, *Ubicada dentro de* (mover el nodo), Código, Orden, Dirección y mapa.
  - Botones: **Guardar y crear otra** (alta en serie), **Crear ubicación** o **Guardar cambios**.
- **Reglas importantes:**
  - **Desactivar** oculta la ubicación y sus sububicaciones de los formularios (aparecen como *Oculta*). Los activos que ya están ahí **conservan** su ubicación e historial. Se puede reactivar.
  - **Eliminar** es un borrado real y solo se permite si la ubicación **no tiene sububicaciones ni activos**. Si no, el botón queda deshabilitado con el motivo.
  - Una ubicación no puede quedar dentro de sí misma ni de sus hijas.
- **Se conecta con:** Hospitales (de donde se llega), Activos (cada activo se asigna a un nodo), Contratos (un contrato puede cubrir un nodo), Usuarios (limitar a un nodo) y las OT (la ubicación de la visita).
- **Para la demo:** abre el hospital de demo y expande «Piso 1 - Urgencias». Se ve de qué cuelgan los activos.
  - *Pregunta probable: «¿Un supervisor solo ve su piso?»* Sí, si se le asigna «Parte del hospital» al crear su usuario.

### 5.4 Activos (`/activos`)

- **Para qué sirve:** inventario de equipos por hospital y ubicación, con su semáforo de mantenimiento.
- **Quién la ve:** ADMIN y SUP (con su alcance). **+ Nuevo activo** y **Editar** son para ADMIN y SUP.
- **Qué se ve:**
  - «Activos — Equipos médicos registrados».
  - **Columna izquierda:** selector de hospital («Seleccionar hospital») y el árbol de ubicaciones con «Todos los activos».
  - **Columna derecha:**
    - Buscador «Buscar código, nombre, serial...» con botón **Buscar**.
    - Filtro «Todos los estados» (Activo, Fuera de servicio, Dado de baja).
    - Chip del filtro de mantenimiento si se llegó desde el Dashboard.
    - Tabla: *Código, Nombre* (con punto de color), *Tipo, Estado, Prioridad, Próximo PM, Acciones*.
    - Paginador de 50 en 50 con *Anterior / Siguiente*.
  - Semáforo (el punto junto al nombre):
    - verde: al día
    - amarillo: próximo en ≤30 días
    - rojo: vencido
    - gris: sin protocolo
- **Qué se puede hacer:** clic en la fila o **Ver ficha** abre la ficha. **Editar** abre el formulario. **+ Nuevo activo** / «+ Crear el primer activo».
- **Reglas importantes:**
  - La pantalla **selecciona automáticamente el primer hospital** de la lista, no «todos».
  - La búsqueda cubre nombre, código, serie, modelo, marca y nombre del hospital.
  - Los filtros viajan en la URL: *Ver activos* de Hospitales, «N activos» de Ubicaciones y las tarjetas del Dashboard llegan ya filtrados.
  - El punto de color y «Próximo PM» salen de la tarea abierta más próxima del protocolo. Un activo con protocolo **pausado** cuenta como «Sin protocolo».
- **Se conecta con:** Hospitales y Ubicaciones (de donde se llega), Ficha del activo, Protocolos (cada activo lleva uno) y Dashboard.
- **Para la demo:** filtra por «Vencido» desde el Dashboard y entra a un activo rojo.
  - *Pregunta probable: «¿Cómo cargamos 500 equipos?»* En esta pantalla no hay importación masiva: se crean de a uno. La importación de Fracttal está planeada aparte **(sin confirmar fecha)**.

### 5.5 Formulario de activo (`/activos/nuevo`, `/activos/:id/editar`)

- **Para qué sirve:** registrar o corregir un equipo en dos pasos.
- **Quién la ve:** ADMIN y SUP.
- **Qué se ve:**
  - **Paso 1 «Identificación»:**
    - Hospital\*
    - Ubicación (con enlace «Gestionar ubicaciones»)
    - Nombre del activo\*
    - Código interno\* (botón **Generar**)
    - Tipo de activo
    - Estado\* (Activo, Fuera de servicio, Dado de baja)
    - Prioridad\* (Alta, Media, Baja)
    - Protocolo («Sin protocolo» o uno, con «(pausado)» si lo está)
  - **Paso 2 «Ficha técnica»:** Fabricante, Modelo, Número de serie, Proveedor, Fecha de compra, Fecha de instalación, Garantía hasta, Horas de uso promedio/día y Notas.
  - Botones: *Cancelar, Anterior, Siguiente* y **Crear activo / Guardar cambios**.
- **Qué se puede hacer:**
  - Crear o editar.
  - Al elegir «Dado de baja» al editar, la pantalla muestra **qué va a pasar** antes de guardar (cuántas tareas se anulan).
  - Cambiar el protocolo avisa que las pendientes del anterior se anulan y las del nuevo **conservan la fecha**.
- **Reglas importantes:**
  - **Dar de baja** anula las tareas pendientes del activo con la nota «El activo se dio de baja» y no las borra. Las que ya están dentro de una OT abierta **no se tocan**: al cerrarse esa OT no se genera la siguiente.
  - **Reactivar** (volver a Activo) reabre las pendientes de su protocolo.
  - **Fuera de servicio** no toca ninguna tarea.
  - Un usuario limitado a un nodo **debe** elegir ubicación, y solo dentro de su alcance.
  - Un protocolo restringido a otro hospital no se puede asignar.
  - **Ojo, brecha de permisos:** el botón **Dar de baja** de la ficha es solo ADMIN. Pero este formulario deja a un **SUP** poner «Dado de baja» y cambiar el protocolo, porque el servidor permite editar al SUP.
- **Se conecta con:** Activos, Ficha del activo, Protocolos, Ubicaciones.
- **Para la demo:** no lo muestres entero. Enseña el selector de estado «Dado de baja» y el recuadro que anticipa el efecto.
  - *Pregunta probable: «¿Si damos de baja un equipo, se pierde su historial?»* No. Las tareas quedan como canceladas.

### 5.6 Ficha del activo (`/activos/:id`)

- **Para qué sirve:** ver todo de un equipo: estado de mantenimiento, cobertura, ficha técnica, QR, tareas, medidores y campos personalizados.
- **Quién la ve:** ADMIN y SUP. **Editar** (ADMIN/SUP, oculto si está de baja) y **Dar de baja** (**solo ADMIN**, oculto si ya está de baja).
- **Qué se ve:**
  - Encabezado con estado, «Prioridad X», nombre, código y la ruta de ubicación.
  - **Pestañas:** *Información general, Tareas, Medidores, Campos personalizados*.
  - **Información general:**
    - *Estado de mantenimiento* (Protocolo con enlace, Próximo mantenimiento, Último mantenimiento, Estado: Al día, Próximo a vencer, Vencido, Sin protocolo).
    - Cobertura: *Garantía* y *Contrato de mantenimiento* vigentes (o «Sin garantía vigente» / «Sin contrato vigente»).
    - Los datos de la ficha técnica.
    - *Código QR* con **Descargar etiqueta PNG**.
  - **Tareas:**
    - *Próximas*: Tarea, Cuándo, Fecha programada (con «Calculada» si fue reprogramada) y Estado («En OT-…», «Vencida» o «Pendiente»).
    - *Historial*: Tarea, Calculada, Programada, Realización, Estado y OT, con botón **Acta** si la OT tiene PDF.
    - Enlace **Ver todas sus OT**.
  - **Medidores:**
    - Por cada medidor: la última lectura, sus activadores («cada N … vence a los X» o «se abre cuando la lectura sea…») y los botones **Historial**, **Registrar lectura** y **+ Agregar medidor** (ADMIN/SUP).
    - Modal de lectura: Lectura, Fecha y hora, «El contador se reinició o se cambió» (solo contadores) y Nota.
  - **Campos personalizados:** los del tipo de activo, o «Este tipo de activo no tiene campos personalizados».
- **Qué se puede hacer:**
  - **Dar de baja** abre un modal que anticipa el efecto («Se anularán N tareas pendientes…») y, al confirmar, informa el resultado y las OT que siguen abiertas con tareas del equipo.
  - Descargar la etiqueta QR.
  - Registrar o borrar lecturas.
- **Reglas importantes:**
  - La etiqueta se baja con la sesión (no con un enlace público).
  - Una lectura **manual** se puede borrar solo si no abrió una tarea. Las lecturas que vienen del checklist se corrigen en la respuesta de la OT.
  - Una lectura menor a la anterior en un contador se toma como un contador que **arrancó de cero**, salvo que se marque el reinicio.
  - La lista de **unidades de medidor** (Amperios, Horas, Presión inHg, Presión PSI, Temperatura, Voltaje) la siembra una migración. **No hay pantalla** para administrarlas (solo el ADMIN por API).
  - Un medidor nace solo con la primera lectura del checklist (campo «Lectura de medidor» con unidad), o con **+ Agregar medidor**.
- **Se conecta con:** Activos, Protocolos (enlace del protocolo), OT (enlaces `En OT-…`), Contratos (cobertura) y el acta (botón **Acta**).
- **Para la demo:** abre la ficha de un equipo con historial. Muestra la pestaña *Tareas*: calculada, programada y realización.
  - *Pregunta probable: «¿Qué diferencia hay entre fecha calculada y programada?»* La calculada la pone la frecuencia. La programada es la que quedó tras reprogramar, con causa registrada.

### 5.7 Contratos y garantías (`/contratos`)

- **Para qué sirve:** llevar la vigencia de los contratos de mantenimiento con cada hospital y de las garantías de equipos. Solo **avisa**: vencer no bloquea nada.
- **Quién la ve:** ADMIN y SUP **leen**. **Solo el ADMIN** crea, edita y elimina. La cuenta CLI ve los suyos en su Dashboard.
- **Qué se ve:**
  - «Contratos y garantías».
  - Botón **+ Nuevo documento** (ADMIN).
  - Dos avisos: «N por vencer en 60 días» (clic filtra) y «N hospitales sin contrato vigente».
  - Vistas *Vigentes, Por vencer, Vencidos, Próximos, Todos*.
  - Filtro de tipo (Contrato de mantenimiento / Garantía de equipos), de hospital y búsqueda por nombre.
  - Tabla: *Documento, Cubre, Vigencia, Estado, Acciones*.
- **Qué se puede hacer:**
  - En el modal *Nuevo documento*:
    - Elegir el tipo.
    - Nombre, Descripción, Hospital.
    - *Cubre* (todo el hospital o una rama del árbol), solo para contratos.
    - *Inicio de la vigencia* y *Fin de la vigencia* (con el atajo «Un año desde el inicio»).
    - Para garantías, un selector de equipos con filtro por ubicación y código.
    - Documento adjunto (PDF, Word o imagen, hasta 20 MB).
  - En la fila: abrir el documento, **Editar** y **Eliminar**.
- **Reglas importantes:**
  - **«Por vencer» = faltan 60 días o menos.**
  - Un contrato cubre un hospital o una rama; una garantía, una lista de equipos.
  - Cada día a las 6:30 a. m. (Colombia) se manda **un solo correo agrupado** a los administradores con lo que cruzó un umbral (60 días, 30 días, vencido). Si no hay nada, no sale.
  - Al crear una OT, si el hospital no tiene contrato vigente, aparece un aviso («Puedes crear la OT igual»).
  - Eliminar no es necesario cuando solo terminó: queda como *Vencido* en el historial.
- **Se conecta con:** Hospitales (columna *Contrato*), Ficha del activo (cobertura), Dashboard (tarjeta y panel), la creación de OT (aviso) y el portal del hospital.
- **Para la demo:** abre «Por vencer» y muestra el documento adjunto.
  - *Pregunta probable: «¿Qué pasa si vence el contrato?»* El sistema avisa por pantalla y por correo, pero no impide crear OT: la decisión es del planificador.

### 5.8 Tareas pendientes (`/tareas-pendientes`)

- **Para qué sirve:** es el **centro de trabajo del planificador**. Aquí se ven las tareas que toca hacer, se agrupan las de una misma visita en una OT, o se reprograman o anulan con causa.
- **Quién la ve:** ADMIN y SUP (dentro de su alcance). Todas las acciones están disponibles para ambos.
- **Qué se ve:**
  - «Tareas pendientes — Marca las de una misma visita y crea la OT, o reprográmalas indicando la causa».
  - **Filtros:** Hospital, *Ubicación (con lo que tiene dentro)*, Protocolo, *Activo o tarea*, *Desde*, *Hasta* y *Solo vencidas*. También llegan por URL desde el Dashboard.
  - Contador «N pendientes · M vencidas».
  - Tabla: casilla, *Fecha programada* («vencida hace…», «Reprogramada · calc. …»), *Activo* (enlace a la ficha, con hospital y ubicación), *Tarea* (tipo · protocolo y, si la abrió un medidor, «Abierta por lectura: …»), *Cuándo* (frecuencia), *Duración* y un botón de **historial**.
- **Qué se puede hacer:** al marcar tareas aparece una barra con «N marcadas · duración total · hospital» y los botones:
  - **Crear OT:** modal con *Asignado a*, *Fecha de la visita*, *Prioridad*, *Ubicación de la visita* (propone la común), *Título* (propuesto), *Indicaciones para el técnico*, y el aviso de contrato si aplica. Al terminar: «OT creada», con **Seguir planificando** o **Ver la OT**.
  - **Reprogramar:** *Nueva fecha\**, *Causa\** (lista de causas) y *Nota*.
  - **Anular:** *Por qué se anula\** (obligatorio).
  - **Desmarcar.**
  - **Historial** de una tarea: fecha calculada, fecha programada y cada reprogramación (de → a, causa, nota, quién y cuándo).
- **Reglas importantes:**
  - **Reprogramar exige una causa.** Las del cliente son: 3 VISITAS, ADELANTADO, ANUAL, APLAZADO, GARANTIA, MANTENIMIENTO PUNTUAL, NO DISPONIBLE, PREVENTIVO, PRIMERA VISITA y SOLO 1 VISITA. La fecha calculada **no cambia**; queda el registro de quién, cuándo y por qué.
  - **Una OT es de un solo hospital.** Con tareas de varios hospitales marcadas, **Crear OT** se deshabilita.
  - **Anular** significa «esta ya no toca»: no se hace ni se crea la siguiente. Si es solo otro día, hay que reprogramar.
  - Solo se reprograma o anula lo **Pendiente**. Lo que ya está en una OT hay que sacarlo de la OT primero.
  - Al cambiar un filtro se **desmarca** la selección, para no meter en una OT algo escondido.
  - La *Fecha de la visita* **no** cambia la fecha programada de cada tarea: para registrar que una se hizo otro día, se reprograma antes.
  - Las pendientes de un protocolo **pausado** no salen en esta lista.
  - Al crear la OT, la tarea toma la **versión del checklist vigente en ese momento**. Si la plantilla no tiene versión publicada, entra sin checklist y el sistema avisa.
- **Se conecta con:** Protocolos (de donde nacen), Ficha del activo, OT (destino) y Calendario y Dashboard (misma fuente).
- **Para la demo:** marca 2 tareas de un mismo piso, **Crear OT**, y muestra que propone el título y la ubicación común.
  - *Pregunta probable: «¿Por qué obligan a poner una causa al reprogramar?»* Para tener trazabilidad: cuánto se corrió cada tarea y por qué (el cliente ya lo hacía con esas causas en Fracttal).

### 5.9 Hallazgos (`/hallazgos`)

- **Para qué sirve:** bandeja del planificador con lo que los técnicos encontraron y no resolvieron en sitio.
- **Quién la ve:** ADMIN y SUP (con su alcance). Ambos deciden.
- **Qué se ve:**
  - «Hallazgos — Lo que los técnicos encontraron en campo y hay que corregir», con el aviso «N críticos o con equipo fuera de servicio».
  - Pestañas **Por decidir** (con contador), **Convertidos, Descartados, Resueltos en sitio**.
  - Filtros de hospital («Todos los hospitales») y severidad («Toda severidad»).
  - Lista ordenada de lo más grave a lo menos: severidad (y «Fuera de servicio»), equipo con su código, hospital · ubicación · OT, la descripción, «Qué se hizo» si se resolvió en sitio, quién lo reportó, cuándo y cuántas fotos.
- **Qué se puede hacer (solo en «Por decidir»):**
  - **Convertir en correctivo:** crea una tarea correctiva pendiente sobre el equipo, con prioridad según la severidad (Crítica y Alta → Alta). Pide *Fecha programada* y *Nota* (opcional), y el botón es **Crear correctivo**.
  - **Descartar:** pide «Por qué se descarta» (obligatorio).
  - Si la OT sigue en curso, en lugar de botones sale «La OT sigue en curso».
- **Reglas importantes:**
  - Solo se decide sobre un hallazgo cuando su OT ya está **En revisión o Finalizada**. Antes, el técnico todavía puede corregirlo.
  - El correctivo creado aparece en **Tareas pendientes** para agruparlo en una OT.
  - El hospital recibe un **correo** al **completar** la OT si hay hallazgos graves. Llega al contacto del hospital y a las cuentas CLI cuyo alcance incluye el equipo.
  - **«Fuera de servicio» en un hallazgo es una marca**: no cambia el estado del activo (sigue «Activo» en Activos).
- **Se conecta con:** OT (tab Hallazgos, de donde sale cada uno), Tareas pendientes (donde cae el correctivo), Dashboard (tarjeta y panel) y portal del hospital.
- **Para la demo:** abre el hallazgo crítico, **Convertir en correctivo**, y ve a Tareas pendientes a mostrar la tarea nueva.
  - *Pregunta probable: «¿Si un equipo queda fuera de servicio por un hallazgo, el sistema lo marca?»* La marca es del hallazgo y alimenta el aviso y el acta. El estado del activo hay que cambiarlo a mano en Editar activo.

### 5.10 Órdenes de trabajo (`/ordenes`)

- **Para qué sirve:** ver y buscar todas las visitas de mantenimiento, en cualquier estado.
- **Quién la ve:** ADMIN y SUP (dentro de su alcance). **+ Nueva OT** es solo para ADMIN.
- **Qué se ve:**
  - «Órdenes de trabajo» con el conteo «N órdenes encontradas».
  - Búsqueda «Título, N° OT, activo...».
  - Filtros: estado (Pendiente, En proceso, En revisión, Finalizada, Cancelada), prioridad, tipo («Todos los tipos») y *Solo vencidas*.
  - Filtros de lugar: Hospital, Ubicación (incluye lo que tiene dentro) y Activo, con **Quitar filtros de lugar**.
  - Tabla: *N° OT, Tipo, Título, Activo* («+N activos»), *Hospital, Prioridad, Estado, Técnico, F. Límite* (con alerta si está vencida), *PDF* y *Acciones* (**Ver**).
  - Paginación de 20 en 20 en el navegador.
- **Qué se puede hacer:** abrir el detalle; **+ Nueva OT** (ADMIN).
- **Reglas importantes:**
  - Las OT no se borran ni se editan desde la lista.
  - Los filtros de lugar viajan por la URL (desde la ficha del activo: «Ver todas sus OT»).
  - Una OT aparece por su hospital y por la ubicación de la visita **o** la de cualquiera de sus activos.
- **Se conecta con:** Tareas pendientes (crean las OT), Detalle de la OT, Ficha del activo y Reportes (columna PDF).
- **Para la demo:** filtra «En revisión» y abre la que está esperando aprobación.
  - *Pregunta probable: «¿Dónde veo las OT vencidas?»* Casilla *Solo vencidas*.

### 5.11 Nueva orden de trabajo (`/ordenes/nueva`)

- **Para qué sirve:** crear a mano una OT correctiva o de verificación, sin pasar por un protocolo.
- **Quién la ve:** **solo ADMIN** (el servidor rechaza al SUP; la ruta sí le abre la página). El SUP crea OT desde **Tareas pendientes**.
- **Qué se ve:**
  - «Nueva orden de trabajo — Solo OT correctivas y de verificación».
  - Campos: Hospital\*, Ubicación (queda como ubicación de la visita), buscador y lista de **Activos\*** (casillas, «Marcar los N de esta lista»), un checklist por activo (de las plantillas con versión publicada, o «Sin checklist»), *Tipo de OT\** (por defecto Correctivo), *Título\**, *Descripción*, *Prioridad\**, *Fecha límite\**, *Duración estimada* (h y min), *Asignado a* y *Notas*.
  - Botón **Crear OT**.
- **Qué se puede hacer:** crear la OT con varios activos del mismo hospital.
- **Reglas importantes:**
  - Todos los activos deben ser de un mismo hospital.
  - La OT nace **Pendiente** y sus tareas ya **Programadas**.
  - *Asignado a* ofrece técnicos, supervisores y administradores.
  - La pantalla dice «solo correctivas y de verificación», pero el selector de tipo ofrece todos los tipos activos del catálogo.
  - Si el hospital no tiene contrato vigente, avisa pero deja crear.
- **Se conecta con:** Órdenes de trabajo, Tipos de tarea (catálogo) y Checklists (versiones).
- **Para la demo:** normalmente no se usa. Muestra solo que existe para correctivos.
  - *Pregunta probable: «¿Un supervisor puede crear una OT?»* Sí, agrupando tareas pendientes. A mano, solo el administrador.

### 5.12 Detalle de la OT (`/ordenes/:id`, y `/mis-ordenes/:id` para el técnico)

Es la pantalla más importante del sistema: la usan todos los roles, cada uno con lo suyo. El técnico la ve con la misma página (ver 7.2).

- **Para qué sirve:** ejecutar, revisar y cerrar una visita, con su checklist, evidencia, repuestos, hallazgos y acta.
- **Quién la ve:**
  - ADMIN y SUP (con alcance).
  - TEC, solo si la tiene asignada.
  - CLI en su portal, con otra pantalla (ver 8.5), y solo si está Finalizada.
- **Qué se ve:**
  - **Encabezado:** número (`OT-2026-…`), tipo, estado y prioridad, título, botón **Editar** (ADMIN/SUP) y los botones de transición (ver abajo).
  - **Tarjetas:**
    - *Activo(s)* (código, nombre, hospital, ubicación).
    - *Asignación*: Asignado a, **Reasignar** (ADMIN), **Asignármela** (ADMIN/SUP, en Pendiente o En proceso, si la OT no es suya), Creado por.
    - *Fechas*: programada, Inicio real, Cierre, Dur. estimada, Dur. real y *Fecha de intervención*.
    - *Progreso*: Avance y Calificación.
  - **Pestañas** (los nombres reales): *Historial de estados, Checklist* (si la OT tiene varios activos se llama **Tareas (N)**), *Evidencia, Repuestos, Reportes, Hallazgos*.
- **Qué se puede hacer:**
  - **Botones de transición:**
    - **Iniciar OT**, **Enviar a revision** (la persona asignada).
    - **Completar**, **Rechazar** (con *Motivo del rechazo…* y **Confirmar rechazo**) para ADMIN y SUP.
    - **Cancelar OT** (solo ADMIN; modal «Cancelar OT» con **Confirmar cancelacion**).
  - **Editar** (ADMIN/SUP): título, descripción, prioridad, fecha límite, duración estimada, asignado a, clasificación 1 y 2, checklist (si nadie lo ha respondido y la OT tiene una sola tarea) y notas.
  - **Pestaña Checklist/Tareas:**
    - Con varios activos hay una lista con el avance de cada uno («N de M · K obligatorios»). Al tocar uno se abre su checklist.
    - En **Pendiente**, ADMIN/SUP pueden **agregar tareas** de ese hospital (modal «Agregar tareas a la OT») y **quitar** una (vuelve a pendientes con su fecha).
    - El técnico responde cada campo y pulsa **Finalizar checklist**.
    - Al dejar todos completos, la app **pregunta** «¿Envías la OT a revisión?» (sugiere, no obliga).
    - En revisión, ADMIN/SUP ven **Corregir respuestas** y **Terminar** (ver reglas).
  - **Pestaña Evidencia:**
    - *Firmas* (lista) y *Agregar firma* (Nombre del firmante\*, Cargo, **Guardar firma**).
    - *Fotos* (galería) y *Agregar foto* (**Tomar foto** o **Seleccionar foto**, «¿De qué activo es?», selector **Antes / Después**, Descripción, **Subir foto**).
    - En revisión, ADMIN/SUP: cambiar la descripción y **Ocultar del acta / Volver a mostrar en el acta**.
  - **Pestaña Repuestos:**
    - Tabla Item, Codigo, Cantidad, Unidad, Costo unit., Fecha, Registrado por.
    - **Agregar repuesto** (modal «Registrar repuesto usado»: buscar item, cantidad, notas). Solo En proceso y por el ADMIN o la persona asignada.
  - **Pestaña Reportes:**
    - El acta de la OT con **Descargar PDF**, hash SHA-256 y envíos por correo.
    - ADMIN: **Reenviar email**, **Generar reporte de nuevo** si falló y **Verificar integridad del documento**.
  - **Pestaña Hallazgos:** **Reportar hallazgo** (técnico o ADMIN/SUP mientras está Pendiente o En proceso) y, ya en revisión, **Convertir en correctivo** / **Descartar**.
  - **Fecha de intervención:** **Corregir** / **Cambiar** / **Quitar la corrección**, en revisión, para ADMIN y SUP.
- **Reglas importantes:**
  - **OT cerrada no se edita.** Finalizada o Cancelada, el servidor responde 403 a cualquier cambio.
  - **Para enviar a revisión faltan, y la pantalla lo lista:**
    - checklists completos;
    - al menos una **foto no oculta**;
    - la **firma**.
    - La foto se exige, no sus coordenadas: sin GPS igual se puede cerrar.
  - **Quién ejecuta:** inicia, llena el checklist, fotos y firma **quien tiene asignada la OT**. Un ADMIN o SUP puede ejecutarla si usa **Asignármela**. Mientras no lo haga, solo revisa.
  - **Reasignar:** el botón es solo ADMIN. Pero **Editar** también incluye «Asignado a» y el servidor lo acepta de un SUP.
  - **Checklist:** solo se edita con la OT **En proceso** y por quien la ejecuta. Cada respuesta se guarda al salir del campo. Los obligatorios cuentan en cada toma de un grupo repetible.
  - **Revisión (ADMIN y SUP):**
    - **Corregir respuestas.** Cada cambio queda como «Corregido por» el nombre del revisor. El valor anterior va a la auditoría.
    - **Fotos:** agregar, cambiar la descripción u **ocultar del acta**. **No se borran.** Quedan en la OT y en la auditoría. El cliente no ve las ocultas.
    - **Fecha de intervención:** por defecto sale de lo que registró el técnico (de la primera a la última respuesta, foto o firma). El revisor la puede corregir, y el acta y el correo usan la corregida. Lo del técnico no se pierde.
    - La constancia queda en la OT y en la auditoría, **no en el acta**.
  - **Rechazar** devuelve la OT a **En proceso**, con el comentario en el historial. El técnico debe enviarla a revisión otra vez.
  - **Cantidad de tomas distinta a la del protocolo:** se avisa «el protocolo dice N y aquí hay M». La diferencia se **ve en la OT** (el texto dice «se le avisará al administrador», pero no hay correo ni notificación: **es solo lo que se ve en pantalla**).
  - **Al Completar:** se genera el acta en segundo plano. Aparece «Generando reporte…» hasta que esté.
  - **Cancelar** reemite las tareas como pendientes, aunque el modal diga «Esta accion no se puede deshacer» (la OT sí queda cancelada para siempre).
  - **Historial de estados:** solo lo ven ADMIN y SUP. El técnico ve «No disponible para tu rol».
  - **Avance y Calificación** de la tarjeta *Progreso* **no los llena ninguna pantalla** hoy. Avance se queda en **0%** y la Calificación en «—». El avance real está en la pestaña Checklist (campos completados).
  - **Repuestos:** al registrar una salida se descuenta el stock. No está en la cola de sincronización, así que **necesita red** **(sin confirmar en la app instalada)**.
  - **Firma:** en la pestaña Evidencia hay dos paneles (agregado el 2026-10-23): «Firma del técnico» y «Firma de quien recibe en el hospital». Cada uno pide el nombre de quien firma y solo se activa con la OT en curso. El acta las imprime como «Realizado por» y «Aceptado por».
- **Se conecta con:** Tareas pendientes (origen de las tareas), Checklists (versión fijada), Inventario (repuestos), Hallazgos, Reportes y portal del hospital.
- **Para la demo (30 s):** abre la OT que está *En revisión*. Muestra el checklist respondido, las fotos (oculta una) y **Completar**. Luego, la pestaña *Reportes* con el PDF.
  - *Pregunta probable: «¿Un supervisor puede corregir lo que puso el técnico?»* Sí, solo en revisión, y queda marcado «Corregido por» con el valor anterior en la auditoría.

### 5.13 Protocolos (`/planes-pm`)

- **Para qué sirve:** definir qué tareas se le hacen a un activo y cada cuánto. Es la fuente de las tareas pendientes.
- **Quién la ve:** ADMIN y SUP **leen**. **Solo el ADMIN** crea, edita, pausa, reanuda y asigna activos (los botones solo aparecen al ADMIN y el servidor lo exige). El SUP puede abrir `/planes-pm/nuevo` por URL, pero no podrá guardar.
- **Qué se ve:**
  - «Protocolos — Cada activo tiene un protocolo; el protocolo dice qué tareas se le hacen y cada cuánto».
  - Botón **Nuevo protocolo** (ADMIN).
  - Filtros *Todos / Activos / Pausados* y búsqueda «Buscar protocolo por nombre».
  - Tabla: *Protocolo* (nombre y descripción), *Tareas* (las 2 primeras con tipo y frecuencia, o «Sin tareas: no genera nada»), *Activos, Próxima fecha* (con «N vencidas»), *Cumplimiento del mes* (barra), *Estado* y *Acciones*.
- **Qué se puede hacer:** **Ver**; **Editar**, **Pausar** y **Reanudar** (ADMIN).
- **Reglas importantes:**
  - **Pausar:** sus pendientes dejan de salir para planificar. Reanudar las repone.
  - Un protocolo **sin tareas no genera nada**.
  - El protocolo no se borra.
  - Un protocolo **restringido a un hospital** solo se asigna a activos de ese hospital, y los demás hospitales no lo ven.
  - El cumplimiento del mes cuenta **tareas** (no OT) del protocolo, dentro del alcance del usuario.
- **Se conecta con:** Detalle del protocolo, Activos (asignación), Tareas pendientes, Checklists (cada tarea apunta a una plantilla) y Tipos de tarea.
- **Para la demo:** muestra un protocolo con tareas, frecuencia y la barra de cumplimiento.
  - *Pregunta probable: «¿Por qué se llama protocolo y no plan?»* Porque así piensa el cliente: protocolos por activo («3 TOMAS», «ALARMA 3 GASES»). En URLs y en el código todavía se llama *plan*.

### 5.14 Detalle del protocolo (`/planes-pm/:id`) y su formulario (`/planes-pm/nuevo`, `/planes-pm/:id/editar`)

- **Para qué sirve:** ver y armar las tareas del protocolo, asignarlo a los activos y ver su cumplimiento.
- **Quién la ve:** ADMIN y SUP leen; solo ADMIN modifica.
- **Qué se ve:**
  - **Encabezado:** estado (Activo/Pausado), prioridad, «Solo {hospital}» si está restringido, y 4 datos (*Tareas activas, Activos con este protocolo, Próxima fecha, Pendientes vencidas*).
  - **Pestañas:** *Tareas (N), Activos (N), Cumplimiento*.
  - **Tareas:** tabla *Tarea, Cuándo, Checklist, Duración, Abiertas / hechas, Acciones*.
  - **Activos:** *Código, Activo, Hospital y ubicación, Próxima fecha, Acciones* (**Ver activo**, **Quitar**), y **Asignar activos**.
  - **Cumplimiento:** barras de los últimos 12 meses (tareas programadas por mes y cuántas se hicieron).
  - **Formulario del protocolo:** Nombre\*, Descripción, Prioridad por defecto, *Solo para el hospital*, Clasificación 1 y 2. Al crear va derecho a la pestaña de tareas.
- **Qué se puede hacer (ADMIN):**
  - **Agregar tarea** (modal «Nueva tarea del protocolo»): Nombre\*, Tipo (catálogo), Prioridad, Duración estimada, Checklist, **veces por bloque repetible** y **Cuándo se hace**:
    - *Por fecha (se repite sola)*: «Cada N días/semanas/meses/años» y «Primera vez».
    - *Por uso del medidor (cada N horas)*.
    - *Por umbral de una lectura*.
    - *Por evento (la creas tú cuando ocurre)*: aparece el botón **Crear para un activo**.
    - **Repetir:** «Siempre» o «Solo N veces».
    - **Programación fija**.
    - La pantalla muestra las **primeras fechas** que saldrían.
  - **Editar**, **Desactivar / Activar** una tarea. Sin historial se puede **Eliminar la tarea**.
  - **Asignar activos** (hospital, ubicación incluida, «Solo activos sin protocolo») y **Quitar protocolo**.
- **Reglas importantes:**
  - **Programación fija o no:**
    - *No marcada* (lo normal): la siguiente se cuenta desde el día en que **se hizo**, como en Fracttal.
    - *Marcada*: se cuenta desde la fecha **calculada**, así que adelantar o aplazar no corre el ciclo.
  - **Al cerrarse la OT** se crea la siguiente pendiente de cada tarea, salvo que se acabaran las repeticiones, que el protocolo se haya quitado o que el equipo ya no esté Activo.
  - **Desactivar una tarea:** anula sus pendientes (las que ya están en una OT siguen) y se conserva el historial.
  - **Un activo tiene un solo protocolo.** Asignarle otro quita el anterior, anula sus pendientes del anterior y las del nuevo **heredan la fecha** de la más próxima.
  - **Quitar el protocolo** a un activo anula sus pendientes de ese protocolo. Si tiene una tarea ya dentro de una OT, esa se hace igual.
  - **Activador por medidor:** «Cada» solo con unidades que acumulan. «Cuando» abre la tarea con fecha de hoy y manda **correo a los administradores**. Mientras esté abierta, otra lectura no abre otra. Las lecturas llegan del checklist (campo «Lectura de medidor») o se registran a mano en la ficha del equipo.
  - **Bloques repetibles:** el número de veces se pide solo si el checklist elegido tiene grupos repetibles.
  - Una plantilla de checklist **sin versión publicada** no deja guardar la tarea hasta publicarla o elegir otra.
- **Se conecta con:** Protocolos, Activos, Checklists, Tipos de tarea, Medidores y Tareas pendientes.
- **Para la demo:** abre la tarea de un protocolo y enseña «Cuándo se hace», con las primeras fechas calculadas, y la pestaña *Activos*.
  - *Pregunta probable: «¿Si un equipo cambia de 3 a 4 tomas?»* Se le asigna el otro protocolo: las pendientes viejas se anulan y las nuevas conservan la fecha, el ciclo no se reinicia.

### 5.15 Calendario (`/calendario-pm`)

- **Para qué sirve:** ver las tareas del mes por su fecha programada.
- **Quién la ve:** ADMIN y SUP (con su alcance).
- **Qué se ve:**
  - «Calendario de mantenimiento — Tareas por su fecha programada».
  - Selector de hospital («Todos los hospitales»), flechas de mes y la cuadrícula Dom–Sáb.
  - Cada día muestra puntos con el conteo por situación: **Vencida** (rojo), **Reprogramada** (ámbar), **Pendiente** (gris), **En OT** (azul), **Finalizada** (verde). Hay una leyenda abajo.
  - Al tocar un día, un panel con cada tarea (código del activo, nombre, tarea · protocolo, hospital · ubicación, «Fecha calculada» si fue reprogramada y la OT).
  - Enlace **Planificar en Tareas pendientes** si el día tiene pendientes.
- **Qué se puede hacer:** navegar por mes, filtrar por hospital y abrir activos y OT. **Es de solo lectura**: no se arrastra para reprogramar.
- **Reglas importantes:**
  - Muestra tareas Pendientes, Programadas y Finalizadas. **No muestra las canceladas.**
  - La fuente es la propia tarea (no hay otra tabla de calendario).
- **Se conecta con:** Tareas pendientes (para actuar), Ficha del activo y OT.
- **Para la demo:** abre el mes actual y toca un día con tareas.
  - *Pregunta probable: «¿Puedo arrastrar para reprogramar?»* No. Se reprograma en Tareas pendientes con causa.

### 5.16 Checklists (`/checklists`)

- **Para qué sirve:** catálogo de plantillas (formularios) que el técnico llena en campo.
- **Quién la ve:** ADMIN y SUP **ven la lista**. **Nueva plantilla** y **Editar** solo aparecen al ADMIN. (El servidor sí permite crear y publicar al SUP, y la ruta del editor está abierta por URL.)
- **Qué se ve:**
  - «Checklists — N plantillas».
  - Filtros *Todas / Activas / Inactivas*.
  - Tabla: *Nombre* (y descripción), *Versión actual* (`vN`), *Campos, Estado, Acciones*.
- **Qué se puede hacer:** **+ Nueva plantilla** (nombre, descripción, **Crear y editar**) lleva directo al editor.
- **Reglas importantes:** las plantillas **no se borran**. En pantalla no hay forma de desactivarlas **(sin confirmar si se hace por otra vía)**.
- **Se conecta con:** Editor del checklist, Protocolos (cada tarea apunta a una plantilla), Nueva OT y Detalle de la OT.
- **Para la demo:** abre una plantilla para mostrar el editor (siguiente sección).
  - *Pregunta probable: «¿Pueden cambiar un checklist sin afectar OT viejas?»* Sí, por versiones.

### 5.17 Editor del checklist (`/checklists/:id/editar`)

- **Para qué sirve:** armar el formulario de campos y publicarlo como una **versión**.
- **Quién la ve:** ADMIN (botón Editar). Por URL, también SUP.
- **Qué se ve:**
  - Título con la versión actual («Versión actual: vN · M campos» o «Sin versiones publicadas») y el botón **Publicar vN+1**.
  - **Pestañas:** *Editor, Vista previa, Historial de versiones*.
  - **Grupos que se repiten:** casillas por cada grupo («Toma»), con cuántos campos tiene.
  - **Paleta de tipos de campo** (clic para agregar):
    - Texto corto, Texto largo, Número
    - Lectura de medidor
    - Sí / No
    - Selección única, Selección múltiple
    - Fecha, Fecha y hora
    - Localización GPS
  - **Cada campo** (arrastrable) lleva: etiqueta, *Grupo / Sección*, *Obligatorio*, *Ayuda* y, según el tipo:
    - *Rango / Unidad* (mín., máx., unidad) en número y lectura.
    - Opciones, en las selecciones.
    - *Permite N/A (no aplica)*, en Sí/No (viene marcada).
    - Elegir **medidor** en «Lectura de medidor».
- **Qué se puede hacer:**
  - **Publicar vN+1:** crea la nueva versión con los campos del editor. Pide confirmación en «Publicar nueva versión».
  - **Vista previa** del formulario.
  - **Historial de versiones:** versiones con fecha, quién las publicó y número de campos.
- **Reglas importantes:**
  - **Publicar crea una versión nueva; la anterior queda archivada.** Las OT **ya completadas** y los checklists ya creados no cambian: cada tarea queda atada a **la versión vigente cuando entró a la OT**.
  - **Foto y Firma ya no se ofrecen** como campos (la OT ya tiene fotos de evidencia y firmas). Las versiones viejas que los traen siguen funcionando. Al abrir una versión con ellos, el editor los quita y avisa «Se quitaron N campos de Foto/Firma». El servidor rechaza publicar uno nuevo que los incluya.
  - **Grupo repetible:** se marca el grupo y se escribe el **mismo** «Grupo / Sección» en sus campos. El protocolo dice cuántas veces va.
  - **Sí/No/N/A:** guarda `true`, `false` o `na`. El acta imprime solo la respuesta.
  - **Lectura de medidor** con medidor elegido: lo que responda el técnico queda como lectura del equipo y puede abrir tareas por uso o umbral. Sin medidor, solo queda en el acta.
  - Los campos no publicados se conservan al cambiar de pestaña (no se pierden al recargar la vista previa).
- **Se conecta con:** Checklists, Protocolos (versión vigente), Detalle de la OT (donde se responde) y Medidores.
- **Para la demo:** agrega un campo, marca «Obligatorio» y enseña la vista previa. No hace falta publicar.
  - *Pregunta probable: «Si cambio el checklist, ¿qué pasa con las OT que ya están en curso?»* Conservan la versión con la que se crearon. Las nuevas toman la vigente.

### 5.18 Inventario (`/inventario`) y Movimientos de un item (`/inventario/:id/movimientos`)

- **Para qué sirve:** controlar repuestos y consumibles y descontarlos desde las OT.
- **Quién la ve:** ADMIN y SUP **ven**. **Nuevo item**, **Editar** y **Registrar movimiento** solo aparecen al ADMIN. (El servidor permite al SUP registrar movimientos, pero no crear items.) El técnico no ve la pantalla, pero registra **salidas** desde su OT.
- **Qué se ve:**
  - *Inventario:*
    - Contador de items, búsqueda «Buscar por nombre o codigo...» y filtro Todos / Solo activos / Solo inactivos.
    - Tabla: *Nombre* (con «Stock bajo»), *Codigo, Unidad, Stock actual, Stock minimo, Estado, Acciones*.
    - Las filas con stock bajo (`stock ≤ mínimo`) van resaltadas. El globo del menú cuenta estas.
  - *Movimientos:* stock actual y mínimo, y la tabla *Fecha, Tipo, Cantidad, OT relacionada, Referencia, Registrado por*.
- **Qué se puede hacer:**
  - **Nuevo item / Editar** (Nombre\*, Codigo\*, Descripcion, Unidad de medida, Stock minimo, Costo unitario, Activo).
  - **Ver movimientos.**
  - **Registrar movimiento:** *Entrada, Salida* o *Ajuste (establece cantidad exacta)*, con cantidad, referencia y notas.
- **Reglas importantes:**
  - El stock **solo cambia por movimientos**; el item no permite editar el stock a mano.
  - Una **salida** mayor al stock se rechaza: «Stock insuficiente».
  - El **técnico** solo registra salidas, ligadas a **su** OT.
  - Un movimiento ligado a una OT solo lo ve quien ve esa OT. El inventario en sí es **global** (no por hospital).
- **Se conecta con:** pestaña *Repuestos* de la OT (donde se consumen) y Dashboard/menú (alerta de stock bajo).
- **Para la demo:** muestra un item en «Stock bajo» y su historial con la OT que lo consumió.
  - *Pregunta probable: «¿Descuenta solo?»* Sí: al registrar el repuesto en la OT, se descuenta del stock.

### 5.19 Usuarios (`/usuarios`) — solo ADMIN

- **Para qué sirve:** crear cuentas, ajustar su alcance, restablecer contraseñas y desactivar usuarios.
- **Quién la ve:** **solo ADMIN** (el SUP puede listar usuarios en el servidor, pero no ve la pantalla ni el menú).
- **Qué se ve:**
  - «Gestión de usuarios» con «N de M usuarios».
  - Botón **Nuevo usuario**.
  - Búsqueda, filtro de rol (Administrador, Supervisor, Tecnico, Cliente) y *Mostrar inactivos*.
  - Tabla: *Nombre completo, Email, Rol, Alcance, Estado, Acciones*. «Todos» para el ADMIN o sin hospital; si no, hospital y la parte del árbol.
- **Qué se puede hacer:**
  - **Nuevo usuario:** Nombre\*, Apellido\*, Email\*, Rol\*. Y **alcance**:
    - para CLI, Hospital\*;
    - para SUP y TEC, «Limitar a un hospital» y «Parte del hospital»;
    - para TEC, Código de empleado y Teléfono.
    - El sistema genera una **contraseña temporal** y la manda por correo.
  - **Ver / editar:** ficha con datos, alcance, **Usuario activo** y *Actividad reciente* (últimas 5 acciones) con **Ver historial completo** (abre Auditoría filtrada).
  - **Restablecer contraseña** (confirmación en línea) y **Desactivar / Activar**.
- **Reglas importantes:**
  - **El rol no se edita** después de crear la cuenta.
  - Un ADMIN **no puede desactivarse a sí mismo**.
  - Una cuenta de hospital (CLI) **requiere** hospital: sin él, no ve nada.
  - El alcance del ADMIN siempre es total (el servidor ignora cualquier límite).
  - La contraseña temporal solo viaja por correo; la pantalla **no la muestra**. Si el envío falla, el servidor lo ignora **en silencio**: habría que restablecerla.
  - Al entrar con la temporal, el usuario debe cambiarla.
- **Se conecta con:** Hospitales y Ubicaciones (alcance), Auditoría y todo el sistema (el alcance filtra cada pantalla).
- **Para la demo:** muestra «Nuevo usuario» con el alcance de un supervisor limitado a un piso.
  - *Pregunta probable: «¿Una biomédica puede ver otro hospital?»* No: su cuenta queda ligada a un hospital, y si se quiere, a una parte.

### 5.20 Reportes (`/reportes`)

- **Para qué sirve:** buscar y descargar las **actas** generadas, y (el ADMIN) pedir un consolidado por periodo.
- **Quién la ve:** ADMIN y SUP. El **Reporte consolidado** solo lo ve el ADMIN.
- **Qué se ve:**
  - «Reportes — Reportes de servicio generados al completar ordenes de trabajo».
  - **Reporte consolidado (ADMIN):** Hospital, Desde, Hasta, Tipo de OT y **Generar reporte consolidado**. Dice «Reporte en generacion. Recibiras un email cuando este listo.»
  - **Filtros:** Hospital (si hay más de uno), N° OT, Desde, Hasta, **Filtrar** y **Limpiar**.
  - **Tabla:** *OT, Titulo, Hospital, Generado, Hash, Envios* (cuántos correos exitosos) y **Descargar**.
- **Qué se puede hacer:** filtrar, descargar el PDF de cada acta y generar el consolidado.
- **Reglas importantes:**
  - El **hash** (SHA-256) permite verificar que el acta no se alteró (el ADMIN lo comprueba en la pestaña *Reportes* de la OT).
  - El N° OT acepta «42» o el código completo.
  - Solo hay actas de OT **Finalizadas**.
  - El consolidado se manda por correo al terminar.
- **Se conecta con:** Detalle de la OT (pestaña Reportes), Formato del acta (qué imprime) y portal del hospital (los mismos PDFs).
- **Para la demo:** filtra por hospital y descarga un acta.
  - *Pregunta probable: «¿Cómo sé que el acta no se editó?»* Lleva un hash en el pie; el sistema puede verificarlo.

### 5.21 Formato del acta (`/formato-acta`) — solo ADMIN

- **Para qué sirve:** decidir qué imprime el acta de servicio, con interruptores (como las «Opciones de impresión» de Fracttal).
- **Quién la ve:** **solo ADMIN**.
- **Qué se ve:**
  - «Formato del acta» con quién hizo el último cambio.
  - Sección *Siempre incluido* (no se puede apagar): número de OT, tipo y fecha de emisión, hospital, respuestas del checklist y hash de integridad.
  - Secciones con interruptores:
    - **Datos de la visita** (ubicación, activos intervenidos, ejecutado por, fecha programada, trabajo en campo, duración, descripción, notas).
    - **Activos** (tabla resumen, ubicación, tipo, fabricante, modelo, serie).
    - **Checklist** (nombre y versión, observaciones, hora y técnico que respondió, mapa GPS).
    - **Hallazgos.**
    - **Fotos** (de cada activo, de la visita, GPS).
    - **Materiales.**
    - **Firmas** (Realizado por, Validado por, Aceptado por).
  - Barra de acciones: «N cambio(s) sin guardar» o «N campo(s) ocultos en el acta».
  - Botones: **Descartar**, **Vista previa** y **Guardar cambios**.
- **Qué se puede hacer:** prender o apagar campos y **Vista previa** (PDF de ejemplo, sin guardar, sobre una OT finalizada).
- **Reglas importantes:**
  - Es **un solo formato** para todo el sistema.
  - Aplica a las actas **nuevas**; las ya generadas no cambian.
  - La numeración de secciones se ajusta sola al apagar alguna.
  - La vista previa necesita **al menos una OT finalizada**; si no, dice «Todavía no hay OTs finalizadas para mostrar un acta de ejemplo».
  - «Validado por» sale de quien aprobó la OT. «Aceptado por» es la firma de quien recibe en el hospital; si no se capturó, sale «No registrada».
- **Se conecta con:** Reportes y OT (cada acta usa esta configuración).
- **Para la demo:** apaga las fotos GPS, **Vista previa**, y muestra el PDF sin esa columna.
  - *Pregunta probable: «¿Cambia las actas antiguas?»* No, solo las que se generen desde ahora.

### 5.22 Tipos de tarea (`/tipos-de-tarea`) — solo ADMIN

- **Para qué sirve:** catálogo de tipos de tarea. Cada tipo dice en qué indicador cuenta.
- **Quién la ve:** **solo ADMIN** (todos los roles leen el catálogo para ver nombres; solo el ADMIN lo modifica).
- **Qué se ve:**
  - «Tipos de tarea» y un formulario *Nuevo tipo / Cuenta como* con **Agregar**.
  - Tabla *Tipo* (nombre, código y «del sistema»), *Cuenta como* (Preventivo, Correctivo o Ninguno), *En uso, Activo, Acciones*.
- **Qué se puede hacer:** **Agregar**, **Renombrar** (el código no cambia), cambiar *Cuenta como*, activar o desactivar y **Borrar** (solo si no se usa).
- **Reglas importantes:**
  - «Cuenta como» decide el indicador:
    - *Preventivo*: entra en el cumplimiento de protocolos.
    - *Correctivo*: entra en el MTTR.
    - *Ninguno*: no entra en esos indicadores.
  - **Preventivo y Correctivo** (del sistema) siempre cuentan así. Los 5 del sistema no se desactivan ni se borran.
  - Un tipo **en uso no se borra**: se desactiva y deja de ofrecerse, pero lo que ya lo usa lo conserva.
  - Los nombres se guardan también para verlos sin red.
- **Se conecta con:** tareas del protocolo, creación de OT, filtros de la lista de OT, Reportes (consolidado) y Dashboard.
- **Para la demo:** cambia lo que «cuenta como» un tipo y explica el efecto en el cumplimiento.
  - *Pregunta probable: «¿Puedo agregar mis propios tipos?»* Sí. El catálogo arrancó con 20 tipos: los cinco del sistema y los que el cliente usa en Fracttal.

### 5.23 Auditoría (`/auditoria`) — solo ADMIN

- **Para qué sirve:** ver quién hizo qué y cuándo.
- **Quién la ve:** **solo ADMIN**. Otro rol ve «No tienes permisos para ver el log de auditoria».
- **Qué se ve:**
  - «Log de auditoria — N registros».
  - Filtros: usuario, acción (Crear, Actualizar, Eliminar, Cambio de estado, Inicio de sesion, Sincronizacion), entidad, Desde y Hasta, con **Aplicar filtros** y **Limpiar**.
  - Tabla *Fecha / Hora, Usuario* («Sistema» si no hay), *Accion, Entidad, ID* (8 primeros caracteres) e *IP*. Una fila se expande y muestra los cambios (antes → después).
  - **Exportar CSV (pagina actual)**.
- **Qué se puede hacer:** filtrar, expandir y exportar.
- **Reglas importantes:**
  - El CSV exporta **solo la página que estás viendo** (50 registros), no el resultado completo del filtro.
  - Los inicios y cierres de sesión también quedan registrados, con IP.
  - El filtro de entidad solo ofrece los tipos que la pantalla conoce. Hallazgos, ubicaciones y tipos de tarea se registran, pero **no están en la lista de filtros** y salen con su nombre técnico.
  - Se llega aquí desde la ficha de un usuario con su filtro ya aplicado.
- **Se conecta con:** Usuarios (historial), OT (correcciones del revisor) y todo lo que escribe por API.
- **Para la demo:** filtra por una OT o por el supervisor y expande una corrección.
  - *Pregunta probable: «¿Se puede borrar el log?»* No hay pantalla ni acción de borrado.

### 5.24 Mi perfil (`/mi-perfil`)

- **Para qué sirve:** ver los datos de la propia cuenta y cambiar la contraseña.
- **Quién la ve:** todos los roles (cada layout lo incluye).
- **Qué se ve:**
  - «Mi perfil» con la nota «Para cambiar tu nombre, correo o rol contacta a un administrador».
  - *Datos de la cuenta*: nombre completo, email, rol, hospital (si tiene), código de empleado (TEC) y teléfono.
  - *Cambiar contrasena*: actual, nueva (con medidor de fortaleza) y confirmar. Botón **Actualizar contrasena**.
- **Qué se puede hacer:** cambiar la contraseña.
- **Reglas importantes:** exige mayúscula, número y carácter especial.
- **Se conecta con:** Inicio de sesión.
- **Para la demo:** no se muestra.

---

## 6. Resumen de permisos por rol

Resumen de **qué puede hacer cada rol** (interfaz y servidor). Las celdas marcadas con ⚠ son brechas entre la interfaz y el servidor.

| Acción | ADMIN | SUP | TEC | CLI |
|---|---|---|---|---|
| Ver Dashboard, Activos, Tareas pendientes, Hallazgos, OT, Calendario | Sí | Sí (con alcance) | No | No |
| Crear, editar y activar hospitales | Sí | No | No | No |
| Crear, editar y borrar ubicaciones | Sí | Sí | No | No |
| Crear y editar activos | Sí | Sí | No | No |
| Dar de baja (botón de la ficha) | Sí | No ⚠ (sí por Editar activo) | No | No |
| Cambiar el protocolo del activo | Sí | Sí ⚠ (por Editar activo) | No | No |
| Crear, editar, pausar protocolos y asignar activos | Sí | No | No | No |
| Crear OT desde tareas pendientes | Sí | Sí | No | No |
| Crear OT manual | Sí | No | No | No |
| Reprogramar y anular tareas | Sí | Sí | No | No |
| Reasignar OT (botón) | Sí | No ⚠ (sí por Editar OT) | No | No |
| Asignármela y ejecutar | Sí | Sí | Sí (las suyas) | No |
| Completar, Rechazar, corregir en revisión | Sí | Sí | No | No |
| Cancelar OT | Sí | No | No | No |
| Convertir o descartar hallazgos | Sí | Sí | No | No |
| Contratos y garantías: crear y editar | Sí | No | No | No |
| Checklists: crear y publicar | Sí | No en la UI ⚠ (sí en el servidor) | No | No |
| Inventario: items | Sí | No | No | No |
| Inventario: registrar movimientos | Sí | No en la UI ⚠ (sí en el servidor) | Solo salidas, en su OT | No |
| Usuarios, Formato del acta, Tipos de tarea, Auditoría | Sí | No | No | No |
| Reporte consolidado y reenviar acta | Sí | No | No | No |
| Portal del hospital (solo lectura) | No | No | No | Sí |

---

## 7. App del técnico

### 7.1 Mis órdenes (`/mis-ordenes`)

- **Para qué sirve:** la lista de trabajo del técnico: las OT que tiene asignadas.
- **Quién la ve:** **TEC**. (ADMIN y SUP que ejecutan usan la web: ven sus OT en la lista de OT.)
- **Qué se ve:**
  - «Mis órdenes de trabajo — Órdenes asignadas a ti».
  - Pestañas **Pendientes, En proceso, En revisión, Todas**.
  - Tarjetas con: número, tipo, prioridad, título, activo (o «N activos»), hospital · ubicación, estado, «Límite: fecha» (o «Vencida —»), y el botón de la transición que le toque (**Iniciar OT** o **Enviar a revision**) y **Ver detalle**.
  - Aviso rojo/ámbar «Datos pendientes de sincronizar» en las tarjetas con cosas por subir.
  - El menú del técnico tiene solo *Mis ordenes* y *Mi perfil*.
- **Qué se puede hacer:** iniciar, enviar a revisión (si cumple los requisitos), abrir el detalle.
- **Reglas importantes:**
  - Solo ve las OT que tiene **asignadas**, sin importar su alcance.
  - Con red, **al abrir esta lista la app descarga en segundo plano el detalle y los checklists de cada OT abierta** y los guarda en el teléfono. Para trabajar sin señal, **hay que abrir la lista con red antes de salir**.
  - Sin red, la lista sale de lo guardado y el filtro por pestaña se aplica en el teléfono.
- **Se conecta con:** Detalle de la OT (siguiente sección) y Mi perfil.
- **Para la demo:** usa el teléfono: muestra la OT pendiente de demo, pulsa **Iniciar OT**.
  - *Pregunta probable: «¿Qué ve el técnico de las OT de otros?»* Nada. Solo las suyas.

### 7.2 Detalle de la OT para el técnico (`/mis-ordenes/:id`) y trabajo sin red

Es la misma pantalla de 5.12, con lo que le corresponde al técnico.

- **Para qué sirve:** ejecutar la visita en campo.
- **Quién la ve:** el técnico asignado.
- **Qué se ve:** el encabezado con el botón de transición, las tarjetas de datos, y las pestañas *Historial de estados* (muestra «No disponible para tu rol»), *Checklist* / *Tareas (N)*, *Evidencia*, *Repuestos*, *Reportes* y *Hallazgos*. No ve **Editar** ni **Reasignar**.
- **Qué se puede hacer, en orden:**
  1. **Iniciar OT.**
  2. Responder el checklist de cada activo. Si hay bloques repetibles, usa **Siguiente: Toma N** y **Agregar toma**. Cierra con **Finalizar checklist**.
  3. En *Evidencia*: **Tomar foto** (con la etiqueta **Antes / Después**) y **Guardar firma**.
  4. **Reportar hallazgo**, si encuentra algo.
  5. *Repuestos* → **Agregar repuesto**, si usó materiales.
  6. **Enviar a revision.** Si falta algo, el botón queda desactivado y dice «Para enviar a revisión falta: …».
- **Reglas importantes:**
  - **El checklist y la evidencia solo se editan con la OT En proceso.** Pendiente dice «Inicia la OT para responder los checklists y adjuntar fotos». En revisión, el técnico ya no cambia nada.
  - **Cada respuesta se guarda al salir del campo.** Si el servidor la rechaza (un valor inválido), el campo muestra el motivo.
  - **Las fotos** se reducen solas si pesan más de 10 MB. Con la cámara nativa se piden foto y GPS a la vez. Sin GPS, la foto sube igual («Sin GPS»).
  - **El técnico no ve el motivo de un rechazo.** Esa información va en el *Historial de estados*, que no ve. **(Sin confirmar** si se lo comunican por otro canal.)
  - **Sin red, funciona:**
    - ver las OT y checklists que ya descargó;
    - responder campos y cerrar el checklist;
    - fotos (se guardan en la cola del teléfono) y firmas;
    - hallazgos (el teléfono pone el id, así un reintento no duplica);
    - cantidad de tomas;
    - **Iniciar OT** y **Enviar a revision**.
    - La barra superior dice «Sin conexion — Modo offline activo», con el número de elementos en cola, y «Foto guardada. Se sincronizara al reconectar».
  - **Sin red, no funciona:**
    - Cancelar OT.
    - Corregir respuestas de un revisor.
    - Repuestos **(sin confirmar)**.
    - Descargar actas.
    - Cualquier pantalla de administración.
  - **Al volver la red**, el motor de sincronización sube **en orden**: respuestas del checklist y evidencia primero, y el cambio de estado de la OT al final (porque «Completar» valida que el checklist esté completo).
  - **Reintentos:**
    - Un fallo de red o del servidor (5xx, 429) se reintenta solo, con espera creciente de 1, 2, 4… hasta 30 minutos.
    - Un rechazo del servidor (por ejemplo 400) **no** se reintenta solo: pasa a **«Hay N elementos que no se pudieron enviar»**, un aviso que **no se puede cerrar**. Cada elemento se queda guardado en el teléfono y solo sale con **Reintentar** o **Reintentar todo**.
- **Se conecta con:** Mis órdenes, y desde ahí la revisión del supervisor.
- **Para la demo (30 s):** en el teléfono, abre la OT con red, **activa el modo avión**, responde un campo y toma una foto («Foto guardada»). Desactiva el modo avión y muestra que sincroniza.
  - *Pregunta probable: «¿Qué pasa si el técnico no tiene señal en un sótano?»* Trabaja igual: todo queda en el teléfono y sube cuando vuelve la señal. La foto se exige, el GPS no.

---

## 8. Portal del hospital (CLI)

El portal es **solo lectura**. El encabezado trae el logo, el menú *Dashboard, Mis activos, Mis reportes, Mi perfil*, el nombre y **Salir**. Todo está filtrado por el alcance de la cuenta (su hospital y, si lo tiene, su parte del árbol). Las cuentas de hospital nunca ven OT en curso, solo **Finalizadas**, ni fotos **ocultas**, ni tareas **canceladas**.

### 8.1 Dashboard del hospital (`/mis-dashboard`)

- **Para qué sirve:** el resumen de su hospital: equipos, lo que viene, cumplimiento, hallazgos, contratos, últimas OT y actas.
- **Quién la ve:** CLI.
- **Qué se ve:**
  - Nombre y dirección del hospital.
  - **Tarjetas** *Total activos* y una por estado (Activo, Fuera de servicio, Dado de baja).
  - **Cumplimiento** de los últimos 12 meses: «N de M mantenimientos realizados; K a tiempo» y «N mantenimientos vencidos».
  - **Próximos mantenimientos** (los 15 más próximos, con «Vencido ·» si ya pasó la fecha).
  - **Hallazgos** (los 10 más recientes, con su estado) y «N sin corregir».
  - **Contratos y garantías** con vigencia, cobertura y el documento.
  - **Ultimas ordenes de trabajo** (con **Ver mis activos**) y **Reportes recientes** (**Descargar**).
- **Qué se puede hacer:** navegar a los equipos y OT, y descargar actas.
- **Reglas importantes:**
  - **Cumplimiento del portal:** de las tareas **del protocolo** cuya fecha programada ya pasó en los últimos 365 días, cuántas se hicieron y cuántas a tiempo. **No es la misma fórmula** que el cumplimiento del Dashboard de administración (mensual, por OT preventivas, con un día de margen). Las cifras no tienen por qué coincidir.
  - El estado del hallazgo se traduce: *Resuelto* (en sitio o correctivo ya hecho), *Corrección programada {fecha}*, *Pendiente de corrección*, *Descartado*.
  - Una cuenta CLI sin hospital recibe un error «Usuario CLI sin hospital asignado».
- **Se conecta con:** Mis activos, Ficha del equipo, Detalle de la OT y Mis reportes.
- **Para la demo:** abre el portal de la biomédica: *Cumplimiento*, un hallazgo y descarga el acta más reciente.
  - *Pregunta probable: «¿El hospital ve las OT que aún están en curso?»* No, solo cuando están finalizadas.

### 8.2 Mis activos (`/mis-activos`)

- **Para qué sirve:** lista de los equipos del hospital.
- **Quién la ve:** CLI.
- **Qué se ve:** «Mis activos — Equipos y dispositivos de su institucion», búsqueda «Buscar por nombre, codigo, marca o modelo...» y tabla *Codigo, Nombre, Marca / Modelo, Ubicacion, Estado* con el enlace **Ver historial**.
- **Qué se puede hacer:** buscar y abrir la ficha.
- **Reglas importantes:** solo equipos de su alcance. No tiene botones de crear ni editar.
- **Se conecta con:** Ficha del equipo.
- **Para la demo:** busca por código y entra a un equipo.

### 8.3 Ficha del equipo para el hospital (`/mis-activos/:id`)

- **Para qué sirve:** ver un equipo, lo que viene y lo que se hizo, con su acta.
- **Quién la ve:** CLI.
- **Qué se ve:** nombre, estado y código; ficha (Ubicación, Tipo, Marca, Modelo, Serie); *Cobertura* (garantía y contrato vigentes); **Próximos mantenimientos**; **Hallazgos** del equipo; **Historial** (*Realizado, Programado, Mantenimiento, Orden* y el botón del acta).
- **Qué se puede hacer:** abrir la OT y descargar el acta.
- **Reglas importantes:** no ve OT en curso ni tareas anuladas (lo filtra el servidor). **No ve** medidores ni campos personalizados (los datos que no están en la ficha del hospital).
- **Se conecta con:** Mis activos y Detalle de la OT del hospital.
- **Para la demo:** abre un equipo con historial y baja el acta desde la fila.

### 8.4 Mis reportes (`/mis-reportes`)

- **Para qué sirve:** todas las actas del hospital.
- **Quién la ve:** CLI.
- **Qué se ve:** «Mis reportes» y una lista con título, N° de OT, fecha, hash SHA-256 abreviado y **Descargar PDF**. Vacío: «Aun no hay reportes disponibles».
- **Qué se puede hacer:** descargar.
- **Reglas importantes:** solo actas de OT **Finalizadas** de su alcance. El portal **no** tiene filtros ni búsqueda.
- **Se conecta con:** Reportes de administración (es la misma fuente) y Dashboard.
- **Para la demo:** descarga un acta.
  - *Pregunta probable: «¿Reciben el acta por correo?»* Sí, al contacto del hospital al completar la OT, además de tenerla aquí.

### 8.5 OT finalizada del hospital (`/historial/:id`)

- **Para qué sirve:** ver una visita ya cerrada con todo su soporte.
- **Quién la ve:** CLI (solo OT finalizadas de su alcance; otra responde «no se encontró»).
- **Qué se ve:**
  - Número de la OT, tipo, fecha de cierre, título y botón del acta.
  - **Equipos intervenidos (N)**, con **Ver checklist / Ocultar checklist** (respuestas, solo lectura).
  - **Hallazgos** (solo lectura, con el estado como lo entiende el hospital).
  - **Fotos** (sin las ocultas) y **Firmas**.
- **Qué se puede hacer:** leer y descargar el acta.
- **Reglas importantes:**
  - Es de solo lectura.
  - Las fotos ocultas por el revisor **no** aparecen.
  - No ve el historial de estados, repuestos ni costos.
- **Se conecta con:** Dashboard del hospital y Ficha del equipo.
- **Para la demo:** abre una OT con hallazgos y despliega el checklist.
  - *Pregunta probable: «¿Pueden ver quién corrigió algo?»* No. Esa constancia queda en la OT y en la auditoría, no en el acta ni en el portal.

---

## 9. Lo que puede sorprender en la demo

1. **La campana de notificaciones no aparece.** El servicio de push es un placeholder y no hay API de lectura. Lo que sí funciona son los correos.
2. **Dashboard → «Cumplimiento de protocolos»:** con un mes sin OT preventivas muestra **0% en rojo**. Es el cálculo mensual por OT, distinto al «Cumplimiento» del portal del hospital (12 meses, por tarea).
3. **MTTR incluye el tiempo en revisión.** Va de «Iniciar» a «Completar» (cuando aprueba el supervisor).
4. **Dashboard con caché de 5 minutos** en el servidor: si cambias un dato y vuelves, **Actualizar** puede mostrar lo anterior.
5. **Detalle de la OT, tarjeta *Progreso*:** el Avance queda en 0% y la Calificación en «—». Ninguna pantalla los llena.
6. **La firma del cliente no tenía pantalla** (el acta imprimía «No registrada»). Se corrigió el 2026-10-23: la pestaña Evidencia tiene un segundo panel. El celular necesita la APK de depuración nueva.
7. **Permisos de SUP con huecos:** puede dar de baja un equipo y cambiar su protocolo desde *Editar activo*, y reasignar una OT desde *Editar* (los botones específicos son solo ADMIN).
8. **Pantalla de Activos arranca con el primer hospital** seleccionado, no con todos.
9. **«Fuera de servicio» en un hallazgo es una marca**: el activo sigue en «Activo» hasta que alguien lo cambie.
10. **El aviso «Se le avisará al administrador» por distinta cantidad de tomas** solo se ve en la OT: no hay correo ni notificación.
11. **El técnico no ve el motivo del rechazo** (el historial de estados no está disponible para su rol).
12. **Cancelar una OT reemite las tareas como pendientes**, aunque el aviso diga «no se puede deshacer».
13. **Offline:** para trabajar sin red el técnico debe abrir **Mis órdenes con red** antes (ahí se descargan los checklists). Repuestos y cancelar no funcionan sin red.
14. **Auditoría:** el CSV exporta solo la página visible, y hallazgos, ubicaciones y tipos de tarea no están en el filtro de entidad.

Para repetir la demo con datos limpios, sigue `docs/DEMO.md` (base de demo con 2 hospitales, 14 equipos, 8 OT finalizadas con acta, 2 hallazgos pendientes, 1 contrato por vencer, 1 garantía y la OT-2026-00009 lista para ejecutar desde el celular).
