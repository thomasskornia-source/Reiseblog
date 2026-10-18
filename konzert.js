/* Konzertmodus (Thomas, 18.10.2026): gemeinsame Hilfen für index.html, musik.html und konzert.html.
   Zustand nur lokal im Browser (localStorage "konzert" = {artist, city, since}). Daten je Band: data/konzerte/<slug>.json (von tools/konzert-bauen.py). */
(function () {
  var REPO = 'thomasskornia-source/Reiseblog';
  var K = window.Konzert = {};

  K.slug = function (s) {
    return String(s || '').toLowerCase().replace(/ß/g, 'ss').normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/&/g, ' and ').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60);
  };
  K.get = function () {
    try { var v = JSON.parse(localStorage.getItem('konzert') || 'null'); return v && v.artist ? v : null; } catch (e) { return null; }
  };
  K.set = function (artist, city) {
    try { localStorage.setItem('konzert', JSON.stringify({ artist: artist, city: city, since: new Date().toISOString().slice(0, 10) })); return true; } catch (e) { return false; }
  };
  K.clear = function () { try { localStorage.removeItem('konzert'); } catch (e) {} };
  K.issueUrl = function (artist, city) {
    return 'https://github.com/' + REPO + '/issues/new?title=' + encodeURIComponent('Konzert: ' + artist + ' (' + city + ')') +
      '&body=' + encodeURIComponent('Interpret: ' + artist + '\nStadt: ' + city + '\n\nBitte unverändert absenden. Daraus entstehen Special, Podcast und Lieder für den Konzertmodus.');
  };
  K.load = function (slug) {
    return fetch('data/konzerte/' + encodeURIComponent(slug) + '.json').then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
  };

  /* ---------- Farben ---------- */
  var HEX = /^#[0-9a-fA-F]{6}$/;
  function hsl(h, s, l) { return 'hsl(' + h + ',' + s + '%,' + l + '%)'; }
  function fallbackTheme(name) {
    var h = 0, i; for (i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) % 360;
    return { dark: true, paper: hsl(h, 28, 11), paperWarm: hsl(h, 26, 17), ink: hsl(h, 20, 93), inkSoft: hsl(h, 14, 72), accent: hsl((h + 20) % 360, 78, 58), gold: hsl((h + 45) % 360, 85, 62), from: hsl(h, 55, 28), to: hsl((h + 30) % 360, 60, 14), font: 'serif' };
  }
  K.theme = function (data, artist) {
    var t = data && data.theme, f = fallbackTheme(artist || '');
    if (t) {
      ['paper', 'paperWarm', 'ink', 'inkSoft', 'accent', 'gold', 'from', 'to'].forEach(function (k) { if (HEX.test(t[k] || '')) f[k] = t[k]; });
      if (['serif', 'sans', 'mono', 'schwer'].indexOf(t.font) !== -1) f.font = t.font;
    }
    return f;
  };
  K.apply = function (t) {
    var r = document.documentElement.style;
    r.setProperty('--paper', t.paper); r.setProperty('--paper-warm', t.paperWarm); r.setProperty('--ink', t.ink);
    r.setProperty('--ink-soft', t.inkSoft); r.setProperty('--rust', t.accent); r.setProperty('--gold', t.accent);
    r.setProperty('--kz-from', t.from); r.setProperty('--kz-to', t.to); r.setProperty('--kz-accent', t.accent); r.setProperty('--kz-gold', t.gold);
    var fam = { serif: "'Fraunces', serif", sans: "'Work Sans', sans-serif", mono: "ui-monospace, 'SF Mono', Menlo, monospace", schwer: "Impact, 'Arial Black', sans-serif" }[t.font] || "'Fraunces', serif";
    r.setProperty('--kz-font', fam);
    document.documentElement.classList.add('kz-an');
    var m = document.querySelector('meta[name=theme-color]'); if (m) m.setAttribute('content', t.paper);
  };
  K.unapply = function () {
    var r = document.documentElement.style;
    ['--paper', '--paper-warm', '--ink', '--ink-soft', '--rust', '--gold', '--kz-from', '--kz-to', '--kz-accent', '--kz-gold', '--kz-font'].forEach(function (p) { r.removeProperty(p); });
    document.documentElement.classList.remove('kz-an');
  };

  /* ---------- Vorlesen (Gerätestimme oder MP3) ---------- */
  var audio = null, spk = false, onStop = null;
  K.stop = function () {
    spk = false; if (audio) { try { audio.pause(); } catch (e) {} audio = null; }
    if ('speechSynthesis' in window) speechSynthesis.cancel();
    if (onStop) { var f = onStop; onStop = null; f(); }
  };
  K.sprich = function (text, mp3, stopCb) {
    K.stop(); onStop = stopCb || null;
    function stimme() {
      if (!('speechSynthesis' in window)) { K.stop(); return; }
      var p = String(text).replace(/\n+/g, ' ').match(/[^.!?:]+[.!?:]+|[^.!?:]+$/g) || [text]; spk = true;
      (function n() { if (!spk) return; if (!p.length) { K.stop(); return; }
        var u = new SpeechSynthesisUtterance(p.shift().trim()); u.lang = 'de-DE'; u.rate = .95; u.onend = n;
        u.onerror = function (er) { if (!er || (er.error !== 'canceled' && er.error !== 'interrupted')) K.stop(); };
        speechSynthesis.speak(u); })();
    }
    if (mp3) {
      var a = new Audio(mp3); audio = a; a.onended = K.stop;
      a.onerror = function () { if (audio === a) { audio = null; stimme(); } };
      var pr = a.play(); if (pr && pr.catch) pr.catch(function () { if (audio === a) { audio = null; stimme(); } });
    } else stimme();
  };
  K.spielt = function () { return !!audio || spk; };
  window.addEventListener('pagehide', function () { K.stop(); });

  /* ---------- Hilfen ---------- */
  K.el = function (tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
  K.tagesSong = function (d) {
    if (!d || !d.songs || !d.songs.length) return null;
    var tag = Math.floor((Date.now() - new Date().getTimezoneOffset() * 60000) / 86400000);
    return d.songs[tag % d.songs.length];
  };
  K.audioHead = function (url) { return fetch(url, { method: 'HEAD' }).then(function (r) { return r.ok; }).catch(function () { return false; }); };
  K.paras = function (box, text) { String(text || '').split(/\n\n+/).forEach(function (x) { if (x.trim()) box.appendChild(K.el('p', '', x.trim())); }); };

  /* ---------- Startseite im Konzertmodus ---------- */
  K.home = function () {
    var box = document.getElementById('konzert-home'); if (!box) return;
    var m = K.get(); if (!m) { K.unapply(); document.body.classList.remove('konzert'); box.hidden = true; return; }
    var slug = K.slug(m.artist);
    K.apply(K.theme(null, m.artist)); document.body.classList.add('konzert'); box.hidden = false; box.textContent = '';
    var hero = K.el('header', 'kz-hero');
    hero.appendChild(K.el('p', 'kz-kicker', 'Konzertmodus · ' + (m.city || '')));
    hero.appendChild(K.el('h1', 'kz-name', m.artist));
    var off = K.el('button', 'kz-off', 'Konzertmodus beenden'); off.type = 'button';
    off.addEventListener('click', function () { K.stop(); K.clear(); K.home(); });
    hero.appendChild(off); box.appendChild(hero);
    var body = K.el('div', 'kz-body'); box.appendChild(body);
    K.load(slug).then(function (d) {
      if (K.get() === null) return;
      if (!d) {
        var w = K.el('div', 'kz-card');
        w.appendChild(K.el('h2', '', 'Special in Arbeit'));
        w.appendChild(K.el('p', '', 'Für ' + m.artist + ' gibt es noch kein Special. Sende die Anfrage ab (GitHub öffnet sich mit fertigem Text, du musst nur „Submit new issue“ drücken). Nach ein paar Minuten erscheinen Lieder, Text, Bild, Podcast und die passenden Farben.'));
        var a = K.el('a', 'kz-btn', 'Special anfordern'); a.href = K.issueUrl(m.artist, m.city || ''); a.target = '_blank'; a.rel = 'noopener'; w.appendChild(a);
        body.appendChild(w); return;
      }
      K.apply(K.theme(d, m.artist));
      var s = K.tagesSong(d);
      if (s) {
        var c = K.el('section', 'kz-card');
        c.appendChild(K.el('p', 'kz-small', 'Lied des Tages'));
        c.appendChild(K.el('h2', '', s.title + (s.year ? ' (' + s.year + ')' : '')));
        c.appendChild(K.el('p', 'kz-by', d.artist));
        var p = K.el('button', 'kz-play', '▶ Geschichte anhören'); p.type = 'button';
        p.addEventListener('click', function () { if (K.spielt()) { K.stop(); return; } p.textContent = '■ Stopp'; K.sprich(s.herkunft + ' ' + s.bedeutung, null, function () { p.textContent = '▶ Geschichte anhören'; }); });
        c.appendChild(p);
        var t = K.el('div', 'kz-text'); t.appendChild(K.el('h3', '', 'Herkunft')); t.appendChild(K.el('p', '', s.herkunft)); t.appendChild(K.el('h3', '', 'Bedeutung')); t.appendChild(K.el('p', '', s.bedeutung));
        if (s.fun) t.appendChild(K.el('p', 'kz-fun', s.fun));
        c.appendChild(t); body.appendChild(c);
      }
      var sp = K.el('a', 'kz-card kz-special'); sp.href = 'konzert.html?k=' + encodeURIComponent(slug);
      if (d.bild && d.bild.datei) { var im = K.el('img', 'kz-bild'); im.alt = ''; im.loading = 'lazy'; im.src = 'https://commons.wikimedia.org/wiki/Special:FilePath/' + encodeURIComponent(d.bild.datei) + '?width=640'; sp.appendChild(im); }
      var st = K.el('div', 'kz-st'); st.appendChild(K.el('p', 'kz-small', 'Special'));
      st.appendChild(K.el('h2', '', (d.special && d.special.titel) || d.artist)); st.appendChild(K.el('p', '', 'Text, Bild, Podcast und alle ' + d.songs.length + ' Lieder'));
      sp.appendChild(st); body.appendChild(sp);
    });
  };

  K.start = function () {
    if (document.getElementById('konzert-home')) K.home();
    else { var m = K.get(); if (m && document.body.hasAttribute('data-kz')) K.apply(K.theme(null, m.artist)); }
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', K.start); else K.start();
})();
