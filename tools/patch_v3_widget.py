"""Fusionne des réglages natifs Elementor (V3) dans un widget d'un document.

Le MCP Elementor refuse les clés de style V3 (couleurs, typo du Nav Menu…) :
on patche donc directement _elementor_data via l'API REST, puis on vide le cache CSS.

Usage : python patch_v3_widget.py <post_id> <element_id> <settings.json> [post_type]
Auth  : variable d'environnement WP_AUTH = "Basic <base64 user:app-password>".
"""
import json
import os
import sys
import urllib.request

ROOT = os.environ.get("WP_SITE", "https://skiclubvence.com") + "/index.php?rest_route="


def call(path, data=None, method=None):
    req = urllib.request.Request(
        ROOT + path,
        json.dumps(data).encode() if data is not None else None,
        {"Authorization": os.environ["WP_AUTH"], "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or "null")


def find(elements, element_id):
    for el in elements:
        if el.get("id") == element_id:
            return el
        hit = find(el.get("elements", []), element_id)
        if hit:
            return hit
    return None


def main(post_id, element_id, settings_file, post_type="elementor_library"):
    patch = json.loads(open(settings_file, encoding="utf-8").read())
    doc = call(f"/wp/v2/{post_type}/{post_id}&context=edit&_fields=meta")
    data = json.loads(doc["meta"]["_elementor_data"])
    el = find(data, element_id)
    if el is None:
        sys.exit(f"élément {element_id} introuvable dans {post_id}")
    el.setdefault("settings", {}).update(patch)
    call(f"/wp/v2/{post_type}/{post_id}", {"meta": {"_elementor_data": json.dumps(data)}})
    call("/elementor/v1/cache", method="DELETE")
    print(f"{element_id} mis à jour ({len(patch)} réglages)")


if __name__ == "__main__":
    main(*sys.argv[1:])
