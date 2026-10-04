(function () {
  var bar = document.getElementById('topbar');
  if (!bar) return;
  var file = location.pathname.split('/').pop() || 'index.html';
  var map = { 'sektoren.html': 'aktien.html', 'wcj-info.html': 'aktien.html', 'megas.html': 'aktien.html', 'cholesterin.html': 'ernaehrung.html', 'lebensmittel-basics.html': 'ernaehrung.html', 'podcast-richtig-essen.html': 'ernaehrung.html' };
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
    if (location.pathname.indexOf('/rezepte/') === -1 && f === 'rezepte.html') w = 'rezept';
    else if (f === 'reiseberater.html') w = 'berater';
    else if (f === 'reisen.html' || /-reise\.html$/.test(f)) w = 'reise';
    else if (/^(finanzplanung|zinseszins|immobiliensuche|gedaechtnistest)\.html$/.test(f)) w = 'geld';
    else if (f === 'muenchen-quiz.html') w = 'quiz';
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
