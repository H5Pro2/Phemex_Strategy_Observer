# ==================================================
# AKTUELLER STAND – MCM TRADING BRAIN
# ==================================================

Dieses Dokument beschreibt den **aktuellen realen Ist-Zustand** des Systems.

Es trennt sauber zwischen:

- **bereits fix im Code umgesetzt**
- **fachlich ausgearbeitet, aber noch nicht vollständig im Code verhärtet**
- **nächsten konkreten Ausbauschritten**

Der Bauplan steht weiter in `UMSETZUNGSPLAN.md`.
Dieses Dokument beschreibt den **realen Umsetzungsstand nach heutigem Stand**. 

---

# --------------------------------------------------
# 1. Gesamtstatus
# --------------------------------------------------

Das Projekt ist **nicht mehr** in einer frühen Fix- oder Basisphase.

Die Kernbasis steht bereits im Code:

- äußere Wahrnehmung ist vorhanden
- innere Runtime ist vorhanden
- Entscheidungstendenz ist vorhanden
- technische Handlungsbahn ist vorhanden
- Episode / Review / Experience sind vorhanden
- Persistenz für Memory- und Runtime-Zustände ist vorhanden

Die Hauptarbeit liegt damit **nicht mehr in der Einführung der Grundmechanik**,
sondern im **Architektur-Endausbau und in der Experience-Vertiefung**. 

---

# --------------------------------------------------
# 2. Bereits fix umgesetzt
# --------------------------------------------------

# --------------------------------------------------
# 2.1 Ebene 1 – äußeres Wahrnehmen
# --------------------------------------------------

Ebene 1 ist als eigenständige Wahrnehmungsbasis real vorhanden.

Bereits produktiv vorhanden:

- `candle_state`
- `tension_state`
- `visual_market_state`
- `structure_perception_state`

Die Wahrnehmung wird aus Marktdaten / `window` aufgebaut
und als neutrales Wahrnehmungspaket weitergegeben. 

### Fachliche Bedeutung

Die Außenwelt ist nicht mehr nur einfache Signalquelle,
sondern bereits mehrschichtig beschrieben als:

- Candle-Zustand
- Spannungszustand
- äußere Marktform
- Struktur-Wahrnehmung

Damit ist Ebene 1 real vorhanden und nicht mehr nur geplant. 

---

# --------------------------------------------------
# 2.2 Ebene 2 – inneres Wahrnehmen / Denken / Handeln
# --------------------------------------------------

Ebene 2 ist bereits als laufende innere Runtime-Schicht vorhanden.

Bereits real vorhanden:

- `MCMBrainRuntime`
- Runtime-Snapshot
- Runtime-Decision-State
- Runtime-Brain-Snapshot
- Runtime-Marktimpuls-Verarbeitung
- Runtime-Idle-Followup

Die innere Zustandskette ist angelegt und im Codepfad vertreten:

- `outer_visual_perception_state`
- `inner_field_perception_state`
- `perception_state`
- `processing_state`
- `felt_state`
- `thought_state`
- `meta_regulation_state`
- `expectation_state` 

### Entscheidungstendenz

Die Handlung entsteht bereits nicht mehr direkt aus einem simplen Signal.

Vorhanden ist eine vorgelagerte Entscheidungstendenz:

- `act`
- `observe`
- `hold`
- `replan`

Erst danach folgt die technische Handlungsbahn. 

### Technische Handlungsbahn

Weiterhin aktiv vorhanden:

- Pending
- Entry
- Position
- Exit

Die technische Mechanik ist damit bereits an die innere Zustandslogik gekoppelt. 

---

# --------------------------------------------------
# 2.3 MCM-Zustandsraum
# --------------------------------------------------

Der MCM-Zustandsraum ist bereits teilweise explizit lesbar.

Vorhanden sind reale Zustandsachsen wie:

- `field_density`
- `field_stability`
- `regulatory_load`
- `action_capacity`
- `recovery_need`
- `survival_pressure`

Diese Größen laufen bereits durch Runtime-, Decision- und Snapshot-Strukturen. 

### Fachliche Bedeutung

Die Zielidee,
den Innenraum des Systems explizit lesbar zu machen,
ist bereits begonnen und produktiv im Code vertreten. :contentReference[oaicite:8]{index=8}

---

# --------------------------------------------------
# 2.4 Ebene 3 – Entwicklung aus Erfahrung
# --------------------------------------------------

Die Entwicklungsebene ist bereits substanziell umgesetzt.

Vorhanden sind:

- `mcm_decision_episode`
- `mcm_decision_episode_internal`
- `mcm_experience_space`
- `outcome_decomposition`
- Review-Logik
- Signature-Memory
- Context-Cluster
- persistenter Memory-State
- In-Trade-Update-Auswertung
- Experience-Linking
- Similarity-/Axis-/Drift-/Reinforcement-Ansätze 

### Nicht-Handlung ist integriert

