# TECHNICAL STATUS

Stand: 2026-05-17

# --------------------------------------------------
# Umgesetzte Erweiterungen
# --------------------------------------------------

## Repository / Start

- `.env` aus Repository entfernt
- `config.json` aus Repository entfernt
- generierte `data/*.json` aus Repository entfernt
- `.gitignore` ergaenzt
- `data/.gitkeep` ergaenzt
- `start_bot.ps1` ergaenzt
- `start_bot.bat` erweitert

## Agenten / CEO

- `agent_runtime_roles.py` ergaenzt
- Rollenvertrag fuer Agenten ergaenzt
- Rollen: Struktur, Momentum, Kontext, Risiko, Entscheidung, Weitere
- CEO-Rollenbewertung erweitert
- Volume als Kontext getrennt
- Risk / Volatility getrennt bewertet
- `check_agent_runtime_roles.py` ergaenzt

## Brain / Replay

- `brain_replay_enhancements.py` ergaenzt
- stabilerer Pattern-Key `v2`
- rollenbasierter Pattern-Key
- robustere Replay-Regelgewichtung
- Asset-spezifische Replay-Regeln bevorzugt
- Edge-Score aus Winrate, AvgR und Profit-Factor
- Mindestdatenmenge abgesichert
- `check_brain_replay_enhancements.py` ergaenzt

## Brain / Dashboard Summary

- `brain_dashboard_enhancements.py` ergaenzt
- `dashboard_summary` im Brain-Status vorbereitet
- Entry-Kontext sichtbar gemacht
- Fallback-Erkennung sichtbar gemacht
- Replay-Adjustment sichtbar gemacht
- Memory-Werte sichtbar gemacht
- Economic-Gate-Status sichtbar gemacht
- `check_brain_dashboard_enhancements.py` ergaenzt

## Dashboard Optik

- `dashboard_agent_roles_patch.js` ergaenzt
- `prepare_dashboard_runtime.py` ergaenzt
- technische Optik `role-ui-v3-tech`
- kompaktere Agentenkarten
- kleinere Schriftgroessen
- weniger Rundungen
- Monospace-Werte fuer technische Kennzahlen
- klare Statuskanten fuer LONG / SHORT / NEUTRAL / Konflikt

# --------------------------------------------------
# Startpruefungen
# --------------------------------------------------

Beim Start ueber `start_bot.ps1` oder `start_bot.bat` werden geprueft:

- Dashboard Runtime
- Agenten-Rollenvertrag
- Brain Replay Enhancements
- Brain Dashboard Enhancements
- Python-Abhaengigkeiten
- Bot-Start

# --------------------------------------------------
# Offene Punkte
# --------------------------------------------------

- echte Dashboard-Ansicht nach Start visuell pruefen
- Replay-Regel-Auswertung im Haupt-Dashboard dauerhaft integrieren
- Brain-Fallbacks im Haupt-Dashboard optisch weiter verdichten
- README und BAUPLAN bei naechstem Dokumentationslauf konsolidieren
- direkte Python-Startpruefung bei fehlender `config.json` verbessern
