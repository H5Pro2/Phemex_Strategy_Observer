# BAUPLAN: Trading Bot Agent System

Stand: 2026-05-17

# --------------------------------------------------
# 1. System-Ist-Zustand
# --------------------------------------------------

## 1.1 Systemrolle

Dieses System ist ein lokales Trading-Agentensystem fuer Marktbeobachtung, Paper-Trading und Entscheidungsanalyse.

Der Bot arbeitet als Observer- und Paper-Trading-System.

Live-Trading bleibt gesperrt.

## 1.2 Pipeline

```text
Agenten
→ CEO Trader Gesamtbewertung
→ Brain / Lernschicht Entry-Optimierung
→ Economic Gate
→ Paper Trade
```

Kernaufgaben:

- Marktdaten laden
- Kerzen und Indikatoren auswerten
- Agentenberichte erzeugen
- CEO-Gesamtbewertung anwenden
- Brain-/Lernschicht auswerten
- Replay-Regeln einbeziehen
- Economic Gate pruefen
- Paper-Trades verwalten
- Dashboard fuer Status, Chart, Agenten und Einstellungen bereitstellen

## 1.3 Projektstruktur

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

## 1.4 Repository-Regeln

Versioniert werden:

- Quellcode
- Vorlagen
- Dokumentation
- statische Assets
- `data/.gitkeep`

Nicht versioniert werden:

- `.env`
- `config.json`
- `data/*.json`
- lokale Exporte
- Logs

Lokale Arbeitsdateien werden aus Vorlagen erzeugt.

## 1.5 Start-Stand

Vorhandene Startwege:

- `start_bot.ps1`
- `start_bot.bat`
- manueller Python-Start

Die Startdateien pruefen:

- Python vorhanden
- `requirements.txt` vorhanden
- `config.json` vorhanden oder aus Vorlage erstellbar
- `.env` vorhanden oder aus Vorlage erstellbar
- `data`-Ordner vorhanden oder erstellbar
- Dashboard Runtime vorbereitet
- Dashboard Runtime Patches gueltig
- Agenten-Rollenvertrag gueltig
- Brain-/Replay-Erweiterung gueltig
- Brain-Dashboard-Erweiterung gueltig
- Python-Abhaengigkeiten installierbar
- Bot-Start ohne Fehler

# --------------------------------------------------
# 2. Agenten / CEO
# --------------------------------------------------

## 2.1 Rollenstand

Technische Rollen:

- Struktur
- Momentum
- Kontext
- Risiko
- Entscheidung
- Weitere

Umgesetzt:

- `agent_runtime_roles.py`
- `checks/check_agent_runtime_roles.py`
- Rollenvertrag fuer Agenten
- CEO-Rollenbewertung
- Volume als Kontext getrennt
- Risk / Volatility getrennt bewertet

## 2.2 Agenten-Setup im Dashboard

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

## 2.3 CEO-Zielbild

CEO prueft:

- Agentenmehrheit
- Richtungskonsens
- Rollen-Konsens
- Konflikte
- Blocking-Agenten
- Mindestscore
- Mindest-Alignment
- Brain-Entscheidung
- Economic-Gate-Status

CEO erzeugt keine eigene Preislogik.

# --------------------------------------------------
# 3. Brain / Replay
# --------------------------------------------------

## 3.1 Brain-Stand

Umgesetzt:

- `brain_replay_enhancements.py`
- `brain_dashboard_enhancements.py`
- `checks/check_brain_replay_enhancements.py`
- `checks/check_brain_dashboard_enhancements.py`

Verbessert:

- stabilerer Pattern-Key `v2`
- rollenbasierter Pattern-Key
- Memory-Matching auf stabile Pattern-Keys vorbereitet
- robustere Replay-Regelgewichtung
- Asset-spezifische Replay-Regeln bevorzugt
- Edge-Score aus Winrate, AvgR und Profit-Factor
- Mindestdatenmenge abgesichert
- GOOD/BAD-Regeln werden nicht blind uebernommen
- `dashboard_summary` fuer Brain-/Replay-Status

## 3.2 Brain-Zielbild

Brain optimiert:

- Richtungskontext
- Entry-Kontext
- Entry-Methode
- Fallback-Entry-Kontext
- SL-Kontext
- TP-Kontext aus echtem Risiko und RR
- Confidence
- Pattern-Key
- Memory-Match
- Replay-Regelgewichtung

