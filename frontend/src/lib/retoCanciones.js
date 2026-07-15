// Canciones sugeridas para acompañar un reto. Listas curadas a mano, sin
// depender de ninguna cuenta/dato del usuario — no se guarda género de
// nadie, así que en vez de apuntar al género real de quien canta, el
// sistema sortea entre estos baldes al azar. A veces coincide, a veces
// cruza, mismo efecto sorpresa sin agregar un campo nuevo a los perfiles.

const FEMENINAS_FUERTES = [
  { titulo: "Rolling in the Deep", artista: "Adele" },
  { titulo: "Someone Like You", artista: "Adele" },
  { titulo: "Hips Don't Lie", artista: "Shakira" },
  { titulo: "La Soledad", artista: "Laura Pausini" },
  { titulo: "Bad Guy", artista: "Billie Eilish" },
  { titulo: "Firework", artista: "Katy Perry" },
  { titulo: "Halo", artista: "Beyoncé" },
];

const MASCULINAS_FUERTES = [
  { titulo: "Vivir Mi Vida", artista: "Marc Anthony" },
  { titulo: "Lose Yourself", artista: "Eminem" },
  { titulo: "Callaita", artista: "Bad Bunny" },
  { titulo: "Livin' on a Prayer", artista: "Bon Jovi" },
  { titulo: "Despacito", artista: "Luis Fonsi" },
  { titulo: "El Rey", artista: "Vicente Fernández" },
  { titulo: "Suavemente", artista: "Elvis Crespo" },
];

const DIFICILES_DIVERTIDAS = [
  { titulo: "Rap God", artista: "Eminem" },
  { titulo: "Bohemian Rhapsody", artista: "Queen" },
  { titulo: "I Will Always Love You", artista: "Whitney Houston" },
  { titulo: "Livin' la Vida Loca", artista: "Ricky Martin" },
  { titulo: "Como La Flor", artista: "Selena" },
];

const BALDES = [
  { lista: FEMENINAS_FUERTES, etiqueta: "🎤 Power vocal femenino" },
  { lista: MASCULINAS_FUERTES, etiqueta: "🎤 Power vocal masculino" },
  { lista: DIFICILES_DIVERTIDAS, etiqueta: "🔥 Reto extra difícil" },
];

export function elegirCancionAsignada() {
  const balde = BALDES[Math.floor(Math.random() * BALDES.length)];
  const cancion = balde.lista[Math.floor(Math.random() * balde.lista.length)];
  return { ...cancion, etiqueta: balde.etiqueta };
}
