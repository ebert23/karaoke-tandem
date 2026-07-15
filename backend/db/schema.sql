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

create table if not exists grupos (
    id text primary key,
    nombre text not null,
    codigo text not null unique,
    foto text not null default '',
    admins text[] not null default '{}',
    fecha_creacion text not null
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
create table if not exists canciones_sesion (
    id bigserial primary key,
    id_sesion text not null references sesiones(id_sesion),
    id_grupo text not null references grupos(id),
    id_cancion text not null,
    orden int not null default 0,
    turno int not null default 0,
    cantada_por text not null default '',
    puntuacion int,
    estado text not null
);
create index if not exists idx_cs_sesion on canciones_sesion(id_sesion);
create index if not exists idx_cs_grupo on canciones_sesion(id_grupo);

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
