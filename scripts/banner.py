#!/usr/bin/env python3
"""Genera el banner animado del perfil (versión oscura y clara).

Uso, desde la raíz del repositorio:
    python scripts/banner.py

Requiere: numpy, Pillow  (pip install -r scripts/requirements.txt)
"""

from __future__ import annotations

import html
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/source/foto.png"
ASSETS = ROOT / "assets"

W, H = 1180, 600
SEED = 2025
MONO = "ui-monospace,SFMono-Regular,Cascadia Code,Consolas,Menlo,monospace"

# Filas del "terminal". Edita aquí tus datos y vuelve a correr el script.
ROWS = [
    ("Nombre",        "Luis Antonio Olvera"),
    ("Rol",           "Desarrollador de Software · Junior"),
    ("Origen",        "Guayaquil, Ecuador"),
    ("Educación",     "ITS Liceo Cristiano · Egresado"),
    ("Estado",        "Buscando mi primera oportunidad"),
    ("Core.Lenguajes", "C# · Python · TypeScript · JavaScript"),
    ("Core.Frontend", "Angular · React · HTML · CSS"),
    ("Core.Backend",  "ASP.NET · Django · Node / Express"),
    ("Core.Mobile",   ".NET MAUI (.NET 10)"),
    ("Core.BD",       "SQL Server · MySQL · MongoDB"),
    ("Core.Infra",    "VirtualBox · Redes · Git"),
    ("Red.Mail",      "luis-olv@outlook.es"),
    ("Red.GitHub",    "github.com/laor25"),
]

THEMES = {
    "dark": {
        "bg": "#0A0F1C", "panel": "#0F1729", "bar": "#131D33", "line": "#1E2A44",
        "muted": "#7C8BA5", "text": "#E2E8F0", "key": "#4FC3F7",
        "portrait": "#4FC3F7", "ok": "#22C55E", "shadow": "#02050B",
    },
    "light": {
        "bg": "#F6F8FA", "panel": "#FFFFFF", "bar": "#EEF2F6", "line": "#D0D9E3",
        "muted": "#5B6B82", "text": "#0F172A", "key": "#0277BD",
        "portrait": "#0B3B5C", "ok": "#16A34A", "shadow": "#AAB7C4",
    },
}

# Zona del retrato dentro del banner
PX, PY, PW, PH = 46, 108, 380, 440
CELL = 3  # separación entre puntos
SCAN_START, SCAN_DUR = 0.3, 2.4  # el escaneo inicial "dibuja" el retrato


