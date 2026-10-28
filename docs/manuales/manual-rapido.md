# TodoGas CMMS

## Manual de uso rápido

**Versión 1.0 · 28 de octubre de 2026**

Una consulta corta por perfil. Para el detalle de cada pantalla, vea el **Manual de uso completo y detallado**.

Los botones y pestañas van entre comillas «así», tal como aparecen en pantalla. Los ejemplos usan datos de demostración («Clínica Demo Norte», «OT-2026-00009»).

## Índice

1. [Para todos: entrar y dejar lista su cuenta](#1-para-todos-entrar-y-dejar-lista-su-cuenta)
2. [Administrador](#2-administrador)
3. [Supervisor](#3-supervisor)
4. [Técnico (app Android)](#4-técnico-app-android)
5. [Cuenta de hospital](#5-cuenta-de-hospital)
6. [Si algo falla](#6-si-algo-falla)

---

## 1. Para todos: entrar y dejar lista su cuenta

### Entrar

1. Abra el navegador (o la app «TodoGas» en Android) y escriba su correo y su contraseña.
2. Pulse «Iniciar sesión».
3. Con la contraseña temporal que le llegó por correo, el sistema abre «Cambia tu contraseña»: escriba la actual, la nueva (mínimo 8 caracteres, una mayúscula, un número y un carácter especial) y pulse «Guardar nueva contraseña».
4. La primera vez, lea el aviso de privacidad y pulse «Acepto».

> [CAPTURA: Inicio de sesión con los campos «Correo electrónico» y «Contraseña» y el botón «Iniciar sesión» (versión pequeña) — Sin sesión, Web]

Con 5 intentos fallidos la cuenta se bloquea **30 minutos**. Si olvidó la contraseña, pídale al Administrador que la restablezca.

### Guardar su firma (Administrador, Supervisor y Técnico)

1. Abra «Mi perfil» → «Mi firma».
2. Dibuje su firma y pulse «Guardar mi firma».

Hágalo **con señal** y antes de salir a campo. Sin firma guardada, el Supervisor y el Administrador no pueden aprobar órdenes.

> [CAPTURA: Sección «Mi firma» de «Mi perfil» con el recuadro «Dibuja tu firma» y el botón «Guardar mi firma» (versión pequeña) — Supervisor, Web]

---

## 2. Administrador

### 2.1 Crear un hospital y armar sus ubicaciones

1. Entre a «Hospitales» → «+ Nuevo hospital».
2. Llene «Nombre» y «Código», y en «Contacto» el **correo** (ahí llega el acta). Pulse «Crear hospital».
3. En la fila del hospital pulse «Ubicaciones» → «Nueva ubicación».
4. Escriba el nombre, elija el «Tipo» y, para una sububicación, «Ubicada dentro de». Pulse «Crear ubicación» (o «Guardar y crear otra»).

> [CAPTURA: Árbol de ubicaciones de «Clínica Demo Norte» (versión pequeña) — Administrador, Web]

### 2.2 Registrar un equipo

1. Entre a «Activos» → «+ Nuevo activo».
2. Elija el «Hospital» y la «Ubicación», y escriba el «Nombre del activo».
3. Pulse «Generar» para el «Código interno».
4. Elija el «Protocolo» y pulse «Siguiente».
5. Llene la ficha técnica y pulse «Crear activo».

Para traer muchos equipos de Fracttal: «Activos» → «Importar desde Fracttal» → suba el Excel → «Revisar archivos» → «Importar…» → «Sí, importar».

> [CAPTURA: Formulario «Registrar activo» paso «Identificación» (versión pequeña) — Administrador, Web]

### 2.3 Crear un protocolo y asignarlo

1. Entre a «Protocolos» → «Nuevo protocolo». Escriba el nombre y pulse «Crear protocolo».
2. En la pestaña «Tareas» pulse «Agregar tarea».
3. Escriba el nombre, elija el tipo y el «Checklist», y en «Cuándo se hace» la frecuencia. Pulse «Agregar tarea».
4. En la pestaña «Activos» pulse «Asignar activos» (o «Asignar ubicaciones»).
5. Marque los equipos, escriba la «Fecha de la primera tarea (opcional)» y confirme.

> [CAPTURA: Protocolo «Mant. salidas de gases» con la pestaña «Tareas» y su frecuencia (versión pequeña) — Administrador, Web]

### 2.4 Armar y asignar una orden

1. Entre a «Tareas pendientes» y filtre por hospital.
2. Marque las tareas de una misma visita.
3. Pulse «Crear OT», elija «Asignado a» y «Fecha de la visita».
4. Pulse crear. Elija «Ver la OT».

Para un correctivo a mano: «Ordenes de trabajo» → «+ Nueva OT». Para cambiar de técnico: en la OT, «Reasignar».

> [CAPTURA: Ventana «Crear OT» con técnico y fecha (versión pequeña) — Administrador, Web]

### 2.5 Revisar y aprobar una orden

1. En «Ordenes de trabajo», filtre por «En revisión» y abra la OT.
2. Revise «Checklist» y «Evidencia». Para corregir, pulse «Corregir respuestas».
3. Pulse «Completar» → «Aprobar y firmar».
4. Si no está de acuerdo, pulse «Rechazar», escriba el motivo y «Confirmar rechazo».

El acta se genera y llega al hospital por correo.

> [CAPTURA: OT «En revisión» con «Completar» y «Rechazar» (versión pequeña) — Administrador, Web]

### 2.6 Decidir hallazgos

1. Entre a «Hallazgos», pestaña «Por decidir».
2. Pulse «Convertir en correctivo» (elija fecha y pulse «Crear correctivo») o «Descartar» (escriba el motivo).

> [CAPTURA: Bandeja «Hallazgos» con «Por decidir» (versión pequeña) — Administrador, Web]

### 2.7 Crear un usuario

1. Entre a «Usuarios» → «Nuevo usuario».
2. Escriba nombre, apellido y correo, y elija el rol. Para una cuenta de hospital, elija el «Hospital».
3. Si quiere limitar su alcance o darle «Permisos adicionales», márquelos.
4. Pulse «Crear usuario». La contraseña temporal le llega por correo.

Para recuperar una contraseña: en la fila, el botón de la llave («Restablecer contrasena») → «Restablecer».

> [CAPTURA: Ventana «Nuevo usuario» (versión pequeña) — Administrador, Web]

### 2.8 Actas, formato y auditoría

1. «Reportes»: filtre y pulse «Descargar». Marque varias y pulse «Reenviar por correo» (hasta 50).
2. «Formato del acta»: prenda o apague campos y pulse «Guardar cambios».
3. «Auditoria»: filtre y pulse «Exportar CSV».

> [CAPTURA: Pantalla «Reportes» con la tabla de actas (versión pequeña) — Administrador, Web]

---

## 3. Supervisor

El Supervisor planifica, revisa y aprueba. No ve «Usuarios», «Formato del acta», «Tipos de tarea» ni «Auditoria». Si está limitado a un hospital o a una parte, solo ve lo de su alcance.

### 3.1 Ver cómo va todo

1. Entre a «Dashboard».
2. Elija el hospital y el periodo, y pulse «Actualizar».
3. Pulse una tarjeta de «Requiere atención» para ir a su lista.

> [CAPTURA: «Dashboard» con «Requiere atención» (versión pequeña) — Supervisor, Web]

### 3.2 Crear una orden desde pendientes

1. Entre a «Tareas pendientes» y filtre por hospital.
2. Marque las tareas de una misma visita (de un solo hospital).
3. Pulse «Crear OT», elija el técnico y la fecha, y confirme.

> [CAPTURA: «Tareas pendientes» con tareas marcadas y el botón «Crear OT» (versión pequeña) — Supervisor, Web]

### 3.3 Reprogramar o anular una tarea

1. Marque la tarea en «Tareas pendientes».
2. Para moverla, pulse «Reprogramar», elija la «Nueva fecha» y la «Causa».
3. Si ya no toca, pulse «Anular» y escriba el motivo.

> [CAPTURA: Ventana «Reprogramar» con la «Causa» (versión pequeña) — Supervisor, Web]

### 3.4 Revisar y aprobar

1. En «Ordenes de trabajo», filtre por «En revisión» y abra la OT.
2. Revise el checklist y las fotos. Con «Corregir respuestas» cambia lo que haga falta; con «Ocultar del acta» oculta una foto mala.
3. Pulse «Completar» → «Aprobar y firmar» (necesita su firma guardada).
4. Si hay que repetir, pulse «Rechazar», escriba el motivo y avise al técnico: él no ve el motivo.

> [CAPTURA: Ventana «Aprobar orden» con la firma guardada (versión pequeña) — Supervisor, Web]

### 3.5 Decidir un hallazgo

1. Entre a «Hallazgos» → «Por decidir».
2. Pulse «Convertir en correctivo» o «Descartar».

> [CAPTURA: Hallazgo en «Por decidir» con sus dos botones (versión pequeña) — Supervisor, Web]

### 3.6 Dar de baja o reactivar equipos

1. En «Activos», marque los equipos (hasta 200).
2. Pulse «Dar de baja» o «Reactivar».
3. Lea el resumen de lo que pasará. Al reactivar, elija «Desde hoy (recomendado)» o «Según su último mantenimiento».
4. Confirme y pulse «Entendido».

> [CAPTURA: Barra «N activos seleccionados» con «Dar de baja» y «Reactivar» (versión pequeña) — Supervisor, Web]

### 3.7 Descargar un acta

1. Entre a «Reportes».
2. Filtre por «Hospital» o «N° OT» y pulse «Filtrar».
3. Pulse «Descargar».

---

## 4. Técnico (app Android)

### 4.1 Antes de salir

1. Abra la app **con señal**.
2. Entre a «Mis ordenes» y espere unos segundos: se descargan sus órdenes.
3. Abra la orden del día una vez y revise que su firma esté guardada («Mi perfil»).

> [CAPTURA: «Mis órdenes de trabajo» con la tarjeta de «OT-2026-00009» (versión pequeña) — Técnico, App Android]

### 4.2 Iniciar y llenar el checklist

1. Pulse «Iniciar OT».
2. En la pestaña «Checklist» pulse «Iniciar checklist».
3. Responda cada campo («Sí», «No» o «N/A»). Se guarda solo al salir del campo.
4. Si hay tomas, pulse «Siguiente: Toma 2». Si hay más tomas, «Agregar toma».
5. Pulse «Finalizar checklist».

> [CAPTURA: Checklist en la app con campos respondidos (versión pequeña) — Técnico, App Android]

### 4.3 Dejar un punto pendiente

1. Bajo el campo, pulse «Marcar pendiente».
2. Escriba por qué no se pudo revisar y pulse «Dejar pendiente».
3. Cuando pueda, responda el campo: el pendiente se va solo.

Con pendientes, la orden no se puede enviar a revisión.

> [CAPTURA: Punto con la franja «Pendiente — no se pudo revisar» (versión pequeña) — Técnico, App Android]

### 4.4 Tomar fotos

1. Abra la pestaña «Evidencia».
2. Pulse «Tomar foto» y tome la foto.
3. Elija «Antes» o «Después», y el equipo en «¿De qué activo es?».
4. Pulse «Subir foto».

Hace falta al menos una foto. Sin GPS, sube igual.

> [CAPTURA: «Agregar foto» con «Antes», «Después» y «Subir foto» (versión pequeña) — Técnico, App Android]

### 4.5 Firmar

1. En «Evidencia», sección «Agregar firma», panel «Firma del técnico»: pulse «Usar mi firma guardada».
2. En el panel «Firma de quien recibe en el hospital»: pase el celular, que la persona firme, escriba su nombre y pulse «Guardar firma».

> [CAPTURA: Los dos paneles de firma (versión pequeña) — Técnico, App Android]

### 4.6 Reportar un hallazgo

1. Abra la pestaña «Hallazgos» → «Reportar hallazgo».
2. Escriba «Qué encontraste» y elija la «Severidad».
3. Marque «El equipo queda fuera de servicio» o «Lo resolví aquí mismo» si aplica.
4. Pulse «Reportar».

> [CAPTURA: Ventana «Reportar hallazgo» (versión pequeña) — Técnico, App Android]

### 4.7 Enviar a revisión

1. Pulse «Enviar a revision».
2. Si está desactivado, lea «Para enviar a revisión falta: …» y complete lo que diga (checklists, una foto, una firma).

> [CAPTURA: Botón «Enviar a revision» con el aviso de lo que falta (versión pequeña) — Técnico, App Android]

### 4.8 Trabajar sin señal

- Con la franja «Sin conexion — Modo offline activo» **puede seguir**: checklist, fotos, firmas, hallazgos y «Enviar a revision».
- Todo se envía **solo** cuando vuelve la señal.
- Si aparece «Hay N elementos que no se pudieron enviar», pulse «Reintentar».
- Sin señal **no** puede: registrar repuestos, cancelar, ni registrar su firma guardada.

> [CAPTURA: Franja «Sin conexion — Modo offline activo» (versión pequeña) — Técnico, App Android]

---

## 5. Cuenta de hospital

### 5.1 Ver el resumen de mi hospital

1. Entre con su correo y contraseña.
2. En «Dashboard» vea los equipos, el cumplimiento, los próximos mantenimientos, los hallazgos y los contratos.

> [CAPTURA: «Dashboard» del hospital (versión pequeña) — Cuenta de hospital, Web]

### 5.2 Buscar un equipo y ver su historial

1. Entre a «Mis activos».
2. Busque por nombre, código, marca o modelo.
3. Pulse «Ver historial». Filtre con «Todos», «Preventivo», «Correctivo» u «Otro».

> [CAPTURA: Ficha de equipo con el historial y los filtros por tipo (versión pequeña) — Cuenta de hospital, Web]

### 5.3 Ver lo que viene

1. En «Dashboard», vea «Próximos mantenimientos».
2. En la ficha de un equipo, vea los de ese equipo. «Vencido» indica que la fecha ya pasó.

### 5.4 Descargar un acta

1. Entre a «Mis reportes».
2. Pulse «Descargar PDF» en el acta que quiera.

> [CAPTURA: «Mis reportes» con «Descargar PDF» (versión pequeña) — Cuenta de hospital, Web]

### 5.5 Ver un hallazgo y su estado

1. En «Dashboard» o en la ficha del equipo, vea «Hallazgos».
2. El estado puede ser «Resuelto», «Corrección programada», «Pendiente de corrección» o «Descartado».

### 5.6 Ver mis contratos

1. En «Dashboard», baje a «Contratos y garantías».
2. Vea la vigencia, qué cubre y abra el documento.

---

## 6. Si algo falla

| Problema | Qué hacer |
|---|---|
| «Cuenta bloqueada temporalmente» | Espere 30 minutos. |
| Olvidé la contraseña | Pida al Administrador que la restablezca. |
| «Para aprobar necesitas registrar tu firma» | «Ir a Mi perfil» y guarde su firma (con señal). |
| «Enviar a revision» desactivado | Lea «Para enviar a revisión falta: …». |
| «Esta OT no está descargada en el teléfono» | Abra «Mis ordenes» con señal. |
| «Hay N elementos que no se pudieron enviar» | Pulse «Reintentar». |
| El hospital no recibe el acta | Revise el correo de contacto en «Hospitales» y reenvíe el acta. |
