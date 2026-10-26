# Guía del presentador: review de sprint del 23 de octubre de 2026

Documentos de apoyo:
- la definición de cada pantalla, en `docs/GUIA-SECCIONES.md`;
- la lista de pruebas, en `docs/PRUEBAS-DEMO.md`;
- las cuentas de demo, en `docs/DEMO.md`, sección 3;
- la presentación, en `docs/presentacion/`.

---

## 1. Una hora antes: dejar todo listo

**En la computadora**
- [ ] Backend de demo arriba en el **8001**, con `DB_NAME=todogas_demo` (`backend-demo` en `.claude/launch.json`).
- [ ] Web de demo arriba en **http://localhost:5199** (`web` en `.claude/launch.json`). **No uses el 5174**: tu navegador tiene guardado ahí NutriFit y puede mostrarlo en vez de TodoGas.
- [ ] Prepara tres navegadores separados, para no tener que cerrar sesión en plena demo:
  - **Chrome normal:** administrador de demo;
  - **Chrome en otro perfil o en incógnito:** supervisor de demo;
  - **Edge:** biomédica de demo.

  Entra con las tres cuentas antes de empezar.
- [ ] En la pestaña del admin deja abierta un **acta PDF ya generada** de una OT finalizada. Es tu plan B si algo falla en vivo.
- [ ] Zoom del navegador al 125 % para que se lea en el proyector. Cierra pestañas y notificaciones (WhatsApp, Teams, correo).
- [ ] La presentación abierta, en modo presentador.

**En el celular**
- [ ] Conéctalo por USB y comprueba que lo ve la computadora:
  ```bash
  adb devices
  ```
- [ ] Abre el túnel hacia el backend de demo:
  ```bash
  adb reverse tcp:8000 tcp:8001
  ```
- [ ] Ajustes del teléfono:
  - **Opciones de desarrollador → Pantalla activa** (no se bloquea mientras carga);
  - modo **No molestar**;
  - brillo alto;
  - batería cargada.
- [ ] Instala la APK de depuración más reciente (trae el panel de la firma del cliente). Conserva la sesión y lo guardado:
  ```bash
  adb install -r frontend/android/app/build/outputs/apk/debug/app-debug.apk
  ```
- [ ] Abre la app, entra con el **técnico de demo**, entra a **Mis órdenes con red** (ahí se descargan los checklists para trabajar sin señal) y abre la **OT-2026-00009**, para que quede guardada en el teléfono.
- [ ] Recomendado: **duplica la pantalla del celular en la computadora** con *scrcpy* (gratis, open source). Así todos ven lo que haces en el teléfono en el proyector:
  ```bash
  winget install Genymobile.scrcpy
  ```
  ```bash
  scrcpy --stay-awake
  ```
  Si no lo quieres instalar, el plan B es la cámara del celular de alguien apuntando al tuyo, o pasar el teléfono.

**Si recreas la base de demo** (por ejemplo, porque ya ejecutaste la OT en un ensayo), sigue la sección 1 de `docs/DEMO.md` y vuelve a abrir la OT en el celular con red.

---

## 2. El cambio de flujo y por qué

Es el corazón de la presentación. En una frase:

> **"Dejamos de pedirles que trabajen como el sistema, y pusimos el sistema a trabajar como ustedes ya trabajan en Fracttal."**

### Antes (hasta septiembre)

1. Un **plan** tenía **un checklist** y **una frecuencia**, compartidos por todos sus equipos.
2. Un proceso nocturno **creaba solo una OT por equipo** cuando llegaba la fecha.
3. Cada OT cubría **un solo equipo**.
4. El técnico llenaba el checklist. Si algo estaba mal, el admin **solo podía devolverle la OT**.
5. El acta salía con la **hora de aprobación** como fecha de intervención, y con el técnico **asignado** (no necesariamente el que la hizo).
6. Los hospitales **no tenían acceso**.
7. Un problema visto durante un preventivo quedaba como **texto libre** en la OT.

### Ahora

