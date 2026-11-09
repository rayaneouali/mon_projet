/**
 * SUIVI DES ÉQUIPES — MDC
 * Base de données : ce Google Sheet. Interface : Index.html (web app).
 *
 * Onglets (créés par setup()) :
 *   Gars      : Nom | Equipe | Actif
 *   Equipes   : Equipe | Chef
 *   Dossiers  : Dossier | Client | Lieu | Actif
 *   Journal   : Date | Equipe | Dossier | Gars | Statut | Note | Saisi le
 *   Samedis   : Id | Samedi | Gars | Dossier | Statut | Note | Créé le
 *   Config    : Cle | Valeur   (code d'accès)
 */

const HEADERS = {
  Gars:     ['Nom', 'Equipe', 'Actif'],
  Equipes:  ['Equipe', 'Chef'],
  Dossiers: ['Dossier', 'Client', 'Lieu', 'Actif'],
  Journal:  ['Date', 'Equipe', 'Dossier', 'Gars', 'Statut', 'Note', 'Saisi le'],
  Samedis:  ['Id', 'Samedi', 'Gars', 'Dossier', 'Statut', 'Note', 'Créé le'],
  Config:   ['Cle', 'Valeur']
};

const STATUTS_SAMEDI = ['Demandé', 'Accepté', 'Refusé', 'Fait'];

/* ---------- Installation (à lancer une seule fois) ---------- */

function setup() {
  const ss = SpreadsheetApp.getActive();
  Object.keys(HEADERS).forEach(function (name) {
    let sh = ss.getSheetByName(name);
    if (!sh) sh = ss.insertSheet(name);
    if (sh.getLastRow() === 0) {
      sh.getRange(1, 1, 1, HEADERS[name].length)
        .setValues([HEADERS[name]]).setFontWeight('bold').setBackground('#e8eef7');
      sh.setFrozenRows(1);
    }
  });
  // Les dates sont stockées en texte AAAA-MM-JJ (évite les décalages de fuseau).
  ss.getSheetByName('Journal').getRange('A:A').setNumberFormat('@');
  ss.getSheetByName('Samedis').getRange('B:B').setNumberFormat('@');

  // Exemples si vide (à remplacer par les vraies données)
  const eq = ss.getSheetByName('Equipes');
  if (eq.getLastRow() < 2) eq.getRange(2, 1, 2, 2).setValues([['Équipe 1', 'Karim'], ['Équipe 2', 'Mehdi']]);
  const g = ss.getSheetByName('Gars');
  if (g.getLastRow() < 2) g.getRange(2, 1, 6, 3).setValues([
    ['Karim', 'Équipe 1', 'Oui'], ['Yanis', 'Équipe 1', 'Oui'], ['Lucas', 'Équipe 1', 'Oui'],
    ['Mehdi', 'Équipe 2', 'Oui'], ['Samir', 'Équipe 2', 'Oui'], ['Thomas', 'Équipe 2', 'Oui']
  ]);
  const d = ss.getSheetByName('Dossiers');
  if (d.getLastRow() < 2) d.getRange(2, 1, 2, 4).setValues([
    ['D-2026-001', 'Client exemple', 'Orléans', 'Oui'],
    ['D-2026-002', 'Client exemple 2', 'Tours', 'Oui']
  ]);
  const c = ss.getSheetByName('Config');
  if (c.getLastRow() < 2) c.getRange(2, 1, 1, 2).setValues([['code', '1234']]);

  // Supprime l'onglet vide par défaut s'il existe
  ['Feuille 1', 'Sheet1', 'Feuille1'].forEach(function (n) {
    const sh = ss.getSheetByName(n);
    if (sh && sh.getLastRow() === 0 && ss.getSheets().length > 1) ss.deleteSheet(sh);
  });
}

/* ---------- Web app ---------- */

function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('Suivi équipes')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

/* ---------- Utilitaires ---------- */

function sheet_(name) {
  const sh = SpreadsheetApp.getActive().getSheetByName(name);
  if (!sh) throw new Error('Onglet "' + name + '" introuvable. Lance setup() une fois.');
  return sh;
}

function rows_(name) {
  const sh = sheet_(name);
  const last = sh.getLastRow();
  if (last < 2) return [];
  return sh.getRange(2, 1, last - 1, HEADERS[name].length).getValues();
}

function d2s_(v) {
  if (v instanceof Date) return Utilities.formatDate(v, Session.getScriptTimeZone(), 'yyyy-MM-dd');
  return String(v || '').trim();
}

function oui_(v) {
  const s = String(v).trim().toLowerCase();
  return s === '' || s === 'oui' || s === 'o' || s === 'true' || s === 'x' || s === '1';
}

function now_() {
  return Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm');
}

function checkCode_(code) {
  const conf = rows_('Config');
  let expected = '';
  conf.forEach(function (r) { if (String(r[0]).trim().toLowerCase() === 'code') expected = String(r[1]).trim(); });
  if (expected && String(code || '').trim() !== expected) throw new Error('Code d\'accès incorrect.');
}

function addDays_(iso, n) {
  const p = iso.split('-').map(Number);
  const d = new Date(p[0], p[1] - 1, p[2] + n);
  return Utilities.formatDate(d, Session.getScriptTimeZone(), 'yyyy-MM-dd');
}

function withLock_(fn) {
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try { return fn(); } finally { lock.releaseLock(); }
}

/* ---------- API appelée par l'interface ---------- */

