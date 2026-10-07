# Rapport de migration — skiclubvence.com → dev.skiclubvence.com

Date : 28 septembre 2026 · Refonte WPBakery → Elementor 4 (widgets atomiques V4, conteneurs Flexbox/Grid) + Pro Elements.

## 1. Style global (Phase 2)

| Élément | Valeur |
|---|---|
| Couleur primaire | `--scv-primary` #0B3C5D (bleu nuit alpin) |
| Secondaire | `--scv-secondary` #1F7AB8 · `--scv-ice` #BFE3F5 |
| Accent | `--scv-accent` #E8552D (orange balise) · `--scv-accent-dark` #C4401C |
| Neutres | `--scv-ink` #132230 · `--scv-muted` #51667A · `--scv-snow` #F3F7FA · `--scv-line` #D8E3EC |
| Polices | Titres **Barlow Condensed** 700/800 capitales · Texte **Source Sans 3** |
| Espacements | `--section-y` clamp(56px, 8vw, 112px) · `--gutter-x` clamp(16px, 4vw, 48px) · `--container-max` 1180px |

- Styles par défaut du kit : h1 → h6, p, a (tailles tablette et mobile incluses).
- Couleurs et typographies globales V3 alignées sur la charte, pour les widgets V3 comme le Nav Menu.
- 26 classes globales réutilisables : `scv-section`, `scv-inner`, `scv-grid-2/3/4`, `scv-card`, `scv-btn` (+ `-ghost`, `-outline`), `scv-field`, `scv-label`, `scv-price`, `scv-pill`, etc.
- Points de rupture : valeurs Elementor par défaut (mobile ≤ 767 px, tablette ≤ 1024 px), utilisées via `@media(--tablet)` et `@media(--mobile)`.

## 2. Theme Builder (Phase 3)

| Modèle | ID | Condition |
|---|---|---|
| En-tête SCV | 217 | Tout le site |
| Pied de page SCV | 218 | Tout le site |

- **En-tête** : logo, menu principal, bouton « Réserver une sortie ». En-tête collant (sticky). Menu burger pleine largeur sous 1024 px.
- **Pied de page** :
  - coordonnées, avec liens `tel:` et `mailto:` ;
  - permanences du jeudi, 17h – 19h ;
  - liens rapides ;
  - boutons Instagram et Facebook ;
  - copyright et lien vers les mentions légales.
