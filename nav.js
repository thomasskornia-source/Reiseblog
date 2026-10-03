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

// Start-Hinweis: dicker, pulsierender Pfeil aufs Logo – einmal pro Sitzung
(function () {
  var brand = document.querySelector('#topbar .brand');
  if (!brand) return;
  try { if (sessionStorage.getItem('pfeil-gesehen')) return; sessionStorage.setItem('pfeil-gesehen', '1'); } catch (e) {}
  var r = brand.getBoundingClientRect();
  var box = document.createElement('div');
  box.className = 'logo-pfeil';
  box.setAttribute('role', 'note');
  box.style.left = Math.max(6, r.left + r.width / 2 - 28) + 'px';
  box.style.top = (r.bottom + 6) + 'px';
  box.innerHTML = '<svg viewBox="0 0 56 64" width="56" height="64" aria-hidden="true"><path d="M28 3 L52 30 H36 V61 H20 V30 H4 Z" fill="#B5502E" stroke="#fff" stroke-width="3" stroke-linejoin="round"/></svg><span>Übersicht – hier geht’s immer zurück</span>';
  document.body.appendChild(box);
  function weg() { if (box.parentNode) box.parentNode.removeChild(box); }
  box.addEventListener('click', weg);
  document.addEventListener('click', weg, { once: true });
  window.addEventListener('scroll', weg, { once: true, passive: true });
  setTimeout(weg, 9000);
})();
