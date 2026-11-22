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


CSS = """
:root{--bg:#fdf7ed;--ink:#0d0c09;--muted:#6b6458;--gold:#b7954c;--gold-dark:#86672a;--gold-soft:#e9d8ae;--hair:#e3d8c2;--pad:clamp(24px,7.2vw,120px);--display:Didot,"Bodoni 72","Bodoni MT","Times New Roman",serif}
*{box-sizing:border-box}
html{overflow-x:clip;-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:Arial,Helvetica,sans-serif;line-height:1.45;overflow-x:clip;font-variant-numeric:tabular-nums}
a{color:inherit}
a:focus-visible,summary:focus-visible,audio:focus-visible{outline:3px solid var(--ink);outline-offset:4px}
.dark a:focus-visible,footer a:focus-visible{outline-color:var(--bg)}
h1,h2,h3,p{margin:0}
h1,h2,.day,.big,.num,.logo,.when{font-family:var(--display)}
.bar{position:relative;z-index:3;display:flex;justify-content:space-between;align-items:baseline;font-size:17px}
.bar .links{margin-left:auto;display:flex;gap:32px}
.bar a:not(.logo){font-weight:700}
.logo{font-weight:700;font-size:22px;text-decoration:none;letter-spacing:-.01em}
mark{background:var(--gold-soft);color:var(--ink);padding:0 .1em}
audio{display:block;width:100%;max-width:460px}

.hero{position:relative;min-height:clamp(640px,58vw,920px);overflow:hidden;padding:44px var(--pad) 0}
.big{position:absolute;right:-5vw;bottom:-10vw;font-size:min(50vw,820px);line-height:.8;font-weight:700;letter-spacing:-.04em;color:var(--gold);user-select:none}
.hero-copy{position:absolute;z-index:3;left:var(--pad);top:clamp(90px,9vw,150px);width:min(46vw,720px);min-width:300px}
.wordmark{display:block;width:min(30vw,420px);min-width:220px;height:auto;margin:0 0 clamp(28px,3vw,48px) -.4em}
.hero h1{font-size:clamp(28px,3.3vw,54px);line-height:1.08;letter-spacing:-.015em;font-weight:700;text-wrap:balance}
.lead{margin-top:clamp(16px,1.8vw,26px);font-size:clamp(17px,1.5vw,22px);line-height:1.45;max-width:540px}
.latest{margin-top:clamp(24px,2.6vw,40px)}
.latest p{font-size:clamp(16px,1.3vw,20px);margin-bottom:10px}
.latest a{font-weight:700}

.dark{background:var(--ink);color:var(--bg);padding:clamp(80px,11vw,180px) var(--pad) clamp(72px,10vw,160px)}
.dark h2{font-size:clamp(34px,5.6vw,92px);line-height:1;letter-spacing:-.025em;font-weight:700;max-width:1200px;text-wrap:balance}
.facts{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:clamp(32px,7vw,120px);align-items:end;margin-top:clamp(64px,9vw,150px)}
.num{font-size:clamp(120px,18vw,290px);line-height:.8;font-weight:700;letter-spacing:-.04em;color:var(--gold)}
.num-cap{margin-top:26px;font-size:clamp(17px,1.46vw,22px);max-width:420px}
.process{font-size:clamp(16px,1.32vw,20px);line-height:1.55;color:#d9d0bf;max-width:460px;justify-self:end}
.process p+p{margin-top:1em}

.list{padding:clamp(80px,10vw,160px) var(--pad) clamp(72px,9vw,150px)}
.list h2{font-size:clamp(30px,3.6vw,58px);line-height:1.05;letter-spacing:-.02em;font-weight:700;max-width:860px;text-wrap:balance;margin-bottom:clamp(40px,5vw,80px)}
.ep{display:grid;grid-template-columns:clamp(84px,12vw,200px) minmax(0,1fr) minmax(0,26rem);gap:clamp(16px,3vw,48px);align-items:center;padding:clamp(18px,2vw,32px) 0;border-top:1px solid var(--hair)}
.ep:last-of-type{border-bottom:1px solid var(--hair)}
.day{font-size:clamp(56px,8.4vw,140px);line-height:.85;font-weight:700;letter-spacing:-.03em;transition:color .15s}
.ep:hover .day{color:var(--gold-dark)}
.ep h3{font-size:clamp(18px,1.6vw,24px);line-height:1.2;letter-spacing:-.005em;font-weight:700}
.ep h3 a{text-decoration:none}
.ep h3 a:hover{text-decoration:underline}
.ep .teaser{margin-top:6px;color:var(--muted);font-size:clamp(15px,1.2vw,18px)}
.ep .meta{margin-top:8px;font-size:13px;color:var(--muted)}

.gold{position:relative;background:var(--gold);color:var(--ink);padding:clamp(72px,8vw,130px) var(--pad) 0;overflow:hidden}
.gold .t{font-family:var(--display);font-size:clamp(28px,3.2vw,52px);line-height:1.1;letter-spacing:-.01em;font-weight:700;max-width:760px;text-wrap:balance}
.gold .links{display:flex;flex-wrap:wrap;gap:12px 36px;margin-top:32px;font-size:clamp(17px,1.46vw,22px);font-weight:700}
.when{margin:clamp(40px,6vw,90px) 0 -.5vw -.04em;font-size:clamp(64px,14.6vw,260px);line-height:.8;font-weight:700;letter-spacing:-.04em;white-space:nowrap;color:var(--bg)}

footer{background:var(--ink);color:#a89f8e;padding:48px var(--pad) 56px;display:flex;justify-content:space-between;gap:60px;font-size:14px}
footer p{max-width:560px}

.ephero{position:relative;overflow:hidden;padding:44px var(--pad) clamp(48px,6vw,96px)}
.ephero .big{font-size:min(40vw,640px);bottom:-6vw;right:-3vw}
.ephero h1{position:relative;z-index:2;margin-top:clamp(64px,9vw,150px);font-size:clamp(36px,5vw,84px);line-height:1;letter-spacing:-.025em;font-weight:700;max-width:760px;text-wrap:balance}
.ephero .sub{position:relative;z-index:2;margin:clamp(18px,2vw,30px) 0 28px;font-size:clamp(17px,1.5vw,22px);max-width:520px}
.ephero audio{position:relative;z-index:2}
.body{padding:clamp(24px,4vw,64px) var(--pad) clamp(64px,8vw,130px);max-width:calc(60rem + 2 * var(--pad))}
.sec{margin-top:clamp(48px,6vw,96px)}
.sec h2{font-size:clamp(30px,3.2vw,52px);line-height:1;letter-spacing:-.02em;font-weight:700;margin-bottom:clamp(20px,2.4vw,36px)}
.story{margin:0 0 clamp(26px,2.6vw,40px);max-width:46rem}
.story a.t{display:block;font-size:clamp(19px,1.7vw,25px);line-height:1.25;font-weight:700;letter-spacing:-.01em}
.story p{margin-top:8px;font-size:clamp(16px,1.25vw,19px);line-height:1.5}
.story .more{color:var(--muted);font-size:14px}
details{margin-top:clamp(56px,7vw,110px);max-width:46rem}
summary{cursor:pointer;font-weight:700;font-size:clamp(17px,1.46vw,22px)}
.script{white-space:pre-wrap;color:var(--muted);font-size:16px;line-height:1.6;margin-top:1.2rem}
.nav{display:flex;justify-content:space-between;gap:32px;margin-top:clamp(56px,7vw,110px);font-size:clamp(18px,1.7vw,26px);font-weight:700;letter-spacing:-.01em}
.nav span{display:block;font-size:13px;font-weight:400;color:var(--muted);letter-spacing:0;margin-bottom:4px}
.nav a{text-decoration:none}
.nav a:hover strong{text-decoration:underline}

@media (max-width:820px){
 .hero{min-height:0;padding-bottom:0}
 .hero-copy{position:relative;left:auto;top:auto;width:auto;min-width:0;padding:10vw 0 0}
 .wordmark{width:62vw;max-width:360px}
 .big{position:relative;display:block;right:auto;bottom:auto;margin:8vw 0 0 8vw;font-size:70vw;line-height:.72;height:50vw}
 .ephero .big{font-size:58vw;height:40vw;margin:6vw 0 0 20vw;position:relative;bottom:auto;right:auto}
 .ephero h1{margin-top:8vw}
 .facts{grid-template-columns:1fr}
 .process{justify-self:start}
 .ep{grid-template-columns:76px 1fr;row-gap:12px}
 .ep .listen{grid-column:1 / -1}
 .logo{font-size:19px;white-space:nowrap}
 .bar{font-size:15px}
 .bar .links{gap:20px}
 .nav{flex-direction:column}
 footer{flex-direction:column;gap:20px}
}
"""


