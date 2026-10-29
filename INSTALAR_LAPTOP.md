# Montar Puebla Ahora en la laptop del stand (MSI)

Guía para **Claude Code** (y para Axel) en una máquina nueva con Windows. Al terminar, la laptop sirve la app del turista, el panel y el asistente en `http://<IP>:8000` para los celulares del stand.

> Reglas del proyecto: las de `CLAUDE.md` siguen valiendo aquí. Antes de cada paso, di qué vas a hacer. **Commits y push los hace Axel.** `backend/.env` y `backend/data/raw/` no se editan.

## 0. Lo que `git clone` NO trae

Están en `.gitignore`. Hay que **copiarlos desde la PC de Axel**, por USB o por OneDrive:

| Qué | De dónde (PC de Axel) | A dónde (laptop) | Para qué |
|---|---|---|---|
| `.env` | `backend\.env` | `backend\.env` | Claves de OpenRouteService y TomTom. **No lo subas a git ni lo pegues en el chat** |
| Archivos oficiales | `backend\data\raw\` (41 MB, 10 archivos) | `backend\data\raw\` | Observatorio, INAH, DENUE y las matrices de traslados ya consultadas a ORS |

Lo demás se genera en la laptop: `backend/data/puebla.db` y `backend/data/chroma/` con el pipeline (paso 4), y `frontend/dist/` con `npm run build` (paso 3).

> Atajo, si no hay tiempo: también se pueden copiar `backend\data\puebla.db` (17 MB) y `backend\data\chroma\` (33 MB) y saltarse el paso 4. Pero esa base trae los reportes y sesiones de las pruebas en la PC, así que el panel no arranca limpio.

## 1. Programas

En PowerShell. Si alguno ya está instalado, `winget` lo dice y no pasa nada:

```powershell
winget install --id Git.Git -e
winget install --id astral-sh.uv -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id Ollama.Ollama -e
```

Después **cierra y abre la terminal** para que se actualice el PATH, y revisa:

```powershell
git --version; uv --version; node -v; ollama --version
```

Versiones con las que se probó en la PC (2026-10-16): git 2.54, uv 0.12.9, Node 24.19, Ollama 0.40.4, Python 3.14.7 (lo pone `uv`; el proyecto pide ≥ 3.12). Vite 8 necesita Node 22.12 o más nuevo.

## 2. Traer el repo

El trabajo integrado (backend + frontend) está en la branch **`feature/integracion-api`**:

```powershell
cd $HOME\Downloads
git clone -b feature/integracion-api https://github.com/Arellano008/hackathon-puebla-turistica-360.git
cd hackathon-puebla-turistica-360
git log --oneline -3
```

Si pide iniciar sesión, usa la ventana de GitHub que abre Git. Luego copia `backend\.env` y `backend\data\raw\` (paso 0).

**Bloqueo de commits para Claude.** En la PC está en `.claude/settings.local.json`, que no se sube a git. En la laptop, créalo con este contenido. El script `sin_commits.mjs` sí viene en el repo:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          {
            "type": "command",
            "command": "node \"$CLAUDE_PROJECT_DIR/.claude/hooks/sin_commits.mjs\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

## 3. Dependencias y frontend

```powershell
cd backend
uv sync
cd ..\frontend
npm ci
npm run build
cd ..
```

`npm run build` crea `frontend/dist/`, que FastAPI sirve en el mismo puerto 8000.

## 4. Ollama y datos

La laptop usa **`qwen3:4b`** (en la PC se usa `qwen3:8b`). Los embeddings son `bge-m3`, igual en las dos:

```powershell
ollama pull qwen3:4b
ollama pull bge-m3
ollama list
[Environment]::SetEnvironmentVariable('OLLAMA_MODELO', 'qwen3:4b', 'User')
$env:OLLAMA_MODELO = 'qwen3:4b'
```

La variable de usuario sirve para las terminales nuevas; la segunda línea, para la actual. Si la variable apunta a un modelo que Ollama no tiene, el chat responde **503**. La terminal lo dice: `Ollama no tiene el modelo 'X'`.

Revisa que la **zona horaria** sea la de Puebla. La app usa la hora local para el semáforo en vivo:

```powershell
Get-TimeZone    # debe ser (UTC-06:00) Guadalajara, Ciudad de México, Monterrey
```

Regenera la base y el índice del asistente desde los archivos copiados. Necesita internet (TomTom y Open-Meteo) y Ollama abierto:

```powershell
cd backend
uv run python -m scripts.pipeline data\raw
```

- El argumento `data\raw` hace que el paso 1 tome los archivos que ya copiaste.
- Los traslados salen de `ors_matriz_*.json` sin volver a consultar ORS.
- El paso 8 (`validar_bd`) debe terminar sin fallas y el paso 9 indexa ChromaDB.
- El pipeline reescribe la fecha en `backend/data/manifiesto_raw.csv`. No hace falta guardar ese cambio: `git checkout -- data/manifiesto_raw.csv`.

## 5. Verificar

```powershell
uv run pytest -q                                   # 111 pruebas (2026-10-16)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

