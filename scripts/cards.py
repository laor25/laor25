#!/usr/bin/env python3
"""Genera tarjetas SVG propias (sin servicios externos que se caen):

  - card-stats-{dark,light}.svg     estrellas, repos, seguidores, contribuciones, rachas
  - card-langs-{dark,light}.svg     lenguajes más usados en repos públicos
  - card-<repo>-{dark,light}.svg    una tarjeta por proyecto de assets/projects.json

Uso:
    GITHUB_TOKEN=... python scripts/cards.py --user laor25 --projects assets/projects.json --out assets

Solo considera repositorios PÚBLICOS. Solo usa la biblioteca estándar.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import urllib.request
from pathlib import Path

API = "https://api.github.com"
FONT = "ui-sans-serif,-apple-system,Segoe UI,Helvetica,Arial,sans-serif"

THEMES = {
    "dark": {"bg": "#0D1117", "border": "#30363D", "title": "#4FC3F7", "text": "#E6EDF3",
             "muted": "#8B949E", "track": "#21262D"},
    "light": {"bg": "#FFFFFF", "border": "#D0D7DE", "title": "#0277BD", "text": "#1F2328",
              "muted": "#57606A", "track": "#EAEEF2"},
}

# Colores de lenguajes (los mismos que usa GitHub)
LANG_COLORS = {
    "C#": "#178600", "Python": "#3572A5", "JavaScript": "#F1E05A", "TypeScript": "#3178C6",
    "HTML": "#E34C26", "CSS": "#663399", "SCSS": "#C6538C", "Java": "#B07219",
    "TSQL": "#E38C00", "PLpgSQL": "#336790", "Shell": "#89E051", "PowerShell": "#012456",
    "Dockerfile": "#384D54", "Vue": "#41B883", "PHP": "#4F5D95",
}


def request(url: str, token: str | None, body: dict | None = None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "laor25-profile-cards"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def public_repos(user: str, token: str | None) -> list[dict]:
    repos, page = [], 1
    while True:
        batch = request(f"{API}/users/{user}/repos?type=owner&per_page=100&page={page}", token)
        repos += [r for r in batch if not r.get("private")]
        if len(batch) < 100:
            return repos
        page += 1


def contributions(user: str, token: str | None) -> dict | None:
    """Contribuciones del último año y rachas (requiere token para GraphQL)."""
    if not token:
        return None
    q = """query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{
           totalContributions weeks{contributionDays{date contributionCount}}}}}}"""
    try:
        res = request(f"{API}/graphql", token, {"query": q, "variables": {"u": user}})
        cal = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    except Exception as e:  # sin permisos o sin red: la tarjeta sale con menos datos
        print("contribuciones no disponibles:", e)
        return None

    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] > 0 else 0
        longest = max(longest, run)
    # La racha actual no se rompe si hoy todavía no hay contribuciones
    current = 0
    today = dt.date.today().isoformat()
    for d in reversed(days):
        if d["contributionCount"] > 0:
            current += 1
        elif d["date"] == today and current == 0:
            continue
        else:
            break
    return {"total": cal["totalContributions"], "current": current, "longest": longest}


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def svg_open(w: int, h: int, label: str, t: dict) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" aria-label="{esc(label)}" font-family="{FONT}">',
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="10" fill="{t["bg"]}" stroke="{t["border"]}"/>',
    ]


def stats_card(user: str, followers: int, repos: list[dict], contrib: dict | None, theme: str) -> str:
    t = THEMES[theme]
    own = [r for r in repos if not r["fork"]]
    tiles = [
        (sum(r["stargazers_count"] for r in own), "Estrellas"),
        (len(own), "Repos públicos"),
        (followers, "Seguidores"),
    ]
    if contrib:
        tiles += [
            (contrib["total"], "Contribuciones (1 año)"),
            (contrib["current"], "Racha actual (días)"),
            (contrib["longest"], "Racha más larga (días)"),
        ]
    rows = (len(tiles) + 2) // 3
    w, h = 480, 62 + rows * 46 + 12
    out = svg_open(w, h, f"{user} estadísticas de GitHub", t)
    out.append(f'<text x="22" y="36" font-size="15" font-weight="700" fill="{t["title"]}">{esc(user)}</text>')
    out.append(f'<text x="{w - 22}" y="36" font-size="11" text-anchor="end" fill="{t["muted"]}">en resumen</text>')
    out.append(f'<line x1="22" y1="48" x2="{w - 22}" y2="48" stroke="{t["border"]}"/>')
    for i, (value, label) in enumerate(tiles):
        x = 22 + (i % 3) * 146
        y = 74 + (i // 3) * 46
        out.append(f'<text x="{x}" y="{y}" font-size="23" font-weight="700" fill="{t["text"]}">{value}</text>')
        out.append(f'<text x="{x}" y="{y + 17}" font-size="10.5" fill="{t["muted"]}">{esc(label)}</text>')
    out.append("</svg>")
    return "".join(out)


def langs_card(totals: dict[str, int], theme: str, limit: int = 6) -> str:
    t = THEMES[theme]
    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    total = sum(v for _, v in top) or 1
    w = 480
    h = 96 + ((len(top) + 1) // 2) * 26
    out = svg_open(w, h, "Lenguajes más usados", t)
    out.append(f'<text x="22" y="36" font-size="15" font-weight="700" fill="{t["title"]}">Lenguajes más usados</text>')
    out.append(f'<text x="{w - 22}" y="36" font-size="11" text-anchor="end" fill="{t["muted"]}">repos públicos</text>')

    # Barra segmentada
    bx, by, bw = 22, 54, w - 44
    out.append(f'<clipPath id="bar"><rect x="{bx}" y="{by}" width="{bw}" height="10" rx="5"/></clipPath>')
    out.append(f'<g clip-path="url(#bar)"><rect x="{bx}" y="{by}" width="{bw}" height="10" fill="{t["track"]}"/>')
    x = bx
    for name, v in top:
        seg = bw * v / total
        out.append(f'<rect x="{x:.1f}" y="{by}" width="{seg + 0.5:.1f}" height="10" fill="{LANG_COLORS.get(name, "#8B949E")}"/>')
        x += seg
    out.append("</g>")

    for i, (name, v) in enumerate(top):
        cx = 22 + (i % 2) * 220
        cy = 92 + (i // 2) * 26
        out.append(f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{LANG_COLORS.get(name, "#8B949E")}"/>')
        out.append(
            f'<text x="{cx + 16}" y="{cy}" font-size="12.5" fill="{t["text"]}">{esc(name)}'
            f'<tspan fill="{t["muted"]}"> {100 * v / total:.1f}%</tspan></text>'
        )
    out.append("</svg>")
    return "".join(out)


def wrap(text: str, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        if len(line) + len(word) + 1 > width and line:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines[:2]


def project_card(p: dict, repo: dict | None, theme: str) -> str:
    t = THEMES[theme]
    w, h = 400, 130
    name = p["repo"]
    out = svg_open(w, h, name, t)
    out.append(f'<text x="20" y="34" font-size="15" font-weight="700" fill="{t["title"]}">{esc(p.get("title", name))}</text>')
    for i, line in enumerate(wrap(p.get("description") or (repo or {}).get("description") or "", 54)):
        out.append(f'<text x="20" y="{58 + i * 18}" font-size="12" fill="{t["muted"]}">{esc(line)}</text>')
    lang = p.get("language") or (repo or {}).get("language") or ""
    stars = (repo or {}).get("stargazers_count", 0)
    x = 20
    if lang:
        out.append(f'<circle cx="{x + 5}" cy="{h - 24}" r="5" fill="{LANG_COLORS.get(lang, "#8B949E")}"/>')
        out.append(f'<text x="{x + 15}" y="{h - 20}" font-size="12" fill="{t["text"]}">{esc(lang)}</text>')
        x += 26 + len(lang) * 7.4
    tags = " · ".join(p.get("tags", []))
    if tags:
        out.append(f'<text x="{x}" y="{h - 20}" font-size="11.5" fill="{t["muted"]}">{esc(tags)}</text>')
    out.append(f'<text x="{w - 20}" y="{h - 20}" font-size="12" text-anchor="end" fill="{t["muted"]}">★ {stars}</text>')
    out.append("</svg>")
    return "".join(out)



def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--projects", default="assets/projects.json")
    ap.add_argument("--out", default="assets")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    out = Path(args.out)

    followers = request(f"{API}/users/{args.user}", token)["followers"]
    repos = public_repos(args.user, token)
    by_name = {r["name"]: r for r in repos}
    contrib = contributions(args.user, token)

    # Bytes por lenguaje en repos públicos propios (sin forks ni el repo del perfil)
    totals: dict[str, int] = {}
    for r in repos:
        if r["fork"] or r["name"].lower() == args.user.lower():
            continue
        for lang, n in request(r["languages_url"], token).items():
            totals[lang] = totals.get(lang, 0) + n

    projects = json.loads(Path(args.projects).read_text(encoding="utf-8"))["projects"]
    for theme in THEMES:
        (out / f"card-stats-{theme}.svg").write_text(stats_card(args.user, followers, repos, contrib, theme), encoding="utf-8")
        (out / f"card-langs-{theme}.svg").write_text(langs_card(totals, theme), encoding="utf-8")
        for p in projects:
            svg = project_card(p, by_name.get(p["repo"]), theme)
            (out / f"card-{p['repo']}-{theme}.svg").write_text(svg, encoding="utf-8")
    print("tarjetas generadas en", out)


if __name__ == "__main__":
    main()
