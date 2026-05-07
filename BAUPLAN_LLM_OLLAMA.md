# BAUPLAN: Phemex Strategy Observer mit lokaler Ollama-/LLM-Schnittstelle

Stand: 2026-05-07

# --------------------------------------------------
# 1. System-Ist-Zustand
# --------------------------------------------------

## 1.1 Was dieses System ist

Dieses System ist ein lokaler Phemex Strategy Observer fuer die Liquiditaets-Sweep-Strategie.

Der Bot ist aktuell als Beobachtungs- und Paper-Trading-System aufgebaut.

Kernaufgabe:

- Phemex-Kerzen laden
- Market-Structure-Indikatoren berechnen
- Agentenberichte erzeugen
- Brain-/Lernschicht auswerten
- CEO-Kontrolle anwenden
- Economic Gate pruefen
- Paper-Trades verwalten
- Lernspeicher aus abgeschlossenen Paper-Trades fortschreiben
- Dashboard fuer Status, Chart, Agenten und Einstellungen bereitstellen

Der Bot ist kein Live-Trading-System.

Live-Trading bleibt im vorhandenen Regelwerk gesperrt.

## 1.2 Aktuelle Pipeline

Die vorhandene Pipeline lautet:

Agenten  
→ Brain / Lernschicht  
→ CEO Trader  
→ Economic Gate  
→ Paper Trade

Bedeutung:

- Agenten lesen Indikator- und Kerzendaten.
- Brain erzeugt daraus eine Handelsentscheidung bzw. einen Trade-Kandidaten.
- CEO kontrolliert Brain-Entscheidung und Konflikte.
- Economic Gate bleibt harte wirtschaftliche Sperre.
- PaperBroker fuehrt nur Paper-Trades aus.

## 1.3 Aktuelle LLM-Vorbereitung

Im aktuellen Code existiert bereits eine vorbereitete LLM-Schicht.

Ist-Zustand:

- `brain_runtime.py` enthaelt `_llm_learning_layer`.
- `brain_llm_layer_enabled` existiert in `config.json` und `config.example.json`.
- Dashboard / Agent Settings enthalten bereits einen Schalter fuer die LLM-Lernschicht.
- Der aktuelle LLM-Modus ist nur Interface / Audit-Text.
- Ohne konfigurierten lokalen Provider wird kein externer Call ausgefuehrt.

Aktuelle Bewertung:

Die Struktur ist geeignet, um Ollama spaeter sauber einzubinden, ohne die bestehende Trade-Logik zu zerstoeren.

# --------------------------------------------------
# 2. Was das System aktuell koennen soll
# --------------------------------------------------

## 2.1 Marktbeobachtung

Das System soll Phemex-Kerzendaten fuer konfigurierte Assets laden.

Aktive Faehigkeiten:

- Single-Asset- und Multi-Asset-Modus
- Phemex-Polling getrennt von interner System-Loop
- Chart-Daten fuer Dashboard
- Watchlist-Assets
- Statusspeicherung

## 2.2 Indikator- und Struktur-Auswertung

Das System soll Marktstruktur berechnen und sichtbar machen.

Aktive Bausteine:

- BOS / CHoCH
- LL / HH Boxen
- HH / LH / HL / LL Labels
- HMA
- SMA
- Triple EMA
- MFI
- Volume-Kontext
- dynamische Support-/Resistance-Level

## 2.3 Agenten-System

Jeder Agent soll genau eine Perspektive auswerten.

Jeder Agent liefert:

- Signal
- Score
- gelesene Daten
- Rueckmeldung
- Konfliktstatus
- optional Blocking

Agenten entscheiden keinen Trade alleine.

## 2.4 Brain / Lernschicht

Das Brain soll Agentenkombinationen mit gespeicherter Paper-Erfahrung abgleichen.

Das Brain optimiert:

- Richtung
- Entry-Kandidat
- Entry-Offset in Strukturboxen
- SL-Kandidat
- TP-Kandidat
- Pattern-Key
- Confidence

## 2.5 CEO Trader

Der CEO Trader soll keine eigene Preislogik erzeugen.

Der CEO soll pruefen:

- Agentenkonflikte
- Brain-Score
- Mindest-Alignment
- Memory-Kontext
- Trade-Plan

## 2.6 Economic Gate

Das Economic Gate bleibt harte Sperre.

Es prueft:

