-- Esquema de puebla.db (docs/05 - Arquitectura y MCP, sección "Esquema").
-- Escrito compatible con PostgreSQL salvo detalles menores, por si algún día se sube a la nube.
-- Cambios respecto a docs/05:
--   * punto.clave: id corto del catálogo (p. ej. 'zona_arq_cholula'); el id entero sigue siendo la llave.
--   * punto.ficha y punto.duracion_sugerida: vienen del catálogo y los usan la tarjeta y ChromaDB.
--   * recinto_inah: los 19 recintos del INAH en Puebla. hecho_inah se guarda por recinto (no por punto)
--     porque la evidencia del problema usa los 19, y un punto puede juntar dos recintos (los Fuertes).
--   * establecimiento: oferta del DENUE (dónde comer o dormir) alrededor de los puntos.

PRAGMA foreign_keys = ON;

-- ───────────── Catálogos ─────────────

CREATE TABLE IF NOT EXISTS fuente (
    id              INTEGER PRIMARY KEY,
    nombre          TEXT NOT NULL UNIQUE,
    url             TEXT,
    licencia        TEXT,
    frecuencia      TEXT,
    fecha_descarga  TEXT,
    archivo         TEXT,
    hash_archivo    TEXT
);

CREATE TABLE IF NOT EXISTS destino (
    id          INTEGER PRIMARY KEY,
    nombre      TEXT NOT NULL UNIQUE,       -- como lo nombra el Observatorio, normalizado
    cve_mun     TEXT,                       -- clave INEGI del municipio (del propio DENUE)
    lat REAL, lon REAL,
    es_piloto   INTEGER DEFAULT 0,
    es_agregado INTEGER DEFAULT 0           -- 1 = 'Estado' o 'Resto del Estado' (no es un lugar)
);