1. **Protocolo por equipo.** Cada protocolo tiene tareas, y cada tarea tiene su propio checklist y su activador:
   - por fecha (cada 6 meses);
   - por evento;
   - por medidor: cada N horas o cuando la presión baja de 50 PSI.
2. El protocolo genera **tareas pendientes**, no OT.
3. El **planificador** abre *Tareas pendientes* y decide:
   - **agrupar varias en una OT**: una visita por piso, como en Fracttal;
   - **reprogramar** con una causa obligatoria, que queda registrada;
   - **anular** con una nota.
4. Una OT cubre **varios equipos**, cada uno con su checklist y sus fotos. Bloques repetibles: "Toma × 20" se define una sola vez.
5. El técnico la hace **en el celular, incluso sin señal**:
   - responde Sí/No/N/A, lecturas en PSI y GPS;
   - toma fotos con etiqueta **Antes/Después**;
   - registra **hallazgos**;
   - captura las firmas;
   - todo se sube solo al volver la señal.
6. **Revisión:** el supervisor o admin **corrige** respuestas, fotos y la **fecha de intervención**, dejando constancia ("Corregido por…" y el valor anterior en auditoría). Luego aprueba.
7. **El acta dice la verdad:**
   - la hora real del trabajo, tomada del teléfono;
   - quién lo hizo;
   - las tres firmas: realizado, validado y aceptado;
   - las fotos agrupadas en Antes y Después;
   - los hallazgos.

   Además se configura con interruptores y lleva un sello de integridad.
8. Los **hallazgos** van a una bandeja del planificador, que los convierte en correctivos. Si es crítico, **al hospital le llega un correo**.
9. La **biomédica del hospital** entra a su portal de solo lectura y ve sus equipos, el historial, las actas, los próximos mantenimientos, los hallazgos y el contrato.

### Por qué cambió

| Cambio | De dónde salió |
|---|---|
| Protocolos por equipo y tareas pendientes | Audio de revisión: "100 tomas se dividen en 5 activos, esos 5 activos tienen 5 protocolos… Alma Mater tiene 1.500 tomas". Además, en su Fracttal la generación automática de OT está **apagada**: arman las OT a mano desde las pendientes. |
| OT con varios equipos | Su patrón real en Fracttal: una OT por piso (alarma + caja de válvulas + tomas). |
| Bloques repetibles "Toma × N" | En Fracttal copian y pegan las 9 preguntas por cada toma. |
| Admin ejecuta y corrige en revisión | "Tengo que hacer reportes donde el técnico no va", y "que el administrador también pueda modificar el checklist y la evidencia". |
| Acta con datos reales y configurable | Pidieron quitar la fecha y el técnico porque **salían mal**. Arreglamos el dato y además el acta se configura con interruptores, como las "Impresiones de OT" de Fracttal. |
| Cuentas para hospitales | En Fracttal, 4 biomédicas ya entran con "Solo lectura con historial". Era la función más valiosa que no teníamos. |
| Hallazgos | Fracttal imprime "Hallazgos encontrados y reportados". Aquí un preventivo genera su correctivo sin perder el rastro. |
| Contratos y garantías | En su Fracttal hay 22 contratos con vigencia. Ahora avisan a 60 y 30 días. |
| **Este sprint:** sin costo, fecha editable, sin Foto/Firma en el checklist, Antes/Después, tablero nuevo, regla de baja | Las decisiones que tomaron en la revisión pasada. |

### Lo que cambió en este último tramo (para la diapositiva "lo que pidieron")
- **Costo de la OT:** ya no aparece en ninguna parte.
- **Fecha de intervención:** se corrige en revisión, con constancia. El acta sale con la corregida.
- **Campos Foto y Firma del checklist:** ya no se pueden agregar, porque van en la OT. Los checklists viejos siguen funcionando.
- **Etiqueta Antes/Después:** se marca con un toque al tomar la foto, también sin señal. El acta agrupa así.
- **Tablero:** primero lo que pide acción (equipos vencidos, hallazgos críticos, OT vencidas, contratos). Luego el estado de los equipos, la planificación de 6 meses, los hallazgos por severidad y las OT por tipo.
- **Dar de baja un equipo:** antes de confirmar, el sistema dice cuántas tareas se anulan. Al reactivarlo, se reabren.
- **Además:**
  - seguridad revisada (cada hospital ve solo lo suyo, en todas las pantallas);
  - fotos pesadas que se comprimen sin rechazarse;
  - aviso claro con "Reintentar" si algo no sube desde el teléfono;
  - el logo de TodoGas en la app;
  - la app de producción 1.1.0 lista;
  - el sistema preparado para la nube.

