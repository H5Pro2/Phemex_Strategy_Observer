# ==================================================
# _gui.py
# ==================================================
# READ-ONLY DARK GUI
# KEIN BOT-START
# KEIN SCHREIBEN
# KEIN RESET
#
# GUI IST REINER LESER VON:
#   debug/trade_stats.json
#   debug/trade_equity.csv
#
# KEIN FREEZE / KEIN RUCKELN
# STATISCHE LAYOUT-GRÖSSEN
# ==================================================

import tkinter as tk
from tkinter import ttk
import time
import os
import json
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import csv
from datetime import datetime
from config import Config
# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
STATS_PATH = "debug/trade_stats.json"
EQUITY_PATH = "debug/trade_equity.csv"
MEMORY_STATE_PATH = str(getattr(Config, "MCM_MEMORY_STATE_PATH", "bot_memory/memory_state.json") or "bot_memory/memory_state.json")
CMAP = 'plasma' 
heatmap_alpha = 0.18
# coolwarm, seismic, RdBu, RdYlBu, RdYlGn, Spectral, PiYG, PRGn, BrBG, PuOr, RdGy
# viridis, plasma, inferno, magma, cividis, turbo
# ─────────────────────────────────────────────
if Config.MODE == "LIVE":
    WORKSPACE_PATH = str(getattr(Config, "CSV_OHLCV_PATH", "data/workspace.csv") or "data/workspace.csv")
else:
    WORKSPACE_PATH = Config.BACKTEST_FILEPATH

# ─────────────────────────────────────────────
REFRESH_MS = 1000

matplotlib.use("TkAgg")

# ─────────────────────────────────────────────
# COLORS / STYLE
# ─────────────────────────────────────────────
BG = "#121212"
FG = "#e0e0e0"
FG_DIM = "#9aa0a6"
ACCENT = "#4fc3f7"
GOOD = "#66bb6a"
BAD = "#ef5350"
# anzeige
green ="#66bb6a"    # grün
orange ="#ffa726"  # orange
red ="#ef5350"   # red

