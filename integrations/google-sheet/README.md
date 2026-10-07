# Commandes WooCommerce → Google Sheet

Chaque commande payée sur skiclubvence.com est copiée automatiquement dans un Google Sheet, **une ligne par article**. Un membre du bureau peut ainsi suivre les inscriptions sans se connecter à WordPress.

| Onglet | Contenu |
|---|---|
| **Commandes** | Toutes les lignes, avec un filtre sur chaque colonne : sortie, formule, statut, nom… |
| **Un onglet par sortie** (ex. « Sortie du samedi 16 janvier 2027 ») | La liste des participants de cette sortie, créée automatiquement |
| **Synthèse** | Nombre de places et montant par sortie et par formule, pour les commandes « En cours », « Terminée » et « En attente » |

**Pas de doublons** : chaque ligne porte une clé unique `n° commande - n° article`, dans la colonne A, masquée. Un renvoi ou un changement de statut (annulation, remboursement…) **met à jour** la ligne existante et sa couleur, sans en créer une nouvelle.

Colonnes : N° commande, Date, Statut, Sortie/produit, Formule, Catégorie, Qté, Montant ligne, Total commande, Prénom, Nom, E-mail, Téléphone, Paiement, Note client, Lien vers la commande, Mis à jour le.

---

## 1. Créer le Google Sheet et le webhook (environ 5 minutes)

1. Créez un Google Sheet vide, par exemple « SCV – Commandes 2026-2027 », avec le compte Google du club.
2. Menu **Extensions → Apps Script**.
3. Remplacez le contenu de `Code.gs` par le fichier [`apps-script/Code.gs`](apps-script/Code.gs).
4. En haut du script, remplacez `REMPLACEZ-PAR-UNE-CLE-SECRETE-LONGUE` par une clé secrète, par exemple 30 caractères aléatoires. **Notez-la** : elle servira dans WordPress.
5. Facultatif mais conseillé : dans **⚙ Paramètres du projet**, réglez le fuseau horaire sur `Europe/Paris`.
6. Cliquez sur **Exécuter** avec la fonction `testDoPost` sélectionnée, puis acceptez les autorisations demandées. Une ligne « TEST » apparaît dans l'onglet « Commandes ». Vous pouvez la supprimer ensuite.
7. **Déployer → Nouveau déploiement** → type **Application Web** :
   - *Exécuter en tant que* : **Moi** ;
   - *Qui a accès* : **Tout le monde**. C'est indispensable pour que WordPress puisse appeler l'URL ; la clé secrète protège l'accès.
8. Copiez l'**URL de l'application Web**, qui se termine par `/exec`.

> Si vous modifiez le script plus tard, faites **Déployer → Gérer les déploiements → ✏️ → Nouvelle version**. L'URL reste la même.

## 2. Installer l'extension WordPress

**Méthode conseillée, sans toucher au thème :**

1. WordPress → **Extensions → Ajouter → Téléverser une extension** → choisissez `scv-google-sheet-sync.zip` → **Installer**, puis **Activer**.
2. **Réglages → Google Sheet SCV** : collez l'URL `/exec` et la clé secrète, puis **Enregistrer**.
3. Cliquez sur **Envoyer une commande de test** : un message vert confirme la réception, et une ligne « TEST » arrive dans le Sheet.

> Il vaut mieux une extension plutôt que `functions.php` : le code est indépendant du thème Hello Elementor, et il ne sera donc pas écrasé lors de ses mises à jour. Il se désactive aussi en un clic.

Variante : vous pouvez définir les réglages dans `wp-config.php` au lieu de l'écran de réglages :

```php
define( 'SCV_SHEET_WEBHOOK_URL', 'https://script.google.com/macros/s/XXXX/exec' );
define( 'SCV_SHEET_SECRET', 'votre-cle-secrete' );
```

## 3. Fonctionnement côté WordPress

- **Déclencheurs** :
  - `woocommerce_payment_complete`, lorsque Monetico confirme le paiement ;
  - `woocommerce_order_status_changed`, pour les statuts En cours, Terminée, En attente, Annulée, Remboursée et Échouée.

  Les commandes en attente de paiement ou en brouillon ne sont **pas** envoyées.
- **Envoi en arrière-plan**, via Action Scheduler de WooCommerce : le paiement du client n'est jamais ralenti. Un seul envoi est mis en file par commande.
- **Échec** (URL ou clé incorrecte, Google indisponible) :
  - une note est ajoutée à la commande ;
  - une erreur est inscrite dans **WooCommerce → État → Journaux**, source `scv-google-sheet` ;
  - l'action apparaît en échec dans **Outils → Actions planifiées**, groupe `scv-sheet`.
- **Renvoi manuel** : dans une commande, liste **Actions de commande → « Envoyer vers le Google Sheet »**. Pratique pour réenvoyer les commandes passées avant l'installation.

## Partager le Sheet

Partagez le Google Sheet **en lecture seule** avec les membres du bureau. Seul le compte qui a déployé le script doit avoir le droit de modification. Les données contiennent les e-mails et téléphones des adhérents : ne le partagez pas publiquement.
