/* Songmusik: spielt nach dem Vorlesen (bzw. leise schon die letzten Sekunden davor) den 30-Sekunden-Ausschnitt des Songs.
   Quelle: iTunes Search API (Apple), kostenlos und ohne Anmeldung. Wird im Browser abgefragt, der Player bleibt unsichtbar. */
(function () {
  var PRE = 10, LOW = 0.16, HIGH = 0.9;
  var url = null, corsOk = false, info = null;
  var m = null, ctx = null, gain = null, canVol = false, started = false, finished = false, cb = null, ramp = 0, tmo = 0;

  function norm(s) { return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, ' ').trim(); }

  function lookup(s) {
    return new Promise(function (res) {
      var name = '__sm' + Date.now(), sc = document.createElement('script'), done = false, t;
      function fin() { if (done) return; done = true; clearTimeout(t); try { delete window[name]; } catch (e) { window[name] = undefined; } if (sc.parentNode) sc.parentNode.removeChild(sc); res(); }
      window[name] = function (d) {
        try {
          var rs = (d && d.results) || [], t1 = norm(s.title), a1 = norm(s.artist).split(' ')[0];
          for (var i = 0; i < rs.length; i++) {
            var r = rs[i];
            if (r.previewUrl && norm(r.trackName).indexOf(t1) === 0 && norm(r.artistName).indexOf(a1) >= 0) { url = String(r.previewUrl).replace(/^http:/, 'https:'); info = r; break; }
          }
        } catch (e) {}
        fin();
      };
      sc.onerror = function () { st = 'Suche blockiert'; fin(); }; t = setTimeout(function () { if (!done && !url) st = 'Suche zu langsam'; fin(); }, 6000);
      sc.src = 'https://itunes.apple.com/search?media=music&entity=song&country=de&limit=8&term=' + encodeURIComponent(s.title + ' ' + s.artist) + '&callback=' + name;
      document.head.appendChild(sc);
    });
  }
  function probeCors() {
    if (!url || !window.fetch) return Promise.resolve();
    return fetch(url, { method: 'HEAD', mode: 'cors' }).then(function (r) { corsOk = r.ok; }).catch(function () { corsOk = false; });
  }
  function setVol(v) { if (gain) gain.gain.value = v; else if (m) { try { m.volume = Math.max(0, Math.min(1, v)); } catch (e) {} } }
  function rampTo(from, to, ms) {
    clearInterval(ramp); var t0 = Date.now();
    ramp = setInterval(function () {
      var f = Math.min(1, (Date.now() - t0) / ms); setVol(from + (to - from) * f);
      if (f >= 1) clearInterval(ramp);
    }, 60);
  }
  function build(cors) {
    var el = new Audio(); if (cors) el.crossOrigin = 'anonymous'; el.preload = 'auto'; el.src = url; gain = null;
    if (cors) {
      try {
        var AC = window.AudioContext || window.webkitAudioContext; ctx = ctx || new AC();
        var src = ctx.createMediaElementSource(el); gain = ctx.createGain(); gain.gain.value = 0; src.connect(gain); gain.connect(ctx.destination);
        if (ctx.state === 'suspended') ctx.resume();
      } catch (e) { gain = null; }
    }
    m = el;
    if (gain) canVol = true; else { try { el.volume = 0.5; canVol = Math.abs(el.volume - 0.5) < 0.01; el.volume = 1; } catch (e) { canVol = false; } }
  }
  var st = 'Suche läuft';
  function setSt(t) {
    st = t;
    var root = document.querySelector('.lb'); if (!root) return;
    var c = root.querySelector('.lb-credit');
    if (!c) { c = document.createElement('div'); c.className = 'lb-credit'; root.appendChild(c); }
    c.textContent = 'Musikausschnitt: Apple Music · ' + t;
  }
  function credit() {}
  function finish() {
    if (finished) return; finished = true; clearInterval(ramp); clearTimeout(tmo);
    var f = cb; cb = null; cleanup(); if (f) f();
  }
  function cleanup() {
    clearInterval(ramp); clearTimeout(tmo);
    if (m) { try { m.onended = null; m.onerror = null; m.pause(); } catch (e) {} }
    m = null; gain = null; started = false;
  }
  function begin(vol) {
    if (!m || started) return; started = true; m.muted = false; setVol(0);
    var p = m.play();
    if (p && p.catch) p.catch(function (e) { setSt('Start abgelehnt'); if (cb) finish(); else cleanup(); });
    rampTo(0, vol, 2000); setSt(canVol ? 'läuft leise' : 'läuft');
  }

  window.Songmusik = {
    prepare: function (s) { url = null; info = null; corsOk = false; st = 'Suche läuft'; cleanup(); if (s.preview) { url = String(s.preview).replace(/^http:/, 'https:'); st = 'Adresse vorhanden'; return probeCors().then(function () { st = 'gefunden' + (corsOk ? ' (Regler ja)' : ' (einfach)'); }); } return lookup(s).then(function () { if (!url && st === 'Suche läuft') st = 'Song nicht gefunden'; }).then(probeCors).then(function () { if (url) st = 'gefunden' + (corsOk ? ' (Regler ja)' : ' (einfach)'); }); },
    ready: function () { return !!url; },
    /* im Tipp des Nutzers aufrufen, damit iPhones das spätere Starten erlauben */
    arm: function () {
      cleanup(); finished = false; cb = null;
      setTimeout(function () { setSt(st); }, 400);
      if (!url) return;
      build(corsOk);
      m.onerror = function () { if (corsOk) { corsOk = false; cleanup(); build(false); setSt('Ladefehler, neuer Versuch'); } else { setSt('Ladefehler'); cleanup(); } };
      m.muted = true; var p = m.play();
      if (p && p.then) p.then(function () { if (m && !started) { m.pause(); m.currentTime = 0; } }).catch(function () {});
    },
    /* Restzeit der Stimme in Sekunden; ab 10 s startet die Musik leise (nur wenn sich die Lautstärke steuern lässt) */
    tick: function (remaining) { if (m && !started && canVol && remaining <= PRE) begin(LOW); },
    /* Stimme ist zu Ende: Musik lauter bzw. jetzt starten; done wird nach dem Ausschnitt (oder sofort ohne Musik) gerufen */
    voiceEnded: function (done) {
      if (!m) { done(); return; }
      cb = done; finished = false;
      m.onended = finish;
      if (!started) begin(canVol ? HIGH : 1); else rampTo(LOW, HIGH, 1500);
      tmo = setTimeout(finish, 45000);
    },
    stop: function () { cb = null; finished = true; cleanup(); }
  };
})();
