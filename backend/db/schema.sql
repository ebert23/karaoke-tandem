-- Esquema de KaraokeTandem en Postgres (Supabase), reemplazo de Google Sheets.
-- Cada tabla corresponde 1:1 a una hoja del Sheet original. Los campos de
-- fecha se guardan como texto ("YYYY-MM-DD HH:MM:SS") a propósito, igual que
-- en Sheets, para no cambiar de comportamiento en esta migración (el resto
-- del código ya sabe ordenar/mostrar ese formato).
--
-- Nota sobre foreign keys: solo id_grupo e id_sesion tienen FK real, porque
-- grupos y sesiones nunca se borran. id_cancion/id_usuario se guardan como
-- texto simple (sin FK) a propósito: hoy se puede borrar una canción o
-- expulsar a un usuario que ya tiene votos/turnos jugados, y esos registros
-- históricos deben sobrevivir intactos (canciones_svc.get_por_id ya maneja
-- con normalidad una referencia a una canción que ya no existe). Una FK
-- estricta ahí rompería ese comportamiento (o borraría historial con
-- CASCADE, que es peor).

-- "modo" distingue los dos productos que conviven sobre las mismas tablas:
--   'grupo' — noche entre amigos (casa o box): una sala, un admin que maneja
--             la cola, la app reproduce el video de YouTube.
--   'salon' — salón principal de un karaoke comercial: mesas con QR, rotación
--             centralizada entre mesas y una vista aparte para el DJ. Acá la
--             app NO reproduce nada; el DJ pone la canción en su equipo.
-- Los grupos que ya existían quedan en 'grupo' por el default, así que su
-- comportamiento no cambia en nada.
create table if not exists grupos (
    id text primary key,
    nombre text not null,
    codigo text not null unique,
    foto text not null default '',
    admins text[] not null default '{}',
    fecha_creacion text not null,
    modo text not null default 'grupo',
    -- Secreto largo para entrar a la vista del DJ. No es auth de verdad (ver
    -- deps.requiere_dj), solo evita que la URL sea adivinable.
    codigo_dj text not null default ''
);

create table if not exists usuarios (
    id text primary key,
    id_grupo text not null references grupos(id),
    nombre text not null,
    foto text not null default '',
    puntos_totales int not null default 0,
    sesiones_jugadas int not null default 0
);
create index if not exists idx_usuarios_grupo on usuarios(id_grupo);

create table if not exists canciones (
    id text primary key,
    id_grupo text not null references grupos(id),
    titulo text not null,
    artista text not null,
    genero text not null,
    link_youtube text not null default '',
    agregado_por text not null,
    fecha_agregado text not null,
    votos int not null default 0,
    veces_cantada int not null default 0
);
create index if not exists idx_canciones_grupo on canciones(id_grupo);

create table if not exists votos (
    id_voto text primary key,
    id_grupo text not null references grupos(id),
    id_cancion text not null,
    id_usuario text not null,
    fecha text not null,
    unique (id_cancion, id_usuario)
);
create index if not exists idx_votos_grupo on votos(id_grupo);

create table if not exists favoritos (
    id_grupo text not null references grupos(id),
    id_usuario text not null,
    id_cancion text not null,
    fecha text not null,
    unique (id_grupo, id_usuario, id_cancion)
);
create index if not exists idx_favoritos_grupo on favoritos(id_grupo);

create table if not exists sesiones (
    id_sesion text primary key,
    id_grupo text not null references grupos(id),
    fecha text not null,
    participantes text[] not null default '{}',
    estado text not null,
    turno_actual int not null default 0
);
create index if not exists idx_sesiones_grupo on sesiones(id_grupo);