Nicht-Handlung ist nicht mehr nur Sonderfall,
sondern realer Teil des Episoden- und Experience-Flusses:

- `observed_only`
- `withheld`
- `replanned`
- `abandoned` 

### Zustandsdelta ist integriert

Episode / Experience führen bereits:

- `state_before`
- `state_after`
- `state_delta`

Damit ist die Kopplung von Handlung / Nicht-Handlung und Zustandsveränderung bereits real umgesetzt. 

---

# --------------------------------------------------
# 2.5 Persistenz
# --------------------------------------------------

Persistenz ist vorhanden für:

- `signature_memory`
- `context_clusters`
- `mcm_runtime_snapshot`
- `mcm_runtime_decision_state`
- `mcm_runtime_brain_snapshot`
- `mcm_decision_episode`
- `mcm_experience_space`
- weitere Memory-Zustände

Damit kann der Bot relevante Langzeitanteile seines Zustandsraums halten. :contentReference[oaicite:12]{index=12}

---

# --------------------------------------------------
# 3. Was heute fachlich zusätzlich klar ausgearbeitet wurde
# --------------------------------------------------

Heute wurde die Entwicklungsrichtung von Ebene 3 fachlich deutlich geschärft.

Wichtig:
Dieser Teil ist **inhaltlich ausgearbeitet**,
aber **noch nicht vollständig in dieser Tiefe im Code umgesetzt**.

---

# --------------------------------------------------
# 3.1 Tragfähigkeit als zentrale Bewertungsgröße
# --------------------------------------------------

Experience soll nicht primär bewerten:

- Profit
- Trefferquote
- klassische Trade-Kennzahlen

Sondern:

- wie tragfähig eine Situation für das System war
- wie viel innere Reibung sie erzeugt hat
- ob Handlung in dieser Situation effizient tragbar war

Damit verschiebt sich die Experience-Bewertung fachlich von:

- Ergebnisbewertung

zu:

- Tragfähigkeitsbewertung

---

# --------------------------------------------------
# 3.2 Lernen als Umgangsfähigkeit
# --------------------------------------------------

Das System soll nicht lernen:

- was abstrakt „richtig“ ist
- wie man maximal aggressiv tradet

Sondern:

- womit es gut umgehen kann
- in welchen Situationen es handlungsfähig bleibt
- welche Struktur-Zustands-Kombinationen effizient tragbar sind

Lernen bedeutet damit:

- effizienter mit Situationen umgehen können
- nicht einfach mehr handeln

---

# --------------------------------------------------
# 3.3 Energie / Reibung / Kohärenz
# --------------------------------------------------

Der Nullpunkt der MCM bedeutet fachlich nicht:

- Stillstand
- Inaktivität
- Handlungsunfähigkeit

Sondern:

- hohe Kohärenz mit der Umwelt
- geringe innere Reibung
- geringe energetische Belastung
- hohe Energieeffizienz bei aktiver Interaktion

Abweichung vom Zentrum bedeutet:

- mehr Reibung
- mehr regulatorische Last
- mehr Unsicherheit
- mehr Energieverbrauch

Kohärenz bedeutet:

- passendere Wahrnehmung
- passendere Handlung
- geringere innere Kosten

---

# --------------------------------------------------
# 3.4 Erfahrungscluster
# --------------------------------------------------

Experience soll fachlich stärker als Cluster-System gedacht werden.

Cluster repräsentieren nicht nur ähnliche Datenlagen,
sondern:

- Typen von Situationen
- wiederkehrende Struktur-Zustands-Muster
- deren Tragfähigkeit für das System

Damit wird aus Experience fachlich:

- nicht nur Verlaufsspeicherung
- sondern Erfahrungsraum über tragfähige Umgangsformen

---

# --------------------------------------------------
# 3.5 Outcome als Zustandswirkung
# --------------------------------------------------

Outcome soll fachlich nicht als Geldzahl wirken,
sondern als Veränderung im Innenraum.

Beispiel:

- Gewinn -> Entlastung / Stabilisierung / evtl. Euphorie
- Verlust -> Belastung / Rückzug / Recovery-Bedarf

Wichtig:

- positive Wirkung darf nicht blind verstärken
- Euphorie ist nicht automatisch Stabilität
- Verlust ist nicht nur schlecht, sondern regulatorisches Feedback

---

# --------------------------------------------------
# 4. Was davon bereits technisch vorbereitet ist
# --------------------------------------------------

Für diese heutige Vertiefung gibt es bereits reale technische Anknüpfungspunkte im Code:

- `context_clusters`
- `signature_memory`
- `mcm_experience_space`
- `similarity_axes`
- `drift`
- `reinforcement`
- `attenuation`
- `review_score`
- `structural_bearing_quality`
- `observation_quality`
- `decision_path_quality`
- `state_before / state_after / state_delta` 

### Einordnung

Das bedeutet:

