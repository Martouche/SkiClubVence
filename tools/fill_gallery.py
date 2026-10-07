"""Remplit les grilles masonry de la page Galerie (#189) avec toutes les photos importées.

Chaque onglet de source/galerie_tabs.json correspond à une grille ; l'élément présent
dans la grille sert de modèle (classes + réglages) et est cloné pour chaque photo.
Pré-requis : page publiée via le MCP AVANT l'exécution (sinon l'autosave écraserait le patch).
Auth : WP_AUTH.
"""
import copy
import json
import secrets
import unicodedata
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0])
from patch_v3_widget import call, find  # noqa: E402

PAGE = 189
# onglet legacy (titre) -> id de la grille masonry sur dev
GRIDS = {
    "Saison 2025 - 2026": ("2173dbe2", "Saison 2025-2026 du Ski Club Vence"),
    "Stage Sestrière 2024 - 2025": ("79808af6", "Stage de ski à Sestrière, saison 2024-2025"),
    "Archives 2024": ("50edb228", "Archives 2024 du Ski Club Vence"),
}


def new_id():
    return secrets.token_hex(4)[:7]


def main():
    tabs = {unicodedata.normalize("NFC", t["title"]): t for t in json.load(open("source/galerie_tabs.json", encoding="utf-8"))}
    media = json.load(open("source/media_map.json", encoding="utf-8"))
    data = json.loads(call(f"/wp/v2/pages/{PAGE}&context=edit&_fields=meta")["meta"]["_elementor_data"])

    for title, (grid_id, alt) in GRIDS.items():
        grid = find(data, grid_id)
        template = grid["elements"][0]
        items, missing = [], 0
        for n, src in enumerate(tabs[title]["images"], 1):
            m = media.get(src)
            if not m:
                missing += 1
                continue
            item = copy.deepcopy(template)
            item["id"] = new_id()
            img = item["elements"][0]
            img["id"] = new_id()
            img["settings"]["image"]["value"]["src"]["value"] = {
                "id": {"$$type": "image-attachment-id", "value": m["id"]},
                "alt": {"$$type": "string", "value": f"{alt} – photo {n}"},
            }
            img["settings"]["link"] = {"$$type": "link", "value": {
                "destination": {"$$type": "url", "value": m["url"]},
                "isTargetBlank": {"$$type": "boolean", "value": False}}}
            items.append(item)
        grid["elements"] = items
        print(f"{title}: {len(items)} photos ({missing} manquantes)")

    call(f"/wp/v2/pages/{PAGE}", {"meta": {"_elementor_data": json.dumps(data)}})
    call("/elementor/v1/cache", method="DELETE")


if __name__ == "__main__":
    main()
