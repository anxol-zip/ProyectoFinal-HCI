---
title: "10 - Análisis FIS"
tags: [hackathon, puebla, turismo, metodologia]
status: propuesta-v2
created: 2026-10-15
updated: 2026-10-15
---

# 📐 Análisis FIS: actores, casos de uso, reglas y estados

> [!info] Para qué es esta nota
> Ordena la v2 con la metodología de **Fundamentos de Ingeniería de Software** (modelo 4+1 de Kruchten y UML), que Angel y Axel usaron en el proyecto Nova Prime. Cubre el entregable "arquitectura o metodología" ([[01 - Convocatoria y reglas]]) y sirve como **contrato entre frontend y backend**: cada caso de uso apunta a sus endpoints de [[05c - Backend FastAPI y frontend React]]. Las reglas de negocio juntan en un solo lugar lo que ya estaba repartido en [[05 - Arquitectura y MCP]] y [[03 - Ideas y alternativas]]. Nomenclatura: `AC_` actor, `CU_` caso de uso, `RN_` regla de negocio, `RNF_` requerimiento no funcional.

## 1. Actores

| ID | Actor | Tipo | Qué hace |
|---|---|---|---|
| AC_01 | **Turista** | Externo, usuario principal | Consulta el semáforo, pide alternativas, reporta y pregunta al asistente. Sin cuenta |
| AC_02 | **Funcionario de turismo** (Secretaría o municipio) | Externo, cliente que paga | Consulta el panel: afluencia, redirecciones, derrama, semáforo estatal |
| AC_03 | **Administrador del sistema** | Interno | Carga el catálogo de puntos, corre el pipeline de datos y activa escenarios de demo |
| AC_04 | **Servicios externos** (Open-Meteo, TomTom, OpenRouteService) | Sistema | Entregan clima, tráfico y traslados |
| AC_05 | **Cliente MCP** (MCP Inspector, Claude Desktop u otro) | Sistema | Usa las mismas funciones vía el servidor MCP |

## 2. Casos de uso

| CU | Nombre | Actor | Endpoints / tools |
|---|---|---|---|
| CU_01 | Abrir la app y elegir intereses | Turista | `POST /api/sesiones` |
| CU_02 | Consultar el semáforo de la zona | Turista | `GET /api/semaforo`, `GET /api/puntos` |
| CU_03 | Consultar el estado de un punto | Turista | `GET /api/puntos/{id}/estado` · tool `estado_punto` |
| CU_04 | Pedir una alternativa ("mejor ve a…") | Turista | `POST /api/recomendar`, `POST /api/busquedas/{id}/aceptar` · tool `recomendar_alternativa` |
| CU_05 | Reportar cómo está un punto ("¿Cómo está?") | Turista | `POST /api/reportes` |
| CU_06 | Preguntar al asistente | Turista, Funcionario, Cliente MCP | `POST /api/chat` · tools `preguntar_asistente`, `buscar_conocimiento` |
| CU_07 | Consultar el panel de gobierno | Funcionario | `GET /api/panel/afluencia`, `/redirecciones`, `/derrama`, `/semaforo-estatal` |
| CU_08 | Seleccionar escenario de demostración | Administrador | `GET /api/escenarios` + parámetro `escenario` |
| CU_09 | Actualizar datos | Administrador, Servicios externos | Pipeline (`scripts/`), caché de clima y tráfico en `turismo_core` |

**Relaciones:**
- CU_04, CU_05 y CU_06 **«include»** CU_01: todo lo que se guarda necesita una sesión.
- CU_04 **«extend»** CU_03: desde un punto en 🔴, el turista *puede* pedir la alternativa.
- CU_05 **«extend»** CU_03: con "Estoy aquí", el turista *puede* reportar.
- CU_07 depende de lo que generan CU_04 y CU_05: sin búsquedas y reportes, el panel solo muestra la estimación.

> [!tip] Flujo principal de la demo
> CU_01 → CU_02 → CU_03 (Cholula 🔴) → CU_04 ("mejor ve a Atlixco 🟢") → CU_05 (el evaluador reporta) → CU_07 (el panel cambia). Así se recorre todo el sistema en un minuto.

## 3. Reglas de negocio

