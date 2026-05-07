# ==================================================
# Agent Brain CEO Regelwerk
# ==================================================

# --------------------------------------------------
# Pipeline
# --------------------------------------------------

Agenten lesen Indikator- und Kerzendaten.

Brain / Lernschicht erzeugt daraus die Handelsentscheidung.

CEO Trader kontrolliert Brain-Entscheidung und Konflikte.

Economic Gate prueft harte Wirtschaftlichkeit.

PaperBroker fuehrt nur Paper-Trades aus.

```text
Agenten
→ Brain / Lernschicht
→ CEO Trader
→ Economic Gate
→ Paper Trade
```

# --------------------------------------------------
# Agenten
# --------------------------------------------------

- BOS / CHoCH Agent
- LL / HH Box Agent
- HH / LH / HL / LL Agent
- HMA Agent
- SMA Agent
- Triple EMA Agent
- MFI Agent
- Volume Agent
- Risk Agent

Agenten entscheiden keinen Trade alleine.

Jeder Agent liefert:

- Signal
- Score
- gelesene Daten
- Rueckmeldung
- Konfliktstatus
- optional Blocking

# --------------------------------------------------
# Brain / Lernschicht
# --------------------------------------------------

Brain matched Agenten-Kombinationen mit gespeicherter Erfahrung.

Brain optimiert:

- Richtung
- Entry-Kandidat
- Entry-Offset in Boxen
- SL-Kandidat
- TP-Kandidat
- Pattern-Key
- Confidence

# --------------------------------------------------
# CEO Trader
# --------------------------------------------------

CEO prueft:

- Agenten-Konflikte
- Brain-Score
- Mindest-Alignment
- Memory-Kontext
- Trade-Plan

CEO erzeugt keine eigene Preislogik ohne Brain.

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

# --------------------------------------------------
# Live Trading
# --------------------------------------------------

Live-Trading bleibt gesperrt.

Der Bot arbeitet als Paper-/Observer-System.