- Preisgeometrie
- Risk / Reward
- Mindest-RR
- Mindest-Netto-Profit
- Gebuehren
- Positionsgroesse

Kein LLM darf diese Stufe umgehen.

# --------------------------------------------------
# 3. Zielbild: Endform mit Ollama / kleinem lokalem LLM
# --------------------------------------------------

## 3.1 Rolle von Ollama

Ollama soll als lokale LLM-Schnittstelle eingebunden werden.

Das LLM soll kein Trader sein.

Das LLM soll ein lokaler Trade-Auditor sein.

Aufgabe:

- Agentenberichte zusammenfassen
- Konflikte erkennen und erklaeren
- Brain-Entscheidung sprachlich bewerten
- Memory-Kontext erklaeren
- Risiko-Hinweis erzeugen
- WAIT / BLOCKED / APPROVED nachvollziehbarer machen
- Dashboard-Text fuer Menschen verbessern

## 3.2 Was Ollama ausdruecklich nicht tun darf

Ollama darf nicht:

- Entry-Preis setzen
- Stop-Loss setzen
- Take-Profit setzen
- Positionsgroesse setzen
- Economic Gate umgehen
- Live-Trading freigeben
- Phemex-Orders ausloesen
- API-Schluessel lesen
- private `.env`-Daten erhalten
- deterministische Preislogik ersetzen

## 3.3 LLM-Ausgabe in der Endform

Die Ollama-Schicht soll eine kleine, streng begrenzte Antwort liefern.

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

Wichtig:

`BLOCK_HINT` ist nur ein Hinweis fuer Brain / CEO.

Die harte Sperre bleibt weiterhin im vorhandenen Code und im Economic Gate.

# --------------------------------------------------
# 4. Geplanter Datenfluss mit Ollama
# --------------------------------------------------

## 4.1 Eingabe an Ollama

Ollama bekommt nur reduzierte, sichere Daten.

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
- Economic-Gate-Ergebnis ja/nein
- Gate-Reason

Nicht erlaubte Eingabedaten:

- API-Key
- API-Secret
- `.env` Inhalte
- rohe Accountdaten mit sensiblen Details
- private Orderrechte

## 4.2 Verarbeitung

Geplanter Ablauf:

1. Agenten erzeugen Reports.
2. Brain erzeugt Score, Richtung und optional Candidate.
3. `_llm_learning_layer` baut einen reduzierten Audit-Kontext.
4. Ollama bewertet diesen Kontext lokal.
5. LLM-Antwort wird als Zusatzinfo gespeichert.
6. CEO zeigt LLM-Hinweis im Agent Viewer.
7. Economic Gate bleibt entscheidend.
8. PaperBroker erstellt nur bei bestehender Freigabe einen Paper-Trade.

## 4.3 Ausgabe im Dashboard

Dashboard soll anzeigen:

- LLM aktiv / aus
- Modellname
- Verdict
- kurze Risiko-Notiz
- Konflikt-Notiz
- menschlich lesbare Begruendung

Dashboard soll nicht anzeigen:

- lange Prompts
- geheime Konfigurationswerte
- API-Secrets
- ungefilterte Rohdaten

# --------------------------------------------------
# 5. Zielarchitektur
# --------------------------------------------------

## 5.1 Bestandteile

### PhemexClient

Laedt Kerzendaten und optional Futures-Accountdaten.

### Indikator-Schicht

Berechnet Struktur, Linien, Boxen und Zusatzindikatoren.

### Agent Runtime

Macht aus Indikator- und Kerzendaten einzelne Agentenberichte.

### Brain Runtime

Berechnet Score, Pattern-Key, Memory-Match und Trade-Kandidat.

### Ollama Audit Layer

Bewertet vorhandene Reports lokal und erzeugt eine begrenzte textliche Zusatzbewertung.

### CEO Trader

Kontrolliert Brain- und LLM-Kontext, bleibt aber ohne eigene Preislogik.

### Economic Gate

Bleibt harte mathematische und wirtschaftliche Sperre.

### PaperBroker

Verwaltet Pending, Open, TP, SL und Expired Paper-Trades.

### Dashboard

Zeigt Bot-Zustand, Agenten, Chart, Memory, Gate und LLM-Audit an.

# --------------------------------------------------
# 6. Empfohlene Ollama-Konfiguration
# --------------------------------------------------

## 6.1 Neue Config-Werte in Zielversion

Empfohlene Parameter:

