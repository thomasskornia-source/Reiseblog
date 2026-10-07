/* WCJ-Rundgang: dunkelt die Seite ab und zeigt Schritt für Schritt ein Element (aktien.html?tour=<kapitel>) */
(function () {
  var q = new URLSearchParams(location.search).get('tour');
  if (!q) return;
  var T = null, S = [], i = 0, root, card, ring, blk = [], raf = 0, warte = null;
  function $(s) { return document.querySelector(s); }
  function el(t, c, x) { var e = document.createElement(t); if (c) e.className = c; if (x) e.textContent = x; return e; }
  var css = el('style'); css.textContent =
    '#tour{position:fixed;inset:0;z-index:9000;pointer-events:none}' +
    '#tour .tb{position:fixed;background:rgba(20,26,22,.72);backdrop-filter:blur(2px);-webkit-backdrop-filter:blur(2px);pointer-events:auto}' +
    '#tour .tr{position:fixed;box-sizing:border-box;border:3px solid #F6C253;border-radius:12px;box-shadow:0 0 0 4px rgba(246,194,83,.35);pointer-events:none;animation:tpuls 1.6s ease-in-out infinite}' +
    '@keyframes tpuls{50%{box-shadow:0 0 0 9px rgba(246,194,83,.15)}}' +
    '#tour .tc{position:fixed;left:50%;transform:translateX(-50%);width:min(520px,calc(100vw - 24px));box-sizing:border-box;background:#FAF3E8;color:#2E3A32;border-radius:16px;padding:14px 16px;box-shadow:0 8px 30px rgba(0,0,0,.35);pointer-events:auto;font-family:inherit}' +
    '#tour .tc small{display:block;font-size:12px;color:#6b756e;margin-bottom:2px}' +
    '#tour .tc b{display:block;font-size:17px;margin-bottom:4px}' +
    '#tour .tc p{margin:0 0 12px;font-size:15px;line-height:1.5}' +
    '#tour .tn{display:flex;gap:8px;align-items:center}' +
    '#tour .tn button{all:unset;cursor:pointer;padding:9px 14px;border-radius:999px;font-size:14.5px;font-weight:600}' +
    '#tour .tn .w{background:#F6C253;color:#262F63}#tour .tn .z{background:rgba(46,58,50,.1)}#tour .tn .e{margin-left:auto;color:#6b756e;font-weight:500}' +
    '#tour .tn button:focus-visible{outline:3px solid #262F63;outline-offset:2px}' +
    '#tour .hint{font-size:13.5px;color:#8a5a00;font-weight:600;margin:-4px 0 10px}#tour .hint:empty{display:none}';
  document.head.appendChild(css);

  function ende() {
    cancelAnimationFrame(raf); clearInterval(warte); document.removeEventListener('click', klick, true); document.removeEventListener('keydown', taste);
    if (root) root.remove();
    var u = new URL(location.href); u.searchParams.delete('tour'); history.replaceState(null, '', u.pathname + u.search + u.hash);
  }
  function taste(e) { if (e.key === 'Escape') ende(); }
  function ziel() { var st = S[i]; return st ? $(st.sel) : null; }
  function zeige() {
    var st = S[i];
    if (T.tab) { var tb = $('#wtabs button[data-tab="' + T.tab + '"]'); if (tb && tb.getAttribute('aria-selected') !== 'true') tb.click(); }
    var m = $('#markt'); if (m && i > 1 && !m.open) m.open = true;
    card.querySelector('small').textContent = 'Schritt ' + (i + 1) + ' von ' + S.length + ' · ' + T.titel;
    card.querySelector('b').textContent = st.titel; card.querySelector('p').textContent = st.text;
    var w = card.querySelector('.w'), h = card.querySelector('.hint');
    var last = i === S.length - 1;
    w.textContent = last ? 'Fertig' : (st.aktion ? 'Überspringen' : 'Weiter');
    h.textContent = st.aktion ? '👆 Tippe auf das gelb markierte Feld' : '';
    card.querySelector('.z').hidden = i === 0;
    var t = ziel(); if (t) { var r = t.getBoundingClientRect(), vh = innerHeight; if (r.top < 70 || r.bottom > vh - 200) scrollTo({ top: scrollY + r.top - Math.max(90, (vh - 260 - Math.min(r.height, vh - 330)) / 2), behavior: 'smooth' }); }
  }
  function weiter() { if (i >= S.length - 1) { ende(); return; } i++; zeige(); }
  function zurueck() { if (i > 0) { i--; zeige(); } }
  function klick(ev) {
    var st = S[i], t = ziel();
    if (st && st.aktion === 'klick' && t && t.contains(ev.target)) setTimeout(weiter, 400);
  }
  function lage() {
    var t = ziel(), vw = innerWidth, vh = innerHeight;
    if (t) {
      var r = t.getBoundingClientRect(), p = 6, x = Math.max(0, r.left - p), y = Math.max(0, r.top - p), x2 = Math.min(vw, r.right + p), y2 = Math.min(vh, r.bottom + p);
      if (y2 < 0 || y > vh) { x = y = x2 = y2 = 0; }
      var set = function (b, l, tp, w, h) { b.style.left = l + 'px'; b.style.top = tp + 'px'; b.style.width = Math.max(0, w) + 'px'; b.style.height = Math.max(0, h) + 'px'; };
      set(blk[0], 0, 0, vw, y); set(blk[1], 0, y2, vw, vh - y2); set(blk[2], 0, y, x, y2 - y); set(blk[3], x2, y, vw - x2, y2 - y);
      set(ring, x, y, x2 - x, y2 - y);
      var cardH = card.offsetHeight, unten = (y + y2) / 2 < vh / 2;
      card.style.top = unten ? 'auto' : '12px'; card.style.bottom = unten ? '12px' : 'auto';
      ring.hidden = false;
    } else {
      blk[0].style.cssText = 'left:0;top:0;width:' + vw + 'px;height:' + vh + 'px'; for (var k = 1; k < 4; k++) blk[k].style.cssText = 'width:0;height:0';
      ring.hidden = true; card.style.top = 'auto'; card.style.bottom = '12px';
    }
    raf = requestAnimationFrame(lage);
  }
  function start() {
    root = el('div'); root.id = 'tour'; root.setAttribute('role', 'dialog'); root.setAttribute('aria-label', 'Rundgang: ' + T.titel);
    for (var k = 0; k < 4; k++) { var b = el('div', 'tb'); blk.push(b); root.appendChild(b); }
    ring = el('div', 'tr'); root.appendChild(ring);
    card = el('div', 'tc'); card.setAttribute('aria-live', 'polite');
    card.appendChild(el('small')); card.appendChild(el('b')); card.appendChild(el('p'));
    var n = el('div', 'tn'), z = el('button', 'z', 'Zurück'), w = el('button', 'w', 'Weiter'), h = el('p', 'hint'), e = el('button', 'e', 'Beenden');
    z.type = w.type = e.type = 'button'; z.onclick = zurueck; w.onclick = weiter; e.onclick = ende;
    n.appendChild(z); n.appendChild(w); n.appendChild(e); card.appendChild(h); card.appendChild(n); root.appendChild(card);
    document.body.appendChild(root);
    document.addEventListener('click', klick, true); document.addEventListener('keydown', taste);
    zeige(); lage();
  }
  fetch('data/wcj-tour.json').then(function (r) { return r.json(); }).then(function (d) {
    T = d[q]; if (!T) return; S = T.schritte;
    var n = 0; warte = setInterval(function () { n++; if (ziel() || n > 60) { clearInterval(warte); start(); } }, 150);
  }).catch(function () {});
})();
