# Prueba completa antes de la demo

Recorrido para comprobar todo, en el orden en que conviene mostrarlo. Usa la
base `todogas_demo` (ver `docs/DEMO.md`): las cuentas y contraseñas de prueba
están en la sección 3 de ese archivo.

Marca cada casilla al probarla. Si algo falla, anota el paso y la pantalla.

## 0. Preparación (5 min)

- [ ] Backend de demo arriba en `127.0.0.1:8001`, con `DB_NAME=todogas_demo`.
- [ ] Web de demo en http://localhost:5199, que usa la API del 8001.
- [ ] Celular conectado por USB, con la depuración USB autorizada:
  - `adb devices` lo muestra como `device`;
  - `adb reverse tcp:8000 tcp:8001` está activo (comprobar con `adb reverse --list`).
- [ ] En el celular, Opciones de desarrollador → **Pantalla activa**: así no se bloquea mientras carga.
- [ ] La app abre con el logo de TodoGas en el ícono y en la pantalla de carga.

## 1. Técnico, en el celular (15 min)

Entra con el **técnico de demo**.

1. [ ] La lista muestra la **OT-2026-00009** pendiente (Clínica Demo Norte, Piso 1 - Urgencias, 2 tomas de oxígeno).
2. [ ] Ábrela **con red**. Desde ese momento queda guardada en el teléfono para trabajar sin señal.
3. [ ] Pulsa **Iniciar**. El estado pasa a "En progreso".
4. [ ] En el primer equipo, abre el checklist "Mantenimiento de tomas":
   - [ ] aparecen **5 tarjetas de "Toma"** (bloque repetible, Toma × 5);
   - [ ] responde una toma con **Sí / No / N/A**, la **presión en PSI** y una observación;
   - [ ] el campo **GPS** toma la ubicación (acepta el permiso);
   - [ ] **no hay** campos de Foto ni Firma dentro del checklist: ahora van en la OT;
   - [ ] agrega una sexta toma ("encontré una más") y verifica que avise de la diferencia con lo planificado.
5. [ ] Toma una **foto** de evidencia y márcala **Antes**. Toma otra y márcala **Después**. Es un toque en el selector.
6. [ ] Reporta un **hallazgo**:
   - severidad **Alta**;
   - con una foto: el selector Antes/Después **no** aparece en las fotos de hallazgo;
   - otro hallazgo marcado como **resuelto en sitio**.
7. **Prueba sin red** (lo más vistoso de la demo):
   - [ ] Activa el **modo avión** en el celular y corta el túnel en la computadora:
     ```bash
     adb reverse --remove tcp:8000
     ```
   - [ ] Completa el segundo equipo, toma una foto y firma. Todo debe guardarse ("se enviará cuando vuelva la señal").
   - [ ] Cierra la app del todo y vuelve a abrirla sin red. Lo hecho sigue ahí.
   - [ ] Vuelve a conectar:
     ```bash
     adb reverse tcp:8000 tcp:8001
     ```
     Luego quita el modo avión. La app sincroniza sola y desaparecen los pendientes.
8. [ ] Captura la **firma del técnico** y la **firma del cliente**.
9. [ ] Pulsa **Enviar a revisión**.

Si algún elemento queda "requiere atención" (aviso rojo con el mensaje del
servidor), prueba **Reintentar**. No hay botón de descartar, a propósito: es
evidencia.

## 2. Supervisor o administrador, en la web (15 min)

Entra en http://localhost:5199 con el **supervisor de demo** (o el admin).

