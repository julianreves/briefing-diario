#!/usr/bin/env python3
"""Publishes one episode to GitHub: MP3 as a Release asset, metadata as a file in the repo.

The push of data/episodes/<date>.json triggers the Pages workflow, which rebuilds the
site and the RSS feed. Only the standard library is used.

Environment:
  PODCAST_GITHUB_TOKEN  Fine-grained token, only this repo, permission "Contents: Read and write".
  PODCAST_REPO          owner/name of the site repo, e.g. someone/briefing-diario

CLI (manual re-publish):
  python3 publish_episode.py 2026-11-17 /path/briefing.mp3 /path/meta.json
meta.json holds: stories (list), script (str), seconds (number).
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

API = 'https://api.github.com'
UPLOADS = 'https://uploads.github.com'


def _call(method: str, url: str, token: str, body: bytes | None = None,
          content_type: str = 'application/json', timeout: int = 300):
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
               'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'briefing-diario-publisher'}
    if body is not None:
        headers['Content-Type'] = content_type
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else {})
    except HTTPError as err:
        if err.code == 404:
            return 404, {}
        raise RuntimeError(f'GitHub {method} {url.split("?")[0]} -> HTTP {err.code}') from None


def _json(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False).encode('utf-8')


def publish(run_id: str, mp3: Path, meta: dict, repo: str | None = None, token: str | None = None) -> str:
    repo = repo or os.environ.get('PODCAST_REPO', '')
    token = token or os.environ.get('PODCAST_GITHUB_TOKEN', '')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', run_id):
        raise ValueError('invalid run_id')
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', repo) or not token:
        raise RuntimeError('PODCAST_REPO and PODCAST_GITHUB_TOKEN are required')
    if not mp3.exists() or mp3.stat().st_size < 1024:
        raise RuntimeError('MP3 missing or too small')

    tag = f'ep-{run_id}'
    asset_name = f'briefing-{run_id}.mp3'

    status, release = _call('GET', f'{API}/repos/{repo}/releases/tags/{tag}', token)
    if status == 404:
        _, release = _call('POST', f'{API}/repos/{repo}/releases', token, _json({
            'tag_name': tag, 'name': f'Briefing {run_id}', 'body': f'Audio del briefing del {run_id}.',
            'make_latest': 'false'}))

    asset = next((a for a in release.get('assets', []) if a['name'] == asset_name), None)
    if asset is None:
        _, asset = _call('POST', f'{UPLOADS}/repos/{repo}/releases/{release["id"]}/assets?name={asset_name}',
                         token, mp3.read_bytes(), 'audio/mpeg', timeout=600)

    episode = {
        'id': run_id,
        'published_at': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'audio': {'url': asset['browser_download_url'], 'bytes': asset['size'],
                  'seconds': int(meta.get('seconds') or 0), 'type': 'audio/mpeg'},
        'stories': meta.get('stories') or [],
        'script': meta.get('script') or '',
    }
    path = f'data/episodes/{run_id}.json'
    status, existing = _call('GET', f'{API}/repos/{repo}/contents/{path}', token)
    if status == 200:
        # Keep the original publication time so the RSS pubDate never moves.
        try:
            old = json.loads(base64.b64decode(existing['content']))
            episode['published_at'] = old.get('published_at', episode['published_at'])
        except (ValueError, KeyError):
            pass
    payload = {'message': f'Episodio {run_id}',
               'content': base64.b64encode(_json(episode)).decode('ascii')}
    if status == 200:
        payload['sha'] = existing['sha']
    _call('PUT', f'{API}/repos/{repo}/contents/{path}', token, _json(payload))
    return asset['browser_download_url']


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    url = publish(sys.argv[1], Path(sys.argv[2]), json.loads(Path(sys.argv[3]).read_text(encoding='utf-8')))
    print(url)
