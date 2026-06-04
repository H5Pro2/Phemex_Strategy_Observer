# Phemex Strategy Observer

Lokales Analyse- und Paper-Trading-System für Phemex. Das Projekt kombiniert technische Signalquellen, eine deterministische Strategy Engine, ein spezialisiertes LLM-Rollenteam und ein Dashboard für Chart-, Analyse- und Setup-Ansichten.

Repository: https://github.com/H5Pro2/Phemex_Strategy_Observer

Das System ist als Observer gebaut. Live-Trading bleibt gesperrt. Der Fokus liegt auf Marktbeobachtung, Kandidatenbewertung, Paper-Trading, Risiko-Checks und nachvollziehbaren LLM-Rollenberichten.

## Kernidee

Der Bot sammelt Phemex-Kerzendaten und Accountdaten, berechnet technische Signale und baut daraus einen Trade-Kandidaten. Danach bewertet ein Rollen-Team den Kandidaten:

- Market Structure Analyst
- Momentum Analyst
- Risk Officer
- Skeptic / Bear Case
- Execution Coach
- CEO / Judge

Der CEO/Judge ist die finale Instanz und entscheidet `APPROVE`, `WAIT` oder `BLOCK`. Die LLM-Rollen erzeugen keine eigene Preislogik. Entry, SL, TP, RR und harte Risiko-Grenzen kommen aus der Strategy Engine und dem Economic Gate.

## Projektstruktur

```text
/
+-- phemex_strategy_observer.py       Webserver, API-Routen, Runtime-Orchestrierung
+-- agent_runtime.py                  Signal- und Agentenruntime
+-- agent_runtime_roles.py            Rollen- und Agenten-Hilfslogik
+-- llm_roles.py                      LLM-Rollen, Prompts und Rollen-Auswertung
+-- brain_runtime.py                  Memory- und Lernschicht
+-- trade_value_gate.py               Economic Gate und harte Risiko-Prüfung
+-- indikator.py                      Indikator- und Signalberechnung
+-- dashboard.html                    Dashboard-Hauptdatei
+-- dashboard_script.js               Dashboard-JavaScript
+-- dashboard_script_check.js         gebündelter Dashboard-Check
+-- config.example.json               Konfigurationsvorlage
+-- .env.example                      Vorlage für private API-Werte
+-- assets.txt                        Asset-Liste
+-- BAUPLAN.md                        Architektur und Zielbild
+-- DESIGNE_ANLEITUNG.md              UI-Designregeln für weitere Arbeiten
+-- strategy.md                       Strategie- und Trading-Regelwerk
+-- checks/                           lokale Prüfscripte
+-- docs/                             technische Dokumentation
+-- tools/                            Hilfs- und Build-Tools
+-- ui/patches/                       Dashboard Runtime-Patches
+-- data/                             lokale Laufzeitdaten, nicht versioniert
```

## Dashboard

Das Dashboard läuft lokal unter:

```text
http://127.0.0.1:8787
```

Hauptbereiche:

- Settings: API, Bot-Config, Sprache, Theme und technische Einstellungen
- Chart View: KLineCharts-Ansicht mit Indikatoren, Status und Chart-Bedienung
- Analyse Viewer: LLM-Rollenberichte, Pipeline, Kostenstatus, Trades und Debugdaten
- Strategie Setup: Strategy Engine, LLM-Rollenteam, Analysten und Datenquellen

Das UI ist auf kompakte, einheitliche Bereiche ausgelegt. Ausklappbare Bereiche sollen dem Stil aus `DESIGNE_ANLEITUNG.md` folgen.

## LLM-Anbindung

Unterstützte Provider:

- OpenAI
- Ollama lokal

OpenAI wird über `.env` konfiguriert. Ollama wird lokal über Base URL und Modell eingestellt, zum Beispiel:

```text
http://127.0.0.1:11434
qwen2.5:3b
```

Die aktiven Signalquellen der Analysten werden als strukturierter Kontext an die jeweiligen Rollen übergeben. Prompt-Erweiterungen können im Strategy Setup gepflegt werden.

## Sicherheit

Private Werte gehören nicht ins Repository.

Nicht versioniert:

- `.env`
- `config.json`
- lokale Runtime-Daten unter `data/*.json`
- Logs und Exporte

Live-Trading ist in diesem Observer absichtlich gesperrt. Das Economic Gate darf nicht durch LLM, CEO/Judge oder UI-Logik umgangen werden.

## Setup

Abhängigkeiten installieren:

```powershell
python -m pip install -r requirements.txt
```

Lokale Konfiguration anlegen:

```powershell
Copy-Item .env.example .env
Copy-Item config.example.json config.json
```

API-Werte werden in `.env` eingetragen. Die Datei bleibt lokal.

## Start

Empfohlen unter Windows PowerShell:

```powershell
.\start_bot.ps1
```

Alternative:

```powershell
.\start_bot.bat
```

Manueller Start:

```powershell
python .\phemex_strategy_observer.py --config .\config.json --web
```

## Prüfungen

Python Runtime:

```powershell
python -m py_compile .\phemex_strategy_observer.py
```

Dashboard-JavaScript:

```powershell
node --check .\dashboard_script.js
node --check .\dashboard_script_check.js
```

LLM-Rollen:

```powershell
python .\checks\check_llm_roles.py
```

Dashboard Runtime-Patches:

```powershell
python .\checks\check_dashboard_runtime_patches.py
```

## Wichtige Dateien

- `BAUPLAN.md`: grober Architektur- und Umbauplan
- `DESIGNE_ANLEITUNG.md`: Designregeln für neue UI-Funktionen
- `strategy.md`: Trading-Regeln und Strategie-Logik
- `docs/TECHNICAL_STATUS.md`: technischer Stand
- `config.example.json`: sichere Vorlage für `config.json`
- `.env.example`: sichere Vorlage für `.env`

## Aktueller Schwerpunkt

Das Projekt entwickelt sich von einem klassischen Indikator-Agenten-System zu einem Rollen-basierten Analyse-System:

1. Signalquellen liefern strukturierte Daten.
2. Die Strategy Engine baut einen Trade-Kandidaten.
3. Das LLM-Rollenteam bewertet den Kandidaten aus Spezialrollen.
4. CEO/Judge entscheidet final.
5. Economic Gate und Paper-Trading prüfen die praktische Umsetzbarkeit.

Ziel ist eine nachvollziehbare Live-Analyse mit sauberer UI, begrenzten LLM-Kosten und klarer Trennung zwischen technischer Preislogik und LLM-Bewertung.
