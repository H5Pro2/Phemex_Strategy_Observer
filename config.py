# ==================================================
# ZENTRALE BOT KONFIGURATION
# Nur aktiv verwendete Variablen
# ==================================================

class Config:

    # ==================================================
    # SYSTEM
    # ==================================================
    MODE = "BACKTEST"            # "BACKTEST" | "LIVE"
    AKTIV_ORDER = True           # Nur relevant im LIVE-Modus

    # ==================================================
    # DATENQUELLE
    # ==================================================
    BACKTEST_FILEPATH = "data/1-2_2026_5m_SOLUSDT.csv" 
    # workspace | 1-12_2023_5m_SOLUSDT | 1-12_2024_5m_SOLUSDT | 1-12_2025_5m_SOLUSDT | 1-2_2026_5m_SOLUSDT 
    
    CSV_OHLCV_PATH = "data/workspace.csv"   # Live Mode OHLCV Daten Börse
    # ==================================================
    # MARKT
    # ==================================================
    COIN = "SOL"
    USDT = "USDT"
    SYMBOL = f"{COIN}/{USDT}"
    TIMEFRAME = "5m"
    MECHANIK = "swap"
    ORDER_SIZE = 0.5
    WORLD_TIME_LOOP_SECONDS = 1.0 # Live-Loop-Wartezeit für den äußeren Welt-/Chart-Loop.
    # WORLD_TIME_LOOP_SECONDS sollte fachlich  eher Polling-Intervall heißen, nicht Weltzeit. !!!!!
    WORLD_REPLAY_LOOP_SECONDS = 0.01 # Replay-Verzögerung im Backtest/CSV-Feed.
    # ==================================================
    # WORKSPACE
    # ==================================================
    WINDOW_SIZE = 500

    # ==================================================
    # RISK MANAGEMENT
    # ==================================================
    RR = 1.6
    MIN_RR = 1
    MAX_RR = 2
    # trade_value_gate.py Ökonomische Absicherung
    BASE_RISK_PCT = 0.0045
    MAX_SL_DISTANCE = 0.01
    MIN_TP_DISTANCE = 0.01

    RR_EXECUTION_MIN = 1.8
    PENDING_ENTRY_MAX_WAIT_BARS = 4

    # ==================================================
    # MCM BRAIN
    # ==================================================
    MCM_DEBUG = True
    MCM_OUTCOME_DEBUG = True

    MCM_ENABLED = True # Aktiviert die MCM-Interne Simulation, um die Entscheidungsfindung der Agenten zu beeinflussen. Deaktivieren, um die MCM-Interne Simulation zu überspringen und direkt auf Marktinformationen zu reagieren.
    MCM_INTERNAL_CYCLES = 1 # Anzahl der MCM-Interne Zyklen pro Weltzeit-Tick. Je höher, desto intensiver die interne Simulation pro Weltzeit-Tick, aber auch rechenintensiver.
    MCM_REPLAY_SCALE = 0.012 # Skalierungsfaktor für die Geschwindigkeit der MCM-Interne Simulation im Vergleich zur Weltzeit. Je kleiner, desto schneller läuft die MCM-Interne Simulation im Verhältnis zur Weltzeit.
    MCM_FIELD_AGENTS = 160 # Agentenzahl im MCM-Feld, beeinflusst die Granularität der Simulation und die Rechenzeit.
    MCM_FIELD_DIMS = 3 # Anzahl der Dimensionen im MCM-Feld, z.B. 3 für einen 3D-Raum.
    MCM_FIELD_LOCAL_NEIGHBORS = 8 # Anzahl der nächsten Nachbarn, die für lokale Interaktionen berücksichtigt werden.
    MCM_FIELD_COUPLING_SIGMA = 0.5 # Standardabweichung für die Kopplungsstärke in Abhängigkeit von der Entfernung im MCM-Feld. Je kleiner, desto stärker die Kopplung bei nahen Agenten und schwächer bei entfernten Agenten.
    MCM_COUPLING = 0.045 # Grundlegende Kopplungsstärke zwischen den Agenten im MCM-Feld. Beeinflusst, wie stark die Agenten sich gegenseitig beeinflussen.
    MCM_NOISE = 0.08 # Stärke des Rauschens in der MCM-Interne Simulation. Beeinflusst die Zufälligkeit der Agentenbewegungen und Entscheidungen.
    MCM_CENTER_FORCE = 0.0100 # Stärke der Anziehungskraft zum Zentrum des MCM-Feldes. Beeinflusst, wie stark die Agenten dazu neigen, sich in der Mitte des Feldes zu versammeln.
    MCM_CLUSTER_EVERY_N_TICKS = 2 # Anzahl der MCM-Interne Zyklen, nach denen eine Clusteranalyse durchgeführt wird, um Muster und Strukturen im Agentenverhalten zu identifizieren.
    MCM_CLUSTER_EPS = 0.4 # Maximale Entfernung zwischen zwei Agenten, damit sie im selben Cluster liegen (DBSCAN-Parameter). Je kleiner, desto dichter müssen die Agenten beieinander liegen, um als Cluster zu gelten.
    MCM_CLUSTER_MIN_SAMPLES = 4 # Minimale Anzahl von Agenten, die erforderlich ist, um einen Cluster zu bilden (DBSCAN-Parameter). Je höher, desto mehr Agenten müssen beieinander liegen, um als Cluster zu gelten.
    MCM_ATTRACTOR_LONG_ALLOW = True # Erlaubt die Bildung von Long-Anziehungspunkten im MCM-Feld, die potenziell auf steigende Marktbewegungen hinweisen.
    MCM_ATTRACTOR_SHORT_ALLOW = True # Erlaubt die Bildung von Short-Anziehungspunkten im MCM-Feld, die potenziell auf fallende Marktbewegungen hinweisen.
    MCM_PRESSURE_WEIGHT = 0.16 # Gewichtung des Drucks (Pressure) in der Entscheidungsfindung der Agenten im MCM-Feld. Beeinflusst, wie stark die Agenten auf den wahrgenommenen Druck reagieren.
    MCM_MEMORY_WEIGHT = 0.08 # Gewichtung der Erinnerung (Memory) in der Entscheidungsfindung der Agenten im MCM-Feld. Beeinflusst, wie stark die Agenten auf vergangene Erfahrungen und Ergebnisse reagieren.
    MCM_REGULATION_WEIGHT = 0.42 # Gewichtung der Regulierung (Regulation) in der Entscheidungsfindung der Agenten im MCM-Feld. Beeinflusst, wie stark die Agenten auf interne und externe Regeln reagieren.
    MCM_STRESS_RISK_FACTOR = 0.70 # Faktor, der das wahrgenommene Risiko (Risk) in Stress umwandelt. Je höher, desto stärker wird das Risiko in Stress umgewandelt, was zu vorsichtigerem Verhalten der Agenten führen kann.
    MCM_EXCITED_RR_FACTOR = 1.06 # Faktor, der die Risikobereitschaft (Risk) in Erregung (Excitement) umwandelt. Je höher, desto stärker wird die Risikobereitschaft in Erregung umgewandelt, was zu risikofreudigerem Verhalten der Agenten führen kann.
    MCM_TP_REWARD = 0.75 # Belohnung für das Erreichen des Take-Profits (TP) in der MCM-Interne Simulation. Beeinflusst, wie stark die Agenten das Erreichen von Gewinnzielen anstreben.
    MCM_SL_PENALTY = 0.85 # Bestrafung für das Erreichen des Stop-Loss (SL) in der MCM-Interne Simulation. Beeinflusst, wie stark die Agenten das Erreichen von Verlustzielen vermeiden.
    MCM_CANCEL_PENALTY = 0.20 # Bestrafung für das Abbrechen von Trades in der MCM-Interne Simulation. Beeinflusst, wie stark die Agenten Trades abbrechen.
    MCM_TIMEOUT_PENALTY = 0.25 # Bestrafung für das Zeitüberschreiten von Trades in der MCM-Interne Simulation. Beeinflusst, wie stark die Agenten auf Zeitüberschreitungen reagieren.
    MCM_OUTCOME_MEMORY_BOOST = 1.0 # Boost für die Erinnerung (Memory) in der Entscheidungsfindung der Agenten im MCM-Feld. Beeinflusst, wie stark die Agenten auf vergangene Erfahrungen und Ergebnisse reagieren.
    MCM_OUTCOME_RISK_SHIFT = 0.18 # Verschiebung des Risikos (Risk) in der Entscheidungsfindung der Agenten im MCM-Feld. Beeinflusst, wie stark die Agenten auf das wahrgenommene Risiko reagieren.
    MCM_SL_PAUSE_STEPS = 5 # Anzahl der MCM-Interne Zyklen, die nach einem Stop-Loss (SL) pausiert werden, bevor die Agenten wieder aktiv werden. Beeinflusst, wie lange die Agenten nach einem Verlust innehalten, um sich neu zu orientieren.
    MCM_PAUSE_ORIENTATION_GAIN = 1.35 # Verstärkung der Orientierung (Orientation) während der Pause nach einem Stop-Loss (SL) in der MCM-Interne Simulation. Beeinflusst, wie stark die Agenten ihre Orientierung während der Pause anpassen, um zukünftige Verluste zu vermeiden.
    MCM_PAUSE_MOTIVATION_DAMP = 0.55 # Dämpfung der Motivation (Motivation) während der Pause nach einem Stop-Loss (SL) in der MCM-Interne Simulation. Beeinflusst, wie stark die Agenten ihre Motivation während der Pause reduzieren, um vorsichtigeres Verhalten zu fördern.
    MCM_PAUSE_RISK_GAIN = 1.20 # Verstärkung des Risikos (Risk) während der Pause nach einem Stop-Loss (SL) in der MCM-Interne Simulation. Beeinflusst, wie stark die Agenten ihr wahrgenommenes Risiko während der Pause erhöhen, um vorsichtigeres Verhalten zu fördern.
    MCM_CONTEXT_DECAY = 0.992 # Rate, mit der die Relevanz von Kontextinformationen im MCM-Feld über die Zeit abnimmt. Je höher, desto schneller verlieren Kontextinformationen an Einfluss auf die Entscheidungsfindung der Agenten.  
    MCM_CONTEXT_MAX_AGE = 320 # Maximales Alter von Kontextinformationen im MCM-Feld, bevor sie als irrelevant betrachtet und aus der Entscheidungsfindung entfernt werden. Beeinflusst, wie lange Kontextinformationen die Entscheidungen der Agenten beeinflussen können.
    MCM_CONTEXT_MIN_TRUST = 0.06 # Minimales Vertrauen, das erforderlich ist, damit Kontextinformationen im MCM-Feld in die Entscheidungsfindung der Agenten einbezogen werden. Je höher, desto mehr Vertrauen ist erforderlich, damit Kontextinformationen berücksichtigt werden.
    MCM_CONTEXT_MATCH_THRESHOLD = 0.28 # Schwelle für die Übereinstimmung von Kontextinformationen im MCM-Feld, um als relevant für die Entscheidungsfindung der Agenten zu gelten. Je höher, desto strenger die Anforderungen an die Übereinstimmung von Kontextinformationen.
    MCM_CONTEXT_LOOKUP_THRESHOLD = 0.30 # Schwelle für die Suche nach Kontextinformationen im MCM-Feld, um als relevant für die Entscheidungsfindung der Agenten zu gelten. Je höher, desto strenger die Anforderungen an die Suche nach Kontextinformationen.
    MCM_CONTEXT_MERGE_THRESHOLD = 0.16 # Schwelle für die Zusammenführung von Kontextinformationen im MCM-Feld, um als relevant für die Entscheidungsfindung der Agenten zu gelten. Je höher, desto strenger die Anforderungen an die Zusammenführung von Kontextinformationen.
    MCM_CONTEXT_SPLIT_VARIANCE = 0.085 # Schwelle für die Aufteilung von Kontextinformationen im MCM-Feld, um als relevant für die Entscheidungsfindung der Agenten zu gelten. Je höher, desto strenger die Anforderungen an die Aufteilung von Kontextinformationen.
    MCM_CONTEXT_SPLIT_RADIUS = 0.24 # Schwelle für die Aufteilung von Kontextinformationen im MCM-Feld basierend auf der räumlichen Verteilung, um als relevant für die Entscheidungsfindung der Agenten zu gelten. Je höher, desto strenger die Anforderungen an die räumliche Verteilung von Kontextinformationen.
    MCM_INHIBITION_GAIN = 0.26 # Verstärkung der Hemmung (Inhibition) in der Entscheidungsfindung der Agenten im MCM-Feld. Beeinflusst, wie stark die Agenten hemmende Signale berücksichtigen, um übermäßige Aktivität zu vermeiden.
    MCM_HABITUATION_GAIN = 0.18 # Verstärkung der Gewöhnung (Habituation) in der Entscheidungsfindung der Agenten im MCM-Feld. Beeinflusst, wie stark die Agenten auf wiederholte Reize mit reduzierter Reaktion reagieren, um sich an häufige Situationen anzupassen.
    MCM_COMPETITION_GAIN = 0.22 # Verstärkung der Konkurrenz (Competition) in der Entscheidungsfindung der Agenten im MCM-Feld. Beeinflusst, wie stark die Agenten konkurrierende Signale berücksichtigen, um Entscheidungen zu treffen.
    MCM_OBSERVE_THRESHOLD = 0.66 # Schwelle für die Beobachtung von Marktbedingungen und internen Zuständen im MCM-Feld, um als relevant für die Entscheidungsfindung der Agenten zu gelten. Je höher, desto strenger die Anforderungen an die Beobachtung von Informationen.
    MCM_META_OBSERVE_PRIORITY_ALLOW = 0.66 # Schwelle für die Priorisierung von Beobachtungen im MCM-Feld, um als relevant für die Entscheidungsfindung der Agenten zu gelten. Je höher, desto strenger die Anforderungen an die Priorisierung von Beobachtungen.
    MCM_META_UNCERTAINTY_ALLOW = 0.72 # Schwelle für die Berücksichtigung von Unsicherheit in der Entscheidungsfindung der Agenten im MCM-Feld. Je höher, desto mehr Unsicherheit wird toleriert, bevor sie als relevant für Entscheidungen betrachtet wird.
    MCM_META_CONFLICT_ALLOW = 0.60 # Schwelle für die Berücksichtigung von Konflikten in der Entscheidungsfindung der Agenten im MCM-Feld. Je höher, desto mehr Konflikte werden toleriert, bevor sie als relevant für Entscheidungen betrachtet werden.
    MCM_META_RUMINATION_ALLOW = 0.64 # Schwelle für die Berücksichtigung von Grübeln (Rumination) in der Entscheidungsfindung der Agenten im MCM-Feld. Je höher, desto mehr Grübeln wird toleriert, bevor es als relevant für Entscheidungen betrachtet wird.
    MCM_META_MATURITY_MIN = 0.34 # Minimale Reife (Maturity), die erforderlich ist, damit die Agenten im MCM-Feld als bereit für komplexe Entscheidungen gelten. Je höher, desto reifer müssen die Agenten sein, um komplexe Entscheidungen zu treffen.
    MCM_META_READINESS_MIN = 0.38 # Minimale Bereitschaft (Readiness), die erforderlich ist, damit die Agenten im MCM-Feld als bereit für Entscheidungen gelten. Je höher, desto bereiter müssen die Agenten sein, um Entscheidungen zu treffen.
    MCM_META_SIGNAL_QUALITY_MIN = 0.24 # Minimale Signalqualität, die erforderlich ist, damit Informationen im MCM-Feld in die Entscheidungsfindung der Agenten einbezogen werden. Je höher, desto mehr Qualität ist erforderlich, damit Informationen berücksichtigt werden.
    MCM_MIN_SL_DISTANCE = 0.0022 # Minimale Stop-Loss-Distanz, die von den Agenten im MCM-Feld berücksichtigt wird. Beeinflusst, wie eng die Agenten ihre Stop-Loss-Positionen setzen, um Verluste zu begrenzen.
    MCM_PLAN_GATE_ALIGN = 0.92 # Schwelle für die Ausrichtung von Plänen im MCM-Feld, um als relevant für die Entscheidungsfindung der Agenten zu gelten. Je höher, desto strenger die Anforderungen an die Ausrichtung von Plänen.
    MCM_PROTECTIVE_WIDTH_GAIN = 0.95 # Verstärkung der Schutzbreite (Protective Width) in der Entscheidungsfindung der Agenten im MCM-Feld. Beeinflusst, wie stark die Agenten ihre Schutzmaßnahmen anpassen, um Risiken zu minimieren.
    MCM_STRESS_WIDTH_GAIN = 0.34 # Verstärkung der Stressbreite (Stress Width) in der Entscheidungsfindung der Agenten im MCM-Feld. Beeinflusst, wie stark die Agenten ihre Reaktionen auf Stress anpassen, um besser mit herausfordernden Situationen umzugehen.
    MCM_INNER_TICKS_PER_WORLD_TICK = 1 # Anzahl der MCM-Interne Zyklen pro Weltzeit-Tick. Je höher, desto intensiver die interne Simulation pro Weltzeit-Tick, aber auch rechenintensiver.
    MCM_INNER_IDLE_BASE_TICKS = 1 # Anzahl der MCM-Interne Zyklen, die als Basis für die Berechnung der Idle-Zeit dienen. Je höher, desto länger die Basis-Idle-Zeit, bevor zusätzliche Faktoren berücksichtigt werden.
    MCM_INNER_IDLE_MAX_TICKS = 2 # Maximale Anzahl der MCM-Interne Zyklen, die als Idle-Zeit verwendet werden können. Beeinflusst, wie lange die Agenten inaktiv bleiben können, bevor sie wieder aktiv werden.
    MCM_INNER_IDLE_SLEEP_MIN_SECONDS = 0.10 # Minimale Schlafzeit in Sekunden, die die Agenten im MCM-Feld während der Idle-Phase verbringen. Beeinflusst, wie kurz die Agenten inaktiv bleiben können, bevor sie wieder aktiv werden.
    MCM_INNER_IDLE_SLEEP_MAX_SECONDS = 0.45 # Maximale Schlafzeit in Sekunden, die die Agenten im MCM-Feld während der Idle-Phase verbringen. Beeinflusst, wie lange die Agenten inaktiv bleiben können, bevor sie wieder aktiv werden.
    MCM_RUNTIME_TICKS_PER_WINDOW = 1 # Anzahl der MCM-Interne Zyklen pro Fensteraktualisierung. Je höher, desto intensiver die interne Simulation pro Fensteraktualisierung, aber auch rechenintensiver.
    MCM_RUNTIME_IDLE_TICKS = 1 # Anzahl der MCM-Interne Zyklen, die als Idle-Zeit während der Laufzeit dienen. Beeinflusst, wie lange die Agenten inaktiv bleiben können, bevor sie wieder aktiv werden.
    MCM_RUNTIME_IDLE_TICKS_MAX = 2 # Maximale Anzahl der MCM-Interne Zyklen, die als Idle-Zeit während der Laufzeit verwendet werden können. Beeinflusst, wie lange die Agenten inaktiv bleiben können, bevor sie wieder aktiv werden.
    MCM_RUNTIME_IDLE_SLEEP_MIN_SECONDS = 0.10 # Minimale Schlafzeit in Sekunden, die die Agenten im MCM-Feld während der Idle-Phase der Laufzeit verbringen. Beeinflusst, wie kurz die Agenten inaktiv bleiben können, bevor sie wieder aktiv werden.
    MCM_RUNTIME_IDLE_SLEEP_MAX_SECONDS = 0.45 # Maximale Schlafzeit in Sekunden, die die Agenten im MCM-Feld während der Idle-Phase der Laufzeit verbringen. Beeinflusst, wie lange die Agenten inaktiv bleiben können, bevor sie wieder aktiv werden.
    MCM_MEMORY_STATE_PATH = "bot_memory/memory_state.json" # Dateipfad für das Speichern des Memory-Zustands der MCM-Interne Simulation. Beeinflusst, wo die Memory-Daten gespeichert werden, um Einblicke in die interne Dynamik zu erhalten.
    MCM_MEMORY_SAVE_COOLDOWN_SECONDS = 1.25 # Minimale Zeit in Sekunden zwischen dem Speichern von Memory-Zuständen, um die Leistung zu optimieren und übermäßiges Schreiben zu vermeiden.
    MCM_SAVE_RUNTIME_STATE = False # Aktiviert das Speichern des Runtime-Zustands der MCM-Interne Simulation, um Einblicke in die interne Dynamik zu erhalten, aber auch mit einem gewissen Leistungsaufwand verbunden.
    DEBUG_WRITE_EVERY_N = 8 # Anzahl der MCM-Interne Zyklen, nach denen Debug-Informationen geschrieben werden. Je höher, desto seltener werden Debug-Informationen geschrieben, was die Leistung verbessern kann, aber weniger Einblicke in die interne Dynamik bietet.

    # ==================================================
    # KOSTEN
    # ==================================================
    FEE_RATE = 0.0006
    FEE_PER_TRADE = 0.0

    # ==================================================
    # EQUITY
    # ==================================================
    START_EQUITY = 100.0