### Revisión y aprobación de la OT del técnico
1. [ ] Órdenes de trabajo → **OT-2026-00009** (En revisión).
2. [ ] **No aparece el costo** en ninguna parte. La tarjeta se llama "Progreso".
3. [ ] **Corrige una respuesta** del checklist. Debe quedar "Corregido por …"; quien respondió sigue siendo el técnico.
4. [ ] En la galería, **cambia la etiqueta** de una foto (Antes ↔ Después) y **oculta** otra del acta. La foto oculta no se borra.
5. [ ] En la tarjeta **Fechas**, **corrige la fecha de intervención**:
   - [ ] prueba poner el fin antes del inicio: lo marca en el campo y no deja guardar;
   - [ ] prueba una fecha en el futuro: lo rechaza;
   - [ ] guarda una fecha válida: queda "Corregido por …";
   - [ ] "Quitar la corrección" vuelve a lo que registró el técnico (y luego vuelve a ponerla para el acta).
6. [ ] **Aprueba** la OT. Se genera el **acta PDF**. Ábrela y revisa:
   - [ ] la fecha y la duración son las corregidas, sin marca;
   - [ ] las fotos van agrupadas en **Antes** y **Después** (la oculta no sale);
   - [ ] los hallazgos salen como "encontrado y corregido" o "pendiente";
   - [ ] no hay costo.

### Tablero
7. [ ] **Dashboard**:
   - [ ] arriba, "Requiere atención": activos vencidos, hallazgos críticos, OT vencidas y contratos. Cada tarjeta lleva a su lista;
   - [ ] **Estado de activos**: el número de la tarjeta coincide con la lista a la que lleva (prueba "Vencido");
   - [ ] **Planificación**: tareas por mes; la barra de un mes abre Tareas pendientes filtradas;
   - [ ] hallazgos por severidad y OT por tipo.
   - Con "Todos los hospitales", la lista de activos elige un hospital por su cuenta. Para que los números cuadren, **elige "Clínica Demo Norte"** en el tablero antes de hacer clic.

### Hallazgos, contratos y protocolos
8. [ ] Mantenimiento → **Hallazgos**: el crítico (compresor fuera de servicio). **Conviértelo en correctivo** y descarta el otro con un motivo.
9. [ ] Activos → **Contratos y garantías**: el contrato que vence en ~25 días.
10. [ ] **Protocolos**: "Mant. salidas de gases" (cada 6 meses, Toma × 5) y "Alarma de presión" (activador < 50 PSI).
11. [ ] **Tareas pendientes**: vencidas, próximas y la que abrió sola la alarma del Hospital Demo Sur (44 PSI).

### Checklists sin Foto ni Firma
12. [ ] Checklists → "Mantenimiento de tomas" → editar. En la paleta de campos **no están** Foto ni Firma.

### Dar de baja un equipo (regla validada)
13. [ ] Activos → un equipo con protocolo (una toma del Piso 3) → **Dar de baja**:
    - [ ] antes de confirmar dice cuántas tareas pendientes se anularán y cuáles siguen en OT abiertas;
    - [ ] confirma: sus tareas pendientes quedan anuladas con una nota;
    - [ ] vuelve a ponerlo **Activo**: sus tareas del protocolo se reabren.

## 3. Biomédica del hospital (5 min)

Entra con la **biomédica de demo** (rol cliente).

1. [ ] Solo ve **Clínica Demo Norte**: nada del Hospital Demo Sur.
2. [ ] Su panel muestra el cumplimiento, lo vencido y los próximos mantenimientos.
3. [ ] Abre un equipo: historial con sus actas, fotos y checklist.
4. [ ] Ve la OT recién aprobada con su acta, **sin** "Corregido por" ni datos internos.
5. [ ] Ve el contrato y la garantía, y descarga el PDF.
6. [ ] No ve OT en curso ni costos.

## 4. Dejar la demo limpia para el martes

Esta prueba ejecuta y aprueba la OT de la demo. Para tenerla pendiente otra
vez el martes, **recrea la base** con el procedimiento de `docs/DEMO.md`
(sección 1) el lunes por la noche. Después:
- vuelve a entrar en la app del celular con el técnico;
- **abre la OT con red** una vez, para que quede guardada en el teléfono.
