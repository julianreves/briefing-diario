# El Briefing Diario, web and RSS

Static site and podcast feed, hosted free on GitHub. This folder is meant to be its own PUBLIC repo (free GitHub Pages needs a public repo). It holds only generated text, links and the cover. No keys, no n8n exports.

How an episode gets here:

1. n8n calls the bridge at 08:00 (`../bridge/kokoro_bridge.py`), sending the script plus the stories and their sources.
2. The bridge renders the audio, sends the Telegram voice note, then makes a 64 kbps mono MP3.
3. `scripts/publish_episode.py` uploads the MP3 as a GitHub Release asset (tag `ep-YYYY-MM-DD`) and commits `data/episodes/YYYY-MM-DD.json`.
4. The commit triggers `.github/workflows/pages.yml`, which runs `build.py` and deploys the site and `feed.xml`.

If the web step fails, Telegram is not affected. The MP3 stays in `~/.kokoro-server/episodes/` and the next call for the same date retries the upload.

## One-time setup

1. Create a public GitHub repo and push the contents of this folder as the repo root.
2. Repo Settings, Pages, Source: GitHub Actions.
3. Create a fine-grained token (Settings, Developer settings): only this repo, permission Contents: Read and write. Nothing else.
4. Start the bridge with two extra variables: `PODCAST_REPO=owner/name` and `PODCAST_GITHUB_TOKEN=...`. Without them the bridge only does Telegram, as before.
5. Re-import the n8n workflow (the Kokoro node now also sends `stories`), then set `testWithoutAudio` to false.
6. Run once manually. Check that the release, the commit, the Actions run and `https://OWNER.github.io/REPO/` all show the episode.

The first run publishes the first episode. Until then the home page says the first one is coming.

## Settings

`config.json`: title, description, author, language. `owner_email` is left empty on purpose: Spotify and Apple use it to verify ownership of the feed, and it becomes public in the feed. Add it only when you submit the feed to them.

A custom domain later: set the repo variable `SITE_URL` (Settings, Secrets and variables, Variables) so the feed and episode links use it.

## Local preview

```bash
SITE_URL=http://localhost:8000 python3 build.py --out dist && cd dist && python3 -m http.server 8000
```

## Limits to know (from GitHub's docs, verify before relying on them)

Pages: site up to 1 GB, soft 100 GB/month bandwidth. Audio lives in Releases so the site stays tiny. At about 8.6 MB per 18 minute episode, a year is about 3 GB of release assets.
