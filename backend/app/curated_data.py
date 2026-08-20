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

    # Categoría aparte y no mezclada en "Picante" a propósito: no todas las
    # noches se toma (una reunión de trabajo, gente manejando, quien no bebe),
    # y teniéndola separada el grupo la incluye o la saca de un toque en vez
    # de tener que borrar reto por reto.
    ["Shot de afinación: toma 1 shot antes de empezar para calentar las cuerdas", "Fácil", "Shots"],
    ["El culpable paga: quien agregó esta canción a la lista toma 1 shot solidario contigo", "Fácil", "Shots"],
    ["Veredicto del jurado: al terminar el grupo vota con el pulgar, y si gana el pulgar abajo tomas 1 shot", "Medio", "Shots"],
    ["Shot doble de escape: puedes pasarle esta canción a otro, pero pagas 2 shots de penalización", "Medio", "Shots"],
    ["Shot cruzado: elige a alguien y tomen un shot con los brazos entrelazados justo antes del coro", "Fácil", "Shots"],
    ["El brindis dramático: pausa antes del coro final, da un discurso emotivo de 15 segundos y brinda con todos", "Medio", "Shots"],
    ["Ruleta rusa: gira una botella al terminar, y a quien apunte toma un shot contigo", "Fácil", "Shots"],
    ["Castigo por risa: si te da un ataque de risa y dejas de cantar más de 3 segundos, pagas 1 shot al final", "Medio", "Shots"],
    ["La ronda de la victoria: si logras que toda la sala cante el coro con los brazos arriba, todos toman menos tú", "Difícil", "Shots"],
    ["Doble o nada: al terminar pide votación. Si es unánime mandas 1 shot a quien quieras; si una sola persona vota en contra, te lo tomas tú", "Difícil", "Shots"],
    ["Shot por gallo: marca una raya cada vez que se te quiebre la voz y toma un shot por cada dos rayas", "Medio", "Shots"],
    ["Bautizo del micrófono: el que canta después de ti elige tu trago y tú eliges el suyo", "Fácil", "Shots"],
    ["Shot del olvido: si tienes que mirar la pantalla más de tres veces porque te perdiste, tomas 1 shot", "Medio", "Shots"],
    ["Brindis por estrofa: antes de cada estrofa levantas el vaso y todos brindan. El que no levante, toma", "Medio", "Shots"],
    ["El precio del aplauso: si nadie aplaude al terminar tomas 1 shot, pero si aplauden de pie eliges a dos que tomen", "Medio", "Shots"],
    ["Shot a ciegas: alguien del grupo te prepara un shot sin decirte qué es y lo tomas antes del último coro", "Difícil", "Shots"],
    ["Cadena de shots: eliges a alguien, esa persona elige a otra y esa a una tercera. Los tres toman contigo al final", "Fácil", "Shots"],
    ["Multa por celular: cualquiera que mire el celular mientras cantas paga 1 shot", "Fácil", "Shots"],
    ["Dueto forzado: canta con quien tengas a la derecha, y si cualquiera de los dos se equivoca toman ambos", "Medio", "Shots"],
    ["Impuesto al desafinado: el que se ría de cómo cantas toma 1 shot, pero si desafinas feo lo tomas tú", "Medio", "Shots"],
    ["La última nota: si sostienes la última nota más de 5 segundos, todos toman un shot en tu honor", "Difícil", "Shots"],
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