def portrait_dots(theme: str) -> list[tuple[float, float, float]]:
    """Convierte la foto en puntos de semitono (x, y, radio) en coordenadas del banner."""
    cols, rows = PW // CELL, PH // CELL
    src = Image.open(SOURCE).convert("RGB")
    # Recorta las franjas negras laterales y encuadra cabeza + hombros
    src = src.crop((132, 0, 618, 560))
    # Se trabaja a 4x de resolución y luego se promedia por celda: más detalle
    big = src.resize((cols * 4, rows * 4), Image.Resampling.LANCZOS)

    rgb = np.asarray(big, dtype=np.float32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    # Fondo celeste: azul y verde altos, rojo bajo
    background = (b - r > 55) & (g - r > 35)
    mask = (
        Image.fromarray(np.uint8(~background) * 255, "L")
        .filter(ImageFilter.MedianFilter(5))
        .filter(ImageFilter.GaussianBlur(2))
        .resize((cols, rows), Image.Resampling.BOX)
    )
    mask = np.asarray(mask, dtype=np.float32) / 255.0

    # Contraste local (imagen menos su desenfoque) para resaltar ojos, lentes y boca
    gray = ImageOps.grayscale(big)
    g_ = np.asarray(gray, dtype=np.float32)
    blur = np.asarray(gray.filter(ImageFilter.GaussianBlur(24)), dtype=np.float32)
    mix = 0.55 * g_ + 0.45 * np.clip(128 + (g_ - blur) * 1.6, 0, 255)
    small = Image.fromarray(np.uint8(np.clip(mix, 0, 255))).resize((cols, rows), Image.Resampling.BOX)
    small = ImageOps.autocontrast(small, cutoff=1, mask=Image.fromarray(np.uint8(mask > 0.5) * 255))
    lum = np.asarray(small, dtype=np.float32) / 255.0

    if theme == "dark":
        # Puntos claros sobre fondo oscuro; un mínimo para que pelo y ropa se vean
        tone = np.maximum(0.13, 0.03 + 0.97 * lum ** 2.2)
    else:
        # Puntos oscuros sobre fondo claro
        tone = 0.10 + 0.90 * (1.0 - lum) ** 1.1
    tone = np.clip(tone, 0, 1) * mask

    dots = []
    for y in range(rows):
        for x in range(cols):
            v = float(tone[y, x])
            if v < 0.06:
                continue
            radius = (0.2 + 1.3 * v) if theme == "dark" else (0.25 + 1.35 * v ** 0.5)
            dots.append((PX + x * CELL + CELL / 2, PY + y * CELL + CELL / 2, radius))
    return dots


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def build(theme: str) -> str:
    t = THEMES[theme]
    rng = np.random.default_rng(SEED)
    dots = portrait_dots(theme)

    out: list[str] = []
    add = out.append
    add(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-label="profile.sh --live · Luis Antonio Olvera" font-family="{MONO}">'
    )
    add(
        "<defs>"
        f'<clipPath id="pc"><rect x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="8"/></clipPath>'
        f'<linearGradient id="scan" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{t["key"]}" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{t["key"]}" stop-opacity="0.28"/></linearGradient>'
        "</defs>"
    )

    # Ventana
    add(f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>')
    add(f'<rect x="16" y="18" width="{W - 32}" height="{H - 36}" rx="14" fill="{t["shadow"]}" opacity="0.35"/>')
    add(f'<rect x="14" y="14" width="{W - 28}" height="{H - 36}" rx="14" fill="{t["panel"]}" stroke="{t["line"]}"/>')
    add(f'<path d="M14 28a14 14 0 0 1 14-14h{W - 56}a14 14 0 0 1 14 14v26H14z" fill="{t["bar"]}"/>')
    add(f'<line x1="14" y1="54" x2="{W - 14}" y2="54" stroke="{t["line"]}"/>')
    for i, c in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
        add(f'<circle cx="{40 + i * 22}" cy="34" r="6.5" fill="{c}"/>')
    add(
        f'<text x="{W / 2}" y="39" text-anchor="middle" font-size="13" fill="{t["muted"]}">'
        "laor25@github: ~/perfil — profile.sh --live</text>"
    )

    # Panel del retrato
    add(f'<rect x="{PX - 12}" y="{PY - 36}" width="{PW + 24}" height="{PH + 48}" rx="10" fill="none" stroke="{t["line"]}"/>')
    add(f'<text x="{PX}" y="{PY - 14}" font-size="12" fill="{t["muted"]}" letter-spacing="1.5">VISUAL.MAP</text>')
    add(f'<text x="{PX + PW}" y="{PY - 14}" text-anchor="end" font-size="12" fill="{t["ok"]}">● live</text>')

    # Los puntos aparecen franja por franja, justo cuando pasa la línea de escaneo
    band_h = CELL * 4
    bands: dict[int, list[str]] = {}
    for x, y, rad in dots:
        bands.setdefault(int((y - PY) // band_h), []).append(
            f'<circle cx="{x:g}" cy="{y:g}" r="{rad:.2f}"/>'
        )
    add(f'<g clip-path="url(#pc)">')
    add(f'<g fill="{t["portrait"]}">')
    for i in sorted(bands):
        begin = SCAN_START + SCAN_DUR * (i * band_h) / PH
        add(
            f'<g opacity="0"><animate attributeName="opacity" values="0;1" begin="{begin:.2f}s" '
            f'dur="0.25s" fill="freeze"/>{"".join(bands[i])}</g>'
        )
    add("</g>")

    # Líneas horizontales finas tipo monitor CRT
    add(
        f'<pattern id="crt" width="4" height="4" patternUnits="userSpaceOnUse">'
        f'<rect width="4" height="1" fill="{t["panel"]}" opacity="0.35"/></pattern>'
        f'<rect x="{PX}" y="{PY}" width="{PW}" height="{PH}" fill="url(#crt)"/>'
    )

    # Línea de escaneo: primero dibuja el retrato y luego sigue pasando suave
    def scanline(begin: str, dur: float, opacity: float, repeat: str) -> str:
        return (
            f'<g opacity="{opacity}">'
            f'<rect x="{PX}" y="-60" width="{PW}" height="60" fill="url(#scan)"/>'
            f'<rect x="{PX}" y="-1.5" width="{PW}" height="2" fill="{t["key"]}"/>'
            f'<animateTransform attributeName="transform" type="translate" values="0 {PY - 2};0 {PY + PH + 60}" '
            f'begin="{begin}" dur="{dur}s" {repeat}/></g>'
        )

    add(f'<g>{scanline(f"{SCAN_START}s", SCAN_DUR, 1, "fill=" + chr(34) + "remove" + chr(34))}</g>')
    loop_begin = SCAN_START + SCAN_DUR + 1.0
    add(f'<g>{scanline(f"{loop_begin}s", 6, 0.45, "repeatCount=" + chr(34) + "indefinite" + chr(34))}</g>')
    add("</g>")

    # Terminal de datos
    tx, ty = 480, 100
    lh = 29
    add(f'<text x="{tx}" y="{ty}" font-size="16" fill="{t["ok"]}">$<tspan fill="{t["text"]}"> ./profile.sh --live</tspan></text>')
    add(f'<line x1="{tx}" y1="{ty + 14}" x2="{W - 46}" y2="{ty + 14}" stroke="{t["line"]}" stroke-dasharray="3 5"/>')

    key_w = 170
    start = 1.4
    step = 0.22
    for i, (k, v) in enumerate(ROWS):
        y = ty + 46 + i * lh
        begin = start + i * step
        # Revelado tipo "escritura": un clip que crece de izquierda a derecha
        cid = f"r{i}"
        add(
            f'<clipPath id="{cid}"><rect x="{tx}" y="{y - 20}" width="0" height="28">'
            f'<animate attributeName="width" from="0" to="{W - tx - 40}" begin="{begin:.2f}s" dur="0.55s" fill="freeze"/>'
            "</rect></clipPath>"
        )
        add(
            f'<g clip-path="url(#{cid})" font-size="15">'
            f'<text x="{tx}" y="{y}" fill="{t["key"]}">{esc(k)}</text>'
            f'<text x="{tx + key_w}" y="{y}" fill="{t["muted"]}">:</text>'
            f'<text x="{tx + key_w + 18}" y="{y}" fill="{t["text"]}">{esc(v)}</text>'
            "</g>"
        )

    # Barra de estado + cursor parpadeante
    end = start + len(ROWS) * step + 0.4
    sy = ty + 46 + len(ROWS) * lh + 10
    status = "$ abierto_a_trabajar --junior --practicas --remoto"
    add(f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{end:.2f}s" dur="0.4s" fill="freeze"/>')
    add(
        f'<text x="{tx}" y="{sy}" font-size="15" fill="{t["ok"]}">$<tspan fill="{t["text"]}"> abierto_a_trabajar</tspan>'
        f'<tspan fill="{t["muted"]}"> --junior --practicas --remoto</tspan></text>'
    )
    add(
        f'<rect x="{tx + len(status) * 9.05 + 6:.0f}" y="{sy - 15}" width="9" height="19" fill="{t["key"]}">'
        '<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1s" repeatCount="indefinite"/>'
        "</rect>"
    )
    add("</g>")

    add(
        f'<text x="{W - 36}" y="39" text-anchor="end" font-size="12" fill="{t["muted"]}">'
        "GYE · UTC-5</text>"
    )
    add("</svg>")
    return "".join(out)


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    for theme in THEMES:
        svg = build(theme)
        path = ASSETS / f"banner-{theme}.svg"
        path.write_text(svg, encoding="utf-8")
        print(f"{path.relative_to(ROOT)}  {len(svg) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
