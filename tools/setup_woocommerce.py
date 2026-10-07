"""Catalogue WooCommerce du Ski Club Vence — saison 2026-2027 (produits payables).

- Licence FFS 2026-2027 : produit variable (attribut « Type ») — en brouillon (prise à la bourse / aux permanences).
- Sorties : UN produit variable par date (attribut « Formule »), stock géré au niveau
  du produit => PLACES places partagées entre toutes les formules de la sortie.
- Stage Dolomites 2027 : produit variable (attribut « Tarif »), assurance 35 € incluse — en brouillon (dossier + règlement à la permanence).
- Matériel d'occasion : produits simples, stock 1 — en brouillon (simple mise en relation).
Idempotent (recherche par SKU). Auth : WP_AUTH.
"""
import json
import os
import urllib.parse
import urllib.request

ROOT = "https://dev.skiclubvence.com/index.php?rest_route=/wc/v3"
PLACES = 50  # places par sortie, partagées entre les formules (None = illimité)
DAYS = {"sorties-mardi": "Mardi", "sorties-samedi": "Samedi"}
MOIS = {12: "décembre", 1: "janvier", 2: "février", 3: "mars", 4: "avril"}


def call(path, data=None, method=None):
    req = urllib.request.Request(ROOT + path, json.dumps(data).encode() if data is not None else None,
                                 {"Authorization": os.environ["WP_AUTH"], "Content-Type": "application/json"},
                                 method=method)
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())


def category(name, slug):
    found = call(f"/products/categories&slug={slug}")
    return found[0]["id"] if found else call("/products/categories", {"name": name, "slug": slug})["id"]


def upsert(body):
    found = call(f"/products&sku={urllib.parse.quote(body['sku'])}&status=any")
    return call(f"/products/{found[0]['id']}", body, "PUT") if found else call("/products", body)


def variable(sku, name, cat, attrs, variations, image, short, stock=None, menu_order=0, status="publish"):
    """attrs : {nom: [options]} ; variations : liste de ({nom: option}, prix).
    Crée/maj le produit puis remplace toutes ses variations."""
    body = {"sku": sku, "name": name, "type": "variable", "status": status, "virtual": True,
            "categories": [{"id": cat}], "images": [{"id": image}], "short_description": short,
            "menu_order": menu_order, "manage_stock": stock is not None,
            "attributes": [{"name": a, "visible": True, "variation": True, "options": o} for a, o in attrs.items()],
            "default_attributes": []}
    if stock is not None:
        body.update({"stock_quantity": stock, "backorders": "no"})
    p = upsert(body)
    old = call(f"/products/{p['id']}/variations&per_page=100")
    if old:
        call(f"/products/{p['id']}/variations/batch", {"delete": [v["id"] for v in old]})
    create = [{"regular_price": str(price), "virtual": True, "manage_stock": False, "sku": f"{sku}-{i + 1}",
               "attributes": [{"name": a, "option": o} for a, o in combo.items()]}
              for i, (combo, price) in enumerate(variations)]
    for k in range(0, len(create), 50):
        call(f"/products/{p['id']}/variations/batch", {"create": create[k:k + 50]})
    print(p["id"], name, len(create), "variations")
    return p["id"]


def simple_options(attr, options):
    return {attr: [o for o, _ in options]}, [({attr: o}, price) for o, price in options]