---

## 3. Demo paso a paso (~18 minutos)

Cuenta todo como **un día de trabajo** de una persona real. Eso le da sentido a cada clic.

### Escena 1: el lunes por la mañana, el administrador (3 min)
*Navegador del admin.*
1. **Dashboard.**
   - *Di:* "Lo primero que ven al entrar es lo que pide acción."
   - Muestra la fila **Requiere atención**: 4 equipos vencidos, 1 hallazgo crítico (el compresor fuera de servicio) y el contrato por vencer.
2. Haz clic en **"Activos con mantenimiento vencido"**: la lista muestra el mismo número. Elige antes "Clínica Demo Norte" en el filtro del tablero, para que los números cuadren.
3. **Planificación de 6 meses.** *Di:* "Esto es lo que viene: así planean la semana."
4. **Hallazgos → el crítico.** Conviértelo en **correctivo**. *Di:* "El hallazgo del técnico se vuelve trabajo, y queda quién lo decidió."

5. **Usuarios → Técnico Demo → Ver:** muestra la sección **Permisos adicionales**.
   - *Di:* "Lo que pidieron en la primera revisión: un técnico de confianza puede hacer más. Por ejemplo, le marco *Revisar y aprobar*. Los permisos solo suman, valen solo en su hospital y cada cambio queda en la auditoría."
   - **No guardes**: cierra sin guardar, para no cambiar la demo. Si lo guardas, quítalo al terminar.

### Escena 2: el planificador arma la visita (3 min)
1. **Protocolos → "Mant. salidas de gases":** cada 6 meses, **Toma × 5**.
   - *Di:* "Antes copiaban 9 preguntas por cada toma; aquí se define una vez."
   - Muestra también **"Alarma de presión"**, con el activador **< 50 PSI**.
2. **Tareas pendientes:**
   - **reprograma** una con la causa "NO DISPONIBLE" y enseña que queda registrada;
   - muestra la tarea que **se abrió sola por presión baja (44 PSI)** en el Hospital Demo Sur.
3. *(Opcional)* **Activos → un equipo → Dar de baja:** muestra el aviso "Se anularán N tareas" y **cancela**. *Di:* "Antes de confirmar, el sistema les dice qué va a pasar."

### Escena 3: el técnico en el sótano de Urgencias (6 min), el momento más fuerte
*Celular, idealmente duplicado en la pantalla.*
1. Abre la **OT-2026-00009**: Clínica Demo Norte, Piso 1 Urgencias, 2 tomas de oxígeno.
   - Muestra **"Ubicación de la visita"**: "Clínica Demo Norte › Bloque A › Piso 1 - Urgencias", con su dirección.
   - Sobre el checklist de cada equipo sale la tarjeta **"Dónde está"**.
   - *Di:* "Lo pidieron así: ubicación en palabras, no coordenadas."
   - Sin la cuenta de Google, "Ver mapa" abre un enlace a Google Maps en vez del mapa dibujado; es la decisión 7 de hoy.

   Luego pulsa **Iniciar**.
2. **Corta la red de verdad:**
   - activa el **modo avión** en el teléfono;
   - en la computadora:
     ```bash
     adb reverse --remove tcp:8000
     ```
   - *Di:* "Estamos en un sótano sin señal."
3. Llena el checklist del primer equipo:
   - las **5 tarjetas de Toma**; responde una con **Sí/No/N/A**, la **presión en PSI** y una observación;
   - el **GPS**;
   - agrega una **sexta toma**. *Di:* "Encontró una más que la planeada; queda registrado y el supervisor ve la diferencia en la OT." No digas que le llega un aviso al administrador: el texto de la pantalla lo sugiere, pero no se envía nada.
