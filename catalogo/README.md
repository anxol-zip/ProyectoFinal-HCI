# Catálogo de la zona piloto

Puntos turísticos de la **capa en vivo** (Puebla capital, Cholula, Atlixco y alternativas a menos de 1 h). Responsable: Axel (borrador inicial de Angel). Lo carga el pipeline en la tabla `punto` de SQLite y sus fichas se indexan en ChromaDB (ver `docs/05 - Arquitectura y MCP.md` y `docs/05b - ChromaDB y RAG.md`).

> **Estado: verificado (2026-10-15).** 23 puntos: los 20 originales (con la Catedral separada del Zócalo) más el Zócalo, la Casa de los Hermanos Serdán y el Acuario Michin, agregados desde "Los imperdibles de Puebla" del Ayuntamiento. Los 20 originales tienen `verificado=1`. Coordenadas: 13 del DENUE 05/2026, 6 de OpenStreetMap y Xanenetla de Google Maps (no está en las otras dos). Horario y costo oficiales solo de los 3 recintos con fuente oficial (Z.A. de Cholula, Fuerte de Loreto y Ex Convento de Huejotzingo); el resto queda vacío y la app lo muestra como "horario por confirmar". La propuesta y su método están en `backend/scripts/verificar_catalogo.py`.

## Archivo

`puntos_zona_piloto.csv` (UTF-8, separado por comas, una fila por punto).

| Columna | Qué es | Ejemplo |
|---|---|---|
| `id` | Identificador corto, único | `zona_arq_cholula` |
| `nombre` | Nombre del punto | Zona Arqueológica de Cholula (Gran Pirámide) |
| `destino` | Centro turístico del Observatorio al que pertenece | San Andrés Cholula |
| `municipio` | Municipio (para cruzar con DENUE e INEGI) | San Andrés Cholula |
| `tipo` | `museo`, `templo`, `zona_arqueologica`, `mercado`, `calle`, `barrio`, `mirador`, `parque`, `pueblo_magico`, `plaza` | `zona_arqueologica` |
| `categorias` | Intereses del turista, separados por coma (los usa el recomendador) | `historia,cultura` |
| `interior` | 1 = techado (sirve si llueve), 0 = al aire libre | `0` |
| `lat`, `lon` | Coordenadas WGS84 | `19.0576`, `-98.3017` |
| `horario` | JSON por día, p. ej. `{"mar":"09:00-18:00"}`; hoy dice `verificar` | `verificar` |
| `costo_mxn` | Costo de entrada (vacío si es gratis o no se sabe) | |
| `duracion_sugerida` | Tiempo sugerido de visita (idea C4 de `docs/03`) | `2 h` |
| `inah` | 1 = recinto operado por el INAH (se cruza con sus estadísticas) | `1` |
| `ficha` | Texto de 2–3 líneas para ChromaDB y para la tarjeta de la app | |
| `fuente` | De dónde salen los datos del punto | |
| `verificado` | 1 = revisado a mano por el equipo | `1` |
| `clee_denue` | Clave del establecimiento en el DENUE, si la coordenada salió de ahí | `21119813210000951000000000U9` |
| `osm_id` | Objeto de OpenStreetMap, si la coordenada salió de ahí | `way/157402817` |

## Cómo se verifica cada punto

1. **Coordenadas:** buscar el punto en OpenStreetMap y copiar lat/lon del lugar exacto (la entrada, no el centro del municipio).
2. **Horario y costo:** recintos INAH en `https://lugares.inah.gob.mx`; museos estatales en el CSV de Museos del Estado de Puebla; el resto, en su página oficial. Si dos fuentes no coinciden, se toma la oficial (ver `docs/04 - Fuentes de datos.md` §1.4).
3. **Ficha:** revisar que lo que dice sea cierto; nada de superlativos sin fuente.
4. Cambiar `verificado` a `1` y anotar la fuente en `fuente`.

## Eventos

Los eventos de temporada (p. ej. **Valle de Catrinas** en Atlixco) no son puntos: van en la tabla `evento`, con su fecha y su fuente oficial.

## Atribución

Las coordenadas tomadas de OpenStreetMap son datos **© colaboradores de OpenStreetMap, licencia ODbL**, y se atribuyen en la app (regla RN_13 de `docs/10 - Análisis FIS.md`).