- **Menus WordPress** :
  - « Menu principal SCV » (#18), rattaché à l'emplacement En-tête ;
  - « Liens rapides SCV » (#19), rattaché à l'emplacement Pied de page.

## 3. Pages créées et publiées (Phase 4)

| Page | ID | Slug | Contenu |
|---|---|---|---|
| Accueil (page d'accueil du site) | 183 | accueil | Hero avec photo, 4 chiffres clés, présentation du club, 3 cartes d'activités, bourse aux skis, dates à venir, webcams et actualités, partenaires, bandeau d'appel à l'action |
| Dossier d'inscription | 184 | dossier-dinscription | 3 étapes, téléchargement du PDF, pièces obligatoires, 4 autres PDF, **formulaire de demande d'information** |
| Tarifs et calendrier | 185 | tarifs-et-calendrier | 5 cartes de licences FFS, 5 cartes de sorties, calendrier des mardis et samedis 2027, règlement, stage, PDF des tarifs |
| Événements & Sorties | 186 | evenements | 6 dates clés, détail des sorties du mardi et du samedi (horaires, points de ramassage, **bouton Réserver pour chaque formule**), stage des Dolomites |
| Matériel d'occasion & bourse | 187 | materiel-doccasion | Grille du matériel (Rossignol Radical 130/120), **formulaire « Vendre mon matériel »** avec photo, bourse aux skis du 14 novembre |
| Webcams | 188 | webcams | 6 webcams en direct Trinum (Auron ×3, Isola 2000 ×3) |
| Galerie photos | 189 | galerie | **3 onglets** (Saison 2025-2026 : 219 photos · Stage Sestrière 2024-2025 : 124 photos + 6 vidéos · Archives 2024 : 92 photos). Grille masonry sans recadrage (4 / 3 / 2 colonnes), chargement progressif, agrandissement au clic. Remplissage par `tools/fill_gallery.py` |
| Contact | 190 | contact | Coordonnées, permanences, informations pratiques, **formulaire de contact** (Nom, E-mail, Téléphone, Sujet, Message), **Google Maps** |
| Réservation | 191 | reservation | Formulaire temporaire de réservation (formule, date, participants, licence, mode de règlement) |
| Mentions légales | 192 | mentions-legales | Éditeur, hébergement, propriété intellectuelle, RGPD, droit à l'image |

Les 4 formulaires envoient un e-mail à **skiclubdevence@gmail.com** et enregistrent les demandes dans Elementor, rubrique Envois (*Submissions*).

## 4. Médias importés (Phase 1)

**86 fichiers** ont été téléversés dans la médiathèque de dev, IDs 64 → 149. La correspondance avec les anciennes URL est dans `source/media_map.json`.

- **Logo** : `skiclubvence.webp` (#75) et `skiclubvence-petit.png` (#119).
- **Photos de pages** : environ 30 (équipe, moniteurs, sorties, Dolomites, hôtel, affiche de la bourse 2026, paysages).
- **Logos partenaires** : 10.
- **PDF** (7) :
  - Inscription 2025-2026 (#110) ;
  - Tarifs 2026-2027 (#117) ;
  - Tarifs 2025-2026 (#113) ;
  - Stage 2027 (#116) ;
  - Stage 2026 (#112) ;
  - Règlement intérieur (#64) ;
  - Informations pratiques (#78).
- **Galerie** : 30 photos de la saison 2024-2025 (#120 → #149), sur les 1 305 de la galerie d'origine.

Le contenu texte de toutes les pages legacy, nettoyé des shortcodes, est dans `source/pages/*.md` (28 pages). L'inventaire complet est dans `source/inventory.md`.

## 5. WooCommerce et Monetico (Phase 5)

Les réservations passent par de **vrais produits WooCommerce payables**. Il n'y a plus de formulaire de réservation. Catalogue créé par `tools/setup_woocommerce.py`, relançable sans créer de doublons :

| Produit (ID) | Choix proposés au client | Prix |
|---|---|---|
| Licence FFS 2026-2027 (680) | Type : Découverte / Adulte / Enfant / Cadre / Familiale | 9 / 93 / 83 / 114 / 290 € |
| Sorties du mardi — **1 produit par date** (11 produits, IDs 765 → 795), ex. « Sortie du mardi 12 janvier 2027 » | Formule : Ski ou Piéton | 50 / 30 € |
| Sorties du samedi — **1 produit par date** (11 produits, IDs 798 → 838) | Formule : Enfant, Adulte ou Piéton | 48 / 50 / 30 € |
| Stage Dolomites 2027 (686) | Tarif : +15 ans / −15 ans / Non-skieur, avec ou sans fidélité (assurance 35 € incluse) | 1 300 / 1 100 / 1 015 € (fidélité 1 200 / 1 000 / 915 €) |
| Rossignol Radical 130 / 120 (263 / 264) | Produits simples, stock = 1 | 70 / 60 € |

- **Places** : **50 par sortie**, partagées entre toutes les formules (stock géré au niveau du produit). La fiche passe en « Rupture de stock » à 0 place. Le nombre se modifie produit par produit dans WooCommerce, ou via `PLACES` dans le script.
- **Boutons « Acheter » et « Réserver »** (pages Tarifs, Événements, Matériel, Réservation) : ils mènent à la fiche produit, avec la formule déjà présélectionnée (`?attribute_formule=…`, `?attribute_type=…`). La page Réservation (#191) propose un **sélecteur de dates par mois** (ancres `#mardi` et `#samedi`), plus la licence et le stage. Les boutons de sorties des pages Tarifs et Événements y mènent.
- **Boutique fermée** : le mode WooCommerce « Bientôt disponible » est actif, limité aux pages de la boutique. Les visiteurs voient une page d'attente sur la boutique, les fiches produit, le panier et la commande. L'administrateur voit tout.
- **Monetico** : le plugin est installé et le moyen de paiement « Paiement par carte bancaire » (moneticostd) est déjà activé, mais pas configuré. Je n'y ai pas touché.

**Pour ouvrir la boutique :**

1. Déconnecter Monetico du site actuel, puis renseigner les clés TPE dans WooCommerce → Réglages → Paiements → Monetico.
2. Passer une commande test.
3. Désactiver le mode « Bientôt disponible » dans WooCommerce → Réglages → Visibilité du site → En ligne.

## 6. Recette (Phase 6)

- **URL des images** : 0 URL vers skiclubvence.com sur les 10 pages (images, liens et arrière-plans CSS). Seul hôte externe : `www.trinum.com`, qui fournit les flux des webcams, volontairement.
- **Résidus WPBakery** : 0 `[vc_*]` et aucun shortcode visible dans le HTML rendu.
- **Responsive** : vérifié en 375 px et 768 px (accueil, tarifs, contact) :
  - les grilles passent de 3 à 2 puis à 1 colonne ;
  - le menu burger s'ouvre en pleine largeur ;
  - aucun défilement horizontal.
- **Outils** : `tools/shot.py` (captures headless découpées) et `tools/patch_v3_widget.py` (réglages natifs des widgets V3).

## 7. Reste à finaliser

1. **Permaliens** : le site est en liens « simples » (`?page_id=…`). Choisir *Réglages → Permaliens → Titre de la publication* pour obtenir `/dossier-dinscription/`, `/contact/`, etc. Les liens internes pointent vers les IDs de page, donc aucun ne cassera.
2. **Test des formulaires** : envoyer une demande sur chacun des 4 formulaires et vérifier la réception sur skiclubdevence@gmail.com. Un SMTP (WP Mail SMTP) est conseillé pour la délivrabilité.
3. **Dossier d'inscription 2026-2027** : seul le PDF 2025-2026 existe sur le site legacy. Téléverser le nouveau fichier et mettre à jour le bouton de la page 184.
4. **Mentions légales** : compléter le directeur de la publication, le RNA/SIRET et l'hébergeur (marqués « [à compléter] »).
5. **Nettoyage** : supprimer les pages du kit de démonstration (Home #34, Our Story #29, Our Services #19, Contact Us #13, Global Styles #9, Page d'exemple #2) et l'ancien menu « Primary Menu » (#3). Les pages WooCommerce (Boutique, Panier, Commande, Mon compte) sont à conserver pour Monetico.
6. **Pages legacy non migrées** : Informations pratiques, Règlement intérieur, Conseils, Skis paraboliques, Snowboard, Avalanches, Partenaires, Accompagnateurs. Leur texte propre est prêt dans `source/pages/`. Les pages Stage de février et Sorties hebdomadaires sont intégrées à Événements & Sorties.
7. **Galerie** : toutes les photos de l'ancienne galerie sont reprises (435 photos uniques et 6 vidéos, 493 médias au total dans la médiathèque). L'ancien onglet « Stage Dolomites 2025-2026 » était une copie exacte de « Saison 2025-2026 » : il n'a pas été recréé. Ajouter un vrai album Dolomites quand les photos seront disponibles.
8. **Redirections 301** à prévoir à la mise en production, par exemple `/tarifs-et-calendrier-2025-2026/` → `/tarifs-et-calendrier/`, `/sorties-hebdomadaires/` et `/stage-de-fevrier/` → `/evenements/`, `/bourse-aux-skis/` → `/materiel-doccasion/`.
9. **Sécurité** : régénérer le mot de passe d'application WordPress utilisé pour le MCP (il a été partagé en clair).
