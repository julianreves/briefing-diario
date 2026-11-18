#!/usr/bin/env python3
"""Builds the static podcast site and RSS feed from data/episodes/*.json.

Usage:  SITE_URL=https://user.github.io/repo python3 build.py [--out dist]
Only the Python standard library is used.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DAYS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
MONTHS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
          'septiembre', 'octubre', 'noviembre', 'diciembre']
SECTIONS = [('mexico', 'México'), ('espana', 'España'), ('ia', 'Inteligencia artificial'),
            ('mundo', 'Mundo y geopolítica'), ('negocios', 'Economía y negocios')]

CSS = """
:root{--bg:#fff;--fg:#111;--muted:#666;--accent:#0b57d0}
@media (prefers-color-scheme:dark){:root{--bg:#0e0e0e;--fg:#f2f2f2;--muted:#9a9a9a;--accent:#8ab4ff}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:18px/1.55 Arial,Helvetica,sans-serif}
main{max-width:40rem;margin:0 auto;padding:3rem 1rem 5rem}
a{color:var(--accent);text-underline-offset:.18em}
a:hover{text-decoration-thickness:2px}
h1{font-size:2.4rem;line-height:1.1;margin:0 0 .75rem;letter-spacing:-.02em}
h2{font-size:1.25rem;line-height:1.3;margin:0 0 .25rem}
h2 a{color:var(--fg);text-decoration:none}
h2 a:hover{text-decoration:underline}
h3{font-size:.85rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:2.5rem 0 .75rem}
p{margin:0 0 1rem}
.lead{font-size:1.15rem;color:var(--muted);margin-bottom:1.5rem}
.muted{color:var(--muted);font-size:.9rem}
.month{font-size:.85rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:3rem 0 1rem}
.ep{margin:0 0 2rem}
.ep p{color:var(--muted);margin:0 0 .6rem}
.latest{margin:2.5rem 0 0}
.latest h2{font-size:1.6rem}
audio{width:100%;display:block;margin:.5rem 0 0}
.story{margin:0 0 1.5rem}
.story strong{display:block;font-weight:700}
details{margin-top:2.5rem}
summary{cursor:pointer;color:var(--accent)}
.script{white-space:pre-wrap;color:var(--muted);font-size:.95rem;margin-top:1rem}
footer{margin-top:4rem}
a:focus-visible,summary:focus-visible,audio:focus-visible{outline:3px solid var(--accent);outline-offset:3px}
"""


def load_config() -> dict:
    cfg = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
    site = os.environ.get('SITE_URL') or cfg.get('site_url') or ''
    cfg['site_url'] = site.rstrip('/')
    return cfg


def load_episodes() -> list[dict]:
    items = []
    for path in sorted((ROOT / 'data' / 'episodes').glob('*.json')):
        ep = json.loads(path.read_text(encoding='utf-8'))
        ep['_date'] = datetime.strptime(ep['id'], '%Y-%m-%d')
        items.append(ep)
    items.sort(key=lambda e: e['id'], reverse=True)
    return items


def long_date(ep: dict) -> str:
    d = ep['_date']
    return f"{DAYS[d.weekday()]} {d.day} de {MONTHS[d.month - 1]} de {d.year}"


def month_label(ep: dict) -> str:
    d = ep['_date']
    return f"{MONTHS[d.month - 1]} {d.year}"


def minutes(ep: dict) -> str:
    secs = (ep.get('audio') or {}).get('seconds')
    return f"{max(1, round(secs / 60))} min" if secs else ''


def safe_url(url: str) -> str:
    return url if url.startswith(('http://', 'https://')) else '#'


def link(url: str, text: str) -> str:
    return f'<a href="{escape(safe_url(url), quote=True)}" rel="noopener">{escape(text)}</a>'


def page(cfg: dict, title: str, body: str, canonical: str, root: str, desc: str) -> str:
    feed = f'{root}feed.xml'
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="{escape(desc, quote=True)}">
<link rel="canonical" href="{escape(canonical, quote=True)}">
<link rel="alternate" type="application/rss+xml" title="{escape(cfg['title'], quote=True)}" href="{escape(feed, quote=True)}">
<link rel="icon" href="{root}cover.png">
<meta property="og:title" content="{escape(title, quote=True)}">
<meta property="og:description" content="{escape(desc, quote=True)}">
<meta property="og:image" content="{escape(cfg['site_url'], quote=True)}/cover.png">
<style>{CSS}</style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""


def player(ep: dict) -> str:
    audio = ep.get('audio')
    if not audio:
        return ''
    return f'<audio controls preload="none" src="{escape(audio["url"], quote=True)}"></audio>'


def teaser(ep: dict) -> str:
    stories = ep.get('stories') or []
    return stories[0]['title'] if stories else ''


def episode_row(ep: dict, root: str, latest: bool = False) -> str:
    url = f"{root}episodios/{ep['id']}/"
    meta = ' '.join(x for x in [f"{len(ep.get('stories') or [])} noticias", minutes(ep)] if x)
    cls = 'ep latest' if latest else 'ep'
    return (f'<article class="{cls}"><h2><a href="{url}">{escape(long_date(ep))}</a></h2>'
            f'<p>{escape(teaser(ep))}</p>{player(ep)}'
            f'<p class="muted" style="margin:.5rem 0 0">{escape(meta)}</p></article>')


def build_index(cfg: dict, eps: list[dict], root: str) -> str:
    parts = [f'<h1>{escape(cfg["title"])}</h1>', f'<p class="lead">{escape(cfg["description"])}</p>',
             f'<p>{link(root + "feed.xml", "Suscríbete por RSS")} en tu app de podcasts.</p>']
    if not eps:
        parts.append('<p class="muted">El primer episodio llega mañana a las 8:00, hora de Madrid.</p>')
    else:
        parts.append(episode_row(eps[0], root, latest=True))
        current = None
        for ep in eps[1:]:
            label = month_label(ep)
            if label != current:
                parts.append(f'<h3 class="month" style="margin-top:3rem">{escape(label)}</h3>')
                current = label
            parts.append(episode_row(ep, root))
    parts.append(f'<footer class="muted">{escape(cfg["disclaimer"])}</footer>')
    return page(cfg, cfg['title'], '\n'.join(parts), f'{cfg["site_url"]}/', root, cfg['description'])


def build_episode(cfg: dict, ep: dict, root: str) -> str:
    title = f"{cfg['title']}, {long_date(ep)}"
    stories = ep.get('stories') or []
    parts = [f'<p><a href="{root}">Todos los episodios</a></p>', f'<h1>{escape(long_date(ep).capitalize())}</h1>']
    if minutes(ep):
        parts.append(f'<p class="muted">{escape(minutes(ep))}, {len(stories)} noticias</p>')
    parts.append(player(ep))
    for key, label in SECTIONS:
        group = [s for s in stories if s.get('section') == key]
        if not group:
            continue
        parts.append(f'<h3>{escape(label)}</h3>')
        for s in group:
            extra = ''.join(f' {link(x["url"], x.get("source") or x["title"])}' for x in s.get('sources') or [])
            parts.append(f'<div class="story"><strong>{link(s["url"], s["title"])}</strong>'
                         f'<span>{escape(s.get("so_what") or "")}</span>'
                         + (f'<br><span class="muted">Más fuentes:{extra}</span>' if extra else '') + '</div>')
    if ep.get('script'):
        parts.append(f'<details><summary>Leer el guion completo</summary><div class="script">{escape(ep["script"])}</div></details>')
    parts.append(f'<footer class="muted">{escape(cfg["disclaimer"])}</footer>')
    return page(cfg, title, '\n'.join(parts), f'{cfg["site_url"]}/episodios/{ep["id"]}/', root, teaser(ep) or cfg['description'])


def item_html(ep: dict) -> str:
    out = []
    for s in ep.get('stories') or []:
        out.append(f'<li><strong>{escape(s["title"])}</strong> {escape(s.get("so_what") or "")} '
                   f'<a href="{escape(safe_url(s["url"]), quote=True)}">Fuente</a></li>')
    return f'<ul>{"".join(out)}</ul>'


def cdata(text: str) -> str:
    return '<![CDATA[' + text.replace(']]>', ']]]]><![CDATA[>') + ']]>'


def build_feed(cfg: dict, eps: list[dict]) -> str:
    site = cfg['site_url']
    items = []
    for ep in eps:
        audio = ep.get('audio')
        if not audio:
            continue
        published = datetime.fromisoformat(ep['published_at']) if ep.get('published_at') else \
            ep['_date'].replace(hour=7, tzinfo=timezone.utc)
        title = f"{cfg['title']}, {long_date(ep)}"
        link_url = f'{site}/episodios/{ep["id"]}/'
        duration = f'<itunes:duration>{int(audio["seconds"])}</itunes:duration>' if audio.get('seconds') else ''
        items.append(f"""    <item>
      <title>{escape(title)}</title>
      <link>{escape(link_url)}</link>
      <guid isPermaLink="false">briefing-{escape(ep['id'])}</guid>
      <pubDate>{format_datetime(published)}</pubDate>
      <description>{cdata(item_html(ep))}</description>
      <enclosure url="{escape(audio['url'], quote=True)}" length="{int(audio.get('bytes') or 0)}" type="{escape(audio.get('type') or 'audio/mpeg')}"/>
      {duration}
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>{'true' if cfg.get('explicit') else 'false'}</itunes:explicit>
    </item>""")
    owner = (f"<itunes:owner><itunes:name>{escape(cfg['author'])}</itunes:name>"
             f"<itunes:email>{escape(cfg['owner_email'])}</itunes:email></itunes:owner>") if cfg.get('owner_email') else ''
    sub = f'<itunes:category text="{escape(cfg["subcategory"])}"/>' if cfg.get('subcategory') else ''
    last = format_datetime(datetime.now(timezone.utc))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{escape(cfg['title'])}</title>
    <link>{escape(site)}/</link>
    <atom:link href="{escape(site)}/feed.xml" rel="self" type="application/rss+xml"/>
    <description>{escape(cfg['description'])}</description>
    <language>{escape(cfg['language'])}</language>
    <lastBuildDate>{last}</lastBuildDate>
    <itunes:author>{escape(cfg['author'])}</itunes:author>
    <itunes:image href="{escape(site)}/cover.png"/>
    <itunes:explicit>{'true' if cfg.get('explicit') else 'false'}</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    {owner}
    <itunes:category text="{escape(cfg['category'])}">{sub}</itunes:category>
{chr(10).join(items)}
  </channel>
</rss>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='dist')
    out = Path(ap.parse_args().out).resolve()
    cfg = load_config()
    if not cfg['site_url']:
        print('Set SITE_URL or site_url in config.json (needed for the RSS feed).', file=sys.stderr)
        return 1
    eps = load_episodes()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    # Relative root so the pages also work under a project path like /repo/.
    (out / 'index.html').write_text(build_index(cfg, eps, './'), encoding='utf-8')
    for ep in eps:
        folder = out / 'episodios' / ep['id']
        folder.mkdir(parents=True)
        (folder / 'index.html').write_text(build_episode(cfg, ep, '../../'), encoding='utf-8')
    (out / 'feed.xml').write_text(build_feed(cfg, eps), encoding='utf-8')
    for name in ('cover.png',):
        src = ROOT / 'assets' / name
        if src.exists():
            shutil.copy(src, out / name)
    print(f'Built {len(eps)} episodes into {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
