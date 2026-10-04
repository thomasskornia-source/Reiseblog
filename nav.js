(function () {
  var bar = document.getElementById('topbar');
  if (!bar) return;
  var file = location.pathname.split('/').pop() || 'index.html';
  var map = { 'cholesterin.html': 'ernaehrung.html', 'lebensmittel-basics.html': 'ernaehrung.html', 'podcast-richtig-essen.html': 'ernaehrung.html' };
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

// Start-Hinweis: grüner Leuchtreklame-Pfeil „Übersicht“ quer aufs Logo – einmal pro Sitzung
(function () {
  var brand = document.querySelector('#topbar .brand');
  if (!brand) return;
  try { if (sessionStorage.getItem('pfeil-gesehen')) return; sessionStorage.setItem('pfeil-gesehen', '1'); } catch (e) {}
  var r = brand.getBoundingClientRect();
  var pts = [[6, 70], [76, 6], [76, 44], [284, 44], [284, 96], [76, 96], [76, 134]];
  var NS = 'http://www.w3.org/2000/svg';
  var svg = '<svg viewBox="0 0 290 140" width="290" height="140" aria-hidden="true">' +
    '<polygon points="' + pts.map(function (q) { return q.join(','); }).join(' ') + '" fill="#1F9D4D" stroke="#0E5E2B" stroke-width="6" stroke-linejoin="round"/>' +
    '<polygon points="' + pts.map(function (q) { return q.join(','); }).join(' ') + '" fill="none" stroke="#7CFFA6" stroke-width="2" stroke-linejoin="round" opacity=".55" transform="translate(0 0)"/>';
  var n = 0;
  for (var i = 0; i < pts.length; i++) {
    var a = pts[i], b = pts[(i + 1) % pts.length];
    var len = Math.hypot(b[0] - a[0], b[1] - a[1]);
    var k = Math.max(1, Math.round(len / 17));
    for (var j = 0; j < k; j++) {
      var x = a[0] + (b[0] - a[0]) * j / k, y = a[1] + (b[1] - a[1]) * j / k;
      svg += '<circle class="lb' + (n % 2) + '" cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="4.6"/>';
      n++;
    }
  }
  svg += '<text x="180" y="79" text-anchor="middle" font-family="Fraunces, serif" font-weight="600" font-size="32" fill="#fff" stroke="#0E5E2B" stroke-width="1" paint-order="stroke">Übersicht</text></svg>';
  var box = document.createElement('div');
  box.className = 'logo-pfeil';
  box.setAttribute('role', 'note');
  box.setAttribute('aria-label', 'Übersicht – hier geht’s immer zurück');
  box.style.left = (r.left + r.width * 0.6 - 6) + 'px';
  box.style.top = (r.bottom + 2 - 70) + 'px';
  box.innerHTML = svg;
  document.body.appendChild(box);
  function weg() { if (box.parentNode) box.parentNode.removeChild(box); }
  box.addEventListener('click', weg);
  document.addEventListener('click', weg, { once: true });
  window.addEventListener('scroll', weg, { once: true, passive: true });
  setTimeout(weg, 6000);
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
