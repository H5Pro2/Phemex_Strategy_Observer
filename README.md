# Trading Bot Agent System

Lokales Trading-Agentensystem fuer Marktbeobachtung, Paper-Trading, Agentenbewertung, CEO-Entscheidung, Brain-/Lernschicht und Dashboard-Steuerung.

Das Projekt ist kein Live-Trading-System. Live-Trading bleibt gesperrt. Der Bot arbeitet als Observer- und Paper-Trading-System.

# --------------------------------------------------
# Ziel
# --------------------------------------------------

Das System soll Marktinformationen auswerten, Agentenberichte erzeugen, Trade-Kandidaten pruefen und Paper-Trades nachvollziehbar auswerten.

Die Hauptlogik ist:

```text
Agenten
→ CEO Trader
→ Brain / Lernschicht
→ Economic Gate
→ Paper Trade
```

# --------------------------------------------------
# Kernbereiche
# --------------------------------------------------

## Agenten

Jeder Agent bewertet eine eigene Datenquelle oder Perspektive.

Beispiele:

- Marktstruktur
- BOS / CHoCH
- LL / HH Boxen
- Support / Resistance
- Swing Labels
- HMA / SMA / Triple EMA
- MACD / MFI / RSI / VWAP
- Breakout / Fakeout
- Volume
- Volatilitaet
- Risiko

Kein einzelner Agent entscheidet alleine ueber einen Trade.

## CEO Trader

Der CEO bewertet die Gesamtlage aus allen Agentenberichten.

Aufgaben:

- Richtungskonsens bewerten
- Konflikte erkennen
- Blocking-Signale beruecksichtigen
- Agentenqualitaet einordnen
- Brain-Entscheidung sichtbar machen

Der CEO erzeugt keine eigene Preislogik.

## Brain / Lernschicht

Das Brain nutzt Agentenkombinationen, Pattern-Keys und Paper-Trade-Ergebnisse.

Aufgaben:

- Entry-Kontext bewerten
- bevorzugte Entry-Zonen nutzen
- Fallback-Entry-Kontext erlauben
- SL/TP-Kontext pruefen
- Memory-Matches auswerten
- Confidence berechnen
- Replay-Regeln gewichten

LL / HH Boxen sind bevorzugte Entry-Zonen, aber keine Pflichtbedingung.

## Economic Gate

Das Economic Gate ist die harte mathematische Sperre.

Es prueft:

- Preisgeometrie
- Risk / Reward
- Mindest-RR
- Mindest-Netto-Profit
- Gebuehren
- Positionsgroesse
- maximale SL-Entfernung

Kein Agent, kein CEO und keine Audit-Schicht darf das Economic Gate umgehen.

## Replay / Auswertung

Replay-Daten dienen zur besseren Bewertung von Pattern-Kombinationen und Regeln.

Ziel:

- Regeln anhand vergangener Paper-Trades besser gewichten
- schlechte Pattern-Kombinationen erkennen
- starke Agenten-Kombinationen hervorheben
- Dashboard-Auswertung verbessern

## Dashboard

Das Dashboard zeigt Status, Chart, Agenten, Brain, CEO, Replay, Trade-History und Einstellungen.

Zielrichtung:

- bessere Uebersicht
- einklappbare Bereiche
- klare Agentenrollen
- sichtbare Entscheidungslogik
- reduzierte, lesbare Hinweise

# --------------------------------------------------
# Lokale Audit-Schicht
# --------------------------------------------------

Das System kann optional eine lokale Audit-Schicht nutzen.

Diese Schicht ist kein Trader.

Erlaubt:

- Agentenberichte zusammenfassen
- Konflikte erklaeren
- Risiko-Hinweise formulieren
- CEO-/Brain-Entscheidungen lesbarer machen
- Dashboard-Texte verbessern

Nicht erlaubt:

- Entry setzen
- Stop-Loss setzen
- Take-Profit setzen
- Positionsgroesse setzen
- Economic Gate umgehen
- Live-Trading freigeben
- API-Schluessel lesen
- Orders ausloesen

Ein lokaler Provider wie Ollama kann verwendet werden, ist aber nicht der Hauptfokus des Projekts.

# --------------------------------------------------
# Setup
# --------------------------------------------------

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
Copy-Item config.example.json config.json
```

API-Daten gehoeren nur in `.env`.

Fuer Public-Klines werden keine privaten Orderrechte benoetigt.

`config.json` ist absichtlich nicht versioniert. Sie muss lokal aus `config.example.json` erstellt werden.

# --------------------------------------------------
# Start
# --------------------------------------------------

Empfohlen unter Windows PowerShell:

```powershell
.\start_bot.ps1
```

Alternative mit Batch-Datei:

```powershell
.\start_bot.bat
```

Manueller Start mit Dashboard:

```powershell
python .\phemex_strategy_observer.py --config .\config.json --web
```

Dashboard:

```text
http://127.0.0.1:8787
```

Einmaliger Scan:

```powershell
python .\phemex_strategy_observer.py --config .\config.json --once
```

Wenn `config.json` fehlt:

```powershell
Copy-Item config.example.json config.json
```

Wenn `.env` fehlt:

```powershell
Copy-Item .env.example .env
```

# --------------------------------------------------
# Startdateien
# --------------------------------------------------

`start_bot.ps1` und `start_bot.bat` pruefen:

- Python vorhanden
- `requirements.txt` vorhanden
- `config.json` vorhanden oder aus Vorlage erstellbar
- `.env` vorhanden oder aus Vorlage erstellbar
- `data`-Ordner vorhanden oder erstellbar
- Python-Abhaengigkeiten installierbar
- Bot-Start ohne Fehler

# --------------------------------------------------
# Konfiguration
# --------------------------------------------------

Wichtige Dateien:

- `config.example.json` Vorlage fuer Konfiguration
- `config.json` lokale Arbeitskonfiguration, nicht versioniert
- `assets.txt` editierbare Asset-Liste
- `.env.example` Vorlage fuer API-Werte
- `.env` lokale private API-Werte, nicht versioniert

# --------------------------------------------------
# Laufzeitdaten
# --------------------------------------------------

Das System speichert lokale Laufzeitdaten unter `data/`.

Wichtige Dateien:

- `data/learning_memory.json`
- `data/observer_state.json`
- `data/runtime_status.json`

Diese Dateien sind Laufzeitdaten und werden nicht versioniert.

# --------------------------------------------------
# Repository-Regeln
# --------------------------------------------------

Versioniert werden:

- Quellcode
- Vorlagen
- Dokumentation
- statische Assets

Nicht versioniert werden:

- `.env`
- `config.json`
- `data/*.json`
- lokale Exporte
- Logs

# --------------------------------------------------
# Projekt-Dokumentation
# --------------------------------------------------

- `README.md` kurzer Einstieg und Projektueberblick
- `BAUPLAN.md` Architektur, Zielbild und naechste Ausbaustufen
- `strategy.md` Regelwerk und Trading-Logik
