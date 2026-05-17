# BAUPLAN: Trading Bot Agent System

Stand: 2026-05-17

# --------------------------------------------------
# 1. System-Ist-Zustand
# --------------------------------------------------

## 1.1 Was dieses System ist

Dieses System ist ein lokales Trading-Agentensystem fuer Marktbeobachtung, Paper-Trading und Entscheidungsanalyse.

Der Bot ist aktuell als Observer- und Paper-Trading-System aufgebaut.

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

Der Bot ist kein Live-Trading-System.

Live-Trading bleibt gesperrt.

## 1.2 Aktuelle Pipeline

```text
Agenten
→ CEO Trader Gesamtbewertung
→ Brain / Lernschicht Entry-Optimierung
→ Economic Gate
→ Paper Trade
```

Bedeutung:

- Agenten lesen Indikator-, Kerzen- und Kontextdaten.
- Jeder Agent bewertet seine eigene Datenquelle eigenstaendig.
- CEO kontrolliert die Gesamtlage aller Agenten.
- Brain erzeugt und optimiert daraus einen Trade-Kontext.
- Replay-Regeln koennen Pattern-Kombinationen gewichten.
- Economic Gate bleibt harte wirtschaftliche Sperre.
- PaperBroker fuehrt nur Paper-Trades aus.

## 1.3 Repository-Stand

Repository-Regeln wurden bereinigt.

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

## 1.4 Start-Stand

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
- Dashboard-Patch-Version verifiziert
- Agenten-Rollenvertrag gueltig
- Brain-/Replay-Erweiterung gueltig
- Python-Abhaengigkeiten installierbar
- Bot-Start ohne Fehler

## 1.5 Technischer Rollenstand

Umgesetzt:

- `agent_runtime_roles.py`
- `check_agent_runtime_roles.py`
- `dashboard_agent_roles_patch.js`
- `prepare_dashboard_runtime.py`

Technische Rollen:

- Struktur
- Momentum
- Kontext
- Risiko
- Entscheidung
- Weitere

Die Rollenpruefung laeuft vor dem Start ueber `start_bot.ps1` und `start_bot.bat`.

## 1.6 Dashboard-Optik-Stand

Aktuelle Dashboard-Patch-Version:

- `role-ui-v3-tech`

Umgesetzt:

- professionelle technische Darstellung
- kompaktere Agentenkarten
- kleinere Schriftgroessen
- Monospace-Werte fuer technische Kennzahlen
- weniger Rundungen
- reduzierte Badge-Optik
- klare Statuskanten fuer LONG / SHORT / NEUTRAL / Konflikt
- kompaktere CEO-, Prioritaets- und Konfliktbereiche
- mobile Darstellung erhalten

`prepare_dashboard_runtime.py` ersetzt vorhandene Patch-Bloecke und prueft, ob die aktuelle Patch-Version eingebettet wurde.

## 1.7 Brain-/Replay-Stand

Umgesetzt:

- `brain_replay_enhancements.py`
- `check_brain_replay_enhancements.py`
- automatische Einbindung ueber `sitecustomize.py`
- Startpruefung ueber `start_bot.ps1`
- Startpruefung ueber `start_bot.bat`

Verbessert:

- stabilerer Pattern-Key `v2`
- rollenbasierter Pattern-Key
- Memory-Matching auf stabile Pattern-Keys vorbereitet
- robustere Replay-Regelgewichtung
- Asset-spezifische Replay-Regeln bevorzugt
- Edge-Score aus Winrate, AvgR und Profit-Factor
- Mindestdatenmenge wird staerker abgesichert
- GOOD/BAD-Regeln werden nicht blind uebernommen

# --------------------------------------------------
# 2. Zielbild
# --------------------------------------------------

## 2.1 Agenten-Mechanik

Jeder Agent soll eine klare Rolle haben.

Rollen:

- Struktur
- Momentum
- Risiko
- Kontext
- Audit
- Entscheidung

Jeder Agent liefert:

- Signal
- Score
- gelesene Daten
- Begruendung
- Konfliktstatus
- Blocking-Status
- Qualitaetsprofil

Kein Agent entscheidet alleine ueber einen Trade.

## 2.2 CEO Trader

Der CEO bewertet alle Agentenberichte gemeinsam.

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

## 2.3 Brain / Lernschicht

Das Brain wertet Agentenkombinationen, Pattern-Keys und Paper-Trade-Ergebnisse aus.

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

## 2.4 Replay-Regeln

Replay-Regeln sollen nicht nur angezeigt, sondern sinnvoll gewichtet werden.

Ziel:

