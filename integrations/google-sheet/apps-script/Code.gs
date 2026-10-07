/**
 * Ski Club Vence — réception des commandes WooCommerce dans Google Sheets.
 *
 * - Onglet « Commandes » : une ligne par article commandé (filtrable par sortie, formule, statut…).
 * - Un onglet par sortie / produit (ex. « Sortie du samedi 16 janvier 2027 ») = liste des participants.
 * - Onglet « Synthèse » : nombre de places payées par sortie et par formule.
 * - Clé unique « commande-article » : un renvoi ou un changement de statut MET À JOUR la ligne
 *   existante au lieu de créer un doublon.
 *
 * À coller dans Extensions > Apps Script du Google Sheet, puis déployer en « Application Web ».
 */

/** Doit être identique à la « Clé secrète » saisie dans WordPress (Réglages > Google Sheet SCV). */
const SECRET = 'REMPLACEZ-PAR-UNE-CLE-SECRETE-LONGUE';

const MAIN_SHEET = 'Commandes';
const SUMMARY_SHEET = 'Synthèse';
const HEADERS = [
  'Clé', 'N° commande', 'Date commande', 'Statut', 'Sortie / produit', 'Formule', 'Catégorie',
  'Qté', 'Montant ligne', 'Total commande', 'Prénom', 'Nom', 'E-mail', 'Téléphone',
  'Paiement', 'Note client', 'Lien commande', 'Mis à jour le',
];
const STATUS_COLORS = {
  processing: '#D9F2E3', completed: '#D9F2E3', 'on-hold': '#FFF4CC',
  cancelled: '#FDE3DB', refunded: '#FDE3DB', failed: '#FDE3DB', test: '#E8EEF4',
};

function doPost(e) {
  const lock = LockService.getScriptLock();
  try {
    lock.waitLock(30000);
    const data = JSON.parse(e.postData.contents);
    if (!data || data.secret !== SECRET) {
      return json_({ ok: false, error: 'Clé secrète invalide' });
    }
    const order = data.order || {};
    const items = data.items || [];
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const main = getSheet_(ss, MAIN_SHEET, true);

    let written = 0;
    items.forEach(function (item) {
      const row = buildRow_(order, item);
      upsert_(main, row, order.status);
      // Onglet par sortie (pas pour la ligne de test)
      if (order.number !== 'TEST' && item.product) {
        upsert_(getSheet_(ss, sheetName_(item.product), false), row, order.status);
      }
      written++;
    });
    try {
      ensureSummary_(ss); // non bloquant : les lignes sont déjà écrites
    } catch (summaryErr) {
      console.warn('Synthèse non créée : ' + summaryErr);
    }
    return json_({ ok: true, rows: written });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}

/** Petit test manuel depuis l'éditeur (bouton Exécuter) : simule une commande. */
function testDoPost() {
  const fake = {
    secret: SECRET,
    order: { id: 0, number: 'TEST', date: '2026-12-01 10:30:00', status: 'test', status_label: 'Test',
      first_name: 'Marie', last_name: 'Dupont', email: 'marie@example.com', phone: '0600000000',
      payment_method: 'Carte bancaire', total: 48, note: '', edit_url: '' },
    items: [{ item_id: 0, product: 'TEST', formule: 'Formule : Enfant', category: 'Sorties du samedi', quantity: 1, total: 48 }],
  };
  Logger.log(doPost({ postData: { contents: JSON.stringify(fake) } }).getContent());
}

/* ------------------------------------------------------------------ */

function buildRow_(order, item) {
  return [
    order.id + '-' + item.item_id,
    order.number,
    parseDate_(order.date),
    order.status_label || order.status,
    item.product || '',
    (item.formule || '').replace(/^Formule\s*:\s*/i, ''),
    item.category || '',
    Number(item.quantity) || 0,
    Number(item.total) || 0,
    Number(order.total) || 0,
    order.first_name || '',
    order.last_name || '',
    order.email || '',
    // Apostrophe : conserve le 0 initial du numéro de téléphone
    order.phone ? "'" + order.phone : '',
    order.payment_method || '',
    order.note || '',
    order.edit_url || '',
    new Date(),
  ];
}

/** Met à jour la ligne portant la même clé (colonne A), sinon l'ajoute en bas. */
function upsert_(sheet, row, status) {
  const found = sheet.getRange('A:A').createTextFinder(String(row[0])).matchEntireCell(true).findNext();
  const r = found ? found.getRow() : sheet.getLastRow() + 1;
  sheet.getRange(r, 1, 1, row.length).setValues([row]);
  sheet.getRange(r, 3).setNumberFormat('dd/mm/yyyy hh:mm');
  sheet.getRange(r, 9, 1, 2).setNumberFormat('#,##0.00 €');
  sheet.getRange(r, 18).setNumberFormat('dd/mm/yyyy hh:mm');
  sheet.getRange(r, 1, 1, row.length).setBackground(STATUS_COLORS[status] || null);
  // Le filtre doit couvrir les nouvelles lignes
  const filter = sheet.getFilter();
  if (filter && filter.getRange().getLastRow() < r) {
    filter.remove();
    sheet.getRange(1, 1, sheet.getMaxRows(), HEADERS.length).createFilter();
  }
}

function getSheet_(ss, name, isMain) {
  let sheet = ss.getSheetByName(name);
  if (sheet) return sheet;
  sheet = ss.insertSheet(name);
  sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS])
    .setFontWeight('bold').setFontColor('#FFFFFF').setBackground('#0B3C5D');
  sheet.setFrozenRows(1);
  sheet.hideColumns(1); // la clé technique reste masquée
  sheet.setColumnWidth(5, 260);
  sheet.setColumnWidth(6, 260);
  sheet.getRange(1, 1, sheet.getMaxRows(), HEADERS.length).createFilter();
  if (isMain) ss.setActiveSheet(sheet);
  return sheet;
}

/** Synthèse : places par sortie et formule (commandes payées ou en attente uniquement). */
function ensureSummary_(ss) {
  if (ss.getSheetByName(SUMMARY_SHEET)) return;
  const s = ss.insertSheet(SUMMARY_SHEET);
  s.getRange('A1').setFormula(
    "=QUERY(" + MAIN_SHEET + "!B:J,\"select E, F, sum(H), sum(I) where (D = 'En cours' or D = 'Terminée' or D = 'En attente') " +
    "group by E, F order by E label E 'Sortie / produit', F 'Formule', sum(H) 'Places', sum(I) 'Montant'\",1)"
  );
  s.getRange('A1:D1').setFontWeight('bold').setFontColor('#FFFFFF').setBackground('#0B3C5D');
  s.setFrozenRows(1);
  s.setColumnWidth(1, 300);
  s.setColumnWidth(2, 300);
}

/** Noms d'onglets : 100 caractères max, sans [ ] * ? / \ : */
function sheetName_(name) {
  return String(name).replace(/[\[\]\*\?\/\\:]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 95) || 'Sans nom';
}

/** « 2026-12-01 10:30:00 » (heure du site) → Date dans le fuseau du script (Europe/Paris). */
function parseDate_(s) {
  const m = String(s || '').match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):?(\d{2})?/);
  return m ? new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0)) : s;
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