4. Toma una **foto** y márcala **Antes**; luego otra marcada **Después**. *Di:* "Un toque, y en el acta salen agrupadas."
5. Reporta un **hallazgo**, severidad alta, con foto, y otro **resuelto en sitio**.
6. **Cierra la app del todo y vuélvela a abrir:** todo sigue ahí. *Di:* "No se pierde nada aunque se apague el teléfono."
7. **Vuelve la red:**
   - en la computadora:
     ```bash
     adb reverse tcp:8000 tcp:8001
     ```
   - quita el modo avión.

   La app **sincroniza sola**. *Di:* "Apenas sale del sótano, todo sube."
8. Pestaña **Evidencia**: la **firma del técnico** y la de **quien recibe en el hospital**, cada una con su nombre. Luego **Enviar a revisión**.

### Escena 4: el supervisor revisa (3 min)
*Navegador del supervisor.*
1. Abre la OT en revisión. *Di:* "No hay costos en la OT, como pidieron."
2. **Corrige una respuesta.** Queda "Corregido por…", y el valor anterior va a la auditoría.
3. En **Fechas**, **corrige la fecha de intervención**:
   - prueba poner el fin antes del inicio, para que vean la validación;
   - después guarda una fecha válida.
4. Cambia la etiqueta de una foto u **oculta** una mala. *Di:* "Se oculta del acta, nunca se borra."
5. **Aprueba** y abre el **acta PDF**. Muestra:
   - la hora real y quién lo hizo;
   - las tres firmas;
   - las fotos **Antes / Después**;
   - los hallazgos;
   - el mapa o las coordenadas.

### Escena 5: la biomédica del hospital (2 min)
*Edge, con la cuenta de la biomédica.*
1. Solo ve **Clínica Demo Norte**: su cumplimiento, lo vencido y los próximos mantenimientos.
2. Abre el equipo recién atendido: historial, **el acta de hoy**, fotos y hallazgos. No ve "Corregido por" ni costos.
3. Ve su **contrato** y lo descarga. *Di:* "Lo mismo que hoy tienen las 4 biomédicas en Fracttal, sin licencias extra."

### Cierre (1 min)
Vuelve a la presentación: **la nube, los precios y las decisiones de hoy.**

---

## 4. Recomendaciones para que salga bien

**Preparación**
1. **Ensaya la demo completa una vez hoy**, cronometrada. Si ejecutas la OT en el ensayo, **recrea la base de demo** después (sección 1 de `docs/DEMO.md`) y vuelve a abrir la OT en el celular con red.
2. **Ten el plan B abierto:**
   - el acta PDF ya generada;
   - unas capturas de las pantallas clave, por si el proyector, el cable o el teléfono fallan.

   No improvises con algo que no ensayaste.
3. **Duplica el celular con scrcpy.** El modo sin red es lo que más impresiona, y nadie lo ve si el teléfono está en tu mano.

**Durante la demo**
4. **Habla de su trabajo, no de la tecnología.** Di "el técnico en el sótano de Urgencias", no "sincronización offline". Usa sus palabras: protocolo, toma, biomédica, acta, Invima.
5. **Empieza por lo que pidieron.** Abre con "lo que nos pidieron en la revisión pasada ya está", y muéstralo rápido. Genera confianza para todo lo demás.
6. **Una sola historia, una sola OT.** No saltes entre pantallas sin razón; cada escena le da paso a la siguiente.
7. **Deja silencios después de lo fuerte:** el modo avión, el acta y el portal de la biomédica. Pregunta "¿así lo hacen hoy?" y escucha.
8. **Anota todo lo que digan**, con nombre de quién lo pidió. Mejor si alguien más toma notas. Al final repite los pedidos en voz alta para confirmarlos.

**Lo que no hay que hacer**
9. **No prometas fechas de salida en vivo.** Di: "Con las decisiones de hoy, la infraestructura queda en 1 a 2 días; la importación de Fracttal y la prueba con ustedes son lo que define la fecha."
10. **No muestres** el panel `/admin/` de Django, la consola, ni errores técnicos. Si algo falla, di "eso lo reviso después" y pasa al plan B.
11. **Cierra con las decisiones.** Lleva la lista de las 6 decisiones y no termines la reunión sin respuesta, o sin un responsable y una fecha para cada una.