- die **Richtung ist technisch vorbereitet**
- die **heutige Experience-Vertiefung ist anschlussfähig**
- aber die **volle fachliche Interpretation als Tragfähigkeits- und Energie-System ist noch nicht komplett ausformuliert bzw. verhärtet**

---

# --------------------------------------------------
# 5. Was noch nicht fertig ist
# --------------------------------------------------

# --------------------------------------------------
# 5.1 KPI / Auswertung
# --------------------------------------------------

Der KPI-/Nachweisbereich ist noch stark von der alten Trade-Welt geprägt.

Aktiv vorhanden sind noch klassische Kennzahlen wie:

- `pnl_netto`
- `pnl_tp`
- `pnl_sl`
- `equity_peak`
- `max_drawdown_abs`
- `max_drawdown_pct`
- `winrate`
- `profit_factor`
- `expectancy` :contentReference[oaicite:14]{index=14}

Diese Größen sind als Hauptbewertung für die Zielarchitektur nicht mehr passend
und müssen später zurückgebaut oder umgeordnet werden.

---

# --------------------------------------------------
# 5.2 GUI / Visualisierung
# --------------------------------------------------

Die GUI-Ausgabeschicht liest aktuell noch stark alte Nachweisstrukturen:

- `trade_stats.json`
- `trade_equity.csv`

Auch die Equity-/PnL-Darstellung ist noch vorhanden. :contentReference[oaicite:15]{index=15}

Hier fehlt später die saubere neue Darstellung von:

- Außenwelt
- Innenwelt
- Zustandsachsen
- Experience-/Tragfähigkeitsverlauf

---

# --------------------------------------------------
# 5.3 Experience-Vertiefung
# --------------------------------------------------

Die heutige Vertiefung ist fachlich ausgearbeitet,
aber noch nicht vollständig als klare technische Logik durchgezogen.

Noch offen ist insbesondere:

- Tragfähigkeit als explizite Bewertungsgröße
- Lernen als Umgangsfähigkeit
- Reibung / Energie als Experience-Kosten
- Cluster-Bewertung über Tragfähigkeit statt Ergebnis
- stärkere Entkopplung von Profitlogik

---

# --------------------------------------------------
# 5.4 Tests
# --------------------------------------------------

Dedizierte Tests fehlen weiterhin insbesondere für:

- `bot_gate_funktions.py`
- `mcm_core_engine.py` :contentReference[oaicite:16]{index=16}

---

# --------------------------------------------------
# 6. Nächste Schritte
# --------------------------------------------------

# --------------------------------------------------
# 6.1 PRIO 2 – Experience / Review vertiefen
# --------------------------------------------------

Nächster sinnvoller Hauptblock ist:

- Experience fachlich von Ergebnisbewertung auf Tragfähigkeitsbewertung schärfen
- Zustandswirkung von Outcome sauberer formulieren
- Cluster stärker als Erfahrungsräume nutzen
- Lernen explizit als Umgangsfähigkeit modellieren

---

# --------------------------------------------------
# 6.2 PRIO 2 – Runtime / Architektur weiter trennen
# --------------------------------------------------

Weiter zu schärfen:

- Ebene 1 = reine Wahrnehmung
- Ebene 2 = reiner Innenprozess
- Ebene 3 = reine Entwicklung / Experience

Ziel:

- weniger Vermischung von Runtime und Bot-State
- klarere strukturelle Trennung der Ebenen

---

# --------------------------------------------------
# 6.3 PRIO 3 – KPI umbauen
# --------------------------------------------------

Später umzubauen:

- weg von PnL als zentraler KPI
- hin zu Zustands- und Tragfähigkeitsmetriken

Beispiele für spätere neue Bewertungsgrößen:

- Zustandsstabilität
- Handlungsfähigkeit
- regulatorische Last
- Regeneration
- Tragfähigkeit je Strukturfeld

---

# --------------------------------------------------
# 6.4 PRIO 3 – Visualisierung umbauen
# --------------------------------------------------

Später aufzubauen:

- getrennte Sicht auf Außenwelt und Innenwelt
- Chart + Wahrnehmungszustände
- Innenraum mit Zustandsachsen
- Experience-/Cluster-/Tragfähigkeitsdarstellung

---

# --------------------------------------------------
# 6.5 PRIO 4 – Tests
# --------------------------------------------------

Danach:

- dedizierte Tests für Kernpfade
- Fokus auf Zustandsentwicklung
- Fokus auf Wahrnehmungs- und Runtime-Konsistenz
- Fokus nicht auf klassischen Trade-Erfolg

---

# --------------------------------------------------
# 7. Fazit
# --------------------------------------------------

Der reale Stand des Projekts ist:

- Kernmechanik steht
- Wahrnehmung steht
- Runtime steht
- Experience steht
- Persistenz steht

Der nächste Hauptschritt ist **nicht mehr Basis-Fixerei**,
sondern:

- **Architektur-Endausbau**
- **Experience-/Tragfähigkeits-Vertiefung**
- **später KPI-/GUI-Neuausrichtung**. 