def short_date(ep: dict) -> str:
    d = ep['_date']
    return f"{DAYS[d.weekday()].capitalize()} {d.day} de {MONTHS[d.month - 1]}"


def avg_minutes(eps: list[dict]) -> int:
    secs = [e['audio']['seconds'] for e in eps[:7] if (e.get('audio') or {}).get('seconds')]
    return round(sum(secs) / len(secs) / 60) if secs else 18


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
<link rel="icon" href="{root}icon.png">
<link rel="apple-touch-icon" href="{root}icon.png">
<meta property="og:title" content="{escape(title, quote=True)}">
<meta property="og:description" content="{escape(desc, quote=True)}">
<meta property="og:image" content="{escape(cfg['site_url'], quote=True)}/cover.png">
<meta name="theme-color" content="#fdf7ed">
<style>{CSS}</style>
</head>
<body>
{body}
</body>
</html>
"""


def player(ep: dict) -> str:
    audio = ep.get('audio')
    if not audio:
        return ''
    return f'<audio controls preload="none" src="{escape(audio["url"], quote=True)}"></audio>'


def teaser(ep: dict, limit: int = 120) -> str:
    stories = ep.get('stories') or []
    if not stories:
        return ''
    text = stories[0]['title']
    if len(text) > limit:
        text = text[:limit].rsplit(' ', 1)[0].rstrip(',;:|-') + '…'
    return text


def bar(cfg: dict, root: str, links: str, brand: bool = True) -> str:
    logo = f'<a class="logo" href="{root}">{escape(cfg["title"])}</a>' if brand else ''
    return f'<div class="bar">{logo}<div class="links">{links}</div></div>'


def footer(cfg: dict, root: str) -> str:
    return (f'<footer><p>{escape(cfg["disclaimer"])}</p>'
            f'<p><a href="{root}feed.xml">Feed RSS</a></p></footer>')


def episode_row(ep: dict, root: str) -> str:
    url = f"{root}episodios/{ep['id']}/"
    d = ep['_date']
    meta = ', '.join(x for x in [minutes(ep), f"{len(ep.get('stories') or [])} noticias"] if x)
    return (f'<article class="ep"><div class="day" aria-hidden="true">{d.day}</div>'
            f'<div><h3><a href="{url}">{escape(long_date(ep).capitalize())}</a></h3>'
            f'<p class="teaser">{escape(teaser(ep))}</p></div>'
            f'<div class="listen">{player(ep)}<p class="meta">{escape(meta)}</p></div></article>')


def build_index(cfg: dict, eps: list[dict], root: str) -> str:
    feed = f'{root}feed.xml'
    apple = 'podcast://' + cfg['site_url'].split('://', 1)[-1] + '/feed.xml'
    mins = avg_minutes(eps)
    latest = eps[0] if eps else None
    big = str(latest['_date'].day) if latest else '8'
    if latest:
        latest_html = (f'<div class="latest"><p>Último episodio: <a href="{root}episodios/{latest["id"]}/">'
                       f'{escape(long_date(latest))}</a></p>{player(latest)}</div>')
    else:
        latest_html = '<div class="latest"><p>El primer episodio llega pronto.</p></div>'
    count = len(latest.get('stories') or []) if latest else 0
    facts = ''
    if latest and count:
        facts = (f'<div class="facts"><div><p class="num">{count}</p>'
                 f'<p class="num-cap">Son las noticias que entraron al episodio del {escape(long_date(latest))}.</p></div>'
                 '<div class="process"><p>El sistema revisa los titulares de medios de México, España y el mundo, elige '
                 'las noticias más relevantes y las analiza. Una voz sintética narra el resultado, con el análisis de '
                 'qué significa cada noticia.</p><p>Todo el proceso es automático y puede equivocarse, así que cada '
                 'episodio enlaza sus fuentes originales y publica el guion completo.</p></div></div>')
    rows = '\n'.join(episode_row(ep, root) for ep in eps) or '<p>Todavía no hay episodios.</p>'
    links = '<a href="#episodios">Episodios</a><a href="#suscribirse">Suscribirse</a>'
    body = f"""<section class="hero">
{bar(cfg, root, links, brand=False)}
<div class="big" aria-hidden="true">{big}</div>
<div class="hero-copy">
<img class="wordmark" src="{root}wordmark.png" width="2537" height="1269" alt="{escape(cfg['title'], quote=True)}">
<h1>Cada mañana tienes las noticias del día en unos {mins} minutos de audio.</h1>
<p class="lead">{escape(cfg['description'])}</p>
{latest_html}
</div>
</section>

