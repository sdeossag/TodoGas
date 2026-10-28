# Compilar y distribuir el APK

Sprint 11. Todo lo relativo a la app nativa Android vive en `frontend/android/`,
generado por Capacitor a partir del build de Vite.

## Requisitos de la maquina de build

| Herramienta | Version | Comprobar con |
|---|---|---|
| JDK | 21 | `java -version` |
| Node | 20+ | `node -v` |
| Android SDK | Platform 36 + Build Tools 36 | `sdkmanager --list_installed` |

El Android SDK **no** viene con el repositorio. Sin el, `gradlew` falla en la
fase de configuracion con `SDK location not found`. Se instala con Android
Studio o con las command line tools:

```bash
# commandlinetools-*-latest.zip de https://developer.android.com/studio
# se descomprime en <SDK>/cmdline-tools/latest/
sdkmanager --licenses
sdkmanager "platform-tools" "platforms;android-36" "build-tools;36.0.0"
```

Y despues se le dice a Gradle donde esta, por variable de entorno
(`ANDROID_HOME`) o por `frontend/android/local.properties`:

```properties
sdk.dir=C:/Users/<usuario>/AppData/Local/Android/Sdk
```

Con **barras normales**: en un `.properties` de Java una barra invertida sola
es caracter de escape, y `C:\Users\...` se lee como `C:Users...`. Gradle falla
entonces con un `IOException` sobre el nombre de archivo, sin decir por que.

## Configuracion que hay que revisar antes de compilar

### 1. URL de la API

`frontend/.env.production` define contra que backend habla el APK:

```
VITE_API_BASE_URL=https://cmms.todogas.com.co
```

Es el dominio de la API que crea `infra/terraform` (`api.<dominio>`). Tiene que
coincidir con `frontend/android/app/src/main/res/xml/network_security_config.xml`,
que bloquea trafico en claro hacia la API y hacia el bucket de evidencia
(`todogas-prod-evidencia`, us-east-1). Si el dominio o el bucket cambian hay
que tocar los dos archivos.

Sin este archivo el bundle sale apuntando a `http://localhost:8000` y el APK
no conecta con nada. **El APK de produccion no funciona hasta que la API este
desplegada y el subdominio delegado en GoDaddy** (ver `infra/README.md`).

La clave de Google Maps del navegador no se versiona: se pasa al compilar como
variable de entorno, `VITE_GOOGLE_MAPS_API_KEY=... npm run android:prod`. Sin
ella, el mapa sale como coordenadas con enlace a Google Maps.

### 2. google-services.json

`frontend/android/app/google-services.json` es un **placeholder**. El APK
compila con el pero no recibe notificaciones push: el registro con FCM falla y
`initFCM()` se rinde en silencio (queda un warning en logcat).

Antes del lanzamiento hay que reemplazarlo por el archivo real de Firebase
Console, del proyecto que tenga registrado el package `com.todogas.cmms`.

### 3. Keystore

`frontend/android/todogas-release.keystore`, alias `todogas`, valido 10.000
dias. **No esta en el repositorio** (ver `.gitignore`).

> El keystore es irrecuperable. Si se pierde, no se puede volver a publicar una
> actualizacion de la app firmada con la misma identidad. Respaldarlo fuera del
> repositorio junto con su contrasena.

Las credenciales estan en el `.env` de la raiz y `build.gradle` las lee del
entorno:

```
ANDROID_KEYSTORE_PASSWORD=...
ANDROID_KEY_ALIAS=todogas
ANDROID_KEY_PASSWORD=...
```

Si faltan, el build sigue pero deja el APK **sin firmar** y avisa por consola.

Para regenerarlo desde cero:

```bash
cd frontend/android
keytool -genkeypair -v -keystore todogas-release.keystore \
  -alias todogas -keyalg RSA -keysize 2048 -validity 10000 \
  -dname "CN=TodoGas CMMS, OU=Desarrollo, O=TodoGas, L=Medellin, ST=Antioquia, C=CO"
```

## Version

Antes de cada entrega sube los dos valores en `frontend/android/app/build.gradle`:
`versionCode` (entero, siempre mayor que el anterior: Android no instala encima
uno menor) y `versionName` (el que ve el usuario). La 1.1.0 es `versionCode 2`.

## Compilar

```bash
cd frontend
npm run android:prod          # vite build --mode production + cap sync android

cd android
export ANDROID_KEYSTORE_PASSWORD=... ANDROID_KEY_ALIAS=todogas ANDROID_KEY_PASSWORD=...
./gradlew assembleRelease bundleRelease
```

En Windows (cmd) las variables se ponen con `set NOMBRE=valor` antes de
`gradlew.bat assembleRelease bundleRelease`. En Git Bash se pueden cargar del
`.env` sin escribirlas en pantalla:

```bash
eval "$(grep -E '^(ANDROID_KEYSTORE_PASSWORD|ANDROID_KEY_ALIAS|ANDROID_KEY_PASSWORD)=' ../../.env | sed 's/\r$//; s/^/export /')"
```

Salen dos archivos:

- `frontend/android/app/build/outputs/apk/release/app-release.apk`: para
  instalar directo en los telefonos.
- `frontend/android/app/build/outputs/bundle/release/app-release.aab`: para
  Google Play, si se publica en la tienda.

```bash
cp app/build/outputs/apk/release/app-release.apk TodoGas-v1.1.0.apk
```

### Verificar antes de entregar

```bash
# Firma: debe listar el certificado CN=TodoGas CMMS
apksigner verify --print-certs TodoGas-v1.1.0.apk
# Version y que no sea depurable (no debe aparecer application-debuggable)
aapt dump badging TodoGas-v1.1.0.apk | grep -E "^package|debuggable"
```

### Instalar en un telefono que ya tiene la app de depuracion

La app de depuracion y la de produccion tienen el mismo paquete
(`com.todogas.cmms`) pero distinta firma, asi que Android no instala una
encima de la otra: hay que desinstalar la de depuracion primero
(`adb uninstall com.todogas.cmms`). Eso borra lo que tenga guardado sin red;
sincroniza antes.

Un APK sin firmar se llama `app-release-unsigned.apk`: si aparece ese nombre,
las variables de entorno no llegaron a Gradle.

## Distribuir

```bash
cd backend
python manage.py upload_apk ../frontend/android/TodoGas-v1.1.0.apk --apk-version 1.1.0
```

El flag es `--apk-version` y no `--version`: `BaseCommand` ya registra
`--version` para imprimir la version de Django, y argparse aborta si se define
dos veces.

Sube el APK a `apk/TodoGas-v{version}.apk` en S3 y devuelve una URL
pre-firmada valida 24 h (`AWS_QUERYSTRING_EXPIRE`). Sin credenciales de AWS cae
a storage local y la URL es solo para pruebas.

## Notas sobre R8

El build de release lleva `minifyEnabled true`. Capacitor resuelve los plugins
por nombre desde `capacitor.plugins.json`, sin ninguna referencia estatica, asi
que R8 los eliminaria: las reglas `-keep` correspondientes estan en
`frontend/android/app/proguard-rules.pro`.

Si se agrega un plugin nuevo que use reflexion, hay que agregar su regla ahi y
**probar el APK de release**, no solo el de debug — un plugin recortado por R8
solo falla en release.