- `brain_llm_layer_enabled`
- `ollama_enabled`
- `ollama_base_url`
- `ollama_model`
- `ollama_timeout_seconds`
- `ollama_max_prompt_chars`
- `ollama_temperature`
- `ollama_block_hint_enabled`

## 6.2 Empfohlene Default-Werte

Empfohlene lokale Standard-Defaults:

- `brain_llm_layer_enabled`: `true`
- `ollama_enabled`: `true`
- `ollama_base_url`: `http://127.0.0.1:11434`
- `ollama_model`: `qwen2.5:3b`
- `ollama_timeout_seconds`: `60`
- `ollama_temperature`: `0.0`
- `ollama_max_prompt_chars`: `4000`
- `ollama_block_hint_enabled`: `false` am Anfang

## 6.3 Empfohlenes lokales Modell

Empfohlen fuer diesen Bot:

- `qwen2.5:3b`

Begruendung:

- Text-/JSON-Audit statt Bildverarbeitung
- kleines lokales Modell
- passend fuer kurze Agenten-, Brain- und Risiko-Zusammenfassungen

Vorhandenes Modell:

- `qwen2.5vl:3b` kann installiert bleiben
- Vision-Funktion wird fuer diesen Bauplan nicht benoetigt

# --------------------------------------------------
# 7. Umsetzung in Bauabschnitten
# --------------------------------------------------

## Abschnitt 1: Dokumentation und Schnittstellenvertrag

Ziel:

- festlegen, was Ollama darf
- festlegen, was Ollama nicht darf
- LLM-Ausgabeformat definieren
- Dashboard-Anzeige planen

Status:

- erledigt

## Abschnitt 2: Lokaler Ollama-Client

Ziel:

- kleine Provider-Funktion fuer lokalen Ollama-HTTP-Call
- Timeout
- Fehlerbehandlung
- keine externen APIs
- kein Zugriff auf `.env`

Betroffene Datei:

- `brain_runtime.py`

Status:

- erledigt

## Abschnitt 3: Config erweitern

Ziel:

- Ollama-Parameter in Config Defaults aufnehmen
- Werte ueber Public Config sichtbar machen
- Werte speicherbar machen

Betroffene Dateien:

- `config.json`
- `config.example.json`
- `phemex_strategy_observer.py`

Status:

- erledigt

## Abschnitt 4: Dashboard erweitern

Ziel:

- Modell / Provider anzeigen
- Ollama aktiv / aus anzeigen
- Verdict anzeigen
- Risiko- und Konflikthinweis anzeigen
- Ollama-Config im Agent Settings Fenster sichtbar und speicherbar machen

Betroffene Dateien:

- `dashboard.html`
- `dashboard_script.js`

Status:

- erledigt

## Abschnitt 5: Sicherheitsgrenzen testen

Ziel:

- LLM aus: bestehendes Verhalten bleibt gleich
- Ollama nicht erreichbar: Bot laeuft weiter
- LLM-Fehler: `ERROR`, aber keine Pipeline-Unterbrechung
- Economic Gate bleibt harte Sperre
- Paper-Trading bleibt Paper-Trading

Status:

- erledigt

Ergebnis:

- LLM deaktiviert erzeugt `NO_DATA` ohne Ollama-Call
- Ollama nicht erreichbar erzeugt `ERROR` ohne Pipeline-Abbruch
- ungueltige Ollama-Antwort erzeugt `WARN` ohne Pipeline-Abbruch
- Economic Gate bleibt harte Sperre und setzt `BLOCKED`
- LLM-Audit wird nach Economic-Gate-Pruefung erneut mit Gate-Daten aktualisiert
- Dashboard-Auditblock wurde layoutseitig korrigiert

# --------------------------------------------------
# 8. To-do / Fixliste
# --------------------------------------------------

## Erledigt

