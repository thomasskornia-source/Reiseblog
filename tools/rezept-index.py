#!/usr/bin/env python3
"""Index für den Wochenplaner: liest alle Rezeptseiten in rezepte/, ergänzt Klassiker und Brotzeiten und schreibt data/wochenplan.json.
Aufruf (nach neuen oder geänderten Rezepten):  python3 tools/rezept-index.py
typ: veggie (ohne Fleisch und Fisch) | fisch | fleisch. Bei fleisch gibt es eine Veggie-Variante (Fleischersatz), die Fleischzeile steht in "fleisch".
warm=False: kalte Gerichte (Salate, Aufstriche), die gehören eher zur Brotzeit als aufs warme Mittagessen."""
import glob, html, json, os, re
ROOT = os.path.join(os.path.dirname(__file__), '..')
FLEISCH = re.compile(r'(hähnchen|huhn|pute\b|puten|hackfleisch|\bhack\b|rind|schwein|speck|schinken|wurst|salami|lamm|bacon|steak|brät)', re.I)
FISCH = re.compile(r'(lachs|forelle|kabeljau|makrele|sardine|garnele|thunfisch|fisch|anchov)', re.I)
KALT = {'makrele-weisse-bohnen-rucola-salat', 'sardinen-weissbohnen-salat', 'thunfisch-kichererbsen-avocado-salat', 'herbstsalat-pastinaken-speck-almkaese', 'meraner-antipasti', 'ackerbohnen-huemmus'}
WARME_ARTEN = ('Hauptgericht', 'Mittagessen', 'Abends', 'Suppe')
def text(s): return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()
def ohne_gehackt(z): return re.sub(r'gehackt\w*', '', z)
out = []
for p in sorted(glob.glob(os.path.join(ROOT, 'rezepte', '*.html'))):
    h = open(p, encoding='utf-8').read(); slug = os.path.basename(p)[:-5]
    t = text(re.search(r'<h1>(.*?)</h1>', h, re.S).group(1))
    art = text(re.search(r'<p class="date">(.*?)</p>', h, re.S).group(1)).split('·')[0].strip() if '<p class="date">' in h else ''
    meta = text(' '.join(re.findall(r'<div class="recipe-meta">(.*?)</div>', h, re.S)))
    mi = re.search(r'(\d+)\s*Min', meta); po = re.search(r'(\d+)\s*Portion', meta)
    m = re.search(r'<div class="recipe-ingredients">(.*?)</div>', h, re.S)
    zut = [text(x) for x in re.findall(r'<li>(.*?)</li>', m.group(1), re.S)] if m else []
    if art not in WARME_ARTEN and slug not in KALT: continue          # Frühstück, Kuchen, Dessert, Beilagen bleiben draußen
    fl = [z for z in zut if FLEISCH.search(ohne_gehackt(z))]
    fi = [z for z in zut if FISCH.search(z)]
    typ = 'fleisch' if fl else 'fisch' if fi else 'veggie'
    out.append({'id': slug, 'quelle': 'rezept', 'titel': t, 'art': art, 'min': int(mi.group(1)) if mi else None, 'portionen': int(po.group(1)) if po else None,
                'typ': typ, 'warm': slug not in KALT, 'zutaten': zut, 'fleisch': fl})
KLASSIKER = [
  ('klassiker-bolognese', 'Spaghetti Bolognese', 40, 4, ['500 g Hackfleisch', '400 g Spaghetti', '2 Zwiebeln', '2 Knoblauchzehen', '2 Karotten', '800 g stückige Tomaten (Dose)', '2 EL Tomatenmark', '2 EL Olivenöl', 'Salz, Pfeffer, Oregano', 'Parmesan']),
  ('klassiker-lasagne', 'Lasagne', 70, 4, ['500 g Hackfleisch', '250 g Lasagneplatten', '2 Zwiebeln', '2 Knoblauchzehen', '700 g Tomatenpassata', '500 ml Milch', '40 g Butter', '40 g Mehl', '200 g Mozzarella', '50 g Parmesan', 'Salz, Pfeffer, Muskat']),
  ('klassiker-chili', 'Chili con Carne', 40, 4, ['500 g Hackfleisch', '2 Zwiebeln', '2 Knoblauchzehen', '1 rote Paprika', '1 Dose Kidneybohnen', '1 Dose Mais', '800 g stückige Tomaten (Dose)', '2 EL Tomatenmark', '2 EL Olivenöl', 'Salz, Chili, Kreuzkümmel, Paprikapulver']),
]
for i, t, mi, po, zut in KLASSIKER:
    out.append({'id': i, 'quelle': 'klassiker', 'titel': t, 'art': 'Klassiker', 'min': mi, 'portionen': po, 'typ': 'fleisch', 'warm': True, 'zutaten': zut, 'fleisch': [zut[0]]})
# Brotzeiten: Mengen für 1 Person
BROTZEIT = [
  ('brotzeit-klassisch', 'Klassische Brotzeit', 'fleisch', ['2 Scheiben Vollkornbrot', '10 g Butter', '40 g Bergkäse', '40 g Schinken', '3 Radieschen', '¼ Gurke', '1 Tomate'], ['40 g Schinken']),
  ('brotzeit-kaese', 'Käse-Brotzeit', 'veggie', ['2 Scheiben Vollkornbrot', '10 g Butter', '40 g Bergkäse', '40 g Camembert', '10 Weintrauben', '¼ Gurke', '1 Tomate'], []),
  ('brotzeit-obazda', 'Obazda mit Brezn', 'veggie', ['1 Brezn', '60 g Obazda', '3 Radieschen', '¼ Gurke', '½ Zwiebel'], []),
  ('brotzeit-hummus', 'Hummus-Brotzeit', 'veggie', ['2 Scheiben Vollkornbrot', '60 g Hummus', '1 Karotte', '¼ Gurke', '5 Oliven', '1 Tomate'], []),
  ('brotzeit-fisch', 'Fisch-Brotzeit', 'fisch', ['2 Scheiben Vollkornbrot', '10 g Butter', '50 g Räucherlachs', '1 TL Meerrettich', '¼ Gurke', '1 Zitrone (Spalte)'], []),
  ('brotzeit-ei', 'Eier-Brotzeit', 'veggie', ['2 Scheiben Vollkornbrot', '10 g Butter', '2 Eier', '40 g Frischkäse', '3 Radieschen', '1 Tomate', 'Schnittlauch'], []),
  ('brotzeit-wurstsalat', 'Wurstsalat mit Brot', 'fleisch', ['2 Scheiben Vollkornbrot', '100 g Fleischwurst', '1 Gewürzgurke', '½ Zwiebel', '1 EL Essig', '1 EL Öl'], ['100 g Fleischwurst']),
  ('brotzeit-aufstrich', 'Aufstrich-Brotzeit', 'veggie', ['2 Scheiben Vollkornbrot', '60 g Frischkäse', '30 g Kräuterquark', '¼ Gurke', '3 Radieschen', '1 Tomate'], []),
]
for i, t, typ, zut, fl in BROTZEIT:
    out.append({'id': i, 'quelle': 'brotzeit', 'titel': t, 'art': 'Brotzeit', 'min': 10, 'portionen': 1, 'typ': typ, 'warm': False, 'zutaten': zut, 'fleisch': fl})
for o in out: print(o['quelle'][:8].ljust(8), o['id'][:40].ljust(40), str(o['min']).rjust(4), o['portionen'], o['typ'], o['warm'])
json.dump({'rezepte': out}, open(os.path.join(ROOT, 'data', 'wochenplan.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
