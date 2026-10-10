#!/usr/bin/env python3
"""Dibuja un gráfico de radar (SVG oscuro y claro) a partir de un JSON.

Uso:
    python scripts/radar.py --data assets/skills.json -o assets/radar
    python scripts/radar.py --data assets/langmix.json -o assets/radar-langs --values

El JSON tiene la forma:
    {"title": "...", "axes": [{"label": "C#", "value": 80}, ...]}
Los valores van de 0 a 100. Solo usa la biblioteca estándar.
"""

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path

FONT = "ui-sans-serif,-apple-system,Segoe UI,Helvetica,Arial,sans-serif"

THEMES = {
    "dark": {
        "title": "#E6EDF3", "label": "#C9D1D9", "value": "#8B949E",
        "ring": "#30363D", "spoke": "#21262D",
        "fill": "#4FC3F7", "stroke": "#4FC3F7", "dot": "#B3E5FC",
    },
    "light": {
        "title": "#1F2328", "label": "#24292F", "value": "#57606A",
        "ring": "#D0D7DE", "spoke": "#E6EAEF",
        "fill": "#0277BD", "stroke": "#0277BD", "dot": "#FFFFFF",
    },
}

W, H = 620, 470
R = 150
CX, CY = W / 2, 252


def point(i: int, n: int, radius: float) -> tuple[float, float]:
    a = -math.pi / 2 + i * math.tau / n
    return radius * math.cos(a), radius * math.sin(a)


def pts(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def build(data: dict, theme: str, show_values: bool) -> str:
    t = THEMES[theme]
    axes = data["axes"]
    n = len(axes)
    title = html.escape(data.get("title", ""))

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-label="{title}" font-family="{FONT}">',
        f'<text x="{W / 2}" y="28" text-anchor="middle" font-size="16" font-weight="700" fill="{t["title"]}">{title}</text>',
        f'<g transform="translate({CX},{CY})">',
    ]

    # Anillos de referencia (25 / 50 / 75 / 100) y radios
    for k in (1.0, 0.75, 0.5, 0.25):
        ring = [point(i, n, R * k) for i in range(n)]
        out.append(f'<polygon points="{pts(ring)}" fill="none" stroke="{t["ring"]}" stroke-width="1"/>')
    for i in range(n):
        x, y = point(i, n, R)
        out.append(f'<line x1="0" y1="0" x2="{x:.1f}" y2="{y:.1f}" stroke="{t["spoke"]}"/>')

    # Área de valores, crece desde el centro al cargar
    shape = [point(i, n, R * max(0, min(100, a["value"])) / 100) for i, a in enumerate(axes)]
    out.append(
        '<g><animateTransform attributeName="transform" type="scale" values="0.05;1" dur="1.1s" '
        'calcMode="spline" keyTimes="0;1" keySplines="0.22 1 0.36 1" fill="freeze"/>'
    )
    out.append(
        f'<polygon points="{pts(shape)}" fill="{t["fill"]}" fill-opacity="0.22" '
        f'stroke="{t["stroke"]}" stroke-width="2.5" stroke-linejoin="round"/>'
    )
    for x, y in shape:
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.8" fill="{t["dot"]}" stroke="{t["stroke"]}" stroke-width="1.5"/>')
    out.append("</g>")

    # Etiquetas
    for i, a in enumerate(axes):
        x, y = point(i, n, R + 22)
        anchor = "middle" if abs(x) < 8 else ("start" if x > 0 else "end")
        dy = -4 if y < -R * 0.9 else (14 if y > R * 0.9 else 4)
        label = html.escape(a["label"])
        out.append(
            f'<text x="{x:.1f}" y="{y + dy:.1f}" text-anchor="{anchor}" font-size="13" '
            f'font-weight="600" fill="{t["label"]}">{label}'
        )
        if show_values:
            out.append(f'<tspan fill="{t["value"]}" font-weight="400"> {a["value"]}</tspan>')
        out.append("</text>")

    out.append("</g></svg>")
    return "".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("-o", "--out", required=True, help="prefijo de salida, ej. assets/radar")
    ap.add_argument("--values", action="store_true", help="mostrar el número junto a cada etiqueta")
    args = ap.parse_args()

    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    for theme in THEMES:
        path = Path(f"{args.out}-{theme}.svg")
        path.write_text(build(data, theme, args.values), encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
