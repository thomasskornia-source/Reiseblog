/* Lieblingsfilme (nur lokal im Browser) und Treffer in Kino, TV und Stream (data/vergnuegen.json) */
window.Filmfans = (function () {
  var KEY = 'lieblingsfilme';
  function lesen() { try { var a = JSON.parse(localStorage.getItem(KEY) || '[]'); return Array.isArray(a) ? a.filter(function (x) { return typeof x === 'string' && x; }) : []; } catch (e) { return []; } }
  function schreiben(a) { try { localStorage.setItem(KEY, JSON.stringify(a)); } catch (e) {} }
  function norm(s) {
    s = String(s || '').toLowerCase().replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue').replace(/ß/g, 'ss');
    try { s = s.normalize('NFD').replace(/[̀-ͯ]/g, ''); } catch (e) {}
    s = s.replace(/&/g, ' und ').replace(/[^a-z0-9]+/g, ' ').trim();
    return s.replace(/^(der|die|das|the|ein|eine|a|an) /, '');
  }
  function heute() { try { return new Date().toLocaleDateString('sv-SE', { timeZone: 'Europe/Berlin' }); } catch (e) { return new Date().toISOString().slice(0, 10); } }
  function aktuell(x) { var h = heute(); if (x.datum_bis && x.datum_bis < h) return false; if (x.datum && /^\d{4}-/.test(x.datum) && x.datum < h && !x.datum_bis) return false; return true; }
  function passt(titel, fav) { var t = ' ' + norm(titel) + ' ', f = norm(fav); return f.length >= 3 && t.indexOf(' ' + f + ' ') !== -1; }
  /* Treffer: [{fav, eintrag}] aus Kino-, TV- und Stream-Einträgen, die heute/aktuell laufen */
  function treffer(items, favs) {
    var out = [];
    (items || []).forEach(function (x) {
      if (['kino', 'tv', 'stream'].indexOf(x.rubrik) === -1 || !aktuell(x)) return;
      for (var i = 0; i < favs.length; i++) if (passt(x.titel, favs[i])) { out.push({ fav: favs[i], eintrag: x }); break; }
    });
    return out;
  }
  function wo(x) { var r = x.rubrik === 'kino' ? 'Kino' : x.rubrik === 'tv' ? 'TV' : 'Stream'; return r + (x.ort ? ' · ' + x.ort : '') + (x.rubrik !== 'stream' && x.datum ? ', ' + (x.datum === heute() ? 'heute' : x.datum) + (x.zeit ? ' ' + x.zeit : '') : ''); }
  function seite(x) { return 'vergnuegen.html?r=' + x.rubrik; }
  var AUS = 'lieblingsfilme-aus';
  function aus() { try { var a = JSON.parse(localStorage.getItem(AUS) || '[]'); return Array.isArray(a) ? a : []; } catch (e) { return []; } }
  function ausSetzen(a) { try { localStorage.setItem(AUS, JSON.stringify(a)); } catch (e) {} }
  return { aus: aus, ausSetzen: ausSetzen, lesen: lesen, schreiben: schreiben, norm: norm, treffer: treffer, wo: wo, seite: seite, heute: heute, aktuell: aktuell, passt: passt };
})();
