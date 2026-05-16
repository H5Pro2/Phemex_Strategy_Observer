# Phemex Strategy Observer

Ein reiner Beobachtungs-/Paper-Bot fuer die Liquiditaets-Sweep-Strategie.

Der Bot tradet nicht live. Er zieht Kerzen von Phemex, erkennt Setups, erzeugt Long/Short-Signale mit Entry/SL/TP, verfolgt intern Pending Orders und Paper-Trades und schreibt eine einfache Lernstatistik ueber Gewinner und Fehltrades.

## Setup

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
Copy-Item config.example.json config.json
```

Trage API-Daten nur in `.env` ein. Fuer die aktuellen Public-Klines werden keine privaten Orderrechte benoetigt.

## Start

```powershell
python .\phemex_strategy_observer.py --config .\config.json
```

Mit lokaler Weboberflaeche:

```powershell
python .\phemex_strategy_observer.py --config .\config.json --web
```

Dashboard:

```text
http://127.0.0.1:8787
```

Das Dashboard zeigt oben den echten Phemex-Futures-Kontostand fuer die konfigurierte Waehrung, standardmaessig `USDT`. Dafuer muessen `PHEMEX_API_KEY` und `PHEMEX_API_SECRET` in `.env` stehen und Leserechte fuer Futures/Contract-Accountdaten haben. Ohne gueltige Credentials steht dort `API nicht verbunden`.

Einmaliger Scan ohne Dauerschleife:

```powershell
python .\phemex_strategy_observer.py --config .\config.json --once
```

## Zeitrahmen

Standard ist:

- Signal-Zeiteinheit: `300` Sekunden, also 5m
- Bestaetigungs-Zeiteinheit: `300` Sekunden, also gleicher Timeframe

Die Strategie arbeitet technisch in einem Timeframe. Bei `single_timeframe_mode=true` wird die Bestaetigungs-Zeiteinheit automatisch auf die Signal-Zeiteinheit gesetzt.

## Trading-Agentensystem

Die aktuelle Zielrichtung ist ein Trading-Agentensystem. Jeder Agent bewertet seine eigene Datenquelle eigenstaendig. Der CEO Trader bewertet alle Agentenberichte zusammen. Das Brain lernt aus Paper-Trades, Entry-Logik, Pattern-Kombinationen und Ergebnissen. Eine LL / HH Box ist nur bevorzugte Entry-Zone und keine Pflichtbedingung. Das Economic Gate bleibt die harte Sperre fuer Wirtschaftlichkeit.

## Loops

Der Bot nutzt zwei getrennte Schleifen:

- `phemex_poll_seconds`: Phemex-Abfrage fuer Kerzen und Accountdaten, Standard `20` Sekunden.
- `system_loop_seconds`: interne Verarbeitung aus dem letzten Kerzen-Cache, Standard `1` Sekunde.

Die System-Loop erzeugt keine zusaetzlichen Phemex-Kerzenabfragen.

## Strategie-Regeln

Die aktuelle Runtime nutzt kein Legacy-StrategyEngine-Setup mehr.

Der Ablauf ist:

```text
Agenten → CEO Trader → Brain / Lernschicht → Economic Gate → Paper Trade
```

Die Agenten lesen Indikator-, Kerzen- und Kontextdaten und liefern eigenstaendige Bewertungen. CEO kontrolliert die Gesamtlage aller Agenten, Konflikte und Blocking-Signale. Brain erzeugt und optimiert daraus den Trade-Kandidaten mit Entry-Logik und Memory. Economic Gate bleibt die harte ökonomische Sperre fuer RR, TP/SL-Geometrie, Gebühren und Mindestgewinn.

Stop-Loss wird wahlweise strukturell oder per ATR berechnet. Der Take-Profit entsteht immer aus dem echten SL-Risiko und dem eingestellten RR. Das Economic Gate kann zusaetzlich eine maximale SL-Entfernung vom Entry in Prozent blockieren.

## Lernschicht

Die Lernschicht ist bewusst simpel und transparent:

- Sie speichert abgeschlossene Paper-Trades.
- Sie bleibt nach Neustarts erhalten: `data/learning_memory.json`.
- Offene und pending Paper-Trades bleiben nach Neustarts erhalten: `data/observer_state.json`.
- Der letzte Bot-/Dashboard-Status wird gespeichert: `data/runtime_status.json`.
- Sie bucketed Formationseigenschaften wie Sweep-Tiefe, Dochtanteil, FVG-Groesse, Trendlage und Session.
- Sie berechnet historische Trefferquote und Durchschnitts-R fuer aehnliche Setups.
- Neue Signale bekommen einen Confidence-Score aus dieser Memory.

Das ist kein magisches KI-Modell, sondern ein nachvollziehbarer Agent, der Fehltrades statistisch auswertet. Spaeter kann man daraus ein echtes ML-Modell bauen.

## Weboberflaeche

Das Dashboard zeigt:

- Bot-Modus, Symbole, Timeframes und letzte Aktualisierung.
- Phemex-Futures-Balance, Paper-Profit, Winrate und Unlock-Status.
- Pending, offene und abgeschlossene Paper-Trades.
- Lern-Buckets mit Anzahl, Winrate und Durchschnitts-R.
- Den letzten Scan-Zyklus mit Kerzendaten und Events.

Die Oberflaeche aktualisiert sich automatisch alle 5 Sekunden.

## Paper-Trading und Positionsgroesse

Im Dashboard kannst du Paper-Trading ein- oder ausschalten. Wenn Paper-Trading aus ist, erzeugt der Bot weiter Signale, legt aber keine neuen virtuellen Paper-Trades an und verfolgt keine neuen TP/SL-Ergebnisse.

Die geplante Positionsgroesse kann eingestellt werden als:

- `USD / USDT`: z. B. 100 USDT Notional pro Signal.
- `Asset-Menge`: z. B. 0.001 BTC pro Signal.

Die Werte werden in `config.json` gespeichert und bleiben nach einem Neustart erhalten.
