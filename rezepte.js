(function () {
  // Bild-Platzhalter: eigene Fotos, sonst Farbverlauf mit Symbol. Echte Fotos lassen sich hier pro Rezept eintragen (photo).
  var R = {
    'haferkleie-porridge': ['🥣', '#F6C177', '#E08A4B'],
    'linsen-curry': ['🍛', '#F2A65A', '#C8562B'],
    'lachs-ofengemuese': ['🐟', '#F59E8B', '#D2644F'],
    'ackerbohnen-huemmus': ['🥙', '#C9D68A', '#7FA16B'],
    'udon-spargel-stirfry': ['🍜', '#B9D88B', '#5E9A63'],
    'skyr-bowl-walnuss': ['🫐', '#B7A5E0', '#7C6BB8'],
    'fusilli-brokkoli-walnuss-pesto': ['🥦', '#A8D58A', '#5C9A55'],
    'suesskartoffeln-tomatensauce': ['🍠', '#F4A261', '#C8472F', 'suesskartoffeln-1.jpg'],
    'noors-tofu-schwarze-limette': ['🥬', '#9CCB9B', '#4F8A66', 'noors-tofu-schwarze-limette-1.jpg'],
    'kartoffelgratin-kokos-limette': ['🥔', '#F6D27A', '#D9A23E', 'kartoffelgratin-kokos-limette-1.jpg'],
    'hellofresh-smashed-potatoes': ['🥔', '#F6C177', '#D98B3A', 'hellofresh-smashed-potatoes-1.jpg'],
    'kaesekuchen-ohne-mehl': ['🍰', '#F9D7A8', '#E7A15B'],
    'mandel-biskuit-boden': ['🥧', '#F3DDB0', '#D9A86A'],
    'falafel-smash-burger-karotten-zaziki': ['🍔', '#F2B86B', '#C9702E'],
    'kaiserschmarrn-mit-apfelmus': ['🥞', '#F8CE86', '#E0883F', 'kaiserschmarrn-mit-apfelmus-1.jpg'],
    'kichererbsen-gruenkohl-pfanne-feta': ['🥬', '#B6D48A', '#5F9A57'],
    'makrele-weisse-bohnen-rucola-salat': ['🐟', '#8FC1D4', '#3E7F9A'],
    'tempeh-erdnuss-pfanne-brokkoli': ['🥜', '#E5B77A', '#B5762F'],
    'toskanisches-huehnchen-weisse-bohnen': ['🍗', '#F0A872', '#C25B30'],
    'kabeljau-kichererbsen-ofenpfanne': ['🐠', '#9CC9D9', '#4A8CA6'],
    'garnelen-quinoa-bowl-edamame': ['🍤', '#F8B49A', '#DB6F52'],
    'ofenforelle-fenchel-mandeln': ['🐟', '#A3CFC0', '#4F9484'],
    'tofu-bohnen-chili': ['🌶️', '#EE8F73', '#B9372A'],
    'putenwurst-gruenkohl-bohnen-suppe': ['🍲', '#B5D08B', '#5C8F4F'],
    'puten-hackbaellchen-weisse-bohnen': ['🍅', '#F0907A', '#C23B2B'],
    'sardinen-weissbohnen-salat': ['🥗', '#A7D1C8', '#4C8E85'],
    'linsen-bolognese-vollkorn-spaghetti': ['🍝', '#F2A07B', '#BF4B2B'],
    'pustertaler-kaese-polenta': ['🧀', '#F6D27A', '#D9A23E'],
    'gersten-maronen-suppe-milch': ['🌾', '#E8D6A8', '#A8884F'],
    'suedtiroler-kuerbiscremesuppe': ['🎃', '#F6B873', '#D9742E'],
    'herbstsalat-pastinaken-speck-almkaese': ['🥗', '#BFD98A', '#6E9A4F'],
    'weisse-bohnen-tomatensauce': ['🫘', '#F0907A', '#C23B2B'],
    'meraner-antipasti': ['🍐', '#D7D58A', '#8E9A4A'],
    'thunfisch-kichererbsen-avocado-salat': ['🐟', '#9CD9CB', '#3E8F80'],
    'schwarze-bohnen-quinoa-bowl-avocado': ['🥑', '#AAD68A', '#5D9A52']
  };
  function slugOf(href) { var m = /([^\/]+)\.html/.exec(href || ''); return m ? m[1] : ''; }
  function media(slug, base) {
    var r = R[slug]; if (!r) return null;
    var d = document.createElement('div'); d.className = 'rmedia';
    d.style.setProperty('--c1', r[1]); d.style.setProperty('--c2', r[2]);
    if (r[3]) { var im = document.createElement('img'); im.src = base + r[3]; im.alt = ''; im.loading = 'lazy'; d.appendChild(im); d.classList.add('has-photo'); }
    else { var e = document.createElement('span'); e.className = 'remo'; e.textContent = r[0]; e.setAttribute('aria-hidden', 'true'); d.appendChild(e); }
    return d;
  }
  // Übersicht
  var cards = document.querySelectorAll('.page-list .entry-preview[href*="rezepte/"]');
  for (var i = 0; i < cards.length; i++) {
    var m = media(slugOf(cards[i].getAttribute('href')), 'rezepte/'); if (!m) continue;
    cards[i].insertBefore(m, cards[i].firstChild); cards[i].classList.add('has-media');
  }
  // Einzelseite
  var art = document.querySelector('.page-recipe article');
  if (art) {
    var slug = slugOf(location.pathname), h = media(slug, ''); if (!h) return;
    h.className += ' rhero';
    var own = art.querySelector('img[src$="-1.jpg"]');
    if (own) { var box = own.closest('figure, .photo-full') || own; box.style.display = 'none'; }
    art.insertBefore(h, art.firstChild);
  }
})();
