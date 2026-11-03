# Instalar Puebla Ahora en una laptop con los datos reales

Guía para montar el proyecto en una computadora que **sí tiene** `backend/.env` y `backend/data/raw/`: la que se usa para la demo, la presentación y las pruebas con usuarios. Cada paso trae los comandos para **Windows (PowerShell)** y **Linux (bash/zsh)**.

Si solo vas a trabajar en la interfaz y no tienes los datos, no necesitas esta guía: usa la base de desarrollo que viene en git (sección *Desarrollo sin los datos reales* del [`README.md`](README.md)).

> `backend/.env` y `backend/data/raw/` **nunca** se suben a git ni se pegan en un chat. El `.gitignore` ya los excluye.

## 0. Lo que `git clone` no trae

| Qué | A dónde | Para qué |
|---|---|---|
| `.env` | `backend/.env` | Claves de OpenRouteService (`ORS_API_KEY`) y TomTom (`TOMTOM_API_KEY`) |
| Archivos oficiales | `backend/data/raw/` (41 MB, 10 archivos) | Observatorio, INAH, DENUE y las matrices de traslados ya consultadas a ORS |

Se copian a mano (USB o OneDrive) desde la computadora que ya los tiene. Lo demás se genera en la laptop: `backend/data/puebla.db` y `backend/data/chroma/` con el pipeline (paso 4) y `frontend/dist/` con `npm run build` (paso 3).

> **Atajo, si no hay tiempo:** también se pueden copiar `backend/data/puebla.db` (17 MB) y `backend/data/chroma/` (33 MB) y saltarse el paso 4. Pero esa base trae las sesiones y los reportes de las pruebas que se hicieron en esa computadora: el panel no arranca limpio.

## 1. Programas

Versiones que pide el proyecto: **Python ≥ 3.12** (lo instala `uv`), **Node ≥ 22.12** (lo exige Vite 8) y **Ollama** para el asistente.

**Windows.** Si alguno ya está instalado, `winget` lo dice y no pasa nada:

```powershell
winget install --id Git.Git -e
winget install --id astral-sh.uv -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id Ollama.Ollama -e
```

Cierra y abre la terminal para que se actualice el `PATH`.

**Linux (Ubuntu).**

```bash
sudo apt update && sudo apt install -y git curl
curl -LsSf https://astral.sh/uv/install.sh | sh                 # uv
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt install -y nodejs                                      # Node 24 LTS
curl -fsSL https://ollama.com/install.sh | sh                   # Ollama (queda como servicio)
```

Abre una terminal nueva y revisa en los dos sistemas:

```bash
git --version; uv --version; node -v; ollama --version
```

## 2. Traer el repo

El trabajo integrado está en **`develop`**:

```bash
git clone -b develop https://github.com/anxol-zip/ProyectoFinal-HCI.git
cd ProyectoFinal-HCI
git log --oneline -3
```

Luego copia `backend/.env` y `backend/data/raw/` (paso 0).

## 3. Dependencias y frontend

