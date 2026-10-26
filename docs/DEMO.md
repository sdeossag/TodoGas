# Demo con el cliente

Base de datos aparte (`todogas_demo`) con datos realistas, para no tocar la del
desarrollador. Se arma con un comando reproducible: `seed_demo`.

## 1. Crear la base de demo de cero

Desde `backend/`, con el venv activo y las credenciales del `.env`:

```bash
# 1) Crear la base (conectado a `postgres`)
psql -U <DB_USER> -h localhost -d postgres -c "CREATE DATABASE todogas_demo;"

# 2) Migrar y cargar los datos
DB_NAME=todogas_demo python manage.py migrate
DB_NAME=todogas_demo python manage.py seed_demo
```

Para **empezar de cero** (el comando no borra nada: todos los FK son PROTECT):

```bash
psql -U <DB_USER> -h localhost -d postgres -c "DROP DATABASE todogas_demo;"
psql -U <DB_USER> -h localhost -d postgres -c "CREATE DATABASE todogas_demo;"
DB_NAME=todogas_demo python manage.py migrate
DB_NAME=todogas_demo python manage.py seed_demo
```

Si el servidor de esa base está abierto, ciérralo antes del `DROP`. El comando
solo corre con los settings de desarrollo y con un `DB_NAME` que contenga
`demo`; si ya hay datos de demo se detiene y lo explica. Opción `--sin-actas`
para omitir los PDF (no hace falta WeasyPrint).

Qué deja: 2 hospitales (Clínica Demo Norte y Hospital Demo Sur) con su árbol,
14 equipos, 3 checklists publicados, 2 protocolos, 8 OT finalizadas con acta
(preventivas y correctivas, repartidas en los últimos 6 meses), tareas vencidas,
próximas y lejanas, 2 hallazgos pendientes (uno crítico que deja el compresor
fuera de servicio), un contrato que vence en ~25 días, una garantía vigente y
la **OT de la demo**: pendiente, en Piso 1 - Urgencias de Clínica Demo Norte, con
2 tomas de oxígeno, asignada al técnico.

## 2. Levantar el backend contra la base de demo

El 8000 queda libre para el entorno normal; la demo usa el **8001**:

```bash
cd backend
DB_NAME=todogas_demo python manage.py runserver 127.0.0.1:8001
```

En PowerShell: `$env:DB_NAME="todogas_demo"; python manage.py runserver 127.0.0.1:8001`.

Web (Vite): el proxy de `frontend/vite.config.js` apunta a `http://localhost:8000`; para la web cámbialo temporalmente a `8001` (o usa `adb reverse` y la APK, que no necesita el cambio).

## 3. Credenciales de prueba

Valores de prueba **solo para esta base local**. Todos los correos son
`@demo.todogas.local`.

| Persona | Correo | Contraseña | Rol | Para qué |
|---|---|---|---|---|
| Administrador | `admin@demo.todogas.local` | `TgDemo-Admin-2026` | ADMIN | Todo |
| Supervisor | `supervisor@demo.todogas.local` | `TgDemo-Super-2026` | SUP | Aprueba y corrige OT |
| Técnico | `tecnico@demo.todogas.local` | `TgDemo-Tecnico-2026` | TEC | Ejecuta la OT en el celular |
| Biomédica del cliente | `biomedica@demo.todogas.local` | `TgDemo-Biomedica-2026` | CLI | Portal de Clínica Demo Norte (solo lectura) |

## 4. Conectar el celular

La APK de depuración apunta a `localhost:8000`. Con el teléfono (o emulador)
conectado por USB/adb, redirige ese puerto al 8001 de la demo:

```bash
adb reverse tcp:8000 tcp:8001
adb reverse --list      # comprobar
```

Entra en la app con el técnico de demo. La OT de la demo aparece asignada y
pendiente. Descárgala **con red** antes de la presentación para tenerla offline
(más detalle de pruebas en el celular: `docs/RELEASE-ANDROID.md`).

## 5. Guion corto (≈ 10 min)

1. **Tablero** (admin): cumplimiento de planes, tareas vencidas y próximas,
   hallazgos abiertos (1 crítico), contrato por vencer.
2. **Equipos y protocolos**: árbol de Clínica Demo Norte; un equipo con su
   protocolo («Mant. salidas de gases» = tarea cada 6 meses, Toma × 5); el
   protocolo «Alarma de presión» con su activador «< 50 PSI».
3. **Tareas pendientes**: vencidas / 30 días / más adelante. La alarma del
   Hospital Demo Sur abrió sola una tarea por presión baja (44 PSI).
4. **OT en vivo desde el celular** (técnico): abrir la OT de Urgencias, iniciar,
   llenar una toma (Sí/No/N/A, presión en PSI, observación), tomar la foto
   *Antes* y *Después*, el GPS, firmar (técnico y cliente) y enviar a revisión.
   Probar también sin red (modo avión) y sincronizar.
5. **Revisión** (supervisor): corregir una respuesta, aprobar la OT; se genera el
   acta PDF.
6. **Historia**: abrir una OT finalizada y su acta (fotos Antes/Después, firmas,
   hallazgos). Mostrar el hallazgo crítico (compresor fuera de servicio) en la
   bandeja del planificador y convertirlo en correctivo.
7. **Portal del cliente** (biomédica): ve solo Clínica Demo Norte: OT, actas,
   hallazgos y vigencia del contrato/garantía.
