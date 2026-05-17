# Trading Bot Agent System

Lokales Trading-Agentensystem fuer Marktbeobachtung, Paper-Trading, Agentenbewertung, CEO-Entscheidung, Brain-/Lernschicht und Dashboard-Steuerung.

Das Projekt ist kein Live-Trading-System. Live-Trading bleibt gesperrt. Der Bot arbeitet als Observer- und Paper-Trading-System.

# --------------------------------------------------
# Projektstruktur
# --------------------------------------------------

```text
/
├─ phemex_strategy_observer.py      Kernruntime / Webserver / Observer
├─ agent_runtime.py                 Agentenruntime
├─ brain_runtime.py                 Brain- und Lernruntime
├─ trade_value_gate.py              Economic Gate
├─ indikator.py                     Indikatorlogik
├─ dashboard.html                   Dashboard-Hauptdatei
├─ dashboard_script.js              Dashboard-JavaScript
├─ styles.css                       Dashboard-Styles
├─ start_bot.ps1                    empfohlener Windows-Start
├─ start_bot.bat                    alternativer Windows-Start
├─ config.example.json              Konfigurationsvorlage
├─ assets.txt                       Asset-Liste
├─ docs/                            Dokumentation
├─ checks/                          lokale Pruefskripte
├─ tools/                           lokale Hilfs- und Vorbereitungstools
├─ ui/patches/                      Dashboard Runtime-Patches
└─ data/                            lokale Laufzeitdaten, nicht versioniert
```

# --------------------------------------------------
# Kernbereiche
# --------------------------------------------------

## Agenten

Jeder Agent bewertet eine eigene Datenquelle oder Perspektive.

Rollen:

- Struktur
- Momentum
- Kontext
- Risiko
- Entscheidung
- Weitere

Rollenlogik:

- `agent_runtime_roles.py`

Pruefung:

- `checks/check_agent_runtime_roles.py`

## Agenten-Setup im Dashboard

Das Agenten-Setup ist getrennt in:

- Chart-Indikator-Agenten
- Struktur- und Signalagenten
- Bewertungsagenten ohne eigene Chart-Pane

Chart-Indikator-Agenten:

- RSI
- VWAP
- Volume
- MACD
- MFI

Struktur- und Signalagenten:

- Breakout / Fakeout
- BOS / CHoCH
- LL / HH Boxen
- Support / Resistance
- Swing Labels

Bewertungsagenten ohne eigene Chart-Pane:

- Volatility Regime
- Risk

## CEO Trader

Der CEO bewertet die Gesamtlage aus allen Agentenberichten.

Aufgaben:

- Richtungskonsens bewerten
- Rollen-Konsens bewerten
- Konflikte erkennen
- Blocking-Signale beruecksichtigen
- Agentenqualitaet einordnen
- Brain-Entscheidung sichtbar machen

Der CEO erzeugt keine eigene Preislogik.

## Brain / Replay

Brain nutzt Agentenkombinationen, Pattern-Keys und Paper-Trade-Ergebnisse.

Erweiterung:

- `brain_replay_enhancements.py`
- `brain_dashboard_enhancements.py`

Pruefungen:

- `checks/check_brain_replay_enhancements.py`
- `checks/check_brain_dashboard_enhancements.py`

Umgesetzt:

- stabilerer Pattern-Key `v2`
- rollenbasierter Pattern-Key
- robustere Replay-Regelgewichtung
- Asset-spezifische Replay-Regeln
- Edge-Score aus Winrate, AvgR und Profit-Factor
- Schutz gegen zu kleine Datenbasis
- `dashboard_summary` fuer Brain-/Replay-Status

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

## Dashboard / Chart

Dashboard-Hauptdateien:

- `dashboard.html`
- `dashboard_script.js`
- `styles.css`

Runtime-Patches:

- `ui/patches/dashboard_agent_roles_patch.js`
- `ui/patches/dashboard_chart_pane_patch.js`
- `ui/patches/dashboard_kline_native_indicators_patch.js`
- `ui/patches/dashboard_agent_setup_cleanup_patch.js`

Vorbereitungstool:

- `tools/prepare_dashboard_runtime.py`

Patch-Pruefung:

- `checks/check_dashboard_runtime_patches.py`

Aktuelle Dashboard-Patches:

- `role-ui-v3-tech`
- `chart-controls-v2-tech`
- `kline-native-indicators-v3-full`
- `agent-setup-cleanup-v2-tech`

Chart-Anzeige:

- MACD eigene native KLineCharts-Pane
- MFI eigene native KLineCharts-Pane
- RSI eigene native KLineCharts-Pane
- Volume eigene native KLineCharts-Pane
- VWAP als Preislinie / Overlay im Hauptchart
- Auto-Scroll AN/AUS
- Realtime
- Zoom + / Zoom -
- Fit

# --------------------------------------------------
# Setup
# --------------------------------------------------

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
Copy-Item config.example.json config.json
```

API-Daten gehoeren nur in `.env`.

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

# --------------------------------------------------
# Technische Pruefungen
# --------------------------------------------------

Dashboard Runtime vorbereiten:

```powershell
python .\tools\prepare_dashboard_runtime.py
```

Dashboard Runtime Patches pruefen:

```powershell
python .\checks\check_dashboard_runtime_patches.py
```

Agentenrollen:

```powershell
python .\checks\check_agent_runtime_roles.py
```

Brain / Replay:

```powershell
python .\checks\check_brain_replay_enhancements.py
```

Brain Dashboard Summary:

```powershell
python .\checks\check_brain_dashboard_enhancements.py
```

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
# Dokumentation
# --------------------------------------------------

- `README.md` kurzer Einstieg und Projektueberblick
- `BAUPLAN.md` Architektur und Zielbild
- `strategy.md` Regelwerk und Trading-Logik
- `docs/TECHNICAL_STATUS.md` aktueller technischer Umsetzungsstand
