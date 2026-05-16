# ==================================================
# Trading Agent CEO Brain Regelwerk
# ==================================================

# --------------------------------------------------
# Zielrichtung
# --------------------------------------------------

Das System ist ein Trading-Agentensystem.

Jeder Agent bewertet seine eigene Datenquelle eigenstaendig.

Kein einzelner Agent ist automatisch Pflichtbedingung fuer einen Trade.

Der CEO Trader bewertet die Gesamtlage aller Agenten.

Das Brain lernt aus Paper-Trades, Entry-Logik, Pattern-Kombinationen und Ergebnissen.

Das Economic Gate bleibt die harte mathematische Sperre.

# --------------------------------------------------
# Pipeline
# --------------------------------------------------

```text
Agenten
→ CEO Trader Gesamtbewertung
→ Brain / Lernschicht Entry-Optimierung
→ Economic Gate
→ Paper Trade
```

Bedeutung:

- Agenten lesen Indikator-, Kerzen- und Kontextdaten.
- Agenten liefern eigenstaendig Signal, Score, gelesene Daten und Konfliktstatus.
- CEO bewertet alle Agentenberichte zusammen.
- Brain optimiert Entry, SL/TP-Kontext, Pattern-Key und Confidence mit Memory.
- Economic Gate prueft harte Wirtschaftlichkeit.
- PaperBroker fuehrt nur Paper-Trades aus.

# --------------------------------------------------
# Agenten
# --------------------------------------------------

- BOS / CHoCH Agent
- LL / HH Box Agent
- Support / Resistance Agent
- HH / LH / HL / LL Agent
- HMA Agent
- SMA Agent
- Triple EMA Agent
- MACD Agent
- MFI Agent
- RSI Agent
- VWAP Agent
- Breakout / Fakeout Agent
- Volume Agent
- Volatility Regime Agent
- Risk Agent

Agenten entscheiden keinen Trade alleine.

Jeder Agent liefert:

- Signal
- Score
- gelesene Daten
- Rueckmeldung
- Konfliktstatus
- optional Blocking

Blocking ist bewusst zu setzen.

Ein deaktivierter oder fehlender Indikator darf nicht automatisch die komplette Trading-Logik neutralisieren.

# --------------------------------------------------
# Agenten-Rollen
# --------------------------------------------------

Agenten werden nach Funktion gruppiert.

## Struktur

Struktur-Agenten lesen Marktstruktur, Zonen und Preisreaktionen.

Dazu gehoeren:

- BOS / CHoCH Agent
- LL / HH Box Agent
- Support / Resistance Agent
- HH / LH / HL / LL Agent
- Breakout / Fakeout Agent

## Momentum

Momentum-Agenten lesen Trendfolge, Indikatorrichtung und Richtungsbestaetigung.

Dazu gehoeren:

- HMA Agent
- SMA Agent
- Triple EMA Agent
- MACD Agent
- MFI Agent
- RSI Agent
- VWAP Agent

## Kontext

Kontext-Agenten lesen Zusatzumgebung, aber entscheiden nicht hart.

Dazu gehoeren:

- Volume Agent

Kontext darf Bias verstaerken oder abschwaechen, aber nicht allein einen Trade erzeugen.

## Risiko

Risiko-Agenten lesen harte Sperren, aktive Trades, Korrelationen und Value-Gate-Kontext.

Dazu gehoeren:

- Volatility Regime Agent
- Risk Agent

Risiko-Agenten duerfen blockieren, wenn eine harte Regel verletzt ist.

## Entscheidung

Entscheidungs-Agenten bewerten keine Kerzen direkt.

Dazu gehoeren:

- CEO Agent
- Brain / Lernschicht
- optionale lokale Audit-Schicht

Entscheidungs-Agenten duerfen keine Preislogik ersetzen.

# --------------------------------------------------
# Agenten-Qualitaet
# --------------------------------------------------

Jeder Agent bekommt eine Qualitaetsstufe.

Erlaubte Stufen:

- `STRONG`
- `OK`
- `WEAK`
- `OFFLINE`
- `BLOCK`

Bedeutung:

- `STRONG`: Signal ist richtungsrelevant und gut nutzbar.
- `OK`: Signal ist nutzbar, aber nicht stark genug als alleiniger Treiber.
- `WEAK`: Signal ist schwach und darf nur gering gewichtet werden.
- `OFFLINE`: Agent ist deaktiviert oder hat keine Daten.
- `BLOCK`: Agent meldet eine harte Blockade.

Offline-Agenten duerfen den CEO nicht neutralisieren.

Weak-Agenten duerfen den CEO nicht dominieren.

Blocking-Agenten muessen im CEO sichtbar bleiben.

# --------------------------------------------------
# CEO Trader
# --------------------------------------------------

CEO prueft:

- Agenten-Mehrheit
- Agenten-Konflikte
- Blocking-Agenten
- Richtungskonsens
- Rollen-Konsens
- Mindestscore
- Mindest-Alignment
- Trade-Plan vorhanden ja/nein

CEO erzeugt keine eigene Preislogik.

CEO darf einen LONG- oder SHORT-Bias anzeigen, auch wenn noch kein Trade-Kandidat freigegeben ist.

CEO soll Struktur und Momentum staerker gewichten als Kontext.

CEO soll Risiko separat ausweisen und nicht mit Momentum vermischen.

# --------------------------------------------------
# Brain / Lernschicht
# --------------------------------------------------

Brain ist nicht mehr von einer einzelnen LL / HH Box abhaengig.

Brain nutzt LL / HH Boxen als bevorzugte Entry-Zone, aber nicht als Pflichtbedingung.

Wenn keine passende Box vorhanden ist, darf Brain eine Fallback-Entry-Logik aus aktuellem Markt-/Kerzenkontext verwenden.

Stop-Loss wird wahlweise strukturell oder per ATR berechnet. Der Take-Profit entsteht immer aus dem echten SL-Risiko und dem eingestellten RR. Alte entfernte Strukturziele duerfen den TP nicht mehr zu einem Swing-Ziel ziehen.

Brain lernt aus:

- Entry-Methode
- Entry-Offset
- Pattern-Key
- Agenten-Kombination
- Memory-Match Count
- Winrate
- AvgR
- Economic-Gate-Ergebnis
- TP/SL-Ergebnis

Brain optimiert:

- Richtungskontext
- Entry-Kandidat
- Entry-Offset in Boxen
- Fallback-Entry-Kontext
- SL-Kandidat aus Struktur oder ATR
- TP-Kandidat aus RR
- Pattern-Key
- Confidence

# --------------------------------------------------
# Economic Gate
# --------------------------------------------------

Economic Gate bleibt harte Sperre.

Es prueft:

- Preisgeometrie
- Risk / Reward
- Mindest-RR
- Mindest-Netto-Profit
- Gebuehren
- Positionsgroesse

Kein Agent, kein CEO und keine Audit-Schicht darf das Economic Gate umgehen.

# --------------------------------------------------
# Live Trading
# --------------------------------------------------

Live-Trading bleibt gesperrt.

Der Bot arbeitet als Paper-/Observer-System.
