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
