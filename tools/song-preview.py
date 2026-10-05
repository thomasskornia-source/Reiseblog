#!/usr/bin/env python3
"""Sucht für jeden Song in data/songs.json den 30-Sekunden-Ausschnitt bei Apple (iTunes Search API, kostenlos, ohne Anmeldung)
und trägt die Adresse als Feld "preview" ein. Nur die Adresse wird gespeichert, keine Audiodatei."""
import json, re, sys, time, unicodedata, urllib.parse, urllib.request

PATH = 'data/songs.json'

def norm(s):
    s = unicodedata.normalize('NFD', s or '').lower()
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()

def find(song):
    q = urllib.parse.urlencode({'term': song['title'] + ' ' + song['artist'], 'media': 'music', 'entity': 'song', 'country': 'de', 'limit': 10})
    req = urllib.request.Request('https://itunes.apple.com/search?' + q, headers={'User-Agent': 'Mozilla/5.0 (Reiseblog)'})
    last = None
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            break
        except Exception as e:
            last = e; time.sleep(3)
    else:
        raise last
    t1, a1 = norm(song['title']), norm(song['artist']).split(' ')[0]
    for r in data.get('results', []):
        if r.get('previewUrl') and norm(r.get('trackName', '')).startswith(t1) and a1 in norm(r.get('artistName', '')):
            return r['previewUrl'].replace('http://', 'https://')
    return None

def main():
    songs = json.load(open(PATH, encoding='utf-8'))
    changed = failed = 0
    for s in songs:
        if s.get('preview') or s.get('previewGeprueft'):
            continue
        try:
            url = find(s)
        except Exception as e:
            print('FEHLER', s['id'], e); failed += 1; continue
        if url:
            s['preview'] = url; print('ok', s['id'], url)
        else:
            s['previewGeprueft'] = True; print('nichts gefunden', s['id'])
        changed += 1
        time.sleep(1)
    if changed:
        with open(PATH, 'w', encoding='utf-8') as f:
            json.dump(songs, f, ensure_ascii=False, indent=1); f.write('\n')
    print('fertig, geändert:', changed, 'Fehler:', failed)
    return 0

if __name__ == '__main__':
    sys.exit(main())
