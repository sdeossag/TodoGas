# Herramientas para las capturas de los manuales

Toma las capturas web (PNG, 1366x768 salvo las que piden una pantalla más alta) con datos de la demo. Solo usa la base y los servidores propios de esta carpeta. Las capturas de la app Android se toman en otra ola (en `capturas.json` están marcadas `omitir`).

## 1. Base aislada

El comando `seed_demo` exige que el nombre de la base contenga `demo`, por eso se llama `todogas_manual_demo`.
Desde la raiz del repo, con las credenciales del `.env` (no hace falta `psql`):

```bash
# Crear (o recrear) la base
backend/.venv/Scripts/python.exe -c "import psycopg2;from decouple import config;c=psycopg2.connect(dbname='postgres',user=config('DB_USER'),password=config('DB_PASSWORD'),host=config('DB_HOST'),port=config('DB_PORT'));c.autocommit=True;k=c.cursor();k.execute('DROP DATABASE IF EXISTS todogas_manual_demo WITH (FORCE)');k.execute('CREATE DATABASE todogas_manual_demo')"
cd backend
DB_NAME=todogas_manual_demo .venv/Scripts/python.exe manage.py migrate
DB_NAME=todogas_manual_demo .venv/Scripts/python.exe manage.py seed_demo   # tarda unos 3 minutos (genera PDF)
```

## 2. Preparar los datos que la demo no genera

`seed_demo` no deja varios estados que piden las capturas (OT en revisión, OT devuelta, «Aprobó / Alerta / Falló», OT histórica de Fracttal, firmas guardadas, inventario, segunda versión de un checklist, razón social y NIT, usuarios para el cambio de contraseña, el aviso de privacidad y la anonimización…). Los deja `preparar_datos_capturas.py`:

```bash
cd backend
DB_NAME=todogas_manual_demo PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe manage.py shell -c "exec(open('../docs/manuales/herramientas/preparar_datos_capturas.py', encoding='utf-8').read(), globals())"
```

- **No** use `manage.py shell < archivo`: Django abre una consola interactiva (rompe las sangrías) y lee la entrada con la página de códigos de Windows (daña los acentos).
- Se niega a correr si `DB_NAME` no es `todogas_manual_demo`. Es idempotente: cada bloque comprueba si ya existe y no duplica.
- Usa el ORM y los servicios del backend (`apps.maintenance.services`, `apps.work_orders.transitions`), sin escribir estados imposibles. Imágenes y firmas son sintéticas.
- Qué deja (todo con correos `@demo.todogas.local`):
  - OT «En revisión» (`OT-2026-00010`, checklist completo, 3 fotos de las que una está oculta, firmas del técnico y del cliente).
  - OT devuelta con motivo (`OT-2026-00011`, vuelve a «En proceso», con dos salidas de inventario ligadas).
  - OT en proceso con campos «Aprobó / Alerta / Falló» respondidos (`OT-2026-00012`) y su plantilla «Verificación del manifold de oxígeno».
  - OT histórica de Fracttal (`OT-2026-00013`: origen, folio 4521, ejecutor externo; solo consulta).
  - Firma guardada del administrador y del técnico (el supervisor de la demo ya la traía); el «Revisor Demo» es un supervisor SIN firma (capturas 35 y 71).
  - Razón social «Gases Demo S.A.» y NIT «900.000.000-0» en el formato del acta.
  - Inventario: 4 artículos (uno en «Stock bajo»), entradas y salidas ligadas a una OT.
  - Segunda versión de la plantilla «Reporte de intervención correctiva».
  - Protocolo «Mant. salidas de gases» asignado también a la ubicación «Piso 1 - Urgencias».
  - Usuarios extra: `nuevo` (debe cambiar la contraseña), `aviso` (no ha aceptado el aviso de privacidad), `restablecer` (para el enlace del correo), `revisor` (sin firma) e `inactivo` (desactivado, para «Anonimizar usuario»).
- Las cuentas que **el script de capturas** usa para entrar son las de `docs/DEMO.md` más `revisor`, `nuevo` y `aviso`. Las capturas 3 y 4 solo se pueden tomar **una vez** por usuario: al aceptar el aviso o cambiar la contraseña el estado se consume (el script no pulsa esos botones, pero no cierre la sesión de esas cuentas a mano).

## 3. Servidores (puertos propios)

```bash
# Backend en 8003
cd backend
DB_NAME=todogas_manual_demo DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:5197 .venv/Scripts/python.exe manage.py runserver 127.0.0.1:8003 --noreload

# Frontend en 5197 (otra terminal, desde la raiz)
VITE_API_BASE_URL=http://localhost:8003 npm --prefix frontend run dev -- --port 5197 --strictPort
```

Reinicie el backend después de preparar los datos solo si lo cambió el código; los datos se leen en cada petición.

## 4. Archivos de muestra (importación)

```bash
backend/.venv/Scripts/python.exe docs/manuales/herramientas/generar_muestras.py
```

Genera en `muestras/` dos Excel de Fracttal y un JSON del extractor, todos inventados («Sede Demo Fracttal»), para las capturas 19 y 106 a 108.

