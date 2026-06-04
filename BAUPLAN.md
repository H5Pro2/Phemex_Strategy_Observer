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
Marktdaten / Indikatoren / Strukturquellen
-> deterministische Kandidaten-Engine
-> OpenAI/LLM Rollen-Team
-> CEO / Judge Gesamtbewertung
-> Economic Gate
-> Paper Trade
```

Kernaufgaben:

- Marktdaten laden
- Kerzen und Indikatoren auswerten
- strukturierte Signalquellen erzeugen
- OpenAI/LLM-Rollenberichte erzeugen
- CEO/Judge-Gesamtbewertung anwenden
- Brain-/Lernschicht auswerten
- Replay-Regeln einbeziehen
- Economic Gate pruefen
- Paper-Trades verwalten
- Dashboard fuer Status, Chart, Agenten und Einstellungen bereitstellen

## 1.3 Projektstruktur

```text
/
â”œâ”€ phemex_strategy_observer.py      Kernruntime / Webserver / Observer
â”œâ”€ agent_runtime.py                 Agentenruntime
â”œâ”€ brain_runtime.py                 Brain- und Lernruntime
â”œâ”€ trade_value_gate.py              Economic Gate
â”œâ”€ indikator.py                     Indikatorlogik
â”œâ”€ dashboard.html                   Dashboard-Hauptdatei
â”œâ”€ dashboard_script.js              Dashboard-JavaScript
â”œâ”€ styles.css                       Dashboard-Styles
â”œâ”€ start_bot.ps1                    empfohlener Windows-Start
â”œâ”€ start_bot.bat                    alternativer Windows-Start
â”œâ”€ config.example.json              Konfigurationsvorlage
â”œâ”€ assets.txt                       Asset-Liste
â”œâ”€ docs/                            Dokumentation
â”œâ”€ checks/                          lokale Pruefskripte
â”œâ”€ tools/                           lokale Hilfs- und Vorbereitungstools
â”œâ”€ ui/patches/                      Dashboard Runtime-Patches
â””â”€ data/                            lokale Laufzeitdaten, nicht versioniert
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
# 2. Agenten / OpenAI-Rollenteam / CEO
# --------------------------------------------------

## 2.1 Zielbild Rollenmodell

Das bisherige Modell mit vielen einzelnen Indikator-Agenten wird zu einem Rollenmodell umgebaut.

Wichtig:

- Indikatoren bleiben technische Datenquellen.
- RSI, MACD, VWAP, EMA/HMA, Volume, BOS, CHoCH, HH/LL und Range erzeugen Fakten.
- Diese Fakten werden nicht mehr als einzelne UI-Agenten mit eigener Trade-Entscheidung behandelt.
- Die eigentliche Bewertung erfolgt durch ein kleines OpenAI/LLM-Team mit festen Spezialrollen.
- Die LLM-Rollen arbeiten auf 30m/1h oder auf Replay-Kandidaten, nicht im schnellen Tick-Hotpath.
- Die deterministische Engine bleibt immer pruefbar und reproduzierbar.

OpenAI/LLM-Rollen:

- Market Structure Analyst
- Momentum Analyst
- Risk Officer
- Skeptic / Bear Case
- Execution Coach
- CEO / Judge

Rollenziele:

- Market Structure Analyst prueft BOS, CHoCH, HH/LL, Range und Trendkontext.
- Momentum Analyst prueft RSI, MACD, EMA/HMA/VWAP und Volumenimpuls.
- Risk Officer prueft Fee/R, SL-Distanz, RR, Volatilitaet, Overtrading und offene Trades.
- Skeptic / Bear Case sucht aktiv Gruende gegen den Trade.
- Execution Coach prueft Entry-Art, Limit/Market-Qualitaet und ob der Trade zu spaet kommt.
- CEO / Judge fasst Rollenberichte zusammen und entscheidet `APPROVE`, `WAIT` oder `BLOCK`.

Bestehende technische Grundlagen:

- `agent_runtime_roles.py`
- `checks/check_agent_runtime_roles.py`
- Rollenvertrag fuer technische Agenten
- CEO-Rollenbewertung
- Volume als Kontext getrennt
- Risk / Volatility getrennt bewertet

## 2.2 Agenten-Setup im Dashboard

Das Agenten-Setup soll auf weniger, klarere Bereiche reduziert werden:

- Signalquellen
- OpenAI/LLM-Rollenteam
- Risiko / Economic Gate
- Replay / Learning

Signalquellen:

- RSI
- VWAP
- Volume
- MACD
- MFI
- Breakout / Fakeout
- BOS / CHoCH
- LL / HH Boxen
- Support / Resistance
- Swing Labels
- Volatility Regime
- Risk

Diese Quellen koennen weiterhin einzeln berechnet und visualisiert werden. Sie sollen aber nicht mehr als eigenstaendige Agenten im Sinne einer finalen Trade-Entscheidung auftreten.

OpenAI/LLM-Rollenteam:

- pro Rolle aktivierbar
- Provider konfigurierbar
- Modell konfigurierbar
- nur strukturierte Eingabedaten
- nur JSON-Ausgabe
- Timeout und Fallback Pflicht
- keine API-Schluessel im Prompt
- keine Order-Ausfuehrung durch LLM

## 2.3 Rollen-Verarbeitung

Die Verarbeitung erfolgt in Stufen:

```text
Signalquellen
-> Kandidaten-Engine
-> Rollen-Kontextpaket
-> OpenAI/LLM-Rollenberichte
-> CEO / Judge
-> Economic Gate
-> Paper Trade
```

