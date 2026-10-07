"""Injecte tools/woocommerce-charte.css dans le CSS personnalisé du kit Elementor actif.

Elementor > Réglages du site > CSS personnalisé (kit #7). Les autres réglages du kit sont
conservés ; une sauvegarde est écrite dans source/kit7_settings_backup.json avant écriture.
Auth : WP_AUTH (Basic). Site : WP_SITE (défaut https://skiclubvence.com).
"""
import json
import os
import urllib.request
from pathlib import Path

SITE = os.environ.get("WP_SITE", "https://skiclubvence.com")
KIT = 7
ROOT = Path(__file__).resolve().parent.parent


def call(path, data=None, method=None):
    req = urllib.request.Request(f"{SITE}/wp-json{path}", json.dumps(data).encode() if data is not None else None,
                                 {"Authorization": os.environ["WP_AUTH"], "Content-Type": "application/json"},
                                 method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or "null")


def main():
    css = (ROOT / "tools" / "woocommerce-charte.css").read_text("utf-8")
    kit = call(f"/wp/v2/elementor_library/{KIT}?context=edit&_fields=meta")
    settings = kit["meta"].get("_elementor_page_settings") or {}
    (ROOT / "source" / "kit7_settings_backup.json").write_text(json.dumps(settings, indent=1), "utf-8")
    settings["custom_css"] = css
    call(f"/wp/v2/elementor_library/{KIT}", {"meta": {"_elementor_page_settings": settings}})
    call("/elementor/v1/cache", method="DELETE")
    # Avis produits inutiles pour des sorties / licences
    call("/wc/v3/settings/products/woocommerce_enable_reviews", {"value": "no"}, "PUT")
    print(f"CSS WooCommerce appliqué ({len(css)} caractères) au kit #{KIT}, avis désactivés")


if __name__ == "__main__":
    main()