## 5. Script

```bash
cd docs/manuales/herramientas
npm install            # solo la primera vez
npx playwright install chromium
node tomar-capturas.mjs                       # todas las de capturas.json
node tomar-capturas.mjs --solo 1,8,10         # solo algunas
node tomar-capturas.mjs --base http://localhost:5197
```

- Las capturas se definen en `capturas.json` (el campo `_ayuda` resume todos los pasos posibles). Cada entrada: `n`, `archivo`, `rol` o `cuenta`, `ruta`, `viewport`, `fullPage`, `clip`, `elemento`, `como` (hereda otra entrada; sirve para las versiones pequeñas del manual rápido), `omitir` y `pasos`.
- Las cuentas se leen de `docs/DEMO.md`; la sesión se reutiliza por rol durante la corrida. Las entradas con `cuenta` entran con un usuario del script de datos en un contexto aparte.
- Acepta solo el aviso de privacidad (salvo `sinAceptarAviso`). No cambia contraseñas ni envía formularios.
- Los PNG quedan en `docs/manuales/capturas/`.
- `pdfVista` (captura 43): el navegador sin cabeza no pinta un PDF dentro de un iframe, así que el script toma el PDF de la respuesta de «Vista previa», lo convierte a PNG con `render_pdf.py` (pypdfium2, ya instalado en el venv del backend) y lo pone en lugar del iframe. Tarda ~1 minuto (WeasyPrint).
- `soloEnCopia` (captura 108, «Importación terminada»): aplicar el JSON **escribe** en la base. El script la omite con la base principal y solo la toma sobre una copia:
  ```bash
  # copia de la base (con el backend 8003 puede quedar encendido)
  backend/.venv/Scripts/python.exe -c "import psycopg2;from decouple import config;c=psycopg2.connect(dbname='postgres',user=config('DB_USER'),password=config('DB_PASSWORD'),host=config('DB_HOST'),port=config('DB_PORT'));c.autocommit=True;k=c.cursor();k.execute('DROP DATABASE IF EXISTS todogas_manual_demo_import WITH (FORCE)');k.execute('CREATE DATABASE todogas_manual_demo_import TEMPLATE todogas_manual_demo')"
  # backend 8004 y web 5200 sobre la copia
  cd backend && DB_NAME=todogas_manual_demo_import DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:5200 .venv/Scripts/python.exe manage.py runserver 127.0.0.1:8004 --noreload
  VITE_API_BASE_URL=http://localhost:8004 npm --prefix frontend run dev -- --port 5200 --strictPort
  cd docs/manuales/herramientas && node tomar-capturas.mjs --base http://localhost:5200 --db todogas_manual_demo_import --solo 108
  ```
  Al terminar se apagan esos dos servidores y se borra la copia (`DROP DATABASE todogas_manual_demo_import WITH (FORCE)`).
- La captura 48 oculta con JS las filas de los usuarios extra del script de datos (y ajusta el contador a «4 de 4») para que se vean los cuatro de la demo; las listas desplegables nativas (28 y 32) se muestran con `size` para que salgan abiertas, y en la 32 se quitan de la lista las personas extra.
- Las capturas de la app Android (marcadas `omitir`) quedan para otra ola; las 111 y 112 son recortes de las 8 y 1.
- Las listas desplegables nativas no salen en una captura: para las que piden «lista desplegada» se les da tamaño con `js` para que muestren sus opciones.

## 5. Generar los manuales en PDF y Word

`generar_documentos.py` convierte `manual-completo.md`, `manual-rapido.md` y `glosario.md` a PDF y Word, con las capturas insertadas en cada marcador `> [CAPTURA: …]`. Se corre desde la raíz del repo:

```bash
backend/.venv/Scripts/python.exe docs/manuales/herramientas/generar_documentos.py
# o solo uno:  ... generar_documentos.py --solo manual-rapido
```

- Salida: `docs/manuales/salida/` (PDF con WeasyPrint; Word con Pandoc si está instalado, si no con python-docx). La carpeta está en `.gitignore`.
- Cada marcador se empareja con su fila de `capturas-pendientes.md` por la descripción (dentro del mismo manual, no por orden). Si falta el PNG, se pone un recuadro gris «Captura pendiente: …» y el generador lo lista al final.
- Los avisos «coincidencia dudosa» suelen ser solo diferencias de final de frase; si aparece un aviso «marcador sin fila» o «filas sin marcador», revisar el texto del marcador y la tabla.
- No modifica los `.md` ni escribe nada dentro de `docs/` salvo `salida/`; el Markdown preprocesado va a un directorio temporal.
- Dependencias añadidas solo en `backend/.venv` (no en los requirements de producción): `markdown` y `python-docx`. WeasyPrint y pypdfium2 ya estaban. Si cambia la versión de Python del venv, reinstalar con `backend/.venv/Scripts/python.exe -m pip install markdown python-docx`.
- Pandoc no estaba instalado al escribir el generador; la rama con Pandoc está escrita pero no probada.
