"""Genera los PNG de la app a partir del mismo dibujo que public/icons/icon.svg.

Existe porque Android e iOS **no aceptan un icono SVG** para instalar la app:
Chrome exige al menos un PNG de 192 y otro de 512 en el manifest para ofrecer
"Instalar", y iOS solo mira el apple-touch-icon PNG. Con el SVG solo, la app
se veía bien en el navegador pero no aparecía como instalable.

Es una herramienta de una sola vez: los PNG quedan versionados en el repo, así
que el build no depende de Python ni de Pillow. Correr solo si cambia el dibujo:

    backend/.venv_check/Scripts/python.exe frontend/scripts/generar_iconos.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

DESTINO = Path(__file__).resolve().parents[1] / "public" / "icons"

FONDO = (10, 10, 15)          # #0a0a0f, igual que theme_color
DESDE = (168, 85, 247)        # #a855f7
HASTA = (255, 47, 176)        # #ff2fb0

LADO = 2048                   # se dibuja grande y se reduce: bordes suaves
ESCALA = LADO / 512           # el SVG original está en un lienzo de 512


def _px(v: float) -> float:
    return v * ESCALA


def _degradado() -> Image.Image:
    """Degradado diagonal, el mismo que el linearGradient del SVG."""
    grad = Image.new("RGB", (LADO, LADO))
    pixeles = grad.load()
    for y in range(LADO):
        for x in range(LADO):
            t = (x + y) / (2 * (LADO - 1))
            pixeles[x, y] = tuple(int(a + (b - a) * t) for a, b in zip(DESDE, HASTA))
    return grad


def _mascara_microfono() -> Image.Image:
    """Silueta del micrófono en blanco sobre negro, para usar de máscara."""
    m = Image.new("L", (LADO, LADO), 0)
    d = ImageDraw.Draw(m)
    cx, cy = _px(256), _px(246)
    grosor = int(_px(18))

    # Cápsula del micrófono.
    d.rounded_rectangle(
        [cx - _px(52), cy - _px(150), cx + _px(52), cy + _px(26)],
        radius=_px(52), fill=255,
    )
    # Arco que lo abraza (media circunferencia inferior, radio 96).
    d.arc(
        [cx - _px(96), cy - _px(106), cx + _px(96), cy + _px(86)],
        start=0, end=180, fill=255, width=grosor,
    )
    # Pie y base.
    d.line([cx, cy + _px(90), cx, cy + _px(140)], fill=255, width=grosor)
    d.line([cx - _px(56), cy + _px(140), cx + _px(56), cy + _px(140)], fill=255, width=grosor)
    # Las puntas redondeadas del SVG (stroke-linecap="round") no las hace line().
    for x, y in ((cx, cy + _px(90)), (cx, cy + _px(140)), (cx - _px(56), cy + _px(140)), (cx + _px(56), cy + _px(140)),
                 (cx - _px(96), cy - _px(10)), (cx + _px(96), cy - _px(10))):
        d.ellipse([x - grosor / 2, y - grosor / 2, x + grosor / 2, y + grosor / 2], fill=255)
    return m


def _arte(escala_contenido: float = 1.0) -> Image.Image:
    """Micrófono con degradado sobre el fondo oscuro, sin recortar esquinas."""
    lienzo = Image.new("RGB", (LADO, LADO), FONDO)
    mascara = _mascara_microfono()
    if escala_contenido != 1.0:
        chico = int(LADO * escala_contenido)
        borde = (LADO - chico) // 2
        mascara = Image.new("L", (LADO, LADO), 0)
        mascara.paste(_mascara_microfono().resize((chico, chico), Image.LANCZOS), (borde, borde))
    lienzo.paste(_degradado(), (0, 0), mascara)
    return lienzo


def _con_esquinas(img: Image.Image) -> Image.Image:
    """Recorta las esquinas con el mismo radio que el SVG (rx=96 sobre 512)."""
    mascara = Image.new("L", (LADO, LADO), 0)
    ImageDraw.Draw(mascara).rounded_rectangle([0, 0, LADO - 1, LADO - 1], radius=_px(96), fill=255)
    salida = Image.new("RGBA", (LADO, LADO), (0, 0, 0, 0))
    salida.paste(img, (0, 0), mascara)
    return salida


def guardar(img: Image.Image, nombre: str, lado: int) -> None:
    ruta = DESTINO / nombre
    img.resize((lado, lado), Image.LANCZOS).save(ruta, "PNG")
    print(f"  {nombre} ({lado}x{lado})")


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    print(f"Generando iconos en {DESTINO}")

    redondeado = _con_esquinas(_arte())
    guardar(redondeado, "icon-192.png", 192)
    guardar(redondeado, "icon-512.png", 512)

    # Maskable: Android le aplica SU propia forma (círculo, squircle, etc.) y
    # recorta hasta un 20% del borde, así que va a sangre y con el dibujo más
    # chico para que no le corte la base del micrófono.
    guardar(_arte(escala_contenido=0.62), "icon-maskable-512.png", 512)

    # iOS ignora el manifest y usa esto; también redondea por su cuenta, así
    # que se le manda cuadrado y opaco (un PNG con alfa le sale con bordes negros).
    guardar(_arte(), "apple-touch-icon-180.png", 180)


if __name__ == "__main__":
    main()
