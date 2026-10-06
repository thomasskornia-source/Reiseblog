(function () {
  var bar = document.getElementById('topbar');
  if (!bar) return;
  var file = location.pathname.split('/').pop() || 'index.html';
  var map = { 'reiseberater.html': 'reisen.html', 'reiseideen.html': 'reisen.html', 'muenchen-quiz.html': 'quiz.html', 'raetsel.html': 'quiz.html', 'vergnuegen.html': 'quiz.html', 'wochenplaner.html': 'rezepte.html', 'sektoren.html': 'aktien.html', 'wcj-info.html': 'aktien.html', 'megas.html': 'aktien.html', 'cholesterin.html': 'ernaehrung.html', 'lebensmittel-basics.html': 'ernaehrung.html', 'podcast-richtig-essen.html': 'ernaehrung.html' };
  if (/-reise\.html$/.test(file)) file = 'reisen.html';
  if (location.pathname.indexOf('/rezepte/') !== -1) file = 'rezepte.html';
  file = map[file] || file;
  var links = bar.querySelectorAll('.topnav a');
  for (var i = 0; i < links.length; i++) {
    if (links[i].getAttribute('href').split('/').pop() === file) {
      links[i].setAttribute('aria-current', 'page');
      var nav = bar.querySelector('.topnav');
      if (nav && nav.scrollWidth > nav.clientWidth) nav.scrollLeft = Math.max(0, links[i].offsetLeft - 60);
    }
  }
  // Farbwelt der Seite (Kopfbereich)
  (function () {
    var f = location.pathname.split('/').pop() || 'index.html', w = '';
    if (location.pathname.indexOf('/rezepte/') === -1 && (f === 'rezepte.html' || f === 'wochenplaner.html')) w = 'rezept';
    else if (f === 'reisen.html' || f === 'reiseberater.html' || f === 'reiseideen.html' || /-reise\.html$/.test(f)) w = 'reise';
    else if (/^(finanzplanung|zinseszins|immobiliensuche|gedaechtnistest)\.html$/.test(f)) w = 'geld';
    else if (f === 'muenchen-quiz.html' || f === 'vergnuegen.html' || f === 'quiz.html') w = 'quiz';
    else if (/^(ernaehrung|cholesterin|lebensmittel-basics|podcast-richtig-essen)\.html$/.test(f)) w = 'essen';
    else if (f === 'notfallvorrat.html') w = 'nacht';
    if (w && document.querySelector('.entry-header')) document.body.setAttribute('data-welt', w);
  })();
  function onScroll() { bar.classList.toggle('stuck', window.scrollY > 6); }
  window.addEventListener('scroll', onScroll, { passive: true }); onScroll();

  // Übersichtskarten: führendes Emoji als großes Symbol
  var re = /^\s*((?:\p{Extended_Pictographic}️?‍?)+)\s*/u;
  var hs = document.querySelectorAll('.page-list .entry-preview h2');
  for (var j = 0; j < hs.length; j++) {
    var m = hs[j].firstChild && hs[j].firstChild.nodeType === 3 && re.exec(hs[j].firstChild.nodeValue);
    if (!m) continue;
    hs[j].firstChild.nodeValue = hs[j].firstChild.nodeValue.slice(m[0].length);
    var s = document.createElement('span'); s.className = 'em'; s.textContent = m[1];
    var card = hs[j].parentNode; card.insertBefore(s, card.firstChild); card.classList.add('has-em');
  }
})();

// Zurück-Pfeil: der Text-Link „← …“ wird zu einem runden Pfeil auf der Höhe der Überschrift
(function () {
  var h1 = document.querySelector('h1'); if (!h1) return;
  var a = [].filter.call(document.querySelectorAll('a.back-link, a.zurueck'), function (x) { return /^\s*←/.test(x.textContent); })[0];
  if (!a) return;
  var ico = document.createElement('a');
  ico.className = 'back-ico'; ico.href = a.getAttribute('href'); ico.setAttribute('aria-label', a.textContent.replace(/^\s*←\s*/, '').trim() || 'Zurück'); ico.title = ico.getAttribute('aria-label');
  ico.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  h1.classList.add('mit-zurueck'); h1.insertBefore(ico, h1.firstChild);
  a.classList.add('back-ersetzt');
  function pos() { var cs = getComputedStyle(h1), lh = parseFloat(cs.lineHeight); if (isNaN(lh)) lh = parseFloat(cs.fontSize) * 1.2; ico.style.top = Math.round(lh / 2 - 19) + 'px'; }
  pos(); window.addEventListener('resize', pos);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(pos);
})();