En otra terminal, o en el navegador:

1. Abre `http://127.0.0.1:8000/api/salud` y espera a que `actualizacion.modelos` diga `{"embeddings":"cargado","llm":"cargado"}`. Revisa también que `ollama.modelo` sea `qwen3:4b`.
2. Abre `http://127.0.0.1:8000`, elige un interés y entra. Revisa la lista y una ficha con "Ver la semana", toca "Pregúntale al asistente" y prueba las 3 preguntas sugeridas. Entra también a `/panel`.
3. **Evaluación del asistente con `qwen3:4b`**, que estaba pendiente. Con el servidor apagado, para no cargar dos veces el modelo:
   ```powershell
   uv run python -m scripts.evaluar_rag
   Copy-Item data\processed\evaluacion_rag.md data\processed\evaluacion_rag_laptop_qwen3-4b.md
   git checkout -- data/processed/evaluacion_rag.md
   ```
   Compara contra la PC (`qwen3:8b`): hit 23/23, sin números inventados 28/28, "no tengo ese dato" 5/5, citas 28/28 y atributos 28/28, con 4.7 s de promedio. Si `qwen3:4b` inventa datos o tarda más de 15 s (RNF_04), díselo a Axel antes del stand.

No mandes reportes ni ajustes del panel de prueba: se quedarían en los datos que verán los evaluadores.

## 6. Red del stand

1. Activa la **zona con cobertura inalámbrica móvil** de Windows. Con ella los celulares también tienen internet, que hace falta para los mosaicos del mapa, el clima y el tráfico.
2. Busca la IP de la laptop en ese adaptador con `ipconfig`. Suele ser `192.168.137.1`, pero confírmala.
3. Abre el puerto 8000 en el firewall. Necesita PowerShell **como administrador**:
   ```powershell
   New-NetFirewallRule -DisplayName "Puebla Ahora 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Any
   ```
4. Arranca el servidor en modo stand. `PUEBLA_DEMO=1` marca las sesiones como demo (RN_11):
   ```powershell
   cd backend
   $env:PUEBLA_DEMO = '1'
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
5. Prueba desde un celular conectado a la zona: `http://<IP>:8000`.

## Problemas conocidos

| Síntoma | Causa | Qué hacer |
|---|---|---|
| El chat responde 503 | `OLLAMA_MODELO` apunta a un modelo que no está, u Ollama está cerrado | Lee la línea `WARNING: Asistente no disponible (503): …` en la terminal |
| La primera pregunta tarda mucho | Ollama está cargando el modelo | Espera a que `/api/salud` diga `cargado` antes de abrir el stand |
| Todo se vuelve lento | Dos procesos usan Ollama con configuraciones distintas, por ejemplo el servidor y `evaluar_rag` | Corre solo uno a la vez y cierra otras apps que usen la GPU |
| "Centrar en mi ubicación" no funciona en el celular | Por `http://IP` el navegador no da la ubicación (no es HTTPS) | Es esperado: la app avisa y usa el lugar que el turista eligió en "Estoy en…" |
| En la laptop "no pudimos obtener tu ubicación" | Windows no tiene de dónde calcularla | Igual que arriba |
| De noche, "¿y si llueve?" da un texto fijo | No hay lugares techados abiertos y el backend no deja que el modelo invente | Es a propósito; de día responde el modelo |

## Dónde seguir

- Reglas y comandos: `CLAUDE.md`.
- Endpoints: `docs/05c`. Reglas de negocio: `docs/10`.
- Nota de seguimiento: está en la bóveda de Obsidian de Axel (OneDrive), `proyectos\Hackathon Puebla Turística 360\14 - Checklist de implementación.md`. Si la laptop no tiene esa bóveda, apunta lo que hagas en tu respuesta final para Axel.
