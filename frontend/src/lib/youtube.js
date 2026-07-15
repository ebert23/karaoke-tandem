// Extrae el ID de video de un link de YouTube en cualquier formato común.
// link_youtube es texto libre (pegado a mano o desde la búsqueda), así que
// esto tiene que ser tolerante y devolver null si no reconoce nada.
export function extractVideoId(url) {
  if (!url) return null;
  const patrones = [
    /(?:youtu\.be\/)([\w-]{11})/,
    /(?:youtube\.com\/watch\?.*[?&]v=)([\w-]{11})/,
    /(?:youtube\.com\/embed\/)([\w-]{11})/,
    /(?:youtube\.com\/shorts\/)([\w-]{11})/,
  ];
  for (const patron of patrones) {
    const m = url.match(patron);
    if (m) return m[1];
  }
  return null;
}
