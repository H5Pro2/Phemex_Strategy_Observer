# ==================================================
# FIX_LISTE.md (bereinigt)
# ==================================================

# --------------------------------------------------
# Beobachtung
# --------------------------------------------------

- PRIO 1 Kernumbau ist umgesetzt:
  - Zustandsdelta (`state_before / state_after / state_delta`)
  - Experience-Kopplung (Struktur × Zustand × Wirkung)
  - Nicht-Handlung integriert (`observe / replan / withheld`)
  - Wahrnehmung vollständig aus `window` ableitbar

- System befindet sich nicht mehr in der Fixphase,
  sondern im Architektur-Endausbau

# --------------------------------------------------
# Schlussfolgerung
# --------------------------------------------------

- PRIO 1 wird geschlossen
- Fokus liegt auf Architektur, Review-Verfeinerung und Tests


# ==================================================
# PRIO 2 – RUNTIME / ENTSCHEIDUNGSBAHN
# ==================================================

- Trenne strikt:
  - Ebene 1 = Wahrnehmung
  - Ebene 2 = Innenprozess
  - Entscheidungstendenz
  - technische Ausführung

- Runtime entkoppeln von:
  - Bot-State Vermischung
  - direkten Seiteneffekten

- Entscheidung:
  - zuerst intern (`act / observe / hold / replan`)
  - danach technische Umsetzung


# ==================================================
# PRIO 2 – REVIEW / EXPERIENCE
# ==================================================

- Tragfähigkeit als zentrale Bewertungsgröße etablieren:
  - Bewertung von Situationen nach Belastung / Entlastung
  - Bewertung nach Handlungsfähigkeit des Systems
  - nicht nach Ergebnis (kein PnL-Fokus)

- Lernen definieren als Umgangsfähigkeit:
  - womit kann das System stabil umgehen
  - in welchen Situationen bleibt es handlungsfähig
  - nicht: was ist „richtig“ oder profitabel

- Zustandswirkung weiter schärfen:
  - Belastung / Entlastung
  - Veränderung von `action_capacity`
  - Veränderung von `recovery_need`

- Experience stärker koppeln an:
  - Zustandsverlauf über Zeit
  - nicht nur Einzel-Events
  - Entwicklung der Tragfähigkeit innerhalb eines Clusters

- Energie-/Reibungsmodell integrieren:
  - Abweichung = erhöhter Energieverbrauch / regulatorische Last
  - Kohärenz = geringe Reibung / hohe Effizienz
  - Ziel: minimale Reibung bei aktiver Interaktion

- Cluster neu interpretieren:
  - nicht nur Kontextgruppen
  - sondern Erfahrungsräume über Tragfähigkeit
  - Struktur + Zustand + Wirkung → Cluster

- Outcome neu interpretieren:
  - kein PnL als Bewertung
  - sondern Zustandswirkung:
    - TP → Entlastung / Stabilisierung / evtl. Euphorie
    - SL → Belastung / Rückzug / Erhöhter Recovery-Bedarf

- Positive Zustände regulieren:
  - Euphorie als Überaktivierung erkennen
  - keine unkontrollierte Verstärkung positiver Outcomes

- Review stabilisieren:
  - keine impliziten Bewertungsreste (z. B. PnL)
  - Fokus vollständig auf Zustand und Tragfähigkeit


# ==================================================
# PRIO 3 – KPI / AUSWERTUNG
# ==================================================

- Entferne PnL als zentrale KPI

- Neue KPI:
  - Zustandsstabilität
  - Handlungsfähigkeit
  - regulatorische Last
  - Regeneration

- Strukturbezogene KPI:
  - Tragfähigkeit je Strukturfeld


# ==================================================
# PRIO 3 – VISUALISIERUNG
# ==================================================

- Visualisierung hinzufügen:

  Ebene 1:
  - Chart (OHLC)
  - Wahrnehmung (`candle_state`, `tension_state`, etc.)

  Ebene 2:
  - Innenzustand:
    - field_density
    - regulatory_load
    - action_capacity
    - recovery_need
    - survival_pressure

- Ziel:
  - Außenwelt und Innenwelt getrennt sichtbar machen


# ==================================================
# PRIO 4 – TESTS
# ==================================================

- dedizierte Tests für:
  - `bot_gate_funktions.py`
  - `mcm_core_engine.py`

- Fokus:
  - Zustandsentwicklung
  - nicht Trade-Ergebnis


# ==================================================
# OPTIONAL – EXTERNES GATE
# ==================================================

- optional:
  - PnL als technisches ValueGate (Notbremse)

- nicht erlaubt:
  - Teil der Entscheidungslogik
  - Teil der Experience


# ==================================================
# STATUS
# ==================================================

- Fixphase abgeschlossen
- Architekturphase aktiv

# --------------------------------------------------
# Schlussfolgerung
# --------------------------------------------------

- dedizierte Tests für `bot_gate_funktions.py`
- dedizierte Tests für `mcm_core_engine.py`y