# Frontend

App del turista y panel de gobierno en **React 19 + Vite**. Responsable: Angel. El diseño y el contrato con el backend están en `docs/05c - Backend FastAPI y frontend React.md` (endpoints), `docs/10 - Análisis FIS.md` (casos de uso y reglas) y `docs/12 - Especificación del frontend.md` (pantallas y lenguaje visual).

## Correrla

La app no tiene datos propios: todo lo pide a la API de Axel (`backend/`). Primero el backend y después Vite:

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000    # API · Swagger en http://localhost:8000/docs

cd frontend                                         # en otra terminal
npm install          # solo la primera vez
npm run dev          # http://localhost:5173 (Vite reenvía /api a localhost:8000)
npm run lint         # antes de cada commit
```

Rutas: `/` (turista: inicio, mapa con semáforo, tarjeta, "Mejor ve a…", "¿Cómo está?" y asistente), `/panel` (Secretaría) y `/acerca` (atribuciones y privacidad).

## En el stand (laptop de Axel)

FastAPI sirve el build del frontend en el mismo puerto que la API: un solo comando y un solo QR.

```bash
cd frontend && npm install && npm run build          # genera frontend/dist/ (repetir tras cada cambio del frontend)
cd ../backend
PUEBLA_DEMO=1 OLLAMA_MODELO=qwen3:4b uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- Los celulares abren `http://<IP de la laptop>:8000` en la misma red (el QR apunta ahí). `/panel` y `/acerca` abren directo porque el build copia `index.html` a esas carpetas (`vite.config.js`).
- FastAPI solo monta `dist/` si existe **al arrancar**: compilar antes de levantar uvicorn.
- `PUEBLA_DEMO=1` marca las sesiones de los evaluadores como demo (RN_11). El panel las cuenta con el interruptor "Contar la demo del stand", que viene encendido.
- Sin Ollama, el asistente avisa que no está disponible; el resto de la app no lo necesita.

## Datos

Todas las llamadas pasan por `src/api/cliente.js` y los componentes usan los nombres del backend tal cual (`id`, `clave`, `color`, `razon`, `nivel`, `traslado.minutos`…); el contrato está en `backend/app/schemas.py`. No hay modo escenario: el semáforo es el de la hora real (decisión del 2026-10-15). Las fotos se buscan por la `clave` de cada lugar en `src/data/fotos.js`.

## Idioma

La app del turista está en español e inglés (selector ES/EN en la cabecera; la primera vez se usa el idioma del celular). Todos los textos van en `src/i18n/textos.js` y se piden con `t('clave')` de `useIdioma()`; un texto nuevo se agrega en los dos idiomas. Lo que el backend redacta en español (razones del semáforo, mensajes del reporte, "Mejor ve a…") se traduce en `src/i18n/backend.js`; si Axel cambia una de esas frases, hay que actualizar su patrón. El panel de la Secretaría y las respuestas del asistente se quedan en español.

## Mapa

Fondo "Light Gray Canvas" de Esri (`src/components/capaBase.js`; términos de uso sin cuenta por confirmar, ver `docs/07`). Botones de acercar, alejar y "mi ubicación": usa el GPS solo si el navegador lo da (https) y, si no, el lugar elegido en el inicio; las coordenadas no salen del celular.

## Estructura

```text
src/
├── api/          # cliente.js: todas las llamadas a la API
├── components/   # Mapa, Inicio, ListaPuntos, TarjetaPunto, Recomendacion, BotonReporte, Chat, Foto…
│   └── panel/    # Indicadores, MapaCalor, Redirecciones, SemaforoEstatal, FijarColor, Umbrales
├── data/         # semáforo, formatos, intereses, fotos y sus créditos, nombre del proyecto
├── hooks/        # useHoja: la hoja inferior arrastrable del celular
├── i18n/         # español e inglés: textos.js, fichas.en.js, traducción de los textos del backend
├── pages/        # Turista, Panel, Acerca
└── index.css     # lenguaje visual: tipografía, colores, radios
```

## Maqueta

`maqueta/index.html` es la maqueta de baja fidelidad (HTML estático, sin dependencias) con la que se diseñó la app.

## Notas

- El mapa usa mosaicos de OpenStreetMap: **sin internet** se ve el fondo gris con los marcadores, y la app sigue funcionando. Las fotos van incluidas en el build.
- `webDesignInspo/` (referencias visuales de terceros) está en `.gitignore`: no se sube.
- El nombre "Puebla Ahora" es provisional; se cambia en `src/data/marca.js`.
