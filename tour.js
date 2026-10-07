/* WCJ-Rundgang: dunkelt die Seite ab, zeigt Schritt für Schritt ein Element und liest den Text vor (aktien.html?tour=<kapitel>) */
(function () {
  var q = new URLSearchParams(location.search).get('tour');
  if (!q) return;
  var T = null, S = [], i = 0, root, card, ring, finger, blk = [], raf = 0, warte = null, gescrollt = false, sperre = false, stimme = true, sprecher;
  try { stimme = localStorage.getItem('tour-stimme') !== 'aus'; } catch (e) {}
  function $(s) { return document.querySelector(s); }
  function el(t, c, x) { var e = document.createElement(t); if (c) e.className = c; if (x) e.textContent = x; return e; }
  var css = el('style'); css.textContent =
    '#tour{position:fixed;inset:0;z-index:9000;pointer-events:none}' +
    '#tour .tb{position:fixed;backdrop-filter:blur(3px);-webkit-backdrop-filter:blur(3px);pointer-events:auto}' +
    '#tour .tr{position:fixed;box-sizing:border-box;border:3px solid #F6C253;border-radius:14px;box-shadow:0 0 0 5px rgba(246,194,83,.32),0 0 0 100vmax rgba(24,30,26,.66);pointer-events:none;animation:tpuls 1.7s ease-in-out infinite}' +
    '@keyframes tpuls{50%{box-shadow:0 0 0 11px rgba(246,194,83,.12),0 0 0 100vmax rgba(24,30,26,.66)}}' +
    '#tour .tf{position:fixed;font-size:30px;line-height:1;pointer-events:none;animation:thop 1s ease-in-out infinite;filter:drop-shadow(0 2px 3px rgba(0,0,0,.4))}' +
    '@keyframes thop{50%{transform:translateY(-7px)}}' +
    '#tour .tc{position:fixed;left:50%;transform:translateX(-50%);width:min(540px,calc(100vw - 24px));box-sizing:border-box;background:#FAF3E8;color:#2E3A32;border-radius:22px;padding:0 18px 16px;box-shadow:0 14px 40px rgba(0,0,0,.4);pointer-events:auto;overflow:hidden}' +
    '#tour .tp{height:5px;margin:0 -18px 14px;background:rgba(46,58,50,.12)}#tour .tp i{display:block;height:100%;width:0;background:linear-gradient(90deg,#B5502E,#F6C253);border-radius:0 4px 4px 0;transition:width .35s ease}' +
    '#tour .th{display:flex;align-items:center;gap:10px;margin-bottom:4px}' +
    '#tour .tk{flex:1;font-size:11.5px;letter-spacing:.07em;text-transform:uppercase;color:#8a6a3a;font-weight:700}' +
    '#tour .ts{all:unset;cursor:pointer;width:38px;height:38px;border-radius:50%;background:rgba(246,194,83,.4);display:flex;align-items:center;justify-content:center;font-size:19px}' +
    '#tour .ts.an{background:#F6C253}#tour .ts.red{animation:tpuls2 1s ease-in-out infinite}@keyframes tpuls2{50%{transform:scale(1.12)}}' +
    '#tour .tt{font-family:Fraunces,Georgia,serif;font-weight:500;font-size:21px;line-height:1.2;margin:2px 0 6px}' +
    '#tour .tx{margin:0 0 12px;font-size:15.5px;line-height:1.5}' +
    '#tour .hint{margin:0 0 12px;padding:8px 12px;border-radius:12px;background:#fff1d6;border:1px solid #F6C253;font-size:14px;font-weight:600;color:#6d4a00}#tour .hint:empty{display:none}' +
    '#tour .tn{display:flex;gap:8px;align-items:center}' +
    '#tour .tn button{all:unset;cursor:pointer;padding:11px 16px;border-radius:999px;font-size:15px;font-weight:700;line-height:1;white-space:nowrap}' +
    '#tour .tn .w{background:#F6C253;color:#262F63;box-shadow:0 3px 10px rgba(246,194,83,.55)}#tour .tn .z{background:rgba(46,58,50,.09)}#tour .tn .e{margin-left:auto;padding-right:4px;color:#6b756e;font-weight:500;font-size:14px}' +
    '#tour .tn button:focus-visible,#tour .ts:focus-visible{outline:3px solid #262F63;outline-offset:2px}' +
    '@media (prefers-reduced-motion:reduce){#tour .tr,#tour .tf,#tour .ts.red{animation:none}}';
  document.head.appendChild(css);

  function sprecheStopp() { if ('speechSynthesis' in window) speechSynthesis.cancel(); setLaut(false); }
  function setLaut(spricht) { if (!sprecher) return; sprecher.textContent = stimme ? '🔊' : '🔇'; sprecher.classList.toggle('an', stimme); sprecher.classList.toggle('red', !!spricht); sprecher.setAttribute('aria-label', stimme ? 'Vorlesen ausschalten' : 'Vorlesen einschalten'); }
  function sprich(st) {
    if (!stimme || !st || !('speechSynthesis' in window) || typeof SpeechSynthesisUtterance === 'undefined') return;
    speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance(st.sprech || st.text); u.lang = 'de-DE'; u.rate = .95;
    u.onstart = function () { setLaut(true); }; u.onend = u.onerror = function () { setLaut(false); };
    speechSynthesis.speak(u);
  }
  function ende() {
    cancelAnimationFrame(raf); clearInterval(warte); sprecheStopp();
    document.removeEventListener('click', klick, true); document.removeEventListener('change', aender, true); document.removeEventListener('keydown', taste);
    if (root) root.remove();
    var u = new URL(location.href); u.searchParams.delete('tour'); history.replaceState(null, '', u.pathname + u.search + u.hash);
  }
  function taste(e) { if (e.key === 'Escape') ende(); }
  function ziel() { var st = S[i]; if (!st) return null; try { return $(st.sel); } catch (e) { return null; } }
  function zeige(vorlesen) {
    var st = S[i]; sperre = false; gescrollt = false;
    var tab = st.tab || (i === 0 ? T.tab : null);
    if (tab) { var tb = $('#wtabs button[data-tab="' + tab + '"]'); if (tb && tb.getAttribute('aria-selected') !== 'true') tb.click(); }
    var m = $('#markt'); if (m && T.tab === 'sp' && i > 1 && !m.open) m.open = true;
    card.querySelector('.tk').textContent = 'Schritt ' + (i + 1) + ' von ' + S.length + ' · ' + T.titel;
    card.querySelector('.tp i').style.width = Math.round((i + 1) / S.length * 100) + '%';
    card.querySelector('.tt').textContent = st.titel; card.querySelector('.tx').textContent = st.text;
    var w = card.querySelector('.w'), h = card.querySelector('.hint'), last = i === S.length - 1;
    w.textContent = last ? 'Fertig ✓' : (st.aktion ? 'Überspringen →' : 'Weiter →');
    h.textContent = st.aktion === 'aendern' ? '👆 Wähle im markierten Feld etwas aus' : (st.aktion ? '👆 Tippe auf das gelb markierte Feld' : '');
    card.querySelector('.z').hidden = i === 0;
    if (vorlesen !== false) sprich(st);
  }
  function weiter(gesprochen) { if (i >= S.length - 1) { ende(); return; } i++; zeige(!gesprochen); }
  function zurueck() { if (i > 0) { i--; zeige(true); } }
  function auto() {   // nach dem Tipp auf das markierte Feld: Vorlesen sofort (iPhone), Wechsel kurz danach
    if (sperre) return; sperre = true;
    var n = i + 1; if (n < S.length) sprich(S[n]);
    setTimeout(function () { weiter(true); }, 450);
  }
  function klick(ev) { var st = S[i], t = ziel(); if (st && st.aktion === 'klick' && t && t.contains(ev.target)) auto(); }
  function aender(ev) { var st = S[i], t = ziel(); if (st && st.aktion === 'aendern' && t && (t === ev.target || t.contains(ev.target))) auto(); }
  function lage() {
    var t = ziel(), vw = innerWidth, vh = innerHeight, set = function (b, l, tp, w, h) { b.style.left = l + 'px'; b.style.top = tp + 'px'; b.style.width = Math.max(0, w) + 'px'; b.style.height = Math.max(0, h) + 'px'; };
    var r = t ? t.getBoundingClientRect() : null;
    if (t && r.width > 0 && r.height > 0) {
      if (!gescrollt) { gescrollt = true; if (r.top < 80 || r.bottom > vh - 240) scrollTo({ top: scrollY + r.top - Math.max(90, (vh - 280 - Math.min(r.height, vh - 360)) / 2), behavior: 'smooth' }); }
      var p = 6, x = Math.max(0, r.left - p), y = Math.max(0, r.top - p), x2 = Math.min(vw, r.right + p), y2 = Math.min(vh, r.bottom + p);
      if (y2 <= y || x2 <= x) { x = y = x2 = y2 = 0; }
      blk[0].style.background = ''; set(blk[0], 0, 0, vw, y); set(blk[1], 0, y2, vw, vh - y2); set(blk[2], 0, y, x, y2 - y); set(blk[3], x2, y, vw - x2, y2 - y);
      set(ring, x, y, x2 - x, y2 - y); ring.hidden = false;
      var a = S[i].aktion; finger.hidden = !a; finger.style.left = Math.min(vw - 36, Math.max(4, x2 - 30)) + 'px'; finger.style.top = Math.min(vh - 40, y2 - 8) + 'px';
      var oben = y > (vh - y2);
      card.style.top = oben ? '12px' : 'auto'; card.style.bottom = oben ? 'auto' : 'calc(12px + env(safe-area-inset-bottom,0px))';
    } else {
      blk[0].style.background = 'rgba(24,30,26,.66)'; set(blk[0], 0, 0, vw, vh); for (var k = 1; k < 4; k++) set(blk[k], 0, 0, 0, 0);
      ring.hidden = true; finger.hidden = true; card.style.top = 'auto'; card.style.bottom = 'calc(12px + env(safe-area-inset-bottom,0px))';
    }
    raf = requestAnimationFrame(lage);
  }
  function start() {
    root = el('div'); root.id = 'tour'; root.setAttribute('role', 'dialog'); root.setAttribute('aria-label', 'Rundgang: ' + T.titel);
    for (var k = 0; k < 4; k++) { var b = el('div', 'tb'); blk.push(b); root.appendChild(b); }
    ring = el('div', 'tr'); root.appendChild(ring); finger = el('div', 'tf', '👆'); finger.hidden = true; root.appendChild(finger);
    card = el('div', 'tc'); card.setAttribute('aria-live', 'polite');
    var tp = el('div', 'tp'); tp.appendChild(el('i')); card.appendChild(tp);
    var th = el('div', 'th'); th.appendChild(el('span', 'tk')); sprecher = el('button', 'ts'); sprecher.type = 'button';
    sprecher.onclick = function () {
      if ('speechSynthesis' in window && speechSynthesis.speaking) { stimme = false; sprecheStopp(); }
      else { stimme = true; sprich(S[i]); }
      try { localStorage.setItem('tour-stimme', stimme ? 'an' : 'aus'); } catch (e) {} setLaut(false);
    };
    th.appendChild(sprecher); card.appendChild(th);
    card.appendChild(el('div', 'tt')); card.appendChild(el('p', 'tx')); card.appendChild(el('p', 'hint'));
    var n = el('div', 'tn'), z = el('button', 'z', '← Zurück'), w = el('button', 'w', 'Weiter →'), e = el('button', 'e', 'Beenden');
    z.type = w.type = e.type = 'button'; z.onclick = zurueck; w.onclick = function () { weiter(false); }; e.onclick = ende;
    n.appendChild(z); n.appendChild(w); n.appendChild(e); card.appendChild(n); root.appendChild(card);
    document.body.appendChild(root); setLaut(false);
    document.addEventListener('click', klick, true); document.addEventListener('change', aender, true); document.addEventListener('keydown', taste);
    zeige(true); lage();
    if ('speechSynthesis' in window && stimme) setTimeout(function () { var h = card.querySelector('.hint'); if (i === 0 && !speechSynthesis.speaking && !h.textContent) h.textContent = '🔊 Kein Ton? Tippe oben rechts auf den Lautsprecher.'; }, 1600);
  }
  fetch('data/wcj-tour.json').then(function (r) { return r.json(); }).then(function (d) {
    T = d[q]; if (!T) return; S = T.schritte;
    var n = 0; warte = setInterval(function () { n++; if (ziel() || n > 60) { clearInterval(warte); start(); } }, 150);
  }).catch(function () {});
})();
