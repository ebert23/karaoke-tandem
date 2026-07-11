# KaraokeTandem — guía de instalación y despliegue

App de karaoke para fiestas: **FastAPI (Python)** de backend, **React + Vite +
Tailwind** de frontend (PWA con soporte offline real vía Service Worker), y tu
**Google Sheet como base de datos** (sin servidor de base de datos aparte).

Tu hoja: `https://docs.google.com/spreadsheets/d/1vnF1vrM_zNWY93Qfotz5Tt-xCuQcCDTFGxrfA-oS7d8/edit`

> ⚠️ **Antes de continuar**: la app, al arrancar, revisa la fila 1 (encabezados)
> de cada hoja y crea las que falten (`Canciones`, `Usuarios`, `Sesiones`,
> `Canciones_Sesion`, `Retos`, `Votos`, `Grupos`, `Favoritos`, `Votos_Turno`).
> Si una hoja ya existe con encabezados distintos a los esperados, **no los
> sobrescribe** (solo registra una advertencia) — la única excepción es la
> migración automática al esquema de Grupos (ver sección 3.1), que inserta
> una columna nueva sin tocar los datos existentes. Ver
> `backend/app/sheets_client.py` para el detalle exacto.

---

## 1. Crear la cuenta de servicio de Google (una sola vez)