CREATE TABLE IF NOT EXISTS punto (
    id                INTEGER PRIMARY KEY,
    clave             TEXT NOT NULL UNIQUE,
    nombre            TEXT NOT NULL,
    destino_id        INTEGER NOT NULL REFERENCES destino(id),
    municipio         TEXT,
    tipo              TEXT,
    categorias        TEXT,
    interior          INTEGER,
    lat REAL NOT NULL, lon REAL NOT NULL,
    horario           TEXT,
    costo_mxn         REAL,
    duracion_sugerida TEXT,
    ficha             TEXT,
    es_inah           INTEGER DEFAULT 0,
    clee_denue        TEXT,
    osm_id            TEXT,
    fuente_texto      TEXT,                 -- columna 'fuente' del catálogo
    fuente_id         INTEGER REFERENCES fuente(id),
    verificado        INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS recinto_inah (
    clave_siinah  TEXT PRIMARY KEY,
    nombre        TEXT NOT NULL,
    siglas        TEXT,
    punto_id      INTEGER REFERENCES punto(id)   -- NULL si no está en la zona piloto
);

CREATE TABLE IF NOT EXISTS evento (
    id          INTEGER PRIMARY KEY,
    nombre      TEXT NOT NULL,
    punto_id    INTEGER REFERENCES punto(id),
    destino_id  INTEGER REFERENCES destino(id),
    inicio      TEXT NOT NULL, fin TEXT NOT NULL,
    impacto     TEXT CHECK (impacto IN ('bajo','medio','alto')),
    fuente_url  TEXT NOT NULL,
    verificado  INTEGER DEFAULT 0,          -- 0 = solo prensa: se guarda, pero el modelo no lo usa
    nota        TEXT                        -- horario real, sede, discrepancias entre fuentes
);

CREATE TABLE IF NOT EXISTS calendario (
    fecha         TEXT PRIMARY KEY,
    dia_semana    INTEGER,                  -- 0 = lunes
    es_festivo    INTEGER, es_puente INTEGER, es_vacaciones INTEGER
);

-- ───────────── Hechos oficiales ─────────────

CREATE TABLE IF NOT EXISTS hecho_observatorio (
    destino_id  INTEGER REFERENCES destino(id),
    periodo     TEXT,                       -- 'YYYY-MM'
    indicador   TEXT,
    valor       REAL,
    es_pandemia INTEGER DEFAULT 0,
    fuente_id   INTEGER REFERENCES fuente(id),
    PRIMARY KEY (destino_id, periodo, indicador)
);

CREATE TABLE IF NOT EXISTS hecho_inah (
    clave_siinah    TEXT REFERENCES recinto_inah(clave_siinah),
    periodo         TEXT,
    tipo_visitante  TEXT,
    nacionalidad    TEXT,                   -- 'nacional' / 'extranjero'
    visitas         INTEGER,
    fuente_id       INTEGER REFERENCES fuente(id),
    PRIMARY KEY (clave_siinah, periodo, tipo_visitante, nacionalidad)
);

CREATE TABLE IF NOT EXISTS establecimiento (
    clee        TEXT PRIMARY KEY,
    nombre      TEXT NOT NULL,
    codigo_act  TEXT NOT NULL,
    nombre_act  TEXT,
    giro        TEXT,                       -- 'museo_sitio', 'hospedaje', 'alimentos'
    per_ocu     TEXT,
    cve_mun     TEXT,
    municipio   TEXT,
    lat REAL, lon REAL,
    fuente_id   INTEGER REFERENCES fuente(id)
);

CREATE TABLE IF NOT EXISTS matriz_traslado (
    origen_id    INTEGER REFERENCES punto(id),
    destino_id   INTEGER REFERENCES punto(id),
    minutos_base REAL, km REAL,                -- en coche, sin tráfico (se multiplica por el factor de tráfico)
    minutos_pie  REAL, km_pie REAL,            -- a pie (útil dentro del centro histórico)
    fuente_id    INTEGER REFERENCES fuente(id),
    PRIMARY KEY (origen_id, destino_id)
);

-- ───────────── En vivo ─────────────

CREATE TABLE IF NOT EXISTS obs_clima (
    punto_id      INTEGER REFERENCES punto(id),
    consultado_en TEXT,
    valido_para   TEXT,
    temp_c REAL, prob_lluvia_pct REAL, lluvia_mm REAL, weather_code INTEGER,
    PRIMARY KEY (punto_id, consultado_en, valido_para)
);

CREATE TABLE IF NOT EXISTS obs_trafico (
    tramo         TEXT,
    consultado_en TEXT,
    vel_actual REAL, vel_libre REAL,
    factor        REAL,
    PRIMARY KEY (tramo, consultado_en)
);

-- ───────────── Lo que genera la app ─────────────

CREATE TABLE IF NOT EXISTS sesion (
    id          TEXT PRIMARY KEY,
    creada_en   TEXT,
    perfil      TEXT,
    es_demo     INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reporte (
    id            INTEGER PRIMARY KEY,
    sesion_id     TEXT REFERENCES sesion(id),
    punto_id      INTEGER REFERENCES punto(id),
    creado_en     TEXT NOT NULL,
    nivel         INTEGER CHECK (nivel IN (1,2,3)),
    espera_min    INTEGER,
    distancia_m   REAL,
    peso          REAL,
    estado        TEXT DEFAULT 'valido',
    motivo        TEXT
);

CREATE TABLE IF NOT EXISTS busqueda (
    id             INTEGER PRIMARY KEY,
    sesion_id      TEXT REFERENCES sesion(id),
    creada_en      TEXT,
    punto_pedido   INTEGER REFERENCES punto(id),
    punto_sugerido INTEGER REFERENCES punto(id),
    motivo         TEXT,
    aceptada       INTEGER
);

-- ───────────── Derivados ─────────────

CREATE TABLE IF NOT EXISTS afluencia_estimada (
    punto_id     INTEGER REFERENCES punto(id),
    para_hora    TEXT,
    base         REAL,
    f_dia_hora   REAL, f_evento REAL, f_clima REAL,
    estimacion   REAL,
    n_reportes   INTEGER,
    valor_final  REAL,
    semaforo     TEXT,
    confianza    TEXT,
    PRIMARY KEY (punto_id, para_hora)
);

CREATE TABLE IF NOT EXISTS umbral_punto (
    punto_id     INTEGER PRIMARY KEY REFERENCES punto(id),
    bajo         REAL NOT NULL,
    alto         REAL NOT NULL,
    metodo       TEXT CHECK (metodo IN ('percentil','general','manual')),
    n_muestras   INTEGER,
    calculado_en TEXT
);

CREATE TABLE IF NOT EXISTS ajuste_manual (
    id           INTEGER PRIMARY KEY,
    punto_id     INTEGER REFERENCES punto(id),
    color        TEXT CHECK (color IN ('verde','amarillo','rojo')),
    motivo       TEXT NOT NULL,
    creado_en    TEXT NOT NULL,
    hasta        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_reporte_punto_fecha ON reporte (punto_id, creado_en);
CREATE INDEX IF NOT EXISTS ix_establecimiento_mun ON establecimiento (cve_mun, giro);
