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

Ziel:

- README auf Agentensystem ausrichten
- Bauplan provider-neutral machen
- Ollama-Fokus entfernen
- Sicherheitsdateien absichern

## Abschnitt 2: Agentenrollen schaerfen

Ziel:

- Agenten klar in Struktur, Momentum, Risiko, Kontext und Audit gruppieren
- Score-Bedeutung je Rolle vereinheitlichen
- Offline-/Weak-/Strong-Qualitaet sauber sichtbar machen

## Abschnitt 3: CEO-Bewertung verbessern

Ziel:

- Rollen-Konsens staerker bewerten
- Konflikte nicht nur zaehlen, sondern gewichten
- Blocking-Regeln transparent anzeigen
- WAIT / BLOCKED / BIAS besser trennen

## Abschnitt 4: Brain verbessern

Ziel:

- Pattern-Key stabilisieren
- Memory-Matches asset-spezifisch nutzbarer machen
- Entry-Fallbacks sichtbarer machen
- Confidence nachvollziehbarer berechnen

## Abschnitt 5: Replay-Regeln verbessern

Ziel:

- Regeln aus Replay-History robuster gewichten
- Mindestdatenmenge beruecksichtigen
- Overfitting-Schutz einbauen
- Asset- und Timeframe-Kontext einbeziehen

## Abschnitt 6: Dashboard verbessern

Ziel:

- Layout konsolidieren
- Bedienung vereinfachen
- Popups reduzieren
- wichtige Entscheidungen nach oben holen
- mobile/kleine Ansicht verbessern

# --------------------------------------------------
# 7. Offene Punkte
# --------------------------------------------------

- Agenten-Gewichtung weiter vereinheitlichen
- CEO-Entscheidung besser visualisieren
- Replay-Regeln robuster auswerten
- Dashboard-Design weiter komprimieren
- Chart-Settings getrennt nach Kerzenkoerper und Docht pruefen
- Laufzeitdaten aus Repository fernhalten