- Abschnitt 1: Dokumentation und Schnittstellenvertrag erstellt
- Abschnitt 2: Lokaler Ollama-Client in `brain_runtime.py` vorbereitet
- Abschnitt 3: Config-Werte fuer Ollama in `config.json`, `config.example.json` und `phemex_strategy_observer.py` aufgenommen
- Modellvorgabe auf `qwen2.5:3b` gesetzt
- Abschnitt 4: Dashboard-Anzeige fuer Ollama-Provider, Modell, Verdict und Hinweise erweitert
- UI-Felder fuer Ollama-Config im Agent Settings Fenster aufgenommen
- Abschnitt 5: Sicherheitsgrenzen getestet
- Test: LLM aus
- Test: Ollama nicht erreichbar
- Test: ungueltige Ollama-Antwort
- Test: Economic Gate bleibt harte Sperre
- Test: Paper-Trading bleibt Paper-Trading
- Fix: LLM-Audit bekommt Economic-Gate-Daten nachgereicht
- Fix: Dashboard-Auditblock nutzt volle Breite statt verschachtelter Grid-Spalte
- Fix: Ollama/LLM laeuft standardmaessig mit `brain_llm_layer_enabled=true` und `ollama_enabled=true`
- Fix: Ollama-Audit laeuft asynchron im Hintergrund-Thread und blockiert die Trading-Pipeline nicht
- Fix: Ollama-Audit erzwingt deutsche JSON-Antworten und verwirft CJK-Schriftzeichen
- Fix: Defekte LLM-Textfelder wie `-',` werden bereinigt und als leerer Hinweis behandelt

## Offen

- Ollama-Statuspruefung gegen lokal installierte Modelle
- Chart-Settings: getrennte Kerzenkoerper-/Dochtfarben umsetzen

## Fixliste

- Erledigt: UI-Felder fuer Ollama-Config sind im Agent Settings Fenster aufgenommen
- Erledigt: Dashboard zeigt LLM-Audit als eigenen sichtbaren Block
- Erledigt: Dashboard-Auditblock wurde auf volle Breite korrigiert
- Erledigt: Ollama-Audit wird nach Economic Gate mit Gate-Daten aktualisiert
- Erledigt: Standardbetrieb fuer lokales LLM aktiviert
- Erledigt: LLM-Audit nutzt Hintergrund-Thread; neue Daten werden nur nach freiem Worker im naechsten Tick uebergeben
- Erledigt: LLM-Audit antwortet nur deutsch/JSON; CJK-Schriftzeichen werden im Backend und Dashboard verworfen
- Erledigt: Kaputte LLM-Hinweisfelder wie `-',` werden im Backend und Dashboard auf `-` normalisiert
- Offen: Ollama-Statuspruefung gegen lokal installierte Modelle fehlt noch
- Offen: Chart-Settings brauchen getrennte Farbwerte fuer Kerzenkoerper und Docht
  - Body / Kerzenkoerper: Farbe separat einstellbar
  - Docht: Farbe separat einstellbar

# --------------------------------------------------
# 9. Sicherheitsregeln fuer die Endform
# --------------------------------------------------

## 9.1 Harte Regeln

- Live-Trading bleibt deaktiviert.
- Ollama bekommt keine Secrets.
- Ollama entscheidet keine Preise.
- Ollama erzeugt keine Orders.
- Ollama darf Economic Gate nicht ueberschreiben.
- Bei Timeout oder Fehler wird normal deterministisch weitergearbeitet.

## 9.2 Fail-Safe-Verhalten

Wenn Ollama ausfaellt:

- Bot stoppt nicht.
- Brain arbeitet weiter deterministisch.
- CEO bekommt LLM-Status `ERROR` oder `NO_DATA`.
- Paper-Trading bleibt nur von vorhandener Pipeline abhaengig.

# --------------------------------------------------
# 10. Endform des Systems
# --------------------------------------------------

Das Zielsystem ist ein lokaler, transparenter Paper-Trading-Observer mit Agenten, Brain, Memory, CEO, Economic Gate und optionaler lokaler LLM-Audit-Schicht.

Die Endform soll nicht versuchen, ein autonomer Live-Trading-Bot zu sein.

Die Endform soll ein kontrolliertes Analyse- und Lernsystem sein:

- deterministische Marktstruktur
- nachvollziehbare Agentenberichte
- Memory aus echten Paper-Ergebnissen
- harte wirtschaftliche Gate-Pruefung
- lokale LLM-Erklaerung ueber Ollama
- keine externe KI-Abhaengigkeit
- keine Live-Orderrechte

# --------------------------------------------------
# 11. Kurzfazit
# --------------------------------------------------

Ollama passt in dieses System als lokale Audit- und Erklaerschicht.

Ollama soll nicht das Gehirn ersetzen.

Das Gehirn bleibt der vorhandene Agent-/Brain-/CEO-/Gate-Code.

Die beste Zielrolle fuer Ollama ist:

Lokaler Risk- und Konflikt-Auditor fuer vorhandene Brain-Entscheidungen.
