// Link de invitación al grupo: lleva directo a la sala (auto-join al abrirlo).
export function linkInvitacion(grupo) {
  return `${window.location.origin}${window.location.pathname}#/?codigo=${grupo.codigo}`;
}