- starke Pattern-Kombinationen bevorzugen
- schwache Pattern-Kombinationen abwerten
- Asset-spezifische Unterschiede erkennen
- Mindestanzahl an Beispielen beruecksichtigen
- Winrate und AvgR gemeinsam bewerten
- Overfitting vermeiden

Replay-Regeln duerfen keine harte Sperre sein, solange sie nicht eindeutig als Blocking-Regel konfiguriert sind.

## 2.5 Economic Gate

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
# 3. Lokale Audit-Schicht
# --------------------------------------------------

## 3.1 Rolle

Die lokale Audit-Schicht soll Entscheidungen erklaeren, nicht treffen.

Sie ist ein optionaler Auswerter fuer Sprache, Konflikte und Risiko-Hinweise.

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

## 3.2 Provider-Neutralitaet

Der Bauplan ist nicht auf einen bestimmten Provider festgelegt.

Moegliche lokale Provider:

- Ollama
- anderer lokaler HTTP-Provider
- spaeter eigene regelbasierte Audit-Schicht

Wichtig:

Der Provider ist austauschbar. Die Kernlogik bleibt Agenten → CEO → Brain → Economic Gate.

## 3.3 Zielausgabe

Die Audit-Schicht soll kurze strukturierte Hinweise liefern.

Zielausgabe:

- `enabled`
- `provider`
- `model`
- `role`
- `verdict`
- `confidence_note`
- `risk_note`
- `conflict_note`
- `advice`
- `block_hint`

Erlaubte Verdicts:

- `OK`
- `WARN`
- `BLOCK_HINT`
- `NO_DATA`
- `ERROR`

`BLOCK_HINT` ist nur ein Hinweis.

# --------------------------------------------------
# 4. Datenfluss
# --------------------------------------------------

## 4.1 Eingabe an die Audit-Schicht

Erlaubte Eingabedaten:

- Symbol
- Timeframe
- Agenten-Signale
- Agenten-Scores
- Konfliktstatus
- Brain-Entscheidung
- Brain-Score
- Memory-Match Count
- Memory Winrate
- Memory AvgR
- Candidate vorhanden ja/nein
- Economic-Gate-Ergebnis
- Gate-Reason

Nicht erlaubte Eingabedaten:

- API-Key
- API-Secret
- `.env` Inhalte
- private Accountdetails
- private Orderrechte

## 4.2 Verarbeitung

Geplanter Ablauf:

1. Agenten erzeugen Reports.
2. CEO bewertet die Gesamtlage.
3. Brain erzeugt Entry-Kontext und optional Candidate.
4. Replay-Regeln werden gewichtet.
5. Economic Gate prueft harte Wirtschaftlichkeit.
6. Audit-Schicht erzeugt optional kurze Hinweise.
7. Dashboard zeigt Entscheidung, Konflikte und Hinweise.
8. PaperBroker erstellt nur bei bestehender Freigabe einen Paper-Trade.

# --------------------------------------------------
# 5. Dashboard-Zielbild
# --------------------------------------------------

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

Wichtige Bereiche:

- Status
- Chart
- Agenten
- CEO
- Brain
- Replay
- Economic Gate
- Paper Trades
- Settings

# --------------------------------------------------
# 6. Naechste Ausbaustufen
# --------------------------------------------------

## Abschnitt 1: Dokumentation bereinigen

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
- `start_bot.bat` erweitert
- `start_bot.ps1` hinzugefuegt
- README um Startdateien erweitert

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

Offen:

- Dashboard-Agentenkarten nach echtem Test weiter feinjustieren
- Rollenanzeige in bestehende Haupt-HTML dauerhaft integrieren

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

## Abschnitt 6: Dashboard verbessern

Status:

- teilweise umgesetzt

Umgesetzt:

- technische Agentenoptik vorbereitet
- kompaktere Agentenkarten
- kompaktere CEO-/Prioritaetsbereiche
- kompaktere Konfliktmatrix
- mobile Darstellung beruecksichtigt

Offen:

- Hauptlayout weiter konsolidieren
- Einstellungen uebersichtlicher gruppieren
- Popups reduzieren
- wichtige Entscheidungen noch staerker nach oben holen

# --------------------------------------------------
# 7. Offene Punkte
# --------------------------------------------------

- direkte Python-Startpruefung bei fehlender `config.json` verbessern
- Dashboard-Agentenkarten nach echtem Test feinjustieren
- CEO-Entscheidung besser visualisieren
- Replay-Regeln im Dashboard sichtbarer machen
- Dashboard-Design weiter konsolidieren
- Chart-Settings getrennt nach Kerzenkoerper und Docht pruefen
