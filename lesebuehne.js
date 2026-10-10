/* Lesebühne: zeigt den vorgelesenen Text groß und lässt ihn passend zur Stimme von unten nach oben laufen */
(function () {
  var root = null, box = null, raf = 0, mode = '', audio = null, cb = null, startY = 0, endY = 0, curY = 0;
  var out = { t0: 0, dur: 1, y0: 0, y1: 0 };
  var sp = { cum: [0], total: 1, i: 0, t0: 0, dur: 1 };
  var tl = { cum: [0], marks: [] };

  function el(tag, cls, txt) { var e = document.createElement(tag); e.className = cls; if (txt) e.textContent = txt; return e; }
  function setY(y) { curY = y; box.style.transform = 'translate3d(0,' + y.toFixed(1) + 'px,0)'; }
  function place(p) {
    p = Math.max(0, Math.min(1, p || 0));
    setY(startY + (endY - startY) * p);
  }
  function layout() {
    if (!box) return;
    var vh = window.innerHeight;
    startY = vh * 0.80; endY = vh * 0.34 - box.offsetHeight;
  }
  function progress() {
    if (mode === 'audio' && audio && audio.duration > 0) return audio.currentTime / audio.duration;
    if (mode === 'timeline' && audio) {   // Zeitmarken je Abschnitt: Text läuft nur, während gesprochen wird, in Denkpausen steht er still
      var t = audio.currentTime, n = tl.marks.length, tot = tl.cum[n] || 1;
      for (var k = 0; k < n; k++) {
        var m = tl.marks[k];
        if (t < m[0]) return tl.cum[k] / tot;
        if (t <= m[1]) return (tl.cum[k] + (tl.cum[k + 1] - tl.cum[k]) * ((t - m[0]) / Math.max(0.1, m[1] - m[0]))) / tot;
      }
      return 1;
    }
    if (mode === 'speech') {
      var f = Math.min(1, (performance.now() - sp.t0) / 1000 / sp.dur), a = sp.cum[sp.i] || 0, b = sp.cum[sp.i + 1] || a;
      return (a + (b - a) * f) / sp.total;
    }
    return 0;
  }
  var last = 0;
  function tick() {
    if (!root) return;
    if (mode === 'outro') {   // Musik läuft: Text wandert gleichmäßig weiter nach oben und verlässt am Ende des Ausschnitts das Bild
      var f = Math.min(1, (performance.now() - out.t0) / out.dur);
      setY(out.y0 + (out.y1 - out.y0) * f); raf = requestAnimationFrame(tick); return;
    }
    var p = progress(); if (p < last && mode === 'speech') p = last; last = p;   // nie rückwärts laufen
    place(p); raf = requestAnimationFrame(tick);
  }
  function onKey(e) { if (e.key === 'Escape') x(); }
  function onResize() { layout(); }
  function x() { var f = cb; close(); if (f) f(); }
  function close() {
    cancelAnimationFrame(raf); mode = ''; audio = null; cb = null;
    window.removeEventListener('resize', onResize); document.removeEventListener('keydown', onKey);
    if (root) { var r = root; root = null; box = null; r.classList.remove('on'); setTimeout(function () { if (r.parentNode) r.parentNode.removeChild(r); }, 380); }
  }

  window.Lesebuehne = {
    /* parts: [{k: 't'|'by'|'h'|'p', t: Text}], onClose: wird aufgerufen, wenn der Nutzer schließt */
    open: function (parts, onClose) {
      close(); cb = onClose || null; last = 0;
      root = el('div', 'lb'); root.setAttribute('role', 'dialog'); root.setAttribute('aria-label', 'Vorgelesener Text');
      var fade = el('div', 'lb-fade'); box = el('div', 'lb-box');
      parts.forEach(function (p) { box.appendChild(el(p.k === 'h' ? 'h2' : 'p', 'lb-' + p.k, p.t)); });
      fade.appendChild(box); root.appendChild(fade);
      var b = el('button', 'lb-x'); b.type = 'button'; b.setAttribute('aria-label', 'Vorlesen beenden');
      b.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';
      b.onclick = x; root.appendChild(b);
      root.onclick = x;   // ein Tipp irgendwo auf den Schirm beendet das Vorlesen
      document.body.appendChild(root);
      layout(); place(0);
      window.addEventListener('resize', onResize); document.addEventListener('keydown', onKey);
      requestAnimationFrame(function () { if (root) root.classList.add('on'); });
      raf = requestAnimationFrame(tick);
    },
    followAudio: function (a) { audio = a; mode = 'audio'; },
    /* Stimme ist zu Ende, die Musik beginnt: Text läuft in sec Sekunden weiter aus dem Bild, das Albumcover (Adresse oder leer) wird eingeblendet */
    outro: function (cover, sec) {
      if (!root || !box || mode === 'outro') return;
      out.t0 = performance.now(); out.dur = Math.max(4, sec || 30) * 1000; out.y0 = curY; out.y1 = -box.offsetHeight - 24; mode = 'outro'; audio = null;
      if (cover && !root.querySelector('.lb-cover')) {
        var im = new Image(), r = root; im.className = 'lb-cover'; im.alt = ''; im.decoding = 'async';
        im.onload = function () { if (r.parentNode) requestAnimationFrame(function () { im.classList.add('on'); }); };
        im.onerror = function () { if (im.parentNode) im.parentNode.removeChild(im); };
        im.src = cover; root.appendChild(im);
      }
    },
    /* parts: wie bei open(), marks: [[Start, Ende] in Sekunden je Teil] */
    followTimeline: function (a, parts, marks) {
      var c = 0; tl.cum = [0]; parts.forEach(function (p) { c += p.t.length; tl.cum.push(c); });
      tl.marks = marks; audio = a; mode = 'timeline';
    },
    /* Sätze, die nacheinander gesprochen werden; sentence(i) meldet den Beginn von Satz i */
    followSpeech: function (sentences) {
      var c = 0; sp.cum = [0]; sentences.forEach(function (s) { c += s.length; sp.cum.push(c); });
      sp.total = c || 1; sp.i = 0; sp.t0 = performance.now(); sp.dur = 1; mode = 'speech';
    },
    sentence: function (i) {
      sp.i = i; sp.t0 = performance.now();
      sp.dur = Math.max(1.2, ((sp.cum[i + 1] || 0) - (sp.cum[i] || 0)) / 13);   // etwa 13 Zeichen pro Sekunde
    },
    close: close,
    /* Rätsel: Überschrift, Geschichte (p), Fragen (h) und Antworten (p) in der Reihenfolge der Segmente */
    quizParts: function (q) {
      return q.segmente.map(function (g, i) { return { k: i === 0 ? 't' : g.k === 'f' ? 'f' : 'p', t: g.t }; });
    },
    songParts: function (s) {
      var p = [{ k: 't', t: s.title }, { k: 'by', t: s.artist + ' · ' + s.year },
        { k: 'h', t: 'Woher kommt der Song?' }, { k: 'p', t: s.herkunft },
        { k: 'h', t: 'Was bedeutet er?' }, { k: 'p', t: s.bedeutung }];
      if (s.fun) { p.push({ k: 'h', t: 'Noch ein Detail' }); p.push({ k: 'p', t: s.fun }); }
      return p;
    }
  };
})();