| RN | Regla | CU | Origen |
|---|---|---|---|
| RN_01 | El color sale del índice relativo de cada punto comparado con **sus propios umbrales** `bajo` y `alto` (percentiles 60 y 85 de su historia). Sin historia suficiente: **< 0.9 🟢 · 0.9–1.3 🟡 · > 1.3 🔴**. Sin estimación: `sin_dato` | 02, 03 | [[05 - Arquitectura y MCP]], [[13 - Referencias y benchmarking]] |
| RN_02 | Una alternativa **nunca** está en 🔴, **se parece** al punto pedido (similitud de sus fichas) y está a **menos de 1 h** de traslado | 04 | 03, 05 |
| RN_03 | Toda recomendación muestra **su razón** (afluencia, clima, traslado, evento) | 03, 04 | 02 |
| RN_04 | Solo se reporta después de **"Estoy aquí"**. A más de 500 m del punto, el reporte es `dudoso`; sin GPS, su peso baja a la mitad | 05 | C1 de 03, 05 |
| RN_05 | Máximo **un reporte por sesión y punto cada 30 min**; los repetidos se `descartan` y la app lo dice en pantalla | 05 | C3 de 03, 05 |
| RN_06 | Se descartan los reportes de puntos **cerrados** y las sesiones con **velocidad imposible** (dos puntos lejanos en minutos) | 05 | 05 |
| RN_07 | **Sin cuenta ni datos personales.** La sesión es un identificador aleatorio y la ubicación **no se guarda**, solo la distancia al punto | 01, 05 | 05; Ley de Protección de Datos Personales ([[07 - Modelo de negocio y escalabilidad]]) |
| RN_08 | Los reportes **caducan**: su peso cae a la mitad en ~30 min y después de 3 h ya casi no cuenta. La estimación equivale a ~2 reportes | 02, 05 | 05 |
| RN_09 | Con 3 o más reportes `valido` en la última hora, el punto dice **"confirmado por turistas"**; si no, **"estimado"** con "normalmente … a esta hora" | 02, 03 | C2 de 03, 05 |
| RN_10 | El asistente responde **solo con datos recuperados**, cita la fuente de cada cifra y, si no tiene el dato, dice "No tengo ese dato" | 06 | [[05b - ChromaDB y RAG]] |
| RN_11 | Todo escenario de demo se **rotula como simulación** en pantalla; sus sesiones se marcan `es_demo` y no entran a las estadísticas reales | 08, 07 | 02, 05 |
| RN_12 | Al gobierno solo se le entregan **agregados** por punto y hora, nunca reportes individuales | 07 | 05 |
| RN_13 | Cada fuente se usa según su licencia y se **atribuye** en la pantalla "Acerca de" (OpenStreetMap, Open-Meteo, INEGI, SIC…) | Todos | [[07 - Modelo de negocio y escalabilidad]] |
| RN_14 | La **derrama** del panel se presenta en dos cifras: **redistribuida** (redirecciones aceptadas) y **nueva estimada** (paradas agregadas), siempre con su supuesto | 07 | 07 |
| RN_15 | *(Fase 2)* Enlaces a prestadores marcados como **patrocinados**, sin alterar el orden de las recomendaciones | 04 | 07 |
| RN_16 | El funcionario puede **fijar el color** de un punto con un motivo y una hora de fin; mientras esté vigente gana sobre el cálculo y la app muestra el motivo | 02, 03, 07 | [[13 - Referencias y benchmarking]] |
| RN_17 | **Desconcentración:** entre alternativas parecidas, la recomendación **prefiere un destino fuera de Cd. Puebla** y se lo dice al turista ("tu visita apoya a la comunidad local") | 04 | [[02 - Problema y propuesta]] |

## 4. Estados de los objetos

> [!warning] Lección de Nova Prime
> En Nova Prime, los diagramas de estados, las reglas y las tablas usaron **nombres distintos** para el mismo estado. Aquí la fuente de verdad es el **valor guardado en la base** de [[05 - Arquitectura y MCP]], y las reglas lo citan tal cual.

| Objeto | Estados (valor en la base) | Transiciones |
|---|---|---|
| **Punto** (`afluencia_estimada.semaforo`) | `verde` · `amarillo` · `rojo` · `sin_dato` | Se recalcula cuando cambia la hora, el clima o entra un reporte (RN_01); un ajuste manual vigente lo fija (RN_16) |
| **Confianza del punto** (`afluencia_estimada.confianza`) | `estimado` · `confirmado por turistas` | Pasa a confirmado con 3 reportes válidos en 1 h; vuelve a estimado al caducar (RN_08, RN_09) |
| **Reporte** (`reporte.estado`) | `valido` · `dudoso` · `descartado` | Se decide al recibirlo con los filtros (RN_04 a RN_06); después solo pierde peso con el tiempo |
| **Búsqueda** (`busqueda.aceptada`) | sin respuesta · `1` aceptada · `0` ignorada | El turista acepta o no la alternativa (CU_04) |
| **Sesión** (`sesion.es_demo`) | real · demo | Se fija al crearla (RN_11) |

## 5. Requerimientos no funcionales

| RNF | Requerimiento |
|---|---|
| RNF_01 | El semáforo de la zona responde en **menos de 2 s** en la red del stand |
| RNF_02 | La app funciona **sin internet**: si una API externa falla, usa el último dato guardado y avisa su antigüedad |
| RNF_03 | Se usa en **celular**, sin instalar nada (web por QR); legible con una mano y sin explicación previa |
| RNF_04 | El asistente responde en **menos de 15 s** con `qwen3:4b` en la laptop del stand |
| RNF_05 | Todo el sistema arranca en la laptop con un solo comando de backend más Ollama |

## 🔗 Relacionado
- [[02 - Problema y propuesta]]
- [[05 - Arquitectura y MCP]]
- [[05c - Backend FastAPI y frontend React]]
- [[07 - Modelo de negocio y escalabilidad]]

---
#hackathon
