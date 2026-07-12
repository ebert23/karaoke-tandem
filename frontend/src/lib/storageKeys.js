// Claves de localStorage compartidas entre GroupContext e IdentityContext.
// Viven acá (no en ninguno de los dos contexts) para que ninguno tenga que
// importar del otro.
export const GRUPO_STORAGE_KEY = "kt_grupo";

export function usuarioStorageKey(idGrupo) {
  return `kt_usuario_${idGrupo}`;
}
