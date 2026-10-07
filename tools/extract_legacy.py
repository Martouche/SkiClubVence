"""Phase 1 — extraction du site legacy skiclubvence.com (WPBakery).

Produit dans source/ :
  pages/<slug>.json   contenu brut + texte nettoyé (sans shortcodes VC)
  pages/<slug>.md     texte nettoyé lisible
  media.json          inventaire complet de la médiathèque
  menus.json          liens de navigation extraits du HTML de l'accueil
  inventory.md        synthèse
"""
import html
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE = "https://skiclubvence.com/index.php?rest_route="
OUT = Path(__file__).resolve().parent.parent / "source"
UA = {"User-Agent": "Mozilla/5.0 (SkiClubVence migration)"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8"), dict(r.headers)


def get_all(route, fields):
    items, page = [], 1
    while True:
        body, headers = get(f"{BASE}{route}&per_page=100&page={page}&_fields={fields}")
        items += json.loads(body)
        if page >= int(headers.get("X-WP-TotalPages", 1)):
            return items
        page += 1


SHORTCODE = re.compile(r"\[/?(vc_|/?vc_)[^\]]*\]")
ANY_SHORTCODE = re.compile(r"\[/?[a-z_][a-z0-9_-]*(?:\s[^\]]*)?\]")


class Text(HTMLParser):
    """HTML -> markdown léger : titres, paragraphes, listes, liens, images."""

    BLOCK = {"p", "div", "section", "br", "tr", "table", "ul", "ol"}

    def __init__(self):
        super().__init__()
        self.out, self.href, self.skip = [], None, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style"):
            self.skip += 1
        elif re.fullmatch(r"h[1-6]", tag):
            self.out.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "li":
            self.out.append("\n- ")
        elif tag in ("td", "th"):
            self.out.append(" | ")
        elif tag in self.BLOCK:
            self.out.append("\n")
        elif tag == "a":
            self.href = a.get("href")
            self.out.append("[")
        elif tag == "img" and a.get("src"):
            self.out.append(f"\n![{a.get('alt', '')}]({a['src']})\n")
        elif tag == "iframe" and a.get("src"):
            self.out.append(f"\n[iframe]({a['src']})\n")
        elif tag in ("strong", "b"):
            self.out.append("**")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1
        elif tag == "a":
            self.out.append(f"]({self.href})" if self.href else "]")
            self.href = None
        elif tag in ("strong", "b"):
            self.out.append("**")
        elif tag in self.BLOCK or re.fullmatch(r"h[1-6]", tag):
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(re.sub(r"\s+", " ", data))

    def text(self):
        t = "".join(self.out)
        t = re.sub(r"\*\*\s*\*\*", "", t)
        t = re.sub(r"\[\s*\]\([^)]*\)", "", t)
        t = re.sub(r"[ \t]+\n", "\n", t)
        return re.sub(r"\n{3,}", "\n\n", t).strip()


def clean(rendered):
    """Supprime tout résidu de shortcode puis convertit en texte structuré."""
    s = ANY_SHORTCODE.sub("", rendered)
    p = Text()
    p.feed(s)
    return html.unescape(p.text())


def main():
    (OUT / "pages").mkdir(parents=True, exist_ok=True)

    pages = get_all("/wp/v2/pages", "id,slug,link,title,content,featured_media,modified")
    summary = []
    for pg in pages:
        rendered = pg["content"]["rendered"]
        txt = clean(rendered)
        title = html.unescape(pg["title"]["rendered"])
        residue = sorted(set(re.findall(r"\[/?(vc_[a-z_]+)", rendered)))
        imgs = sorted(set(re.findall(r"https?://skiclubvence\.com/wp-content/uploads/[^\"' )]+", rendered)))
        data = {"id": pg["id"], "slug": pg["slug"], "title": title, "link": pg["link"],
                "modified": pg["modified"], "featured_media": pg["featured_media"],
                "vc_residue_in_rendered": residue, "uploads_referenced": imgs,
                "clean_text": txt, "rendered_html": rendered}
        (OUT / "pages" / f"{pg['slug']}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
        (OUT / "pages" / f"{pg['slug']}.md").write_text(f"# {title}\n\nSource : {pg['link']}\n\n{txt}\n", "utf-8")
        summary.append((pg["slug"], title, pg["link"], len(txt), len(imgs)))

    media = get_all("/wp/v2/media", "id,date,slug,title,alt_text,mime_type,source_url,media_details.filesize")
    (OUT / "media.json").write_text(json.dumps(media, ensure_ascii=False, indent=2), "utf-8")

    home, _ = get("https://skiclubvence.com/")
    nav = re.findall(r'<a[^>]*href="(https://skiclubvence\.com[^"]*)"[^>]*>(.*?)</a>', home, re.S)
    menu = []
    for href, label in nav:
        label = html.unescape(re.sub(r"<[^>]+>", "", label)).strip()
        if label and not label.isdigit() and (href, label) not in menu:
            menu.append((href, label))
    (OUT / "menus.json").write_text(json.dumps([{"url": h, "label": l} for h, l in menu], ensure_ascii=False, indent=2), "utf-8")

    by_type = {}
    for m in media:
        by_type[m["mime_type"]] = by_type.get(m["mime_type"], 0) + 1
    lines = ["# Inventaire skiclubvence.com", "", f"## Pages ({len(summary)})", "",
             "| Slug | Titre | Caractères | Images |", "|---|---|---|---|"]
    lines += [f"| [{s}]({l}) | {t} | {n} | {i} |" for s, t, l, n, i in sorted(summary)]
    lines += ["", f"## Médias ({len(media)})", ""] + [f"- {k} : {v}" for k, v in sorted(by_type.items())]
    lines += ["", "### Documents PDF", ""] + [f"- {m['source_url']}" for m in media if m["mime_type"] == "application/pdf"]
    lines += ["", f"## Menu ({len(menu)} liens)", ""] + [f"- {l} → {h}" for h, l in menu]
    (OUT / "inventory.md").write_text("\n".join(lines) + "\n", "utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