// Logo blinkt zu Beginn sechsmal unregelmäßig und dezent auf (einmal pro Sitzung): so findet man den Weg zur Übersicht
(function () {
  var img = document.querySelector('#topbar .brand img');
  if (!img || !img.animate) return;
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  try { if (sessionStorage.getItem('logo-blink')) return; sessionStorage.setItem('logo-blink', '1'); } catch (e) {}
  var n = 0;
  function blink() {
    img.animate([
      { transform: 'scale(1)', boxShadow: '0 2px 8px rgba(181,80,46,.35)' },
      { transform: 'scale(1.1)', boxShadow: '0 0 0 5px rgba(181,80,46,.22), 0 0 14px rgba(181,80,46,.5)', offset: 0.4 },
      { transform: 'scale(1)', boxShadow: '0 2px 8px rgba(181,80,46,.35)' }
    ], { duration: 850, easing: 'ease-in-out' });
    if (++n < 6) setTimeout(blink, 1300 + Math.random() * 2700);
  }
  setTimeout(blink, 1200 + Math.random() * 800);
})();

/* PC-Ansicht Reise-Detailseiten: Abschnitte (Überschrift + Inhalt) zusammenhalten, damit sie nicht zwischen Spalten umbrechen */
(function () {
  var b = document.body;
  if (!b || !b.classList.contains('pc') || !(b.classList.contains('page-info') || b.classList.contains('page-read'))) return;
  var art = document.querySelector('article');
  if (!art || art.querySelector(':scope > section.sec')) return;
  var kids = [].slice.call(art.children), sec = null;
  kids.forEach(function (el) {
    if (el.matches && el.matches('h2.subhead')) { sec = document.createElement('section'); sec.className = 'sec'; art.insertBefore(sec, el); }
    if (sec && !el.matches('script,style')) sec.appendChild(el);
  });
})();

/* Trendbruch-Warnung (Thomas, 05.10.2026): schmaler Hinweis unter der Kopfleiste, wenn der S&P 500 unter die 21-Tage-Linie fällt.
   Stufe 1 gelb: nur die 21er; Stufe 2 orange: ein weiteres Zeichen; Stufe 3 rot: zwei oder mehr. Weitere Zeichen: 8er unter 21er,
   Wochen-MACD unter der Signallinie, Kurs unter dem 8-Wochen-EMA, Kurs unter der 50er. Nur auf Startseite und WCJ. Keine Anlageberatung. */
(function () {
  var p = location.pathname.split('/').pop() || 'index.html';
  if (p !== 'index.html' && p !== 'aktien.html' && p !== '') return;
  var test = (location.search.match(/warntest=([123])/) || [])[1];
  function zeigen(stufe, zeichen, stand) {
    var bar = document.getElementById('topbar'); if (!bar || document.getElementById('trendwarnung')) return;
    var d = document.createElement('a'); d.id = 'trendwarnung'; d.href = 'aktien.html'; d.className = 'tw tw' + stufe;
    var kopf = ['Hinweis', 'Warnung', 'Alarm'][stufe - 1];
    d.innerHTML = '<b>' + kopf + ' Markt:</b> S&amp;P 500 unter der 21-Tage-Linie' + (zeichen.length ? ' · ' + zeichen.join(' · ') : '') +
      ' <span class="tw-s">Stand ' + stand + '. Jede größere Korrektur begann mit so einem Bruch; kann auch ein falscher Bruch sein. Keine Anlageberatung.</span>';
    bar.parentNode.insertBefore(d, bar.nextSibling);
  }
  fetch('data/markt.json?v=' + Date.now()).then(function (r) { return r.json(); }).then(function (m) {
    var z = [];
    if (m.ma8 < m.ma21) z.push('8er unter 21er');
    if (m.woche && m.woche.macd_ueber_signal === false) z.push('Wochen-MACD unter Signallinie');
    if (m.woche && m.woche.ueber_ema8 === false) z.push('unter dem 8-Wochen-EMA');
    if (m.kurs < m.ma50) z.push('unter der 50er');
    var unter = m.kurs < m.ma21;
    if (test) { zeigen(+test, z.slice(0, +test - 1), m.stand); return; }
    if (!unter) return;
    zeigen(z.length >= 2 ? 3 : z.length === 1 ? 2 : 1, z, m.stand);
  }).catch(function () {});
})();