# ==================================================
# GUI
# ==================================================
class TradeStatsGUI:

    def __init__(self, root):
        self.root = root
        self.root.title(f"{Config.COIN} Trade Stats - {Config.MODE} Mode | RegimeStructure RL Bot")
        self.root.configure(bg=BG)

        # ---------------- STYLE ----------------
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 11, "bold"), foreground=ACCENT)
        style.configure("Value.TLabel", font=("Consolas", 10))
        style.configure("Dim.TLabel", foreground=FG_DIM)

        self.vars = {}

        # Gemeinsamer Container für Header + Plot
        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        # Equity State
        self._eq_trades = []
        self._eq_pnl_netto = []
        self._eq_pnl_tp = []
        self._eq_pnl_sl = []
        self._eq_last_line_count = 0

        # RL Heatmap Handles
        self.rl_heatmap = None
        self.cbar = None
        self._rl_last_mtime = 0.0

        # UI Aufbau
        self._build_ui(self.container)
        self._build_equity_window(self.container)

        # Initial laden
        self._reset_equity_state()
        self._load_full_equity()

        # Update Loop
        self._update_loop()

    # ─────────────────────────────────────────────
    # LOAD FULL EQUITY
    # ─────────────────────────────────────────────
    def _load_full_equity(self):
        if not os.path.exists(EQUITY_PATH):
            return

        try:
            with open(EQUITY_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines[1:]:
                parts = line.strip().split(",")
                if len(parts) != 4:
                    continue

                self._eq_trades.append(int(parts[0]))
                self._eq_pnl_netto.append(float(parts[1]))
                self._eq_pnl_tp.append(float(parts[2]))
                self._eq_pnl_sl.append(float(parts[3]))

            self._eq_last_line_count = len(lines)

        except Exception:
            pass

    # ─────────────────────────────────────────────
    # RL Heatmap: NUR DATEN (Matrix) – KEIN imshow / KEIN remove / KEIN self-call
    # ─────────────────────────────────────────────
    def _resolve_memory_state_path(self):

        configured = str(MEMORY_STATE_PATH or "debug/memory_state.json")
        base_dir = os.path.dirname(os.path.abspath(__file__))

        candidates = []

        if os.path.isabs(configured):
            candidates.append(configured)
        else:
            candidates.append(os.path.join(base_dir, configured))
            candidates.append(configured)

        fallback = "debug/memory_state.json"
        if configured != fallback:
            candidates.append(os.path.join(base_dir, fallback))
            candidates.append(fallback)

        seen = set()

        for candidate in candidates:
            candidate = str(candidate)
            if candidate in seen:
                continue
            seen.add(candidate)

            if os.path.exists(candidate):
                return candidate

        return str(candidates[0]) if candidates else str(configured)

    def _heat_value(self, value, scale=1.0):

        try:
            value = float(value)
        except Exception:
            value = 0.0

        scale = max(float(scale or 1.0), 1e-9)
        normalized = 0.5 + (value / (2.0 * scale))

        if normalized < 0.0:
            return 0.0
        if normalized > 1.0:
            return 1.0
        return float(normalized)

    def _positive_heat_value(self, value, scale=1.0):

        try:
            value = float(value)
        except Exception:
            value = 0.0

        scale = max(float(scale or 1.0), 1e-9)
        normalized = value / scale

        if normalized < 0.0:
            return 0.0
        if normalized > 1.0:
            return 1.0
        return float(normalized)

    def _outcome_heat_value(self, tp=0.0, sl=0.0, cancel=0.0, timeout=0.0):

        tp = float(tp or 0.0)
        sl = float(sl or 0.0)
        cancel = float(cancel or 0.0)
        timeout = float(timeout or 0.0)

        total = max(tp + sl + cancel + timeout, 1.0)
        score = (tp - sl - (cancel * 0.55) - (timeout * 0.75)) / total
        return self._heat_value(score, 1.0)

    def _vector_to_lane_row(self, vector):

        values = list(vector or [])

        if len(values) < 26:
            values.extend([0.0] * (26 - len(values)))

        try:
            values = [float(v) for v in values[:26]]
        except Exception:
            cleaned = []
            for value in values[:26]:
                try:
                    cleaned.append(float(value))
                except Exception:
                    cleaned.append(0.0)
            values = cleaned

        world_signal = (
            (values[0] / 2.2)
            + values[1]
            + (values[2] / 2.0)
            + values[3]
            + values[4]
        ) / 5.0

        perception_signal = (
            values[5]
            + values[6]
            + values[7]
            - abs(values[8])
            + values[18]
            - values[19]
        ) / 6.0

        felt_signal = (
            values[9]
            + values[10]
            + values[11]
            - values[12]
        ) / 4.0

        thought_meta_signal = (
            values[13]
            + values[14]
            + values[15]
            + values[16]
            + values[17]
        ) / 5.0

        memory_signal = (
            values[20]
            - values[21]
            + values[22]
            + (values[23] / 12.0)
            + (values[24] / 2.0)
            + (values[25] / 2.0)
        ) / 6.0

        return [
            self._heat_value(world_signal, 1.0),
            self._heat_value(perception_signal, 1.0),
            self._heat_value(felt_signal, 1.0),
            self._heat_value(thought_meta_signal, 1.0),
            self._heat_value(memory_signal, 1.0),
        ]

    def _build_summary_heat_row(self, memory):

        signature_memory = dict((memory or {}).get("signature_memory", {}) or {})
        context_clusters = dict((memory or {}).get("context_clusters", {}) or {})
        mcm_memory = list((memory or {}).get("mcm_memory", []) or [])

        attractor_map = {
            "defense": -1.0,
            "analysis": -0.5,
            "neutral": 0.0,
            "cooperate": 0.5,
            "explore": 1.0,
        }

        action_map = {
            "stressed": -1.0,
            "stable": 0.0,
            "active": 0.5,
            "excited": 1.0,
        }

        last_attractor = attractor_map.get(str((memory or {}).get("mcm_last_attractor", "neutral") or "neutral").strip().lower(), 0.0)
        last_action = action_map.get(str((memory or {}).get("mcm_last_action", "stable") or "stable").strip().lower(), 0.0)

        return [
            self._positive_heat_value(len(signature_memory), 24.0),
            self._positive_heat_value(len(context_clusters), 16.0),
            self._positive_heat_value(len(mcm_memory), 12.0),
            self._heat_value(last_attractor, 1.0),
            self._heat_value(last_action, 1.0),
            self._positive_heat_value((memory or {}).get("context_cluster_seq", 0), 24.0),
            1.0 if (memory or {}).get("last_signature_key") else 0.0,
            1.0 if (memory or {}).get("last_context_cluster_id") else 0.0,
        ]

    def _build_context_cluster_heat_rows(self, memory):

        clusters = dict((memory or {}).get("context_clusters", {}) or {})

        rows = []

        items = sorted(
            clusters.values(),
            key=lambda item: (
                abs(float((item or {}).get("score", 0.0) or 0.0)),
                float((item or {}).get("trust", 0.0) or 0.0),
                int((item or {}).get("seen", 0) or 0),
            ),
            reverse=True,
        )[:8]

        for item in items:

            lane_row = self._vector_to_lane_row((item or {}).get("center_vector", []))
            outcome_value = self._outcome_heat_value(
                tp=(item or {}).get("tp", 0),
                sl=(item or {}).get("sl", 0),
                cancel=(item or {}).get("cancel", 0),
                timeout=(item or {}).get("timeout", 0),
            )

            rows.append(
                lane_row + [
                    self._heat_value((item or {}).get("score", 0.0), 12.0),
                    self._positive_heat_value((item or {}).get("trust", 0.0), 1.0),
                    outcome_value,
                ]
            )

        return rows

    def _build_signature_heat_rows(self, memory):

        signature_memory = dict((memory or {}).get("signature_memory", {}) or {})

        rows = []

        items = sorted(
            signature_memory.values(),
            key=lambda item: (
                abs(float((item or {}).get("score", 0.0) or 0.0)),
                int((item or {}).get("seen", 0) or 0),
                -int((item or {}).get("age", 0) or 0),
            ),
            reverse=True,
        )[:8]

        for item in items:

            lane_row = self._vector_to_lane_row((item or {}).get("signature_vector", []))
            outcome_value = self._outcome_heat_value(
                tp=(item or {}).get("tp", 0),
                sl=(item or {}).get("sl", 0),
                cancel=(item or {}).get("cancel", 0),
                timeout=(item or {}).get("timeout", 0),
            )

            rows.append(
                lane_row + [
                    self._heat_value((item or {}).get("score", 0.0), 6.0),
                    self._positive_heat_value((item or {}).get("seen", 0), 12.0),
                    outcome_value,
                ]
            )

        return rows

    def _build_mcm_memory_heat_rows(self, memory):

        memory_items = list((memory or {}).get("mcm_memory", []) or [])

        rows = []

        items = sorted(
            memory_items,
            key=lambda item: int((item or {}).get("strength", 0) or 0),
            reverse=True,
        )[:8]

        for item in items:

            center = float((item or {}).get("center", 0.0) or 0.0)
            strength = float((item or {}).get("strength", 0) or 0.0)

            rows.append([
                self._heat_value(center, 2.2),
                0.50,
                0.50,
                0.50,
                self._heat_value(center, 2.2),
                self._heat_value(center * max(1.0, strength / 6.0), 4.0),
                self._positive_heat_value(strength, 12.0),
                self._heat_value(center, 2.2),
            ])

        return rows

    def _ensure_heatmap_artist(self, matrix, alpha):

        if matrix is None:
            return

        if self.rl_heatmap is None:
            self.rl_heatmap = self.eq_ax.imshow(
                matrix,
                cmap=CMAP,
                alpha=alpha,
                aspect="auto",
                origin="lower",
                extent=(0, 1, 0, 1),
                transform=self.eq_ax.transAxes,
                interpolation="bicubic",
                zorder=0
            )
        else:
            self.rl_heatmap.set_data(matrix)
            self.rl_heatmap.set_alpha(alpha)

        self.rl_heatmap.set_clim(0.0, 1.0)

        if self.cbar is None:
            fig = self.eq_ax.figure
            self.cbar = fig.colorbar(
                self.rl_heatmap,
                ax=self.eq_ax,
                location="right",
                fraction=0.03,
                pad=0.02
            )

            self.cbar.ax.yaxis.set_tick_params(color=FG)
            self.cbar.outline.set_edgecolor(FG_DIM)
            self.cbar.ax.set_facecolor(BG)

            for label in self.cbar.ax.get_yticklabels():
                label.set_color(FG)

        self.cbar.set_label("Memory State", color=FG)

    def _draw_rl_heatmap(self):

        path = self._resolve_memory_state_path()

        if not os.path.exists(path):
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                memory = json.load(f)
        except Exception:
            return None

        summary_row = self._build_summary_heat_row(memory)
        context_rows = self._build_context_cluster_heat_rows(memory)
        signature_rows = self._build_signature_heat_rows(memory)
        mcm_rows = self._build_mcm_memory_heat_rows(memory)

        matrix = []

        if summary_row:
            matrix.append(summary_row)

        if context_rows:
            matrix.extend(context_rows)

        if signature_rows:
            if matrix:
                matrix.append([0.10] * len(summary_row))
            matrix.extend(signature_rows)

        if mcm_rows:
            if matrix:
                matrix.append([0.18] * len(summary_row))
            matrix.extend(mcm_rows)

        if not matrix:
            return None

        return matrix

    # ─────────────────────────────────────────────
    # PRINT TIMERANGE
    # ─────────────────────────────────────────────
    def print_Time_Range(self, path):
        if not os.path.exists(path):
            return "-"

        first_ts = None
        last_ts = None

        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    ts = row.get("timestamp_ms")
                    if ts is None:
                        continue

                    ts = int(float(ts))

                    if first_ts is None:
                        first_ts = ts

                    last_ts = ts
        except Exception:
            return "-"

        if first_ts and last_ts:

            if first_ts > 10_000_000_000_000:
                first_ts = first_ts / 1000

            if last_ts > 10_000_000_000_000:
                last_ts = last_ts / 1000

            first_dt = datetime.fromtimestamp(first_ts / 1000).strftime("%d.%m.%Y")
            last_dt = datetime.fromtimestamp(last_ts / 1000).strftime("%d.%m.%Y")

            return f"{first_dt}  →  {last_dt}"

        return "-"

    # ─────────────────────────────────────────────
    # FIELD
    # ─────────────────────────────────────────────
    def _field(self, parent, row, name):
        ttk.Label(
            parent, text=name, style="Dim.TLabel"
        ).grid(row=row, column=0, sticky="w", pady=2)

        var = tk.StringVar(value="-")
        lbl = ttk.Label(
            parent,
            textvariable=var,
            style="Value.TLabel",
            width=26,
            anchor="e",
        )
        lbl.grid(row=row, column=1, sticky="e", pady=2)

        self.vars[name] = (var, lbl)

    # ─────────────────────────────────────────────
    # HEADER (3 BLÖCKE · BILD-LAYOUT)
    # ─────────────────────────────────────────────
    def _build_ui(self, parent):

        main = ttk.Frame(parent, padding=14)
        main.pack(fill="x", expand=False)

        main.grid_anchor("center")
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)
        main.grid_columnconfigure(2, weight=1)

        # LEFT BLOCK
        left = ttk.Frame(main)
        left.grid(row=0, column=0, sticky="n", padx=20)
        left.grid_columnconfigure(0, weight=1)
        left.grid_columnconfigure(1, weight=1)

        ttk.Label(
            left,
            text="TRADE SUMMARY",
            style="Title.TLabel",
            anchor="center",
            justify="center"
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        left_fields = [
            "TRADES",
            "TP_COUNT",
            "SL_COUNT",
            "WINRATE",
            "PROFIT_FACTOR",
        ]

        for row_index, field_name in enumerate(left_fields, start=1):
            self._field(left, row_index, field_name)

        # CENTER BLOCK
        center = ttk.Frame(main)
        center.grid(row=0, column=1, sticky="n", padx=20)
        center.grid_columnconfigure(0, weight=1)
        center.grid_columnconfigure(1, weight=1)

        ttk.Label(
            center,
            text="PNL / KPI",
            style="Title.TLabel",
            anchor="center",
            justify="center"
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        center_fields = [
            "PNL_NETTO",
            "PNL_TP",
            "PNL_SL",
            "ZONE_SHARE",
            "Time_Range",
        ]

        for row_index, field_name in enumerate(center_fields, start=1):
            self._field(center, row_index, field_name)

        # RIGHT BLOCK
        right = ttk.Frame(main)
        right.grid(row=0, column=2, sticky="n", padx=20)
        right.grid_columnconfigure(0, weight=1)
        right.grid_columnconfigure(1, weight=1)

        ttk.Label(
            right,
            text="MCM STATE",
            style="Title.TLabel",
            anchor="center",
            justify="center"
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        right_fields = [
            "FIELD_DENSITY",
            "FIELD_STABILITY",
            "REGULATORY_LOAD",
            "ACTION_CAPACITY",
            "RECOVERY_NEED",
            "SURVIVAL_PRESSURE",
            "EXPECTANCY",            
            "MAX_DD_PCT",
            "ATTEMPT_DENSITY",
            "CONTEXT_QUALITY",
            "OVERTRADE_PRESSURE",                        
        ]

        for row_index, field_name in enumerate(right_fields, start=1):
            self._field(right, row_index, field_name)

    # ─────────────────────────────────────────────
    # READ MEMORY STATE
    # ─────────────────────────────────────────────
    def _read_memory_state(self):
        path = self._resolve_memory_state_path()

        if not os.path.exists(path):
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
        
    # ─────────────────────────────────────────────
    # EQUITY RESET (bei Bot-Neustart / CSV Reset)
    # ─────────────────────────────────────────────
    def _reset_equity_state(self):
        self._eq_trades = []
        self._eq_pnl_netto = []
        self._eq_pnl_tp = []
        self._eq_pnl_sl = []
        self._eq_last_line_count = 0

        if hasattr(self, "line_total"):
            self.line_total.set_data([], [])
            self.line_win.set_data([], [])
            self.line_loss.set_data([], [])
            self.eq_canvas.draw_idle()

        # --------------------------------------------------
        # BACKTEST TOTAL SIZE + CSV TIMESTAMP RANGE
        # --------------------------------------------------
        self._workspace_rows_total = 0
        self._csv_start_ts = None
        self._csv_end_ts = None

        try:
            if os.path.exists(WORKSPACE_PATH):

                with open(WORKSPACE_PATH, "r", encoding="utf-8") as f:

                    reader = csv.reader(f)
                    header = next(reader, None)

                    first_row = next(reader, None)

                    last_row = None
                    rows = 0

                    for row in reader:
                        last_row = row
                        rows += 1

                    self._workspace_rows_total = max(rows - Config.WINDOW_SIZE, 1)

                    if first_row:
                        self._csv_start_ts = first_row[0]

                    if last_row:
                        self._csv_end_ts = last_row[0]

        except Exception:

            self._workspace_rows_total = 0
            self._csv_start_ts = None
            self._csv_end_ts = None
    # ─────────────────────────────────────────────
    # EQUITY WINDOW
    # ─────────────────────────────────────────────
    def _build_equity_window(self, parent):
        main = ttk.Frame(parent)
        main.pack(fill="both", expand=True)
        
        plot_frame = ttk.Frame(main)
        plot_frame.pack(fill="both", expand=True)

        fig = Figure(figsize=(9, 5), dpi=100, facecolor=BG)
        self.eq_ax = fig.add_subplot(111)
        self.eq_ax.set_facecolor(BG)
        self.eq_ax.tick_params(colors=FG)

        for spine in self.eq_ax.spines.values():
            spine.set_color(FG_DIM)

        self.eq_ax.grid(True, color="#1e1e1e", linestyle="-", linewidth=0.5)

        # --------------------------------------------------
        # RL Heatmap Background
        # --------------------------------------------------
        matrix = self._draw_rl_heatmap()

        if matrix is not None:
            self._ensure_heatmap_artist(matrix, alpha=heatmap_alpha)

            try:
                self._rl_last_mtime = os.path.getmtime(self._resolve_memory_state_path())
            except Exception:
                self._rl_last_mtime = 0.0

        self.line_total, = self.eq_ax.plot([], [], label="PNL_NETTO", color=green)
        self.line_win, = self.eq_ax.plot([], [], label="PNL_TP", color=orange)
        self.line_loss, = self.eq_ax.plot([], [], label="PNL_SL", color=red)

        legend = self.eq_ax.legend(facecolor=BG, edgecolor=FG_DIM)
        for text in legend.get_texts():
            text.set_color(FG)

        self.eq_ax.set_xlabel("Trades", color=FG)
        self.eq_ax.set_ylabel("PnL", color=FG)

        # --------------------------------------------------
        # BACKTEST PROGRESS BAR
        # --------------------------------------------------
        if Config.MODE == 'BACKTEST': #LIVE
            progress_frame = ttk.Frame(plot_frame)
            progress_frame.pack(fill="x", padx=100, pady=(6, 4))

            self.progress = ttk.Progressbar(
                progress_frame,
                orient="horizontal",
                mode="determinate"
            )

            self.progress.pack(side="left", fill="x", expand=True)

            self.progress_text = tk.Label(
                progress_frame,
                text="0%",
                fg=FG,
                bg=BG,
                font=("Arial", 12),
                relief= "raised",
                stat= 'normal',
                width=6,
                anchor="center"
            )

            self.progress_text.pack(side="left", padx=(5, 10))

        self.eq_canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        self.eq_canvas.draw_idle()
        self.eq_canvas.get_tk_widget().configure(bg=BG, highlightthickness=0)
        self.eq_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(0, 60))   

    # ─────────────────────────────────────────────
    # READ STATS
    # ─────────────────────────────────────────────
    def _read_stats(self):
        if not os.path.exists(STATS_PATH):
            return {}

        try:
            with open(STATS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    # ─────────────────────────────────────────────
    # LOOP UPDATE
    # ─────────────────────────────────────────────
    def _update_loop(self):
        stats = self._read_stats()

        trades = int(stats.get("trades", 0) or 0)
        tp = int(stats.get("tp", 0) or 0)
        sl = int(stats.get("sl", 0) or 0)

        pnl_netto = float(stats.get("pnl_netto", 0.0) or 0.0)
        pnl_tp = float(stats.get("pnl_tp", 0.0) or 0.0)
        pnl_sl = float(stats.get("pnl_sl", 0.0) or 0.0)

        kpi_summary = dict(stats.get("kpi_summary", {}) or {})
        proof = dict(kpi_summary.get("proof", {}) or {})
        memory_state = dict(self._read_memory_state() or {})

        winrate = float(proof.get("winrate", 0.0) or 0.0) * 100.0
        expectancy = float(proof.get("expectancy", 0.0) or 0.0)
        profit_factor = float(proof.get("profit_factor", 0.0) or 0.0)
        attempt_density = float(proof.get("attempt_density", 0.0) or 0.0)
        context_quality = float(proof.get("context_quality", 0.0) or 0.0)
        overtrade_pressure = float(proof.get("overtrade_pressure", 0.0) or 0.0)
        zone_share = float(proof.get("attempt_zone_share", 0.0) or 0.0)
        max_dd_pct = float(proof.get("max_drawdown_pct", 0.0) or 0.0) * 100.0
        field_density = float(memory_state.get("field_density", 0.0) or 0.0)
        field_stability = float(memory_state.get("field_stability", 0.0) or 0.0)
        regulatory_load = float(memory_state.get("regulatory_load", 0.0) or 0.0)
        action_capacity = float(memory_state.get("action_capacity", 0.0) or 0.0)
        recovery_need = float(memory_state.get("recovery_need", 0.0) or 0.0)
        survival_pressure = float(memory_state.get("survival_pressure", 0.0) or 0.0)

        self.vars["TRADES"][0].set(trades)
        self.vars["TP_COUNT"][0].set(tp)
        self.vars["SL_COUNT"][0].set(sl)
        self.vars["WINRATE"][0].set(f"{winrate:.2f} %")
        self.vars["EXPECTANCY"][0].set(f"{expectancy:.4f}")
        self.vars["PROFIT_FACTOR"][0].set(f"{profit_factor:.3f}")
        self.vars["MAX_DD_PCT"][0].set(f"{max_dd_pct:.2f} %")

        self.vars["PNL_NETTO"][0].set(f"{pnl_netto:.4f}")
        self.vars["PNL_TP"][0].set(f"{pnl_tp:.4f}")
        self.vars["PNL_SL"][0].set(f"{pnl_sl:.4f}")
        self.vars["ATTEMPT_DENSITY"][0].set(f"{attempt_density:.3f}")
        self.vars["CONTEXT_QUALITY"][0].set(f"{context_quality:.3f}")
        self.vars["OVERTRADE_PRESSURE"][0].set(f"{overtrade_pressure:.3f}")
        self.vars["ZONE_SHARE"][0].set(f"{zone_share * 100.0:.2f} %")
        self.vars["FIELD_DENSITY"][0].set(f"{field_density:.3f}")
        self.vars["FIELD_STABILITY"][0].set(f"{field_stability:.3f}")
        self.vars["REGULATORY_LOAD"][0].set(f"{regulatory_load:.3f}")
        self.vars["ACTION_CAPACITY"][0].set(f"{action_capacity:.3f}")
        self.vars["RECOVERY_NEED"][0].set(f"{recovery_need:.3f}")
        self.vars["SURVIVAL_PRESSURE"][0].set(f"{survival_pressure:.3f}")

        ws_range = self.print_Time_Range(WORKSPACE_PATH)
        self.vars["Time_Range"][0].set(ws_range)

        self.vars["PNL_NETTO"][1].configure(foreground=green)
        self.vars["PNL_TP"][1].configure(foreground=orange)
        self.vars["PNL_SL"][1].configure(foreground=red)

        self._update_equity_plot()

        self.root.after(REFRESH_MS, self._update_loop)

    # ─────────────────────────────────────────────
    # EQUITY UPDATE
    # ─────────────────────────────────────────────
    def _update_equity_plot(self):

        if not os.path.exists(EQUITY_PATH):
            return

        try:
            with open(EQUITY_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()

            total_lines = len(lines)

            if total_lines < self._eq_last_line_count:
                self._reset_equity_state()
                self._load_full_equity()

            if total_lines > self._eq_last_line_count:

                new_lines = lines[self._eq_last_line_count:]
                self._eq_last_line_count = total_lines

                for line in new_lines:
                    parts = line.strip().split(",")
                    if len(parts) != 4:
                        continue
                    if parts[0] == "trade":
                        continue

                    self._eq_trades.append(int(parts[0]))
                    self._eq_pnl_netto.append(float(parts[1]))
                    self._eq_pnl_tp.append(float(parts[2]))
                    self._eq_pnl_sl.append(float(parts[3]))

        except Exception:
            return

        if not self._eq_trades:
            return

        # --------------------------------------------------
        # RL HEATMAP LIVE UPDATE (mit mtime-Prüfung)
        # --------------------------------------------------
        path = self._resolve_memory_state_path()

        if os.path.exists(path):
            try:
                mtime = os.path.getmtime(path)
            except Exception:
                mtime = 0.0

            if mtime > self._rl_last_mtime:

                matrix = self._draw_rl_heatmap()

                if matrix is not None:
                    self._ensure_heatmap_artist(matrix, alpha=0.18)
                    self._rl_last_mtime = mtime

        self.line_total.set_data(self._eq_trades, self._eq_pnl_netto)
        self.line_win.set_data(self._eq_trades, self._eq_pnl_tp)
        self.line_loss.set_data(self._eq_trades, self._eq_pnl_sl)

        self.eq_ax.relim()
        self.eq_ax.autoscale_view()

        self.eq_canvas.draw_idle()
        # --------------------------------------------------
        # BACKTEST PROGRESS UPDATE
        # --------------------------------------------------
        if self._workspace_rows_total > 0 and Config.MODE == 'BACKTEST':

            current_ts = None

            try:

                if os.path.exists(STATS_PATH):

                    with open(STATS_PATH, "r", encoding="utf-8") as f:

                        stats_data = json.load(f)

                        current_ts = stats_data.get("current_timestamp")

            except Exception:

                current_ts = None


            ts_value = None

            if current_ts:

                try:

                    ts_value = float(current_ts)

                    # µs → s
                    if ts_value > 10_000_000_000_000:
                        ts_value /= 1_000_000.0

                    # ms → s
                    elif ts_value > 10_000_000_000:
                        ts_value /= 1_000.0

                    if not (1_000_000_000 < ts_value < 4_000_000_000):
                        ts_value = None

                except Exception:

                    ts_value = None


            progress = 0.0

            if ts_value and self._csv_start_ts and self._csv_end_ts:

                try:

                    start_ts = float(self._csv_start_ts)
                    end_ts = float(self._csv_end_ts)

                    if start_ts > 10_000_000_000_000:
                        start_ts /= 1_000_000.0
                    elif start_ts > 10_000_000_000:
                        start_ts /= 1_000.0

                    if end_ts > 10_000_000_000_000:
                        end_ts /= 1_000_000.0
                    elif end_ts > 10_000_000_000:
                        end_ts /= 1_000.0

                    if end_ts > start_ts:
                        progress = (ts_value - start_ts) / (end_ts - start_ts)
                        progress = max(0.0, min(progress, 1.0))

                except Exception:

                    progress = 0.0

            percent = int(progress * 100)

            if percent < 0:
                percent = 0
            elif percent > 100:
                percent = 100

            self.progress["value"] = percent
            self.progress_text.config(text=f"{percent}%")
# ==================================================
# START
# ==================================================
if __name__ == "__main__":
    root = tk.Tk()
    TradeStatsGUI(root)
    root.mainloop()