Igual en los dos sistemas (en Windows, con `\` o `/`, PowerShell acepta ambos):

```bash
cd backend
uv sync
cd ../frontend
npm ci
npm run build
cd ..
```

`npm run build` crea `frontend/dist/`, que FastAPI sirve en el mismo puerto 8000.

## 4. Ollama y datos

### Modelos

Sin configurar nada, el backend usa **`qwen3:8b`**. En una laptop con poca memoria de video conviene **`qwen3:4b`**. Los embeddings son **`bge-m3`** en los dos casos:

```bash
ollama pull qwen3:4b      # o qwen3:8b si la laptop aguanta
ollama pull bge-m3
ollama list
```

Si usas `qwen3:4b`, define `OLLAMA_MODELO` (sin editar el `.env`):

```powershell
# Windows: la primera línea es para las terminales nuevas, la segunda para la actual
[Environment]::SetEnvironmentVariable('OLLAMA_MODELO', 'qwen3:4b', 'User')
$env:OLLAMA_MODELO = 'qwen3:4b'
```

```bash
# Linux: cambia ~/.bashrc por ~/.zshrc si usas zsh
echo "export OLLAMA_MODELO=qwen3:4b" >> ~/.bashrc
export OLLAMA_MODELO=qwen3:4b
```

Si la variable apunta a un modelo que Ollama no tiene, el chat responde **503**. La terminal del backend lo dice: `Ollama no tiene el modelo 'X'`.

### Zona horaria

El semáforo en vivo usa la hora local, así que la laptop tiene que estar en la hora de Puebla:

```powershell
Get-TimeZone      # Windows: (UTC-06:00) Guadalajara, Ciudad de México, Monterrey
```

```bash
timedatectl       # Linux: Time zone: America/Mexico_City
```

### Base real e índice del asistente

Este paso necesita internet (TomTom y Open-Meteo) y Ollama abierto:

```bash
cd backend
uv run python -m scripts.pipeline data/raw
```

- El argumento `data/raw` hace que el paso 1 tome los archivos que ya copiaste.
- Los traslados salen de los `ors_matriz_*.json` sin volver a consultar ORS.
- El paso 8 (`validar_bd`) debe terminar sin fallas, y el paso 9 indexa ChromaDB. Sin Ollama, el paso 9 se salta con un aviso y el resto de la app funciona.
- El pipeline reescribe la fecha en `backend/data/manifiesto_raw.csv`. Ese cambio no se commitea: `git checkout -- data/manifiesto_raw.csv`.
- La afluencia estimada cubre los próximos días. Antes de una demo o de una sesión de pruebas, vuelve a correr el pipeline si la base tiene más de una semana.

## 5. Verificar

```bash
uv run pytest -q          # desde backend/: 111 pruebas (develop, 2026-11-02)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

En el navegador:

1. `http://127.0.0.1:8000/api/salud`: en `claves`, `ORS_API_KEY` y `TOMTOM_API_KEY` deben salir en `true`. En `ollama`, `disponible: true` y el `modelo` que elegiste. En `chroma`, que el índice exista.
2. `http://127.0.0.1:8000`: elige un interés y entra. Revisa la lista, una ficha, que cada estado del semáforo tenga su forma y las opciones de lectura (tamaño de letra, colores para daltonismo e idioma). Prueba el asistente con las preguntas sugeridas. Entra también a `/panel`.

**Para trabajar en la interfaz con recarga en vivo**, en lugar del `dist/`, deja el backend corriendo y en otra terminal:

```bash
cd frontend
npm run dev               # http://localhost:5173 (el backend ya acepta ese origen)
```

## 6. Pruebas con usuarios en celulares

Para que otras personas usen la app desde su celular, todos tienen que estar en la misma red que la laptop.

**Windows**

1. Activa la **zona con cobertura inalámbrica móvil**. Así los celulares también tienen internet, que hace falta para el mapa, el clima y el tráfico.
2. Busca la IP de la laptop en ese adaptador con `ipconfig` (suele ser `192.168.137.1`).
3. Abre el puerto 8000. Necesita PowerShell **como administrador**:
   ```powershell
   New-NetFirewallRule -DisplayName "Puebla Ahora 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Any
   ```

**Linux**

1. Comparte la red desde *Configuración → Wi-Fi → Activar punto de acceso*, o conecta la laptop y los celulares a la misma red.
2. Busca la IP con `ip -4 addr` o `hostname -I`.
3. Si el firewall está activo (`sudo ufw status`), abre el puerto: `sudo ufw allow 8000/tcp`.

**En los dos sistemas**, arranca el servidor en modo demo. `PUEBLA_DEMO=1` marca las sesiones como de prueba (RN_11), y así no se mezclan con datos reales:

```powershell
cd backend
$env:PUEBLA_DEMO = '1'
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

```bash
cd backend
PUEBLA_DEMO=1 uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Prueba desde un celular: `http://<IP>:8000`.

## Problemas conocidos

| Síntoma | Causa | Qué hacer |
|---|---|---|
| El chat responde 503 | `OLLAMA_MODELO` apunta a un modelo que no está, u Ollama está cerrado | Lee la línea `WARNING: Asistente no disponible (503): …` en la terminal del backend |
| La primera pregunta tarda mucho | Ollama está cargando el modelo | Espera a que `/api/salud` diga que el modelo está cargado antes de empezar |
| Todo se vuelve lento | Dos procesos usan Ollama a la vez (por ejemplo, el servidor y `scripts.evaluar_rag`) | Corre solo uno a la vez y cierra otras apps que usen la GPU |
| `/api/salud` dice `false` en una clave | El `.env` no está en `backend/` o le falta la clave | Revisa que el archivo se llame exactamente `.env`; en Windows el explorador puede ocultar que quedó como `.env.txt` |
| "Centrar en mi ubicación" no funciona en el celular | Por `http://IP` el navegador no da la ubicación (no es HTTPS) | Es esperado: la app avisa y usa el lugar que se eligió en "Estoy en…" |
| De noche, "¿y si llueve?" da un texto fijo | No hay lugares techados abiertos y el backend no deja que el modelo invente | Es a propósito; de día responde el modelo |

## Dónde seguir

- Qué es el proyecto, la estructura y la base de desarrollo: [`README.md`](README.md).
- Propuesta y criterios de las pruebas de usabilidad: [`docs/Propuesta_Inicial.md`](docs/Propuesta_Inicial.md).
- Endpoints y reglas de negocio heredados del hackathon: [`docs/hackathon/`](docs/hackathon/).
