// Claves de localStorage compartidas entre GroupContext e IdentityContext.
// Viven acá (no en ninguno de los dos contexts) para que ninguno tenga que
// importar del otro.
export const GRUPO_STORAGE_KEY = "kt_grupo";

// Sesión del DJ en modo salón: {id_grupo, nombre, codigo}. Separada de la del
// grupo porque el DJ entra con su propio código y su celular no está unido a
// ninguna sala.
export const DJ_STORAGE_KEY = "kt_dj";

// Nombre que escribió el cliente en la mesa, por código de mesa. Se guarda
// para no volver a pedírselo en cada canción que encola.
export function nombreMesaStorageKey(codigo) {
  return `kt_mesa_nombre_${codigo}`;
}

// "No me ofrezcas más instalar la app". No se borra al cerrar sesión: es una
// preferencia del dispositivo, no del grupo.
export const INSTALAR_STORAGE_KEY = "kt_instalar_oculto";

export function usuarioStorageKey(idGrupo) {
  return `kt_usuario_${idGrupo}`;
}
