/* Bayern-Rätsel vorlesen: Gemini-Stimme wie beim Song, mit Denkpausen (Audiodatei + Zeitmarken); ohne Audiodatei gibt es einen Hinweis statt der Gerätestimme.
   Gemeinsam für quiz.html (gelber Knopf auf der Kachel) und raetsel.html. Braucht lesebuehne.js. */
(function () {
  var synth = ('speechSynthesis' in window) ? window.speechSynthesis : null;
  var q = null, marks = null, hasAudio = false, reading = false, started = false, timer = null, keep = [], player = null;
  var onState = function () {}, onNote = function () {};

  function state(on) { onState(on); }
  function stopAudio() { if (player) { player.pause(); player = null; } }
  function stop() {
    reading = false; clearTimeout(timer); stopAudio(); if (window.Lesebuehne) Lesebuehne.close();
    if (synth && (synth.speaking || synth.pending)) synth.cancel();
    state(false);
  }
  function germanVoice() {
    var vs = synth.getVoices() || [], i;
    for (i = 0; i < vs.length; i++) if (/^de[-_]DE/i.test(vs[i].lang)) return vs[i];
    for (i = 0; i < vs.length; i++) if (/^de/i.test(vs[i].lang)) return vs[i];
    return null;
  }
  function speakSeg(i) {
    if (!reading) return;
    if (i >= q.segmente.length) { stop(); return; }
    var seg = q.segmente[i], parts = seg.t.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [seg.t], n = 0;
    if (window.Lesebuehne) Lesebuehne.sentence(i);
    function next() {
      if (!reading) return;
      if (n >= parts.length) { timer = setTimeout(function () { speakSeg(i + 1); }, ((seg.pause || 0) + 0.7) * 1000); return; }
      var u = new SpeechSynthesisUtterance(parts[n++]);
      keep.push(u); if (keep.length > 6) keep.shift();
      u.lang = 'de-DE'; u.rate = 0.95; u.volume = 1;
      var v = germanVoice(); if (v) u.voice = v;
      u.onstart = function () { started = true; clearTimeout(timer); onNote(''); };
      u.onend = next;
      u.onerror = function (e) {
        if (e && (e.error === 'canceled' || e.error === 'interrupted')) return;
        stop(); onNote('Vorlesen hat nicht geklappt (' + ((e && e.error) || 'Fehler') + '). Bitte Lautstärke und Stummschalter prüfen.');
      };
      synth.speak(u);
      if (synth.paused) synth.resume();
    }
    next();
  }
  function startSpeech() {
    if (synth.speaking || synth.pending) synth.cancel();
    if (window.Lesebuehne) Lesebuehne.followSpeech(q.segmente.map(function (g) { return g.t; }));
    reading = true; started = false; onNote(''); state(true);
    speakSeg(0);
    timer = setTimeout(function () {
      if (reading && !started) { stop(); onNote('Es kommt kein Ton. Bitte den Stummschalter am Gerät und die Lautstärke prüfen.'); }
    }, 5000);
  }
  function playFile(fallback) {
    var a = new Audio('audio/raetsel-' + encodeURIComponent(q.id) + '.mp3');
    player = a; a.preload = 'auto'; state(true); reading = true;
    if (window.Lesebuehne) Lesebuehne.followTimeline(a, Lesebuehne.quizParts(q), marks);
    a.onended = function () { if (player === a) player = null; stop(); };
    a.onerror = function () { player = null; reading = false; fallback(); };
    var p = a.play();
    if (p && p.catch) p.catch(function () { if (player === a) { player = null; reading = false; fallback(); } });
  }
  function start() {
    if (!q) return;
    if (!hasAudio || !window.Audio) {   // keine Gerätestimme: die Sprecherstimme (wie beim Song) kommt aus der Audiodatei
      onNote('Die Sprecherstimme wird noch erzeugt und ist spätestens morgen früh da. Bis dahin gern unten nachlesen.');
      return;
    }
    if (window.Lesebuehne) Lesebuehne.open(Lesebuehne.quizParts(q), function () { stop(); });
    playFile(function () { stop(); onNote('Das Anhören hat nicht geklappt. Bitte Lautstärke und Stummschalter prüfen.'); });
  }

  window.RaetselPlayer = {
    canRead: function () { return !!window.Audio; },
    load: function (quiz) {
      q = quiz; hasAudio = false; marks = null;
      if (window.fetch) fetch('audio/raetsel-' + encodeURIComponent(q.id) + '.json').then(function (r) { return r.ok ? r.json() : null; })
        .then(function (j) { if (j && j.marken && j.marken.length === q.segmente.length) { marks = j.marken; hasAudio = true; } }).catch(function () {});
      if (synth && synth.getVoices) synth.getVoices();
    },
    toggle: function () { if (reading) stop(); else start(); },
    stop: stop,
    isReading: function () { return reading; },
    onState: function (f) { onState = f; },
    onNote: function (f) { onNote = f; }
  };
  window.addEventListener('pagehide', stop);
  window.addEventListener('pageshow', function (e) { if (e.persisted) stop(); });
})();