def main():
    cats = {k: category(n, k) for k, n in [
        ("licences-ffs", "Licences FFS"), ("sorties-mardi", "Sorties du mardi"),
        ("sorties-samedi", "Sorties du samedi"), ("stage-fevrier", "Stage de février"),
        ("materiel-occasion", "Matériel d'occasion")]}

    # Anciens produits simples (brouillons) remplacés par les produits variables
    for sku in ["SCV-LIC-DECOUVERTE", "SCV-LIC-ADULTE", "SCV-LIC-ENFANT", "SCV-LIC-CADRE", "SCV-LIC-FAMILLE",
                "SCV-MAR-SKI", "SCV-MAR-PIETON", "SCV-SAM-ENFANT", "SCV-SAM-ADULTE", "SCV-SAM-PIETON",
                "SCV-STAGE-2027-15P", "SCV-STAGE-2027-15M", "SCV-STAGE-2027-NS",
                "SCV-SORTIE-MARDI-2027", "SCV-SORTIE-SAMEDI-2027"]:
        for p in call(f"/products&sku={sku}&status=any"):
            call(f"/products/{p['id']}", method="DELETE")  # corbeille (pas de force)

    ids = {}
    ids["licence"] = variable(
        "SCV-LIC-2027", "Licence FFS 2026-2027", cats["licences-ffs"],
        *simple_options("Type", [("Pass Découverte", 9), ("Adulte (+18 ans)", 93), ("Enfant (-18 ans)", 83),
                                 ("Cadre dirigeant", 114), ("Familiale (4 pers. min.)", 290)]),
        75, "Licence de la Fédération Française de Ski, obligatoire pour toutes les sorties ski "
            "(sauf formule piéton). Le Pass Découverte suffit pour une première sortie.",
        status="draft")  # licence prise à la bourse aux skis ou aux permanences de décembre

    ids["stage"] = variable(
        "SCV-STAGE-2027", "Stage Dolomites – du 21 au 27 février 2027", cats["stage-fevrier"],
        *simple_options("Tarif", [("Plus de 18 ans", 1300), ("Moins de 18 ans", 1100), ("Non-skieur", 1015),
                                  ("Plus de 18 ans – fidélité", 1200), ("Moins de 18 ans – fidélité", 1000),
                                  ("Non-skieur – fidélité", 915)]),
        111, "6 nuits en pension complète à l'hôtel Regina Fassa (Mazzin Fassa), 5 jours de ski sur le "
             "Sella Ronda et le Dolomiti Superski. Assurance obligatoire (35 €) incluse. Tarif fidélité : "
             "participation à au moins un stage du club entre 2023 et 2026. Licence FFS obligatoire.",
        status="draft")  # pas de paiement en ligne : dossier + règlement à la permanence ou par courrier

    mardis = [(2026, 12, 15)] + [(2027, m, d) for m, d in [(1, 5), (1, 12), (1, 19), (1, 26), (2, 2), (2, 9), (2, 16), (3, 9), (3, 16), (3, 23), (3, 30)]]
    samedis = [(2026, 12, 12)] + [(2027, m, d) for m, d in [(1, 9), (1, 16), (1, 23), (1, 30), (2, 6), (2, 13), (3, 6), (3, 13), (3, 20), (3, 27), (4, 3)]]
    def sorties(prefix, cat, dates, formules, image, short):
        """Un produit variable par date ; stock géré au niveau du produit => places partagées."""
        out = []
        for n, (y, m, d) in enumerate(dates):
            confirm = " (à confirmer)" if (m, d) == (4, 3) else ""
            out.append(variable(f"{prefix}-{y}{m:02d}{d:02d}", f"Sortie du {DAYS[cat].lower()} {d} {MOIS[m]} {y}{confirm}",
                                cats[cat], *simple_options("Formule", formules), image, short,
                                stock=PLACES, menu_order=n))
        return out

    ids["mardi"] = sorties("SCV-MAR", "sorties-mardi", mardis, [("Ski – forfait + cours", 50), ("Piéton", 30)], 103,
                           "Adultes. Départ 7h15 parking Sainte-Anne (Vence), 7h30 parking de la Scierie "
                           "(Castagniers), retour 18h-18h30. Transport en minibus. Casque obligatoire, repas à votre "
                           "charge. 6 participants minimum. Licence FFS obligatoire (sauf piéton).")
    ids["samedi"] = sorties("SCV-SAM", "sorties-samedi", samedis,
                            [("Enfant (-18 ans) – forfait + cours + goûter", 48), ("Adulte – forfait + cours", 50),
                             ("Piéton", 30)], 106,
                            "Enfants dès 6 ans et adultes, cours par des moniteurs fédéraux. Départ 6h50 parking "
                            "Sainte-Anne (Vence), 7h05 McDonald's Cagnes-sur-Mer, 7h30 Castagniers. Goûter offert. "
                            "Licence FFS obligatoire (sauf piéton).")

    for sku in ["SCV-MAT-RADICAL130", "SCV-MAT-RADICAL120"]:
        for p in call(f"/products&sku={sku}&status=any"):
            call(f"/products/{p['id']}", {"status": "draft"}, "PUT")  # simple mise en relation, pas de vente par le club
            ids.setdefault("materiel", []).append(p["id"])

    json.dump(ids, open("source/woo_ids.json", "w"), indent=1)
    links = {pid: call(f"/products/{pid}")["permalink"] for k in ("mardi", "samedi") for pid in ids[k]}
    json.dump(links, open("source/woo_links.json", "w"), indent=1)
    print(json.dumps(ids))


if __name__ == "__main__":
    main()
