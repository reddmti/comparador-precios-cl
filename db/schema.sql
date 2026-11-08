-- Esquema del comparador de precios (PostgreSQL).
-- Corresponde al modelo de datos documentado en el informe: un producto es la entidad
-- conceptual, una variante es cómo ese producto aparece en una cadena concreta, y los
-- precios son registros fechados asociados a una variante.

CREATE TABLE IF NOT EXISTS cadenas (
    id          SMALLSERIAL PRIMARY KEY,
    nombre      TEXT NOT NULL UNIQUE,
    url_base    TEXT NOT NULL,
    activa      BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS productos (
    id                  BIGSERIAL PRIMARY KEY,
    nombre_normalizado  TEXT NOT NULL,
    categoria           TEXT NOT NULL,
    -- El formato se guarda en unidad base (ml o g) y como cantidad total del envase,
    -- de modo que un pack de 12 x 1 L sea 12000 ml y no se confunda con una botella.
    formato_unidad      TEXT,
    formato_cantidad    NUMERIC(10, 2),
    -- Distinguen productos parecidos: integral, sin lactosa, grado 1, para freír, etc.
    -- Variantes ordenadas y unidas por "|": portable entre PostgreSQL y SQLite
    variantes           TEXT NOT NULL DEFAULT '',
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (nombre_normalizado, formato_unidad, formato_cantidad, variantes)
);

CREATE TABLE IF NOT EXISTS variantes_por_cadena (
    id                BIGSERIAL PRIMARY KEY,
    producto_id       BIGINT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    cadena_id         SMALLINT NOT NULL REFERENCES cadenas(id) ON DELETE CASCADE,
    nombre_en_cadena  TEXT NOT NULL,
    url_producto      TEXT,
    -- Similitud con la que se asoció a su producto; permite auditar el emparejamiento
    -- y rehacer las asociaciones dudosas sin volver a obtener los datos.
    score             NUMERIC(5, 2),
    UNIQUE (cadena_id, nombre_en_cadena)
);

CREATE TABLE IF NOT EXISTS precios (
    id                 BIGSERIAL PRIMARY KEY,
    variante_id        BIGINT NOT NULL REFERENCES variantes_por_cadena(id) ON DELETE CASCADE,
    precio             INTEGER NOT NULL CHECK (precio > 0),
    precio_por_unidad  INTEGER,
    fecha_registro     DATE NOT NULL DEFAULT CURRENT_DATE,
    -- Una sola observación por variante y día: si el proceso se repite, actualiza.
    UNIQUE (variante_id, fecha_registro)
);

-- El historial se consulta siempre por variante y rango de fecha.
CREATE INDEX IF NOT EXISTS idx_precios_variante_fecha ON precios (variante_id, fecha_registro DESC);
-- La búsqueda por nombre usa coincidencia parcial sobre el nombre normalizado.
CREATE INDEX IF NOT EXISTS idx_productos_nombre ON productos USING GIN (to_tsvector('spanish', nombre_normalizado));
CREATE INDEX IF NOT EXISTS idx_variantes_producto ON variantes_por_cadena (producto_id);

-- ── Listas de compra ────────────────────────────────────────────────────────
-- No hay usuarios: la lista se asocia a una sesión anónima, de modo que el sistema
-- no trata datos personales.
CREATE TABLE IF NOT EXISTS listas (
    id          BIGSERIAL PRIMARY KEY,
    sesion_id   TEXT NOT NULL,
    creada_en   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS items_lista (
    id              BIGSERIAL PRIMARY KEY,
    lista_id        BIGINT NOT NULL REFERENCES listas(id) ON DELETE CASCADE,
    texto_original  TEXT NOT NULL,
    -- Opcional: con la cobertura actual del emparejamiento, parte de los ítems que
    -- escribe el usuario no tendrá producto asociado y se muestra como no reconocido.
    producto_id     BIGINT REFERENCES productos(id) ON DELETE SET NULL,
    cantidad        SMALLINT NOT NULL DEFAULT 1 CHECK (cantidad > 0)
);

CREATE INDEX IF NOT EXISTS idx_items_lista ON items_lista (lista_id);
CREATE INDEX IF NOT EXISTS idx_listas_sesion ON listas (sesion_id);

-- ── Vista de consulta ───────────────────────────────────────────────────────
-- Último precio conocido de cada variante, que es lo que necesita la comparación.
CREATE OR REPLACE VIEW precios_vigentes AS
SELECT DISTINCT ON (p.variante_id)
       p.variante_id,
       v.producto_id,
       v.cadena_id,
       c.nombre AS cadena,
       v.nombre_en_cadena,
       v.url_producto,
       p.precio,
       p.precio_por_unidad,
       p.fecha_registro
  FROM precios p
  JOIN variantes_por_cadena v ON v.id = p.variante_id
  JOIN cadenas c ON c.id = v.cadena_id
 ORDER BY p.variante_id, p.fecha_registro DESC;

INSERT INTO cadenas (nombre, url_base) VALUES
    ('Jumbo', 'https://www.jumbo.cl'),
    ('Santa Isabel', 'https://www.santaisabel.cl'),
    ('Unimarc', 'https://www.unimarc.cl')
ON CONFLICT (nombre) DO NOTHING;
