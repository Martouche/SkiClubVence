"""Téléverse source/media et source/gallery dans la médiathèque de dev.skiclubvence.com.

Idempotent : un fichier déjà présent (même nom de fichier) n'est pas renvoyé.
Écrit la correspondance ancien URL -> {id, url} dans source/media_map.json.
Auth : variable d'environnement WP_AUTH = "Basic <base64 user:app-password>".
"""
import json
import mimetypes
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "source"
API = "https://dev.skiclubvence.com/index.php?rest_route=/wp/v2/media"
AUTH = os.environ["WP_AUTH"]


def call(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={"Authorization": AUTH, **(headers or {})})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def existing():
    found, page = {}, 1
    while True:
        try:
            items = call(f"{API}&per_page=100&page={page}&_fields=id,source_url")
        except urllib.error.HTTPError:
            return found
        if not items:
            return found
        for it in items:
            found[it["source_url"].rsplit("/", 1)[-1]] = it
        page += 1


def main():
    mp = ROOT / "media_map.json"
    mapping = json.loads(mp.read_text("utf-8")) if mp.exists() else {}
    have = existing()
    lists = {"media": ROOT / "media_to_import.txt", "gallery": ROOT / "gallery_to_import.txt"}
    if len(sys.argv) > 1:  # ex. : gallery=gallery_full.txt
        lists = dict(a.split("=", 1) for a in sys.argv[1:])
        lists = {k: ROOT / v for k, v in lists.items()}
    for folder, lst in lists.items():
        for src in lst.read_text().split():
            local = ROOT / folder / src.split("/uploads/")[1].replace("/", "_")
            name = src.rsplit("/", 1)[-1]
            if src in mapping:
                continue
            if name in have:
                mapping[src] = {"id": have[name]["id"], "url": have[name]["source_url"], "group": folder}
                continue
            mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
            res = call(API, local.read_bytes(), {
                "Content-Type": mime,
                "Content-Disposition": f'attachment; filename="{name}"',
            })
            mapping[src] = {"id": res["id"], "url": res["source_url"], "group": folder}
            print(res["id"], res["source_url"], flush=True)
            mp.write_text(json.dumps(mapping, indent=2), "utf-8")
    mp.write_text(json.dumps(mapping, indent=2), "utf-8")
    print(f"{len(mapping)} médias mappés", file=sys.stderr)


if __name__ == "__main__":
    main()
