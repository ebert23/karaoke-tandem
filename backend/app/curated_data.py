"""Datos curados a mano, sin dependencia de ninguna base de datos: retos
default para un grupo nuevo y sugerencias de canciones por género."""

DEFAULT_RETOS: list[list[str]] = [
    ["Canta agachado toda la canción", "Fácil", "Normal"],
    ["Cambia la letra por algo gracioso en el coro", "Medio", "Creativo"],
    ["Baila sin cantar los primeros 15 segundos", "Fácil", "Normal"],
    ["Cántale la canción a alguien del grupo mirándolo a los ojos", "Medio", "Picante"],
    ["Todo el grupo debe hacer los coros contigo", "Fácil", "Grupo"],
    ["Inventa una coreografía en 10 segundos y úsala toda la canción", "Difícil", "Creativo"],
    ["Canta con acento de otro país", "Medio", "Creativo"],
    ["Elige a alguien para que sea tu dueto sorpresa", "Medio", "Grupo"],
    ["Si te equivocas en la letra, debes repetir la estrofa bailando", "Difícil", "Picante"],
    ["Regala un piropo cantado a alguien del público antes de empezar", "Fácil", "Picante"],
    ["Canta esta canción como si fueras del género contrario al tuyo", "Medio", "Creativo"],
    ["Canta con un estilo de voz totalmente opuesto al tuyo (agudo si sos grave, grave si sos agudo)", "Difícil", "Creativo"],

    # Los 12 de arriba dejaban categorías de 2 retos: al filtrar por "Normal"
    # o por "Grupo" salía siempre el mismo. Estos 21 emparejan las cuatro
    # categorías en 8-9 cada una, que alcanza para una noche entera sin que
    # se note la repetición.
    ["Canta la primera estrofa con los ojos cerrados", "Fácil", "Normal"],
    ["Sostén el micrófono con la mano que no usas normalmente", "Fácil", "Normal"],
    ["Canta de espaldas al público hasta que llegue el coro", "Fácil", "Normal"],
    ["No puedes soltar el micrófono ni apoyarlo hasta terminar", "Medio", "Normal"],
    ["Canta sentado en el piso toda la canción", "Fácil", "Normal"],
    ["Cada vez que digas la palabra que más se repite en la canción, levanta la mano", "Medio", "Normal"],

    ["Dedícale la canción a alguien del grupo y di por qué antes de empezar", "Medio", "Picante"],
    ["Elige a alguien para que te acompañe al frente, aunque no cante nada", "Fácil", "Picante"],
    ["Antes de empezar, confiesa la canción que te da vergüenza que te guste", "Medio", "Picante"],
    ["Si desafinas, el grupo elige tu próxima canción", "Difícil", "Picante"],
    ["Termina la canción de rodillas, como si fuera la balada más trágica del mundo", "Medio", "Picante"],

    ["Canta la canción como si estuvieras narrando un partido de fútbol", "Difícil", "Creativo"],
    ["Reemplaza todas las vocales por la letra 'i' cuando llegue el coro", "Difícil", "Creativo"],
    ["Susurra toda la estrofa y grita el coro", "Medio", "Creativo"],
    ["Presenta la canción como locutor de radio antes de empezar", "Fácil", "Creativo"],

    ["El grupo elige una palabra prohibida: si la cantas, todos gritan", "Medio", "Grupo"],
    ["Todos tienen que bailar sentados mientras cantas", "Fácil", "Grupo"],
    ["Elige a dos personas para que sean tus bailarines de fondo", "Fácil", "Grupo"],
    ["El grupo canta el coro y tú solo las estrofas", "Fácil", "Grupo"],
    ["El primero que se ría canta la siguiente contigo", "Medio", "Grupo"],
    ["Todos aplauden al ritmo hasta que termines", "Fácil", "Grupo"],
]

# Sugerencias de canciones populares por género, para el modal de "agregar
# canción" (chips de un click). Curada a mano — no depende de cuota de
# ninguna API externa. El link queda vacío a propósito: el usuario lo
# completa buscando en YouTube o pegándolo manualmente.
SUGERENCIAS_POR_GENERO: dict[str, list[tuple[str, str]]] = {
    "Pop": [
        ("Shape of You", "Ed Sheeran"),
        ("Blinding Lights", "The Weeknd"),
        ("Levitating", "Dua Lipa"),
    ],
    "Rock": [
        ("Livin' on a Prayer", "Bon Jovi"),
        ("Zombie", "The Cranberries"),
        ("De Musica Ligera", "Soda Stereo"),
    ],
    "Balada": [
        ("Perfect", "Ed Sheeran"),
        ("Un Beso", "Aventura"),
        ("Amor Eterno", "Rocio Durcal"),
    ],
    "Reggaeton": [
        ("Danza Kuduro", "Don Omar"),
        ("Gasolina", "Daddy Yankee"),
        ("Vivir Mi Vida", "Marc Anthony"),
    ],
    "Cumbia": [
        ("La Cumbia del Rio", "Los Angeles Azules"),
        ("El Sonidito", "Hechizeros Band"),
        ("Cumbia Sobre el Rio", "Selena"),
    ],
    "Salsa": [
        ("Vivir Mi Vida", "Marc Anthony"),
        ("La Vida es un Carnaval", "Celia Cruz"),
        ("Pedro Navaja", "Ruben Blades"),
    ],
    "Norteña": [
        ("El Rey", "Vicente Fernandez"),
        ("Cielito Lindo", "Ana Gabriel"),
        ("Volver Volver", "Vicente Fernandez"),
    ],
}