Jede Rolle bekommt ein kleines, maschinenlesbares Kontextpaket:

```json
{
  "asset": "BTCUSDT",
  "timeframe": "1h",
  "candidate": {
    "direction": "LONG",
    "entry": 77257.36,
    "sl": 77619.70,
    "tp": 77257.36,
    "rr": 1.6,
    "fee_to_risk": 0.18
  },
  "structure": {},
  "momentum": {},
  "risk": {},
  "memory": {}
}
```

Jede Rolle muss JSON liefern:

```json
{
  "role": "Risk Officer",
  "decision": "BLOCK",
  "confidence": 0.82,
  "reasons": ["Fee/R ist zu hoch fuer den geplanten SL."],
  "hard_block": true
}
```

## 2.4 CEO / Judge-Zielbild

CEO prueft:

- Rollenberichte
- Richtungskonsens
- Rollen-Konsens
- Rollen-Konflikte
- Hard-Blocks
- Mindestscore
- Mindest-Alignment
- Brain-Entscheidung
- Economic-Gate-Status

CEO / Judge erzeugt keine eigene Preislogik.

CEO / Judge darf:

- `APPROVE` geben
- `WAIT` geben
- `BLOCK` geben
- Rollenberichte zusammenfassen
- Konflikte erklaeren
- ein finales JSON-Ergebnis fuer Dashboard und Replay erzeugen

CEO / Judge darf nicht:

- Entry setzen
- Stop-Loss setzen
- Take-Profit setzen
- Positionsgroesse setzen
- Economic Gate umgehen
- Live-Trading freigeben

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
- einklappbare Signalquellen- und Rollenbereiche
- kompakte CEO/Judge-Zusammenfassung
- OpenAI/LLM-Rollenberichte sichtbar
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

Kein Signal, kein OpenAI/LLM-Agent, kein CEO/Judge, kein Brain und keine Audit-Schicht darf diese Stufe umgehen.

# --------------------------------------------------
# 6. OpenAI/LLM Rollen-Team
# --------------------------------------------------

Die OpenAI/LLM-Schicht soll als kleines Rollen-Team arbeiten.

Sie bewertet nur vorberechnete, strukturierte Kandidaten. Sie ersetzt keine Indikatorberechnung, keine Preislogik und kein Economic Gate.

Ziel:

- weniger einzelne Indikator-Agenten in der Bedienung
- klare Spezialrollen statt kleinteiliger Schalter
- bessere Begruendung von `APPROVE`, `WAIT` und `BLOCK`
- Replay-faehige Rollenberichte
- OpenAI-Anbindung als optionaler Review-Layer fuer 30m/1h oder manuelle Kandidaten

Erlaubt:

- Signalquellen zusammenfassen
- Rollenberichte erzeugen
- Konflikte erklaeren
- CEO/Judge-Gesamtbewertung sprachlich und maschinenlesbar beschreiben
- Brain-Entscheidung erklaeren
- Memory-Kontext lesbar machen
- Risiko-Hinweise erzeugen
- Dashboard-Texte verbessern
- Replay-Kandidaten bewerten
- Bear-Case gegen einen Trade formulieren

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

Pflichtanforderungen:

- Rollen antworten als JSON.
- Rollen haben feste Systemprompts.
- Jede Rolle hat Timeout, Retry-Limit und Fallback.
- Bei LLM-Fehler laeuft die deterministische Pipeline weiter.
- API-Schluessel werden nie an Rollenprompts uebergeben.
- Das finale CEO/Judge-Ergebnis wird fuer Replay und Dashboard gespeichert.

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

## Abschnitt 2: OpenAI/LLM-Rollenteam aufbauen

Status:

- geplant

Ziel:

- technische Indikator-Agenten zu Signalquellen degradieren
- OpenAI/LLM-Rollen als Review-Team einfuehren
- Rollenberichte als JSON speichern
- CEO/Judge als finale Rollen-Zusammenfassung nutzen
- Dashboard auf wenige Rollenbereiche reduzieren
- Replay mit Rollenentscheidungen auswertbar machen

Bestehende Vorarbeit:

- Rollenvertrag technisch ergaenzt
- CEO-Rollenbewertung vorbereitet
- Kontext-Rolle fuer Volume ergaenzt
- Risk/Volatility getrennt von Momentum bewertet
- lokale Rollenpruefung ergaenzt
- Dashboard-Rollenpatch vorbereitet
- technische Dashboard-Rollenoptik umgesetzt
- Agenten-Setup in Chart-/Struktur-/Bewertungsbereiche getrennt

Offen:

- `llm_roles.py` oder gleichwertiges Rollenmodul erstellen
- OpenAI Provider-Konfiguration ergaenzen
- Rollenprompts fuer Structure, Momentum, Risk, Skeptic, Execution und CEO/Judge definieren
- JSON-Schema fuer Rollenberichte pruefen
- Replay-Kandidaten durch Rollen-Team laufen lassen
- altes Agenten-Setup in Signalquellen / LLM-Team / Risiko / Replay gliedern
- einzelne Indikator-Agenten aus der finalen Entscheidungs-UI entfernen

## Abschnitt 3: CEO/Judge-Bewertung verbessern

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

- CEO/Judge auf Rollenberichte statt Agentenmehrheit ausrichten
- `APPROVE` / `WAIT` / `BLOCK` optisch final trennen
- Hard-Blocks von Risk Officer und Skeptic sichtbar machen
- finale Entscheidung im Replay speichern

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