/** Vérifie le code et renvoie les listes de référence. */
function getRefs(code) {
  checkCode_(code);
  const equipes = rows_('Equipes').filter(function (r) { return String(r[0]).trim(); })
    .map(function (r) { return { nom: String(r[0]).trim(), chef: String(r[1]).trim() }; });
  const gars = rows_('Gars').filter(function (r) { return String(r[0]).trim() && oui_(r[2]); })
    .map(function (r) { return { nom: String(r[0]).trim(), equipe: String(r[1]).trim() }; });
  const dossiers = rows_('Dossiers').filter(function (r) { return String(r[0]).trim() && oui_(r[3]); })
    .map(function (r) { return { code: String(r[0]).trim(), client: String(r[1]).trim(), lieu: String(r[2]).trim() }; });
  return { equipes: equipes, gars: gars, dossiers: dossiers };
}

/** Saisies et samedis d'une semaine (lundi -> dimanche). */
function getWeek(code, monday) {
  checkCode_(code);
  const end = addDays_(monday, 6);
  const journal = rows_('Journal').map(function (r) {
    return { date: d2s_(r[0]), equipe: String(r[1]), dossier: String(r[2]), gars: String(r[3]),
             statut: String(r[4]), note: String(r[5]) };
  }).filter(function (e) { return e.date >= monday && e.date <= end; });
  const samedis = rows_('Samedis').map(function (r) {
    return { id: String(r[0]), samedi: d2s_(r[1]), gars: String(r[2]), dossier: String(r[3]),
             statut: String(r[4]), note: String(r[5]) };
  }).filter(function (s) { return s.samedi >= monday && s.samedi <= end; });
  return { journal: journal, samedis: samedis };
}

/** Saisie d'une équipe pour un jour. Remplace la saisie précédente de cette équipe ce jour-là. */
function saveDay(code, p) {
  checkCode_(code);
  if (!p || !p.date || !p.equipe) throw new Error('Date et équipe obligatoires.');
  if (!p.lignes || !p.lignes.length) throw new Error('Aucun gars dans la saisie.');
  return withLock_(function () {
    const sh = sheet_('Journal');
    const data = rows_('Journal');
    const garsSaisis = {};
    p.lignes.forEach(function (l) { garsSaisis[l.gars] = true; });
    // Lignes à supprimer : même jour ET (même équipe OU même gars déplacé ici)
    const toDelete = [];
    data.forEach(function (r, i) {
      if (d2s_(r[0]) === p.date && (String(r[1]) === p.equipe || garsSaisis[String(r[3])])) toDelete.push(i + 2);
    });
    for (let k = toDelete.length - 1; k >= 0; k--) sh.deleteRow(toDelete[k]);
    const stamp = now_();
    const out = p.lignes.map(function (l) {
      return [p.date, p.equipe, p.dossier || '', l.gars, l.statut === 'Absent' ? 'Absent' : 'Présent', l.note || '', stamp];
    });
    const start = sh.getLastRow() + 1;
    sh.getRange(start, 1, out.length, 1).setNumberFormat('@');
    sh.getRange(start, 1, out.length, out[0].length).setValues(out);
    return { ok: true, n: out.length };
  });
}

/** Ajoute une demande de travail le samedi (une ligne par gars). */
function addSamedi(code, p) {
  checkCode_(code);
  if (!p || !p.samedi || !p.gars || !p.gars.length) throw new Error('Samedi et gars obligatoires.');
  return withLock_(function () {
    const sh = sheet_('Samedis');
    const stamp = now_();
    const out = p.gars.map(function (g) {
      return [Utilities.getUuid().slice(0, 8), p.samedi, g, p.dossier || '', 'Demandé', p.note || '', stamp];
    });
    const start = sh.getLastRow() + 1;
    sh.getRange(start, 2, out.length, 1).setNumberFormat('@');
    sh.getRange(start, 1, out.length, out[0].length).setValues(out);
    return { ok: true };
  });
}

/** Demandes samedi à partir d'une date (incluse). */
function getSamedis(code, fromIso) {
  checkCode_(code);
  return rows_('Samedis').map(function (r) {
    return { id: String(r[0]), samedi: d2s_(r[1]), gars: String(r[2]), dossier: String(r[3]),
             statut: String(r[4]), note: String(r[5]) };
  }).filter(function (s) { return s.id && s.samedi >= fromIso; })
    .sort(function (a, b) { return a.samedi < b.samedi ? -1 : a.samedi > b.samedi ? 1 : a.gars.localeCompare(b.gars); });
}

/** Change le statut d'une demande samedi. */
function setSamediStatut(code, id, statut) {
  checkCode_(code);
  if (STATUTS_SAMEDI.indexOf(statut) < 0) throw new Error('Statut inconnu.');
  return withLock_(function () {
    const sh = sheet_('Samedis');
    const data = rows_('Samedis');
    for (let i = 0; i < data.length; i++) {
      if (String(data[i][0]) === String(id)) { sh.getRange(i + 2, 5).setValue(statut); return { ok: true }; }
    }
    throw new Error('Demande introuvable.');
  });
}

/** Supprime une demande samedi. */
function deleteSamedi(code, id) {
  checkCode_(code);
  return withLock_(function () {
    const sh = sheet_('Samedis');
    const data = rows_('Samedis');
    for (let i = 0; i < data.length; i++) {
      if (String(data[i][0]) === String(id)) { sh.deleteRow(i + 2); return { ok: true }; }
    }
    return { ok: true };
  });
}
