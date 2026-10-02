"""Mustererkennung im 1-Jahres-Chart: Wendepunkte, Trendlinien aus höheren Tiefs / tieferen Hochs, Bodenbildung.

Alle Indizes beziehen sich auf die übergebenen Tageslisten (hier: das letzte Jahr = die Serie im Chart).
Die Regeln sind bewusst einfach und offen:
  Wendepunkt: Tief (Hoch) ist der niedrigste (höchste) Wert in +-K Tagen. Der jüngste Wendepunkt steht erst K Tage später fest.
  Unterstützungslinie: die letzten Tiefs steigen (je mindestens 1 % höher, mindestens 10 Tage Abstand). Bei drei steigenden
    Tiefs, die auf einer Linie liegen (Abweichung höchstens 2 %), gelten sie als drei Berührungen, sonst zählen die letzten zwei.
  Widerstandslinie: dasselbe spiegelverkehrt mit fallenden Hochs.
  Bodenbildung: Das Jahrestief liegt mindestens 15 Tage zurück, davor ein Rückgang von mindestens 15 %; danach ein zweites Tief
    (Doppelboden: höchstens 3 % über dem ersten, höheres Tief: bis 15 % darüber), dazwischen eine Erholung von mindestens 6 %
    (Nackenlinie). Status: in Bildung (Kurs über dem zweiten Tief), Ausbruch (Kurs über der Nackenlinie, höchstens 10 % darüber), sonst kein Muster.
  Gebrochen heißt: der Schlusskurs liegt mehr als 1 % auf der falschen Seite der Linie.
"""
K = 5

def wendepunkte(w, art):
    """art 'tief' oder 'hoch'; liefert [(Index, Wert)], Plateaus zählen einmal (der erste Tag)."""
    out = []
    for i in range(K, len(w) - K):
        fenster = w[i - K:i + K + 1]
        if (art == 'tief' and w[i] == min(fenster)) or (art == 'hoch' and w[i] == max(fenster)):
            if out and i - out[-1][0] <= K: continue
            out.append((i, w[i]))
    return out

def _linie(pkte, steigend, abstand_min=10):
    """Trendlinie durch die letzten Wendepunkte, deren Richtung stimmt."""
    if len(pkte) < 2: return None
    vorz = 1 if steigend else -1
    def ok(a, b):
        return (b[0] - a[0]) >= abstand_min and vorz * (b[1] / a[1] - 1) >= 0.01
    if len(pkte) >= 3:
        a, m, b = pkte[-3], pkte[-2], pkte[-1]
        if ok(a, m) and ok(m, b) and ok(a, b):
            soll = a[1] + (b[1] - a[1]) * (m[0] - a[0]) / (b[0] - a[0])
            if abs(m[1] / soll - 1) <= 0.02:
                return a, b, 3
    a, b = pkte[-2], pkte[-1]
    return (a, b, 2) if ok(a, b) else None

def trendlinien(hi, lo, cl):
    n = len(cl); res = {}
    for name, w, art, steigend in (('unterstuetzung', lo, 'tief', True), ('widerstand', hi, 'hoch', False)):
        l = _linie(wendepunkte(w, art), steigend)
        if not l: res[name] = None; continue
        (i1, p1), (i2, p2), nb = l
        steigung = (p2 - p1) / (i2 - i1)
        ende = p1 + steigung * (n - 1 - i1)
        # gebrochen: Schlusskurs liegt jetzt klar auf der falschen Seite der Linie
        falsch = (cl[-1] < ende * 0.99) if steigend else (cl[-1] > ende * 1.01)
        res[name] = {'i1': i1, 'p1': round(p1, 2), 'i2': i2, 'p2': round(p2, 2), 'ende': round(ende, 2),
                     'beruehrungen': nb, 'status': 'gebrochen' if falsch else 'intakt'}
    return res

def boden(hi, lo, cl):
    n = len(cl)
    L = min(range(n), key=lambda i: lo[i])
    if L > n - 16 or L == 0: return None
    vorher = max(hi[max(0, L - 126):L]) if L > 0 else 0
    if not vorher or (vorher - lo[L]) / vorher < 0.15: return None
    nach = [(i, p) for i, p in wendepunkte(lo, 'tief') if i >= L + 10]
    if not nach: return None
    i2, p2 = min(nach, key=lambda x: x[1])
    if p2 > lo[L] * 1.15: return None
    nacken = max(hi[L:i2 + 1])
    if nacken < lo[L] * 1.06: return None
    typ = 'Doppelboden' if p2 <= lo[L] * 1.03 else 'Höheres Tief nach dem Tief'
    if cl[-1] < p2 * 0.99: return None
    if cl[-1] > nacken:
        if cl[-1] > nacken * 1.10: return None   # Ausbruch liegt schon länger zurück, kein aktuelles Muster
        status = 'Ausbruch über die Nackenlinie'
    else:
        status = 'in Bildung (Boden hält)'
    return {'typ': typ, 'status': status, 'i1': L, 'p1': round(lo[L], 2), 'i2': i2, 'p2': round(p2, 2), 'nacken': round(nacken, 2)}

def erkennen(hi, lo, cl):
    m = trendlinien(hi, lo, cl)
    m['boden'] = boden(hi, lo, cl)
    return m