-- "orden" reemplaza al truco de usar el orden físico de filas de Sheets
-- para la cola: ahora reordenar es un UPDATE de dos enteros, sin tener que
-- resolver "row_number" a mano (ver mover_en_cola en services/sesiones.py).
-- En modo salón esta misma tabla guarda los "pedidos" de las mesas: la fila
-- lleva id_mesa y una "ronda" (ver services/sesiones.py::_calcular_ronda). En
-- modo grupo id_mesa queda NULL y ronda en 0, y nada de eso se mira.
create table if not exists canciones_sesion (
    id bigserial primary key,
    id_sesion text not null references sesiones(id_sesion),
    id_grupo text not null references grupos(id),
    id_cancion text not null,
    orden int not null default 0,
    turno int not null default 0,
    cantada_por text not null default '',
    puntuacion int,
    estado text not null,
    id_mesa text,
    -- Nombre libre que escribió el cliente en la mesa ("Juan"). No es un
    -- usuario del grupo: en un salón el público rota toda la noche y crear
    -- un usuario permanente por cada uno solo acumularía basura.
    pedido_por text not null default '',
    ronda int not null default 0,
    -- Cuándo se pidió y cuándo sonó. Con la segunda el DJ puede ver "esta ya
    -- se cantó hace 40 min" cuando otra mesa pide la misma canción.
    fecha_pedido text not null default '',
    fecha_cantada text not null default ''
);
create index if not exists idx_cs_sesion on canciones_sesion(id_sesion);
create index if not exists idx_cs_grupo on canciones_sesion(id_grupo);
create index if not exists idx_cs_mesa on canciones_sesion(id_mesa);

create table if not exists votos_turno (
    id bigserial primary key,
    id_grupo text not null references grupos(id),
    id_sesion text not null references sesiones(id_sesion),
    id_cancion text not null,
    turno int not null,
    id_usuario text not null,
    puntuacion int not null,
    fecha text not null,
    unique (id_sesion, id_cancion, turno, id_usuario)
);
create index if not exists idx_votos_turno_sesion on votos_turno(id_sesion);

create table if not exists retos (
    id text primary key,
    id_grupo text not null references grupos(id),
    texto text not null,
    dificultad text not null,
    categoria text not null
);
create index if not exists idx_retos_grupo on retos(id_grupo);


-- --------------------------------------------------------------------------
-- Modo salón
-- --------------------------------------------------------------------------

-- Una mesa física del salón, con su QR. El ciclo de vida es por noche: el
-- local la abre cuando se sienta gente y la cierra cuando se va. Cerrarla
-- cancela sus pedidos pendientes — si no, el DJ termina llamando al micrófono
-- a una mesa que ya pagó y se fue, que es el fallo más común de estos sistemas.
create table if not exists mesas (
    id text primary key,
    id_grupo text not null references grupos(id),
    -- Texto y no int a propósito: los locales usan "12", "Barra 3", "VIP 2".
    numero text not null,
    -- El código que va en el QR. Largo (no los 6 dígitos de los grupos):
    -- si fuera corto, cualquiera lo enumera y encola desde afuera del local.
    codigo text not null unique,
    tamano int not null default 2,
    -- Cuántas canciones seguidas puede meter la mesa dentro de una misma
    -- ronda. Se deriva del tamaño (1 persona -> 1, 2+ -> 2) pero queda
    -- editable porque cada local tiene su criterio de qué es "justo".
    cupo_por_ronda int not null default 2,
    estado text not null default 'Cerrada',
    id_sesion text,
    -- Ronda de la rotación en la que entró al abrirse. Es lo que hace que una
    -- mesa que llega a las 11 de la noche no se cuele al principio de la cola
    -- ni quede al final de todo: arranca en la vuelta que está corriendo.
    ronda_base int not null default 0,
    fecha_apertura text not null default ''
);
create index if not exists idx_mesas_grupo on mesas(id_grupo);
create unique index if not exists idx_mesas_grupo_numero on mesas(id_grupo, numero);

-- Canciones que el cliente pidió y el local no tiene en su catálogo. No entran
-- a la rotación (el DJ no las puede poner); le llegan como sugerencia para que
-- el local sepa qué le falta comprar.
create table if not exists sugerencias_mesa (
    id bigserial primary key,
    id_grupo text not null references grupos(id),
    id_sesion text not null,
    id_mesa text not null,
    titulo text not null,
    artista text not null default '',
    pedido_por text not null default '',
    fecha text not null
);
create index if not exists idx_sug_mesa_sesion on sugerencias_mesa(id_sesion);