LL / HH Boxen sind bevorzugte Entry-Zonen, aber keine Pflichtbedingung.

## 3.3 Replay-Zielbild

Replay-Regeln sollen nicht nur angezeigt, sondern sinnvoll gewichtet werden.

Ziel:

- starke Pattern-Kombinationen bevorzugen
- schwache Pattern-Kombinationen abwerten
- Asset-spezifische Unterschiede erkennen
- Mindestanzahl an Beispielen beruecksichtigen
- Winrate und AvgR gemeinsam bewerten
- Overfitting vermeiden

Replay-Regeln duerfen keine harte Sperre sein, solange sie nicht eindeutig als Blocking-Regel konfiguriert sind.

# --------------------------------------------------
# 4. Chart / Dashboard
# --------------------------------------------------

## 4.1 Dashboard Runtime-Patches

Runtime-Patches:

- `ui/patches/dashboard_agent_roles_patch.js`
- `ui/patches/dashboard_chart_pane_patch.js`
- `ui/patches/dashboard_kline_native_indicators_patch.js`
- `ui/patches/dashboard_agent_setup_cleanup_patch.js`

Vorbereitung:

- `tools/prepare_dashboard_runtime.py`

Pruefung:

- `checks/check_dashboard_runtime_patches.py`

Aktuelle Patch-Versionen:

- `role-ui-v3-tech`
- `chart-controls-v2-tech`
- `kline-native-indicators-v3-full`
- `agent-setup-cleanup-v2-tech`

## 4.2 KLineCharts-Stand

Umgesetzt:

- `indicator_display_enhancements.py`
- MACD eigene native KLineCharts-Pane
- MFI eigene native KLineCharts-Pane
- RSI eigene native KLineCharts-Pane
- Volume eigene native KLineCharts-Pane
- VWAP als Preislinie / Overlay im Hauptchart
- Chart-Bedienleiste
- Auto-Scroll AN/AUS
- Realtime
- Zoom + / Zoom -
- Fit

## 4.3 Dashboard-Zielbild

Dashboard soll staerker auf Entscheidung und Bedienbarkeit ausgerichtet werden.

Ziel:

- klare Bereiche
- einklappbare Agentengruppen
- kompakte CEO-Zusammenfassung
- Brain-Status sichtbar
- Replay-Regeln sichtbar und erklaert
- Trade-History filterbar
- Einstellungen uebersichtlich gruppiert
- Chart-Einstellungen vom Agenten-Setup trennen
- Chart-Indikatoren sauber in eigenen Panes darstellen

# --------------------------------------------------
# 5. Economic Gate
# --------------------------------------------------

Das Economic Gate bleibt die harte mathematische Sperre.

Es prueft:

- Entry / SL / TP Geometrie
- Risk / Reward
- Mindest-RR
- Mindest-Netto-Profit
- Gebuehren
- Positionsgroesse
- maximale SL-Entfernung

Kein Agent, kein CEO, kein Brain und keine Audit-Schicht darf diese Stufe umgehen.

# --------------------------------------------------
# 6. Lokale Audit-Schicht
# --------------------------------------------------

Die lokale Audit-Schicht soll Entscheidungen erklaeren, nicht treffen.

Erlaubt:

- Agentenberichte zusammenfassen
- Konflikte erklaeren
- CEO-Gesamtbewertung sprachlich beschreiben
- Brain-Entscheidung erklaeren
- Memory-Kontext lesbar machen
- Risiko-Hinweise erzeugen
- Dashboard-Texte verbessern

Nicht erlaubt:

- Entry setzen
- Stop-Loss setzen
- Take-Profit setzen
- Positionsgroesse setzen
- Economic Gate umgehen
- Live-Trading freigeben
- API-Schluessel lesen
- private `.env`-Daten erhalten
- Orders ausloesen
- deterministische Preislogik ersetzen

# --------------------------------------------------
# 7. Naechste Ausbaustufen
# --------------------------------------------------

## Abschnitt 1: Dokumentation / Struktur

Status:

- umgesetzt

Umgesetzt:

- README auf Agentensystem ausgerichtet
- Bauplan provider-neutral gemacht
- Ollama-Fokus entfernt
- `BAUPLAN_LLM_OLLAMA.md` durch `BAUPLAN.md` ersetzt
- `.env` aus Repository entfernt
- `.gitignore` ergaenzt
- `config.json` aus Repository entfernt
- generierte `data/*.json` aus Repository entfernt
- `data/.gitkeep` hinzugefuegt
- `checks/` eingefuehrt
- `tools/` eingefuehrt
- `ui/patches/` eingefuehrt
- `docs/` fuer technische Dokumentation genutzt

## Abschnitt 2: Agentenrollen schaerfen

Status:

- teilweise umgesetzt

Umgesetzt:

- Rollenvertrag technisch ergaenzt
- CEO-Rollenbewertung vorbereitet
- Kontext-Rolle fuer Volume ergaenzt
- Risk/Volatility getrennt von Momentum bewertet
- lokale Rollenpruefung ergaenzt
- Dashboard-Rollenpatch vorbereitet
- technische Dashboard-Rollenoptik umgesetzt
- Agenten-Setup in Chart-/Struktur-/Bewertungsbereiche getrennt

Offen:

- Dashboard-Agentenkarten nach echtem Test weiter feinjustieren
- Rollenanzeige dauerhaft in Haupt-HTML integrieren

## Abschnitt 3: CEO-Bewertung verbessern

Status:

- teilweise umgesetzt

Umgesetzt:

- Rollen-Konsens technisch ergaenzt
- Struktur und Momentum staerker gewichtet
- Kontext niedriger gewichtet
- Risk separat ausgewiesen
- BLOCKED-Verhalten pruefbar gemacht
- CEO-Darstellung technisch kompakter vorbereitet

Offen:

- CEO-Entscheidung im Dashboard nach Live-Test weiter schaerfen
- WAIT / BLOCKED / BIAS optisch final trennen

## Abschnitt 4: Brain verbessern

Status:

- teilweise umgesetzt

Umgesetzt:

- stabilerer Pattern-Key `v2`
- rollenbasierter Pattern-Key
- Memory-Matching auf stabilen Pattern-Key vorbereitet
- lokale Brain-/Replay-Pruefung ergaenzt
- Brain-Dashboard-Summary ergaenzt

Offen:

- Entry-Fallbacks im Dashboard sichtbarer machen
- Confidence noch nachvollziehbarer darstellen

## Abschnitt 5: Replay-Regeln verbessern

Status:

- teilweise umgesetzt

Umgesetzt:

- robustere Replay-Regelgewichtung
- Asset-Regeln bevorzugt
- Mindestdatenmenge abgesichert
- Edge-Score aus Winrate, AvgR und Profit-Factor
- GOOD/BAD-Regeln werden nicht blind uebernommen

Offen:

- Replay-Regel-Auswertung im Dashboard sichtbarer machen
- Asset- und Timeframe-Kontext weiter ausbauen

## Abschnitt 6: Dashboard / Chart verbessern

Status:

- teilweise umgesetzt

Umgesetzt:

- technische Agentenoptik vorbereitet
- kompaktere Agentenkarten
- kompaktere CEO-/Prioritaetsbereiche
- kompaktere Konfliktmatrix
- mobile Darstellung beruecksichtigt
- Chart-Bedienleiste ergaenzt
- native KLineCharts-Panes fuer MACD / MFI / RSI / Volume vorbereitet
- VWAP als Hauptchart-Overlay vorbereitet

Offen:

- echte Dashboard-Ansicht nach Start visuell pruefen
- getrennte KLineCharts-Panes fuer MACD / MFI / RSI / Volume im Browser pruefen
- VWAP Overlay im Hauptchart pruefen
- Hauptlayout weiter konsolidieren
- Einstellungen uebersichtlicher gruppieren
- Popups reduzieren
- wichtige Entscheidungen noch staerker nach oben holen

# --------------------------------------------------
# 8. Offene Punkte
# --------------------------------------------------

- direkte Python-Startpruefung bei fehlender `config.json` verbessern
- Dashboard-Agentenkarten nach echtem Test feinjustieren
- CEO-Entscheidung besser visualisieren
- Replay-Regeln im Dashboard sichtbarer machen
- Chart-Settings getrennt nach Kerzenkoerper und Docht pruefen
- Runtime-Patches spaeter dauerhaft in Hauptdateien integrieren
