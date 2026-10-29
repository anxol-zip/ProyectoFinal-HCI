# Puebla Ahora, para todas las personas

Proyecto final de **Interacción Persona Máquina** (13009A-O26, Dra. Gabriela A. Rodríguez Ruiz), Universidad Iberoamericana Puebla. Tema del curso: *Interfaces Inteligentes para el Bienestar Social*.

**Equipo:** Angel Rugerio Jiménez (201720), Axel García Arellano (201251), Diego Navarro Sánchez (202497) y Yohualli Ollin Luna Reyes (198670).

## De qué va

**Puebla Ahora** responde *"¿a dónde voy ahora?"*: un semáforo en vivo de 23 lugares turísticos de Puebla, Cholula y Atlixco (buen momento / con precaución / mejor después). Si el lugar que buscas está lleno, te recomienda otro parecido y más tranquilo. También tiene un asistente con IA local que responde solo con los datos de la app, y un panel para la Secretaría de Turismo.

La app nació en un hackathon. En este proyecto **rediseñamos su interfaz con los principios de la materia** para que la pueda usar cualquier turista, sin importar su edad, cómo ve los colores o cuánto sabe de tecnología:

- **Tamaño de letra ajustable**, que también respeta la configuración del dispositivo.
- **Semáforo que no depende del color:** formas por estado, modo para daltonismo y alto contraste.
- **Barra lateral ampliable** para ver todos los lugares a la vez, sin scroll.
- **Para distintas edades y capacidades:** botones grandes, uso con teclado y lector de pantalla, y lectura en voz alta.
- **Pruebas de usabilidad** con personas ajenas al equipo, antes y después.

La propuesta completa está en [`docs/Propuesta_Inicial.md`](docs/Propuesta_Inicial.md) y en su [PDF](docs/Proyecto%20Final%20-%20Propuesta%20inicial.pdf). La propuesta mencionaba PySide6 y Qt Designer: la profesora autorizó después seguir en React.

## Origen del código

El código parte del repositorio del hackathon **"Puebla Turística 360°"** (Tech Capital Puebla 2026, SECIHTI Puebla), donde Axel y Angel construyeron la primera versión:

- **Repositorio:** [`Arellano008/hackathon-puebla-turistica-360`](https://github.com/Arellano008/hackathon-puebla-turistica-360)
- **Commit copiado:** `db1c2fa` de `develop`, el 29 de octubre de 2026
- **Autoría:** `backend/` (FastAPI, `turismo_core`, servidor MCP, pipeline de datos y asistente) es de **Axel García Arellano**. `frontend/` y `catalogo/` son de **Angel Rugerio Jiménez**.

Se copió **sin historia de git** y sin `backend/.env` (claves) ni `backend/data/raw/` (datos oficiales). De la documentación del hackathon solo se trajeron dos notas de referencia, en [`docs/hackathon/`](docs/hackathon/): el análisis de casos de uso y reglas de negocio, y la especificación del frontend.

## Estructura

| Carpeta | Qué hay |
| --- | --- |
| `frontend/` | La app en **React 19 + Vite**: aquí está el trabajo de la materia |
| `backend/` | API en **FastAPI**, `turismo_core` (semáforo, recomendador y reportes), servidor MCP y asistente con Ollama |
| `catalogo/` | Los lugares de la zona piloto |
| `docs/` | Propuesta, instrucciones del proyecto y referencias del hackathon |
| `INSTALAR_LAPTOP.md` | Guía de instalación del hackathon (Windows); se adaptará a este repositorio |

## Cómo correrlo

La app no tiene datos propios: todo lo pide al backend. Este necesita dos cosas que no vienen en git y se copian a mano: `backend/.env` y la base de datos, que se genera desde `backend/data/raw/` con el pipeline. Los pasos completos están en [`INSTALAR_LAPTOP.md`](INSTALAR_LAPTOP.md).

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000    # API; Swagger en http://localhost:8000/docs

cd frontend                                         # en otra terminal
npm install                                         # solo la primera vez
npm run dev                                         # http://localhost:5173
```

Requisitos: Python ≥ 3.12 con [`uv`](https://docs.astral.sh/uv/), Node ≥ 22.12 y, para el asistente, [Ollama](https://ollama.com) con `qwen3:4b` y `bge-m3`.

## Uso de inteligencia artificial

Usamos asistentes de IA (Claude Code) para investigar, depurar y apoyar la programación, como permite la guía del proyecto. Cada integrante debe poder explicar y modificar su parte del código sin IA. El asistente del turista usa un modelo de lenguaje local que responde solo con los datos de la app y cita sus fuentes.