---

### Trampas conocidas: qué no tocar en vivo

Salen de la revisión de cada pantalla (`docs/GUIA-SECCIONES.md`):
- **Tarjeta "Progreso" de la OT:** "Avance" queda en 0 % y "Calificación" en "—" (nada los llena). No te detengas ahí.
- **"Cumplimiento de protocolos" del tablero:** sale en 0 % y en rojo si en el mes aún no hay OT preventivas finalizadas. Si preguntan: "es el cumplimiento de este mes; sube al aprobar las visitas".
- **El tablero guarda sus números 5 minutos.** Después de aprobar la OT, no vuelvas al tablero esperando ver el cambio: tarda y "Actualizar" no lo fuerza.
- **Cumplimiento del portal frente al del tablero:** el portal usa tareas de los últimos 12 meses y el tablero las OT del mes. No compares las dos cifras en vivo.
- **"Fuera de servicio" en un hallazgo** es una marca para el planificador y el hospital: no cambia sola el estado del equipo. No digas que lo hace.
- **No demuestres "rechazar" una OT:** el técnico no ve el motivo del rechazo, porque el historial dice "No disponible para tu rol".
- **"Cancelar OT":** el aviso dice "no se puede deshacer", pero las tareas vuelven a pendientes. No lo muestres.
- **Activos** arranca con el primer hospital elegido, no con todos.

## 5. Preguntas probables y qué responder

| Pregunta | Respuesta |
|---|---|
| ¿Cuándo lo podemos usar? | Con las decisiones de hoy, la infraestructura se crea en 1 a 2 días. Después hay que importar los datos de Fracttal (lo más grande que falta) y hacer una prueba con ustedes antes de un piloto en un hospital. |
| ¿Cuánto cuesta al mes? | US$71 la opción recomendada, sin IVA. Con la cuenta a nombre de TodoGas, el IVA sale neutro por retención (que lo confirme su contador). No hay licencias por usuario: los hospitales entran sin costo extra. |
| ¿Y si se cae internet o el servidor? | El técnico sigue trabajando en el celular y todo sube después. Los datos se respaldan a diario, con vuelta a cualquier minuto de los últimos 30 días. |
| ¿Se pueden borrar o cambiar las actas? | No. Una OT aprobada no se puede editar, el PDF lleva un sello de integridad y el almacenamiento impide borrarlo durante los años de retención que ustedes definan. |
| ¿Qué pasa con lo que tenemos en Fracttal? | Se importa: hospitales, equipos, protocolos e historial. Es el siguiente gran paso y lo hacemos sobre el sistema ya terminado. |
| ¿Por qué no se crean solas las OT? | Porque en su Fracttal esa opción está apagada: ustedes las arman desde las pendientes. Si la quieren, se activa. |
| ¿Puede el técnico tener más permisos? | Hoy los roles son fijos y operan como usuario único. La matriz de permisos por usuario está planeada para cuando repartan el trabajo. |
| ¿Notificaciones al celular? | La app ya está preparada. Falta conectarla al servicio de notificaciones; está en la lista de pendientes. |
| ¿Y los códigos de activo? | Quedaron aplazados por decisión de ustedes. Cuando definan el sistema, se aplica. |

---

## 6. Lo que todavía no existe (para no prometerlo)
- El mapa dibujado y la dirección automática del GPS: esperan la cuenta de Google de TodoGas. Sin ella se ven la ruta, la dirección y un enlace a Google Maps.
- La importación desde Fracttal.
- Notificaciones push al celular (el servidor no las envía).
- Inventario por institución (almacenes).
- "Enviar a revisión al firmar".
- El grupo del equipo (eléctricas, neumáticas).
- La matriz de permisos por usuario.
- La infraestructura en AWS: está escrita y probada, pero **no está desplegada**. La app de producción no conecta hasta que lo esté.