<section class="dark">
<h2>Un sistema automático <mark>lee los medios por ti</mark> desde las 8:00, hora de Madrid, y prepara el episodio del día.</h2>
{facts}
</section>

<section class="list" id="episodios">
<h2>Todos los episodios están aquí, del más reciente al más antiguo.</h2>
{rows}
</section>

<section class="gold" id="suscribirse">
<p class="t">Suscríbete y cada episodio llega solo a tu app de podcasts.</p>
<p class="links"><a href="{escape(apple, quote=True)}">Apple Podcasts</a><a href="{feed}">Feed RSS para cualquier app</a></p>
<p class="when" aria-hidden="true">Todos los días</p>
</section>
{footer(cfg, root)}"""
    return page(cfg, f"{cfg['title']}: {cfg['description']}", body, f'{cfg["site_url"]}/', root, cfg['description'])


def build_episode(cfg: dict, ep: dict, root: str, newer: dict | None, older: dict | None) -> str:
    title = f"{long_date(ep).capitalize()}, {cfg['title']}"
    stories = ep.get('stories') or []
    sub = f'Dura {minutes(ep)} y cubre {len(stories)} noticias.' if minutes(ep) else ''
    secs = []
    for key, label in SECTIONS:
        group = [s for s in stories if s.get('section') == key]
        if not group:
            continue
        items = []
        for s in group:
            extra = ''.join(f' {link(x["url"], x.get("source") or x["title"])}' for x in s.get('sources') or [])
            items.append(f'<div class="story"><a class="t" href="{escape(safe_url(s["url"]), quote=True)}" rel="noopener">'
                         f'{escape(s["title"])}</a><p>{escape(s.get("so_what") or "")}</p>'
                         + (f'<p class="more">Más fuentes:{extra}</p>' if extra else '') + '</div>')
        secs.append(f'<div class="sec"><h2>{escape(label)}</h2>{"".join(items)}</div>')
    script = (f'<details><summary>Leer el guion completo</summary><div class="script">{escape(ep["script"])}</div></details>'
              if ep.get('script') else '')
    nav = ''
    nav += (f'<a href="{root}episodios/{older["id"]}/"><span>Episodio anterior</span><strong>{escape(short_date(older))}</strong></a>'
            if older else '<i></i>')
    nav += (f'<a href="{root}episodios/{newer["id"]}/"><span>Episodio siguiente</span><strong>{escape(short_date(newer))}</strong></a>'
            if newer else '<i></i>')
    body = f"""<section class="ephero">
{bar(cfg, root, f'<a href="{root}#episodios">Todos los episodios</a>')}
<div class="big" aria-hidden="true">{ep['_date'].day}</div>
<h1>{escape(long_date(ep).capitalize())}</h1>
<p class="sub">{escape(sub)}</p>
{player(ep)}
</section>
<div class="body">
{''.join(secs)}
{script}
<nav class="nav">{nav}</nav>
</div>
{footer(cfg, root)}"""
    return page(cfg, title, body, f'{cfg["site_url"]}/episodios/{ep["id"]}/', root, teaser(ep) or cfg['description'])


def item_html(ep: dict, page_url: str) -> str:
    out = []
    for s in ep.get('stories') or []:
        out.append(f'<li><a href="{escape(safe_url(s["url"]), quote=True)}">{escape(s["title"])}</a></li>')
    return (f'<p>Las noticias de hoy:</p><ul>{"".join(out)}</ul>'
            f'<p><a href="{escape(page_url, quote=True)}">Análisis completo y guion</a></p>')


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
        title = long_date(ep).capitalize()
        link_url = f'{site}/episodios/{ep["id"]}/'
        duration = f'<itunes:duration>{int(audio["seconds"])}</itunes:duration>' if audio.get('seconds') else ''
        items.append(f"""    <item>
      <title>{escape(title)}</title>
      <link>{escape(link_url)}</link>
      <guid isPermaLink="false">briefing-{escape(ep['id'])}</guid>
      <pubDate>{format_datetime(published)}</pubDate>
      <description>{cdata(item_html(ep, link_url))}</description>
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
    <description>{escape(cfg.get('feed_description') or cfg['description'])}</description>
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
    for i, ep in enumerate(eps):
        folder = out / 'episodios' / ep['id']
        folder.mkdir(parents=True)
        newer = eps[i - 1] if i > 0 else None
        older = eps[i + 1] if i + 1 < len(eps) else None
        (folder / 'index.html').write_text(build_episode(cfg, ep, '../../', newer, older), encoding='utf-8')
    (out / 'feed.xml').write_text(build_feed(cfg, eps), encoding='utf-8')
    for name in ('cover.png', 'icon.png', 'wordmark.png'):
        src = ROOT / 'assets' / name
        if src.exists():
            shutil.copy(src, out / name)
    print(f'Built {len(eps)} episodes into {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
