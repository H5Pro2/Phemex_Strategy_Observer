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
- `checks/check_agent_runtime_roles.py` ergaenzt

## Agenten-Setup / Dashboard

- `ui/patches/dashboard_agent_setup_cleanup_patch.js` ergaenzt
- Chart-Indikator-Agenten getrennt
- Struktur- und Signalagenten getrennt
- Bewertungsagenten ohne eigene Chart-Pane getrennt
- RSI / VWAP / Volume aus direktem Bewertungsbereich entfernt
- Breakout / Fakeout in Struktur-/Signalbereich verschoben

## Brain / Replay

- `brain_replay_enhancements.py` ergaenzt
- stabilerer Pattern-Key `v2`
- rollenbasierter Pattern-Key
- robustere Replay-Regelgewichtung
- Asset-spezifische Replay-Regeln bevorzugt
- Edge-Score aus Winrate, AvgR und Profit-Factor
- Mindestdatenmenge abgesichert
- `checks/check_brain_replay_enhancements.py` ergaenzt

## Brain / Dashboard Summary

- `brain_dashboard_enhancements.py` ergaenzt
- `dashboard_summary` im Brain-Status vorbereitet
- Entry-Kontext sichtbar gemacht
- Fallback-Erkennung sichtbar gemacht
- Replay-Adjustment sichtbar gemacht
- Memory-Werte sichtbar gemacht
- Economic-Gate-Status sichtbar gemacht
- `checks/check_brain_dashboard_enhancements.py` ergaenzt

## Dashboard Optik

- `ui/patches/dashboard_agent_roles_patch.js` ergaenzt
- `tools/prepare_dashboard_runtime.py` ergaenzt
- technische Optik `role-ui-v3-tech`
- kompaktere Agentenkarten
- kleinere Schriftgroessen
- weniger Rundungen
- Monospace-Werte fuer technische Kennzahlen
- klare Statuskanten fuer LONG / SHORT / NEUTRAL / Konflikt

## Chart / KLineCharts

- `indicator_display_enhancements.py` ergaenzt
- `ui/patches/dashboard_chart_pane_patch.js` ergaenzt
- `ui/patches/dashboard_kline_native_indicators_patch.js` ergaenzt
- MACD eigene native KLineCharts-Pane
- MFI eigene native KLineCharts-Pane
- RSI eigene native KLineCharts-Pane
- Volume eigene native KLineCharts-Pane
- VWAP als Preislinie / Overlay im Hauptchart
- Chart-Bedienleiste ergaenzt
- Auto-Scroll AN/AUS ergaenzt
- Realtime / Zoom / Fit ergaenzt

# --------------------------------------------------
# Startpruefungen
# --------------------------------------------------

Beim Start ueber `start_bot.ps1` oder `start_bot.bat` werden geprueft:

- Dashboard Runtime
- Dashboard Runtime Patches
- Agenten-Rollenvertrag
- Brain Replay Enhancements
- Brain Dashboard Enhancements
- Python-Abhaengigkeiten
- Bot-Start

# --------------------------------------------------
# Offene Punkte
# --------------------------------------------------

- echte Dashboard-Ansicht nach Start visuell pruefen
- getrennte KLineCharts-Panes fuer MACD / MFI / RSI / Volume im Browser pruefen
- VWAP Overlay im Hauptchart pruefen
- Replay-Regel-Auswertung im Haupt-Dashboard dauerhaft integrieren
- Brain-Fallbacks im Haupt-Dashboard optisch weiter verdichten
- direkte Python-Startpruefung bei fehlender `config.json` verbessern