1. Ve a [console.cloud.google.com](https://console.cloud.google.com/) y crea
   un proyecto (o usa uno existente).
2. En **APIs y servicios → Biblioteca**, activa:
   - **Google Sheets API**
   - **Google Drive API**
3. En **APIs y servicios → Credenciales → Crear credenciales → Cuenta de
   servicio**. Dale un nombre (p.ej. `karaoketandem`) y créala.
4. Entra a la cuenta de servicio creada → pestaña **Claves** → **Agregar
   clave → Crear clave nueva → JSON**. Se descarga un archivo `.json`.
5. Copia el campo `"client_email"` de ese JSON (algo como
   `karaoketandem@tu-proyecto.iam.gserviceaccount.com`).
6. Abre tu Google Sheet → botón **Compartir** → pega ese email y dale rol
   **Editor**.

Guarda el archivo `.json` descargado; lo usarás en el paso 2 (local) o 3 (Render).

---

## 2. Correr en local

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # en Windows (PowerShell: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt

copy .env.example .env        # y edita GOOGLE_SHEET_ID si usas otro Sheet
# Coloca el JSON descargado como backend/credentials.json
# (no necesitas tocar GOOGLE_SERVICE_ACCOUNT_JSON si usas el archivo)

uvicorn app.main:app --reload --port 8000
```

Abre `http://localhost:8000/health` — debe responder `{"status": "ok"}`.
La primera vez, revisa los logs: si faltan credenciales verás una advertencia
`sheets_not_ready` en vez de un crash.

### Frontend

En otra terminal:

```bash
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173`. Vite redirige `/api/*` al backend en `:8000`
(configurado en `vite.config.js`).

---

## 3. Desplegar en Vercel (ya desplegado ✅)

La app ya está publicada en producción:

**https://karaoketandem.vercel.app**

Se desplegó con `vercel.json` (propiedad `services`): un servicio `frontend`
(Vite, `frontend/`) y un servicio `backend` (Python/FastAPI,
`backend/`, entrypoint `app.main:app`), con rewrites `/api/*` → backend y
todo lo demás → frontend, en un mismo proyecto/dominio.

**Falta un solo paso para que funcione de verdad**: agregar las credenciales
de Google, porque no se pueden establecer variables de entorno de forma
automatizada — hay que hacerlo desde el dashboard:

1. Entra a [vercel.com/ebert23s-projects/karaoketandem/settings/environment-variables](https://vercel.com/ebert23s-projects/karaoketandem/settings/environment-variables).
2. Agrega estas variables (entorno **Production**, y también
   **Preview**/**Development** si quieres probarlas ahí):
   - `GOOGLE_SHEET_ID` = `1vnF1vrM_zNWY93Qfotz5Tt-xCuQcCDTFGxrfA-oS7d8`
   - `GOOGLE_SERVICE_ACCOUNT_JSON` = el contenido completo del archivo
     `.json` de la cuenta de servicio (ver paso 1 de esta guía), pegado tal
     cual como una sola variable de texto.
   - `YOUTUBE_API_KEY` (opcional) = ver sección 3.2 más abajo. Sin esta
     variable la app funciona igual, solo que el buscador de YouTube al
     agregar canciones no aparece (favoritos, sugerencias por género y todo
     lo demás no dependen de esto).
3. Guarda y vuelve a desplegar (**Deployments → ⋯ → Redeploy** en el
   deployment más reciente, o pídemelo y yo vuelvo a correr el deploy).

Hasta que esas variables no estén configuradas, el frontend carga bien pero
las llamadas a `/api/*` responden `500` (no hay cómo hablar con el Sheet).

### 3.1 Grupos / salas

Cada grupo de amigos tiene su propio espacio aislado (canciones, usuarios,
sesiones, retos y ranking no se mezclan entre grupos), con un código de
invitación de 6 dígitos para unirse.

Si el Sheet ya tenía datos de antes de que existiera este concepto (por
ejemplo, tu lista de canciones y usuarios original), la primera vez que la
app arranca con el código nuevo **migra sola**: crea un grupo llamado
`Original` y le asigna automáticamente todo lo que ya existía, sin perder ni
reordenar nada (revisa `ensure_sheets()` en `backend/app/sheets_client.py`).
El código de ese grupo queda en la hoja `Grupos` que se crea en tu Sheet —
ábrela y compártelo con la gente que ya venía usando la app para que sigan
todos en el mismo espacio.

### 3.2 Búsqueda de canciones en YouTube (opcional)

Para que el buscador de YouTube funcione al agregar canciones, necesitas una
API Key de **YouTube Data API v3** (mismo proyecto de Google Cloud que ya
usaste para la cuenta de servicio):

1. En [console.cloud.google.com](https://console.cloud.google.com/), con tu
   proyecto seleccionado, ve a **APIs y servicios → Biblioteca** y activa
   **YouTube Data API v3**.
2. Ve a **APIs y servicios → Credenciales → Crear credenciales → Clave de
   API**. Se genera una key al instante (no necesitas cuenta de servicio
   para esto).
3. (Recomendado) Haz clic en la key recién creada → **Restricciones de la
   API** → selecciona solo "YouTube Data API v3", para que esa key no sirva
   para otra cosa si se filtra.
4. Copia la key y agrégala en Vercel como `YOUTUBE_API_KEY` (paso 2 de la
   sección anterior), luego redeploy.

Esta API tiene una cuota diaria gratuita generosa para uso normal de una
fiesta; si algún día se agota, el buscador simplemente deja de responder
hasta el día siguiente — el resto de la app no se ve afectado.

### Alternativa: Render (Docker, siempre activo)

Si prefieres un servidor Docker siempre-activo en vez de funciones
serverless (sin cold starts, pero se "duerme" tras inactividad en el plan
free):

1. Sube este repo a GitHub.
2. En [render.com](https://render.com): **New +** → **Blueprint** → conecta
   el repo (detecta `render.yaml` automáticamente).
3. Pega `GOOGLE_SHEET_ID` y `GOOGLE_SERVICE_ACCOUNT_JSON` cuando lo pida.
4. Deploy. Tu app queda en `https://karaoketandem-XXXX.onrender.com`.

---

## 4. Instalar como app (PWA)

- **Android/Chrome**: abre la URL → menú (⋮) → "Instalar app" / "Agregar a
  pantalla de inicio".
- **iPhone/Safari**: abre la URL → botón compartir → "Agregar a pantalla de
  inicio".

### Sobre el modo offline

El Service Worker (Workbox, vía `vite-plugin-pwa`) cachea el shell de la app
(HTML/CSS/JS) para que **abra sin conexión**, y guarda en caché las últimas
respuestas GET de la API (canciones, ranking, retos, etc.) para poder
**consultarlas** sin internet. Las acciones que escriben datos (agregar
canción, votar, marcar cantada…) necesitan conexión, porque terminan
escribiendo en el Google Sheet en tiempo real — no hay una cola de
sincronización offline en esta versión.

---

## 5. Estructura del proyecto

```
KaraokeTandem/
├── backend/                  # FastAPI
│   ├── app/
│   │   ├── main.py           # arranque, CORS, monta el frontend compilado
│   │   ├── config.py         # variables de entorno
│   │   ├── deps.py           # dependencia FastAPI: header X-Grupo-Id
│   │   ├── sheets_client.py  # conexión a Google Sheets + acceso genérico a "tablas" + migración a Grupos
│   │   ├── youtube_client.py # búsqueda en YouTube Data API v3 (opcional)
│   │   ├── schemas.py        # modelos Pydantic (request/response)
│   │   ├── services/         # lógica de negocio por dominio (grupos, canciones, sesiones, ...)
│   │   └── routers/          # endpoints HTTP por dominio
│   └── requirements.txt
├── frontend/                 # React + Vite + Tailwind (PWA)
│   └── src/
│       ├── pages/            # Semana, Karaoke, Retos, Ranking, Estadisticas, Historial, Grupo
│       ├── components/       # Shell (nav), GroupGate, IdentityGate, Icons
│       └── lib/               # api.js, GroupContext, IdentityContext, ToastContext
├── Dockerfile                 # imagen única (build frontend + runtime backend)
└── render.yaml                 # blueprint de despliegue en Render
```

## 6. Cómo entran los usuarios

Primero se elige un **grupo/sala** (crear uno nuevo o unirse con el código de
6 dígitos de otro) — eso separa completamente los datos de cada grupo de
amigos. Dentro de un grupo, no hay contraseñas: cada quien escribe su nombre
al entrar (se guarda en `localStorage` del dispositivo, por grupo). Si el
nombre ya existe en ese grupo se reutiliza esa fila (sin distinguir
mayúsculas/minúsculas); si no, se crea. Es intencionalmente simple para una
app de fiesta entre amigos — la misma persona puede tener identidades
distintas en distintos grupos del mismo dispositivo.
