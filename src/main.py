import asyncio
import threading
import traceback
from pathlib import Path

import flet as ft
import pandas as pd

def _try_import():
    try:
        import pm4py
        return pm4py
    except ImportError:
        return None

pm4py = _try_import()

# ══════════════════════════════════════════════════════════════════════════════
# DESIGN TOKENS
# ══════════════════════════════════════════════════════════════════════════════
BG1    = "#0f172a"
BG2    = "#1e293b"
BG3    = "#334155"
FG1    = "#f1f5f9"
FG2    = "#cbd5e1"
FG3    = "#94a3b8"
ACCENT = "#38bdf8"
SUCCESS= "#10b981"
WARNING= "#f59e0b"
ERROR  = "#ef4444"
BORDER = "#334155"

# ══════════════════════════════════════════════════════════════════════════════
# APP STATE
# ══════════════════════════════════════════════════════════════════════════════
class AppState:
    def __init__(self):
        self.log        = None
        self.log_path   = ""
        self.net        = None
        self.im         = None
        self.fm         = None
        self.tree       = None
        self.model_name = ""

state = AppState()

# ══════════════════════════════════════════════════════════════════════════════
# UI HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _lbl(text):
    return ft.Text(text, size=12, weight=ft.FontWeight.W_500, color=FG2)

def _mono(ref=None, value=""):
    return ft.Text(ref=ref, value=value, size=12, color=FG2,
                   font_family="Courier New", selectable=True)

def _card(title, body, accent=ACCENT):
    return ft.Container(
        content=ft.Column([
            ft.Text(title, size=16, weight=ft.FontWeight.W_600, color=accent),
            ft.Divider(color=BORDER, height=1),
            body,
        ], spacing=10),
        bgcolor=BG2,
        border=ft.Border.all(1, BORDER),
        border_radius=12, padding=20,
        margin=ft.Margin.only(bottom=12),
    )

def _infobox(text):
    return ft.Container(
        content=ft.Text(text, size=12, color=FG2),
        bgcolor="#0e2030",
        border=ft.Border.only(left=ft.BorderSide(3, ACCENT)),
        border_radius=6, padding=12,
        margin=ft.Margin.only(bottom=10),
    )

def _badge(text, fg, bg):
    return ft.Container(
        content=ft.Text(text, size=11, weight=ft.FontWeight.W_600, color=fg),
        bgcolor=bg, border_radius=20,
        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
    )

def _dd(options, ref=None, value=None):
    return ft.Dropdown(
        ref=ref, value=value,
        options=[ft.dropdown.Option(o) for o in options],
        bgcolor=BG3, color=FG1,
        border_color=BORDER, focused_border_color=ACCENT,
        text_size=13, height=44,
    )

def _tf(placeholder="", value="", ref=None,
        keyboard_type=ft.KeyboardType.TEXT):
    return ft.TextField(
        ref=ref, value=value, hint_text=placeholder,
        bgcolor=BG3, color=FG1,
        border_color=BORDER, focused_border_color=ACCENT,
        hint_style=ft.TextStyle(color=FG3),
        text_size=13, height=44, keyboard_type=keyboard_type,
    )

def _btn(text, icon_name, on_click, style="primary"):
    bg = {"primary": ACCENT, "secondary": BG3,
          "success": SUCCESS, "danger": ERROR}.get(style, ACCENT)
    fg = BG1 if style in ("primary", "success") else FG1
    return ft.Button(
        content=ft.Row(
            [ft.Icon(icon_name, size=15, color=fg),
             ft.Text(text, size=13, weight=ft.FontWeight.W_600, color=fg)],
            spacing=7, tight=True,
        ),
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=bg,
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
        ),
    )

def _section_header(icon, title, subtitle):
    return ft.Column([
        ft.Text(f"{icon} {title}", size=26, weight=ft.FontWeight.BOLD, color=FG1),
        ft.Text(subtitle, size=13, color=FG3),
        ft.Divider(color=BORDER),
    ], spacing=4)

def _spin_row(ref):
    return ft.Container(
        ref=ref, visible=False,
        content=ft.Row([
            ft.ProgressRing(color=ACCENT, width=20, height=20),
            ft.Text("Läuft…", color=FG3, size=12),
        ], spacing=8),
    )

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main(page: ft.Page):
    page.title = "PM4PY Suite"
    page.bgcolor = BG1
    page.padding = 0
    page.window_min_width = 1000
    page.window_min_height = 640

    content_area = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=0)

    def snack(msg, color=ACCENT, duration=4000):
        page.snack_bar = ft.SnackBar(
            ft.Text(msg, color=BG1, weight=ft.FontWeight.W_500),
            bgcolor=color, duration=duration,
        )
        page.snack_bar.open = True
        page.update()

    def err(msg):
        snack(f"❌ {msg}", ERROR, 6000)

    async def run_bg(fn, *args, **kwargs):
        return await asyncio.to_thread(fn, *args, **kwargs)

    # ═════════════════════════════════════════════════════════════════════
    # IMPORT
    # ═════════════════════════════════════════════════════════════════════
    def build_import():
        file_lbl     = ft.Ref[ft.Text]()
        fmt_ref      = ft.Ref[ft.Dropdown]()
        case_ref     = ft.Ref[ft.TextField]()
        act_ref      = ft.Ref[ft.TextField]()
        ts_ref       = ft.Ref[ft.TextField]()
        info_ref     = ft.Ref[ft.Container]()
        info_txt_ref = ft.Ref[ft.Text]()
        spin_ref     = ft.Ref[ft.Container]()
        picked_path  = [""]

        csv_opts = ft.Container(
            visible=False,
            content=ft.Column([
                ft.Text("CSV Spalten-Mapping", size=13,
                        weight=ft.FontWeight.W_600, color=FG3),
                ft.Row([
                    ft.Column([_lbl("Case-ID Spalte"),
                               _tf("case:concept:name", "case:concept:name", case_ref)], expand=1),
                    ft.Column([_lbl("Aktivitäts-Spalte"),
                               _tf("concept:name", "concept:name", act_ref)], expand=1),
                    ft.Column([_lbl("Timestamp-Spalte"),
                               _tf("time:timestamp", "time:timestamp", ts_ref)], expand=1),
                ], spacing=12),
            ], spacing=6),
        )

        async def pick_file(e):
            files = await ft.FilePicker().pick_files(
                dialog_title="Event Log öffnen",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["xes", "csv", "parquet"],
            )
            if not files:
                return
            f = files[0]
            picked_path[0] = f.path
            file_lbl.current.value = f.name
            ext = Path(f.name).suffix.lower()
            fmt_map = {".xes": "XES", ".csv": "CSV", ".parquet": "Parquet"}
            if ext in fmt_map:
                fmt_ref.current.value = fmt_map[ext]
            csv_opts.visible = (ext == ".csv")
            file_lbl.current.update()
            fmt_ref.current.update()
            csv_opts.update()

        async def load_log(e):
            if not picked_path[0]:
                err("Bitte erst eine Datei auswählen."); return

            path = picked_path[0]
            fmt = fmt_ref.current.value
            case_id = case_ref.current.value or "case:concept:name"
            activity_key = act_ref.current.value or "concept:name"
            timestamp_key = ts_ref.current.value or "time:timestamp"

            def _load(path, fmt, case_id, activity_key, timestamp_key):
                if fmt == "XES":
                    return pm4py.read_xes(path)
                elif fmt == "CSV":
                    raw = pd.read_csv(path)
                    return pm4py.format_dataframe(
                        raw,
                        case_id=case_id,
                        activity_key=activity_key,
                        timestamp_key=timestamp_key,
                    )
                else:
                    raw = pd.read_parquet(path)
                    return pm4py.format_dataframe(raw)

            if spin_ref.current:
                spin_ref.current.visible = True
                page.update()

            try:
                df = await run_bg(_load, path, fmt, case_id, activity_key, timestamp_key)
            except Exception as exc:
                traceback.print_exc()
                err(str(exc))
                return
            finally:
                if spin_ref.current:
                    spin_ref.current.visible = False
                    page.update()

            state.log = df
            n_cases  = df["case:concept:name"].nunique()
            n_events = len(df)
            acts = sorted(df["concept:name"].unique())
            t_min = df["time:timestamp"].min()
            t_max = df["time:timestamp"].max()
            info_txt_ref.current.value = (
                f"Datei:       {Path(path).name}\n"
                f"Format:      {fmt}\n"
                f"Cases:       {n_cases:,}\n"
                f"Events:      {n_events:,}\n"
                f"Zeitraum:    {str(t_min)[:10]} → {str(t_max)[:10]}\n"
                f"Aktivitäten: {len(acts)}\n"
                f"  {', '.join(acts[:10])}"
                + (" …" if len(acts) > 10 else "")
            )
            info_ref.current.visible = True
            page.update()
            snack(f"✅ {n_cases:,} Cases, {n_events:,} Events geladen", SUCCESS)

        return ft.Column([
            _section_header("📂", "Event Log Import",
                            "Laden Sie Ihren Event Log (XES, CSV, Parquet)"),
            _card("Datei hochladen", ft.Column([
                _infobox("PM4PY unterstützt XES, CSV und Parquet. "
                         "Bei CSV bitte Spaltennamen angeben."),
                ft.Row([
                    _btn("Datei wählen…", ft.Icons.FOLDER_OPEN, pick_file),
                    ft.Text(ref=file_lbl, value="Keine Datei ausgewählt",
                            size=13, color=FG3),
                ], spacing=12),
                ft.Container(height=4),
                _lbl("Format"),
                _dd(["XES", "CSV", "Parquet"], ref=fmt_ref, value="XES"),
                csv_opts,
                ft.Container(height=6),
                ft.Row([
                    _btn("Log laden", ft.Icons.DOWNLOAD, load_log),
                    _spin_row(spin_ref),
                ], spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=6)),
            ft.Container(
                ref=info_ref, visible=False,
                content=_card("Geladener Log", ft.Column([
                    _badge("✓ Log erfolgreich geladen", SUCCESS, "#0d2b1e"),
                    ft.Container(
                        content=_mono(ref=info_txt_ref),
                        bgcolor=BG3, border_radius=8, padding=14,
                    ),
                ], spacing=10)),
            ),
        ], spacing=0, scroll=ft.ScrollMode.AUTO)

    # ═════════════════════════════════════════════════════════════════════
    # ALPHA MINER
    # ═════════════════════════════════════════════════════════════════════
    def build_alpha():
        var_ref  = ft.Ref[ft.Dropdown]()
        out_ref  = ft.Ref[ft.Container]()
        txt_ref  = ft.Ref[ft.Text]()
        spin_ref = ft.Ref[ft.Container]()

        async def run(e):
            if state.log is None: err("Kein Log geladen!"); return
            variant = var_ref.current.value

            def _run(log, variant):
                if variant == "Alpha Classic":
                    return pm4py.discover_petri_net_alpha(log)
                return pm4py.discover_petri_net_alpha_plus(log)

            if spin_ref.current:
                spin_ref.current.visible = True
                page.update()

            try:
                net, im, fm = await run_bg(_run, state.log, variant)
            except Exception as exc:
                traceback.print_exc()
                err(str(exc))
                return
            finally:
                if spin_ref.current:
                    spin_ref.current.visible = False
                    page.update()

            state.net = net; state.im = im; state.fm = fm
            state.model_name = f"Alpha ({variant})"
            txt_ref.current.value = (
                f"Variante:    {variant}\n"
                f"Places:      {len(net.places)}\n"
                f"Transitions: {len(net.transitions)}\n"
                f"Arcs:        {len(net.arcs)}"
            )
            out_ref.current.visible = True
            page.update()
            snack("✅ Alpha Miner abgeschlossen", SUCCESS)

        def viz(e):
            if state.net is None: err("Erst Discovery starten!"); return
            threading.Thread(target=lambda: pm4py.view_petri_net(
                state.net, state.im, state.fm), daemon=True).start()

        return ft.Column([
            _section_header("α", "Alpha Miner", "Process Discovery mit dem Alpha Algorithmus"),
            _card("Konfiguration", ft.Column([
                _infobox("Der Alpha Miner entdeckt ein Petri-Netz aus dem Event Log."),
                _lbl("Variante"),
                _dd(["Alpha Classic", "Alpha Plus"], ref=var_ref, value="Alpha Classic"),
                ft.Container(height=8),
                ft.Row([
                    _btn("Discovery starten", ft.Icons.PLAY_ARROW, run),
                    _btn("Petri-Netz anzeigen", ft.Icons.VISIBILITY, viz, "secondary"),
                    _spin_row(spin_ref),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=6)),
            ft.Container(ref=out_ref, visible=False,
                content=_card("Ergebnis", ft.Column([
                    _badge("✓ Petri-Netz generiert", ACCENT, "#0b1e2d"),
                    ft.Container(content=_mono(ref=txt_ref), bgcolor=BG3, border_radius=8, padding=14),
                ], spacing=10))),
        ], spacing=0, scroll=ft.ScrollMode.AUTO)

    # ═════════════════════════════════════════════════════════════════════
    # INDUCTIVE MINER
    # ═════════════════════════════════════════════════════════════════════
    def build_inductive():
        var_ref   = ft.Ref[ft.Dropdown]()
        noise_ref = ft.Ref[ft.TextField]()
        out_ref   = ft.Ref[ft.Container]()
        txt_ref   = ft.Ref[ft.Text]()
        spin_ref  = ft.Ref[ft.Container]()

        async def run(e):
            if state.log is None: err("Kein Log geladen!"); return
            variant = var_ref.current.value
            try: noise = float(noise_ref.current.value or "0.0")
            except ValueError: err("Noise Threshold muss Zahl sein!"); return

            def _run(log, noise):
                net, im, fm = pm4py.discover_petri_net_inductive(log, noise_threshold=noise)
                tree = pm4py.discover_process_tree_inductive(log, noise_threshold=noise)
                return net, im, fm, tree

            if spin_ref.current:
                spin_ref.current.visible = True
                page.update()

            try:
                net, im, fm, tree = await run_bg(_run, state.log, noise)
            except Exception as exc:
                traceback.print_exc()
                err(str(exc))
                return
            finally:
                if spin_ref.current:
                    spin_ref.current.visible = False
                    page.update()

            state.net = net; state.im = im; state.fm = fm; state.tree = tree
            state.model_name = f"Inductive ({variant})"
            txt_ref.current.value = (
                f"Variante:    {variant}\n"
                f"Noise:       {noise}\n"
                f"Places:      {len(net.places)}\n"
                f"Transitions: {len(net.transitions)}\n"
                f"Arcs:        {len(net.arcs)}\n"
                f"Tree:        {str(tree)[:200]}"
            )
            out_ref.current.visible = True
            page.update()
            snack("✅ Inductive Miner abgeschlossen", SUCCESS)

        def viz_tree(e):
            if state.tree is None: err("Erst Discovery starten!"); return
            threading.Thread(target=lambda: pm4py.view_process_tree(state.tree), daemon=True).start()

        def viz_net(e):
            if state.net is None: err("Erst Discovery starten!"); return
            threading.Thread(target=lambda: pm4py.view_petri_net(state.net, state.im, state.fm), daemon=True).start()

        return ft.Column([
            _section_header("🔄", "Inductive Miner",
                            "Robuste Process Discovery mit garantiert soundem Modell"),
            _card("Konfiguration", ft.Column([
                _infobox("Garantiert soundes Modell. IMf filtert mit Noise Threshold seltene Abläufe."),
                _lbl("Variante"),
                _dd(["IM (Standard)", "IMf (Noise Threshold)", "IMd (Direkt folgt)"],
                    ref=var_ref, value="IM (Standard)"),
                ft.Container(height=6),
                _lbl("Noise Threshold (0.0 – 1.0)"),
                _tf(value="0.0", ref=noise_ref, keyboard_type=ft.KeyboardType.NUMBER),
                ft.Container(height=8),
                ft.Row([
                    _btn("Discovery starten", ft.Icons.PLAY_ARROW, run),
                    _btn("Process Tree", ft.Icons.ACCOUNT_TREE, viz_tree, "secondary"),
                    _btn("Petri-Netz", ft.Icons.SHARE, viz_net, "secondary"),
                    _spin_row(spin_ref),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True),
            ], spacing=6)),
            ft.Container(ref=out_ref, visible=False,
                         content=_card("Ergebnis", ft.Column([
                             _badge("✓ Modell generiert", SUCCESS, "#0d2b1e"),
                             ft.Container(content=_mono(ref=txt_ref), bgcolor=BG3, border_radius=8, padding=14),
                         ], spacing=10))),
        ], spacing=0, scroll=ft.ScrollMode.AUTO)

    # ═════════════════════════════════════════════════════════════════════
    # HEURISTICS MINER
    # ═════════════════════════════════════════════════════════════════════
    def build_heuristics():
        dep_ref  = ft.Ref[ft.TextField]()
        and_ref  = ft.Ref[ft.TextField]()
        loop_ref = ft.Ref[ft.TextField]()
        mac_ref  = ft.Ref[ft.TextField]()
        out_ref  = ft.Ref[ft.Container]()
        txt_ref  = ft.Ref[ft.Text]()
        spin_ref = ft.Ref[ft.Container]()

        async def run(e):
            if state.log is None: err("Kein Log geladen!"); return
            try:
                dep  = float(dep_ref.current.value  or "0.5")
                and_ = float(and_ref.current.value  or "0.65")
                loop = float(loop_ref.current.value or "0.5")
            except ValueError: err("Parameter müssen Zahlen sein!"); return

            def _run(log, dep, and_, loop):
                return pm4py.discover_petri_net_heuristics(
                    log, dependency_threshold=dep,
                    and_threshold=and_, loop_two_threshold=loop)

            if spin_ref.current:
                spin_ref.current.visible = True
                page.update()

            try:
                net, im, fm = await run_bg(_run, state.log, dep, and_, loop)
            except Exception as exc:
                traceback.print_exc()
                err(str(exc))
                return
            finally:
                if spin_ref.current:
                    spin_ref.current.visible = False
                    page.update()

            state.net = net; state.im = im; state.fm = fm
            state.model_name = "Heuristics Miner"
            txt_ref.current.value = (
                f"Dependency:  {dep}\n"
                f"AND:         {and_}\n"
                f"Loop:        {loop}\n"
                f"Places:      {len(net.places)}\n"
                f"Transitions: {len(net.transitions)}\n"
                f"Arcs:        {len(net.arcs)}"
            )
            out_ref.current.visible = True
            page.update()
            snack("✅ Heuristics Miner abgeschlossen", SUCCESS)

        def viz(e):
            if state.net is None: err("Erst Discovery!"); return
            threading.Thread(
                target=lambda: pm4py.view_petri_net(state.net, state.im, state.fm),
                daemon=True,
            ).start()

        return ft.Column([
            _section_header("📊", "Heuristics Miner", "Frequenz-basierte Process Discovery"),
            _card("Parameter", ft.Column([
                ft.Row([
                    ft.Column([_lbl("Dependency Threshold"),
                               _tf(value="0.5", ref=dep_ref, keyboard_type=ft.KeyboardType.NUMBER)], expand=1),
                    ft.Column([_lbl("AND Threshold"),
                               _tf(value="0.65", ref=and_ref, keyboard_type=ft.KeyboardType.NUMBER)], expand=1),
                ], spacing=14),
                ft.Row([
                    ft.Column([_lbl("Loop Threshold"),
                               _tf(value="0.5", ref=loop_ref, keyboard_type=ft.KeyboardType.NUMBER)], expand=1),
                    ft.Column([_lbl("Min Activity Count"),
                               _tf(value="1", ref=mac_ref, keyboard_type=ft.KeyboardType.NUMBER)], expand=1),
                ], spacing=14),
                ft.Container(height=8),
                ft.Row([
                    _btn("Net generieren", ft.Icons.HUB, run),
                    _btn("Petri-Netz anzeigen", ft.Icons.VISIBILITY, viz, "secondary"),
                    _spin_row(spin_ref),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=10)),
            ft.Container(ref=out_ref, visible=False,
                         content=_card("Ergebnis", ft.Column([
                             _badge("✓ Heuristics Net generiert", SUCCESS, "#0d2b1e"),
                             ft.Container(content=_mono(ref=txt_ref), bgcolor=BG3, border_radius=8, padding=14),
                         ], spacing=10))),
        ], spacing=0, scroll=ft.ScrollMode.AUTO)

    # ═════════════════════════════════════════════════════════════════════
    # DFG
    # ═════════════════════════════════════════════════════════════════════
    def build_dfg():
        type_ref = ft.Ref[ft.Dropdown]()
        out_ref  = ft.Ref[ft.Container]()
        txt_ref  = ft.Ref[ft.Text]()
        spin_ref = ft.Ref[ft.Container]()

        async def run(e):
            if state.log is None: err("Kein Log geladen!"); return
            dtype = type_ref.current.value

            def _run(log, dtype):
                if dtype == "Frequency DFG":
                    dfg, sa, ea = pm4py.discover_dfg(log)
                else:
                    dfg, sa, ea = pm4py.discover_performance_dfg(log)
                return dfg, sa, ea, dtype

            if spin_ref.current:
                spin_ref.current.visible = True
                page.update()

            try:
                dfg, sa, ea, dtype = await run_bg(_run, state.log, dtype)
            except Exception as exc:
                traceback.print_exc()
                err(str(exc))
                return
            finally:
                if spin_ref.current:
                    spin_ref.current.visible = False
                    page.update()

            top5 = sorted(dfg.items(),
                          key=lambda x: x[1] if isinstance(x[1], (int, float))
                          else x[1].get("mean", 0), reverse=True)[:5]
            lines = [f"Typ: {dtype}", f"Kanten: {len(dfg)}",
                     f"Start: {list(sa.keys())[:5]}", ""]
            for (a, b), v in top5:
                val = v if isinstance(v, (int, float)) else v.get("mean", 0)
                unit = "×" if dtype == "Frequency DFG" else "s Ø"
                lines.append(f" {a} → {b}: {val:.0f}{unit}")
            txt_ref.current.value = "\n".join(lines)
            out_ref.current.visible = True
            page.update()
            snack("✅ DFG generiert", SUCCESS)

        def viz(e):
            if state.log is None: err("Kein Log geladen!"); return
            dtype = type_ref.current.value
            def _v():
                if dtype == "Frequency DFG":
                    dfg, sa, ea = pm4py.discover_dfg(state.log)
                    pm4py.view_dfg(dfg, sa, ea)
                else:
                    dfg, sa, ea = pm4py.discover_performance_dfg(state.log)
                    pm4py.view_performance_dfg(dfg, sa, ea)
            threading.Thread(target=_v, daemon=True).start()

        return ft.Column([
            _section_header("🔀", "Directly-Follows Graph (DFG)", "Visualisierung direkter Folgebeziehungen"),
            _card("Optionen", ft.Column([
                _lbl("DFG Typ"),
                _dd(["Frequency DFG", "Performance DFG"], ref=type_ref, value="Frequency DFG"),
                ft.Container(height=8),
                ft.Row([
                    _btn("DFG generieren", ft.Icons.SHARE, run),
                    _btn("DFG anzeigen", ft.Icons.VISIBILITY, viz, "secondary"),
                    _spin_row(spin_ref),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=6)),
            ft.Container(ref=out_ref, visible=False,
                content=_card("Ergebnis", ft.Column([
                    _badge("✓ DFG generiert", ACCENT, "#0b1e2d"),
                    ft.Container(content=_mono(ref=txt_ref), bgcolor=BG3, border_radius=8, padding=14),
                ], spacing=10))),
        ], spacing=0, scroll=ft.ScrollMode.AUTO)

    # ═════════════════════════════════════════════════════════════════════
    # TOKEN REPLAY
    # ═════════════════════════════════════════════════════════════════════
    def build_token():
        out_ref      = ft.Ref[ft.Container]()
        txt_ref      = ft.Ref[ft.Text]()
        spin_ref     = ft.Ref[ft.Container]()
        model_lbl    = ft.Ref[ft.Text]()

        async def pick_model(e):
            files = await ft.FilePicker().pick_files(
                dialog_title="Prozessmodell laden (PNML / BPMN)",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["pnml", "bpmn"],
            )
            if not files:
                return
            f = files[0]
            ext = Path(f.name).suffix.lower()
            if ext == ".bpmn":
                bpmn = pm4py.read_bpmn(f.path)
                net, im, fm = pm4py.convert_to_petri_net(bpmn)
            else:
                net, im, fm = pm4py.read_pnml(f.path)
            state.net = net; state.im = im; state.fm = fm
            state.model_name = Path(f.name).stem
            model_lbl.current.value = f"📄 {f.name}"
            model_lbl.current.update()
            snack(f"✅ Modell geladen: {f.name}", SUCCESS)

        async def run(e):
            if state.log is None: err("Kein Log geladen!"); return
            if state.net is None: err("Kein Modell vorhanden – Discovery starten oder PNML laden!"); return

            def _run(log, net, im, fm):
                replayed = pm4py.conformance_diagnostics_token_based_replay(
                    log, net, im, fm)
                fitness = pm4py.fitness_token_based_replay(
                    log, net, im, fm)
                return replayed, fitness

            if spin_ref.current:
                spin_ref.current.visible = True
                page.update()

            try:
                replayed, fitness = await run_bg(_run, state.log, state.net, state.im, state.fm)
            except Exception as exc:
                traceback.print_exc()
                err(str(exc))
                return
            finally:
                if spin_ref.current:
                    spin_ref.current.visible = False
                    page.update()

            n_fit = sum(1 for t in replayed if t.get("trace_is_fit", False))
            txt_ref.current.value = (
                f"Modell: {state.model_name}\n"
                f"Log Fitness: {fitness.get('log_fitness', 0):.4f}\n"
                f"Avg Trace Fitness: {fitness.get('average_trace_fitness', 0):.4f}\n"
                f"Fitting Traces: {n_fit}/{len(replayed)}"
                f" ({fitness.get('percentage_of_fitting_traces', 0):.1f}%)\n"
                f"Missing Tokens: {sum(t.get('missing_tokens',0) for t in replayed):,}\n"
                f"Remaining Tokens: {sum(t.get('remaining_tokens',0) for t in replayed):,}"
            )
            out_ref.current.visible = True
            page.update()
            snack(f"✅ Fitness = {fitness.get('log_fitness', 0):.4f}", SUCCESS)

        return ft.Column([
            _section_header("🎯", "Token-based Replay", "Conformance Checking mit Token Replay"),
            _card("Token Replay", ft.Column([
                _infobox("Verwendet das aktuelle Discovery-Modell oder ein extern geladenes PNML."),
                ft.Row([
                    _btn("PNML / BPMN laden…", ft.Icons.UPLOAD_FILE, pick_model, "secondary"),
                    ft.Text(ref=model_lbl,
                            value="(Discovery-Modell wird verwendet)",
                            size=12, color=FG3),
                ], spacing=10),
                ft.Container(height=6),
                ft.Row([_btn("Replay starten", ft.Icons.PLAY_CIRCLE, run), _spin_row(spin_ref)],
                       spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=8)),
            ft.Container(ref=out_ref, visible=False,
                content=_card("Ergebnisse", ft.Column([
                    _badge("✓ Replay abgeschlossen", SUCCESS, "#0d2b1e"),
                    ft.Container(content=_mono(ref=txt_ref), bgcolor=BG3, border_radius=8, padding=14),
                ], spacing=10))),
        ], spacing=0, scroll=ft.ScrollMode.AUTO)

    # ═════════════════════════════════════════════════════════════════════
    # ALIGNMENTS
    # ═════════════════════════════════════════════════════════════════════
    def build_alignments():
        out_ref   = ft.Ref[ft.Container]()
        txt_ref   = ft.Ref[ft.Text]()
        spin_ref  = ft.Ref[ft.Container]()
        model_lbl = ft.Ref[ft.Text]()

        async def pick_model(e):
            files = await ft.FilePicker().pick_files(
                dialog_title="Prozessmodell laden (PNML / BPMN)",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["pnml", "bpmn"],
            )
            if not files:
                return
            f = files[0]
            ext = Path(f.name).suffix.lower()
            if ext == ".bpmn":
                bpmn = pm4py.read_bpmn(f.path)
                net, im, fm = pm4py.convert_to_petri_net(bpmn)
            else:
                net, im, fm = pm4py.read_pnml(f.path)
            state.net = net; state.im = im; state.fm = fm
            state.model_name = Path(f.name).stem
            model_lbl.current.value = f"📄 {f.name}"
            model_lbl.current.update()
            snack(f"✅ Modell geladen: {f.name}", SUCCESS)

        async def run(e):
            if state.log is None: err("Kein Log geladen!"); return
            if state.net is None: err("Kein Modell vorhanden – Discovery starten oder PNML laden!"); return

            def _run(log, net, im, fm):
                fitness = pm4py.fitness_alignments(log, net, im, fm)
                aligned = pm4py.conformance_diagnostics_alignments(
                    log, net, im, fm)
                return fitness, aligned

            if spin_ref.current:
                spin_ref.current.visible = True
                page.update()

            try:
                fitness, aligned = await run_bg(_run, state.log, state.net, state.im, state.fm)
            except Exception as exc:
                traceback.print_exc()
                err(str(exc))
                return
            finally:
                if spin_ref.current:
                    spin_ref.current.visible = False
                    page.update()

            n_perfect = sum(1 for a in aligned if a.get("fitness", 0) == 1.0)
            avg_cost = sum(a.get("cost", 0) for a in aligned) / max(len(aligned), 1)
            txt_ref.current.value = (
                f"Modell: {state.model_name}\n"
                f"Log Fitness: {fitness.get('log_fitness', 0):.4f}\n"
                f"Avg Trace Fitness: {fitness.get('average_trace_fitness', 0):.4f}\n"
                f"Fitting Traces: {n_perfect}/{len(aligned)}"
                f" ({fitness.get('percentage_of_fitting_traces', 0):.1f}%)\n"
                f"Avg Alignment Cost:{avg_cost:.2f}"
            )
            out_ref.current.visible = True
            page.update()
            snack(f"✅ Alignments: Fitness = {fitness.get('log_fitness', 0):.4f}", SUCCESS)

        return ft.Column([
            _section_header("🔗", "Alignments", "Optimale Conformance Checking via Alignments"),
            _card("Konfiguration", ft.Column([
                _infobox("⚠️ Bei großen Logs kann die Berechnung mehrere Minuten dauern."),
                ft.Row([
                    _btn("PNML / BPMN laden…", ft.Icons.UPLOAD_FILE, pick_model, "secondary"),
                    ft.Text(ref=model_lbl,
                            value="(Discovery-Modell wird verwendet)",
                            size=12, color=FG3),
                ], spacing=10),
                ft.Container(height=6),
                ft.Row([_btn("Alignments berechnen", ft.Icons.LINK, run), _spin_row(spin_ref)],
                       spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=8)),
            ft.Container(ref=out_ref, visible=False,
                content=_card("Ergebnisse", ft.Column([
                    _badge("✓ Alignments berechnet", SUCCESS, "#0d2b1e"),
                    ft.Container(content=_mono(ref=txt_ref), bgcolor=BG3, border_radius=8, padding=14),
                ], spacing=10))),
        ], spacing=0, scroll=ft.ScrollMode.AUTO)

    # ═════════════════════════════════════════════════════════════════════
    # FILTERING
    # ═════════════════════════════════════════════════════════════════════
    def build_filter():
        t_start = ft.Ref[ft.TextField]()
        t_end   = ft.Ref[ft.TextField]()
        min_ev  = ft.Ref[ft.TextField]()
        max_ev  = ft.Ref[ft.TextField]()
        top_k   = ft.Ref[ft.TextField]()
        out_ref = ft.Ref[ft.Container]()
        txt_ref = ft.Ref[ft.Text]()

        def apply_filters(e):
            if state.log is None: err("Kein Log geladen!"); return
            df = state.log.copy()
            applied = []
            try:
                if t_start.current.value.strip():
                    df = pm4py.filter_time_range(
                        df, t_start.current.value.strip(),
                        t_end.current.value.strip() or "9999-12-31",
                        mode="traces_intersecting")
                    applied.append(f"Zeitraum: {t_start.current.value} – {t_end.current.value}")
                if min_ev.current.value.strip() or max_ev.current.value.strip():
                    mn = int(min_ev.current.value or "1")
                    mx = int(max_ev.current.value or "99999")
                    df = pm4py.filter_case_size(df, mn, mx)
                    applied.append(f"Case-Größe: {mn}–{mx}")
                if top_k.current.value.strip():
                    k = int(top_k.current.value)
                    df = pm4py.filter_variants_top_k(df, k)
                    applied.append(f"Top-{k} Varianten")
            except Exception as exc:
                err(str(exc)); return
            state.log = df
            n_c = df["case:concept:name"].nunique()
            n_e = len(df)
            txt_ref.current.value = (
                "Filter:\n  " + "\n  ".join(applied) + "\n\n"
                f"Cases:  {n_c:,}\nEvents: {n_e:,}"
            )
            out_ref.current.visible = True
            out_ref.current.update(); txt_ref.current.update()
            snack(f"✅ Filter angewendet – {n_c:,} Cases übrig", SUCCESS)

        def reset_filters(e):
            for r in [t_start, t_end, min_ev, max_ev, top_k]:
                r.current.value = ""
            page.update()
            snack("Filter zurückgesetzt. Log neu laden für Originalzustand.", WARNING)

        return ft.Column([
            _section_header("🔍", "Log Filtering", "Filtern Sie Event Logs nach verschiedenen Kriterien"),
            _card("Filter Optionen", ft.Column([
                ft.Row([
                    ft.Column([_lbl("Zeitraum Start"), _tf("YYYY-MM-DD", ref=t_start)], expand=1),
                    ft.Column([_lbl("Zeitraum Ende"),  _tf("YYYY-MM-DD", ref=t_end)],   expand=1),
                ], spacing=14),
                ft.Row([
                    ft.Column([_lbl("Min. Events/Case"),
                               _tf("1",  ref=min_ev, keyboard_type=ft.KeyboardType.NUMBER)], expand=1),
                    ft.Column([_lbl("Max. Events/Case"),
                               _tf("100", ref=max_ev, keyboard_type=ft.KeyboardType.NUMBER)], expand=1),
                    ft.Column([_lbl("Top-K Varianten"),
                               _tf("",   ref=top_k,  keyboard_type=ft.KeyboardType.NUMBER)], expand=1),
                ], spacing=14),
                ft.Container(height=6),
                ft.Row([
                    _btn("Filter anwenden", ft.Icons.FILTER_LIST, apply_filters),
                    _btn("Zurücksetzen", ft.Icons.RESTART_ALT, reset_filters, "secondary"),
                ], spacing=10),
            ], spacing=10)),
            ft.Container(ref=out_ref, visible=False,
                content=_card("Filter-Ergebnis", ft.Column([
                    _badge("✓ Filter angewendet", SUCCESS, "#0d2b1e"),
                    ft.Container(content=_mono(ref=txt_ref), bgcolor=BG3, border_radius=8, padding=14),
                ], spacing=10))),
        ], spacing=0, scroll=ft.ScrollMode.AUTO)

    # ═════════════════════════════════════════════════════════════════════
    # VARIANTS
    # ═════════════════════════════════════════════════════════════════════
    def build_variants():
        out_ref  = ft.Ref[ft.Container]()
        list_ref = ft.Ref[ft.Column]()
        spin_ref = ft.Ref[ft.Container]()

        async def run(e):
            if state.log is None: err("Kein Log geladen!"); return

            def _run(log):
                return pm4py.get_variants_as_tuples(log)

            if spin_ref.current:
                spin_ref.current.visible = True
                page.update()

            try:
                variants = await run_bg(_run, state.log)
            except Exception as exc:
                traceback.print_exc()
                err(str(exc))
                return
            finally:
                if spin_ref.current:
                    spin_ref.current.visible = False
                    page.update()

            sv = sorted(variants.items(), key=lambda x: x[1], reverse=True)
            total = sum(v for _, v in sv)
            items = []
            for i, (trace, count) in enumerate(sv[:20], 1):
                pct = count / total * 100
                acts = " → ".join(trace)
                items.append(ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Text(str(i), size=11, color=ACCENT,
                                            weight=ft.FontWeight.W_600), width=26),
                        ft.Column([
                            ft.Text(acts[:80]+("…" if len(acts)>80 else ""),
                                    size=12, color=FG1),
                            ft.Text(f"{count:,} Cases ({pct:.1f}%)", size=11, color=FG3),
                        ], spacing=2, expand=1),
                    ], spacing=8),
                    bgcolor=BG3, border_radius=6, padding=10,
                ))
            list_ref.current.controls = items
            out_ref.current.visible = True
            page.update()
            snack(f"✅ {len(sv)} Varianten gefunden", SUCCESS)

        return ft.Column([
            _section_header("📈", "Variant Analysis", "Analyse von Prozessvarianten"),
            _card("Varianten Analyse", ft.Column([
                ft.Row([_btn("Varianten analysieren", ft.Icons.STACKED_BAR_CHART, run),
                        _spin_row(spin_ref)],
                       spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ])),
            ft.Container(ref=out_ref, visible=False,
                content=_card("Top-20 Varianten",
                              ft.Column(ref=list_ref, controls=[], spacing=6))),
        ], spacing=0, scroll=ft.ScrollMode.AUTO)

    # ═════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═════════════════════════════════════════════════════════════════════
    def build_statistics():
        out_ref  = ft.Ref[ft.Container]()
        txt_ref  = ft.Ref[ft.Text]()
        spin_ref = ft.Ref[ft.Container]()

        async def run(e):
            if state.log is None: err("Kein Log geladen!"); return

            def _run(df):
                n_cases = df["case:concept:name"].nunique()
                n_events = len(df)
                ev_per_case = df.groupby("case:concept:name").size()
                acts = df["concept:name"].value_counts()
                case_ts = df.groupby("case:concept:name")["time:timestamp"]
                dur = (case_ts.max() - case_ts.min()).dt.total_seconds() / 86400
                return n_cases, n_events, ev_per_case, acts, dur

            if spin_ref.current:
                spin_ref.current.visible = True
                page.update()

            try:
                n_cases, n_events, epc, acts, dur = await run_bg(_run, state.log)
            except Exception as exc:
                traceback.print_exc()
                err(str(exc))
                return
            finally:
                if spin_ref.current:
                    spin_ref.current.visible = False
                    page.update()

            txt_ref.current.value = (
                f"══ Cases ══\n"
                f"Gesamt: {n_cases:,}\n"
                f"Ø Events/Case: {epc.mean():.1f}\n"
                f"Min/Max Events: {epc.min()} / {epc.max()}\n\n"
                f"══ Performance ══\n"
                f"Ø Dauer: {dur.mean():.2f} Tage\n"
                f"Median: {dur.median():.2f} Tage\n"
                f"Min/Max: {dur.min():.2f} / {dur.max():.2f} Tage\n\n"
                f"══ Aktivitäten ══\n"
                f"Unique: {len(acts)}\n"
                + "\n".join(f" {a}: {c:,}×" for a, c in acts.head(8).items())
            )
            out_ref.current.visible = True
            page.update()
            snack("✅ Statistiken berechnet", SUCCESS)

        return ft.Column([
            _section_header("📊", "Statistiken", "Event Log Statistiken und Metriken"),
            _card("Log Statistiken", ft.Column([
                ft.Row([_btn("Statistiken generieren", ft.Icons.BAR_CHART, run),
                        _spin_row(spin_ref)],
                       spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ])),
            ft.Container(ref=out_ref, visible=False,
                content=_card("Übersicht", ft.Column([
                    _badge("✓ Statistiken berechnet", SUCCESS, "#0d2b1e"),
                    ft.Container(content=_mono(ref=txt_ref), bgcolor=BG3, border_radius=8, padding=14),
                ], spacing=10))),
        ], spacing=0, scroll=ft.ScrollMode.AUTO)

    # ═════════════════════════════════════════════════════════════════════
    # PERFORMANCE
    # ═════════════════════════════════════════════════════════════════════
    def build_performance():
        out_ref  = ft.Ref[ft.Container]()
        txt_ref  = ft.Ref[ft.Text]()
        spin_ref = ft.Ref[ft.Container]()

        async def run(e):
            if state.log is None: err("Kein Log geladen!"); return

            def _run(log):
                dfg, sa, ea = pm4py.discover_performance_dfg(log)
                return dfg

            if spin_ref.current:
                spin_ref.current.visible = True
                page.update()

            try:
                dfg = await run_bg(_run, state.log)
            except Exception as exc:
                traceback.print_exc()
                err(str(exc))
                return
            finally:
                if spin_ref.current:
                    spin_ref.current.visible = False
                    page.update()

            top8 = sorted(dfg.items(),
                          key=lambda x: x[1].get("mean", 0), reverse=True)[:8]
            lines = ["Ø Wartezeiten (Stunden):\n"]
            for (a, b), v in top8:
                lines.append(
                    f" {a} → {b}\n"
                    f" Ø {v.get('mean',0)/3600:.1f}h "
                    f"min {v.get('min',0)/3600:.1f}h "
                    f"max {v.get('max',0)/3600:.1f}h"
                )
            txt_ref.current.value = "\n".join(lines)
            out_ref.current.visible = True
            page.update()
            snack("✅ Performance berechnet", SUCCESS)

        def viz(e):
            if state.log is None: err("Kein Log geladen!"); return
            def _v():
                dfg, sa, ea = pm4py.discover_performance_dfg(state.log)
                pm4py.view_performance_dfg(dfg, sa, ea)
            threading.Thread(target=_v, daemon=True).start()

        return ft.Column([
            _section_header("⚡", "Performance Analysis", "Zeitbasierte Prozessanalyse"),
            _card("Performance Metriken", ft.Column([
                ft.Row([
                    _btn("Wartezeiten berechnen", ft.Icons.TIMER, run),
                    _btn("Performance DFG", ft.Icons.HOURGLASS_EMPTY, viz, "secondary"),
                    _spin_row(spin_ref),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True),
            ])),
            ft.Container(ref=out_ref, visible=False,
                content=_card("Ergebnisse", ft.Column([
                    _badge("✓ Performance berechnet", SUCCESS, "#0d2b1e"),
                    ft.Container(content=_mono(ref=txt_ref), bgcolor=BG3, border_radius=8, padding=14),
                ], spacing=10))),
        ], spacing=0, scroll=ft.ScrollMode.AUTO)

    # ═════════════════════════════════════════════════════════════════════
    # SOCIAL NETWORK
    # ═════════════════════════════════════════════════════════════════════
    def build_social():
        type_ref = ft.Ref[ft.Dropdown]()
        out_ref  = ft.Ref[ft.Container]()
        txt_ref  = ft.Ref[ft.Text]()
        spin_ref = ft.Ref[ft.Container]()

        async def run(e):
            if state.log is None: err("Kein Log geladen!"); return
            if "org:resource" not in state.log.columns:
                err("Log hat keine 'org:resource' Spalte!"); return
            typ = type_ref.current.value

            def _run(log, typ):
                if typ == "Handover of Work":
                    return pm4py.discover_handover_of_work_network(log)
                elif typ == "Working Together":
                    return pm4py.discover_working_together_network(log)
                elif typ == "Subcontracting":
                    return pm4py.discover_subcontracting_network(log)
                else:
                    return pm4py.discover_similar_activities_network(log)

            if spin_ref.current:
                spin_ref.current.visible = True
                page.update()

            try:
                result = await run_bg(_run, state.log, typ)
            except Exception as exc:
                traceback.print_exc()
                err(str(exc))
                return
            finally:
                if spin_ref.current:
                    spin_ref.current.visible = False
                    page.update()

            if isinstance(result, dict):
                vals = sorted(result.items(), key=lambda x: x[1], reverse=True)[:8]
            else:
                vals = []
            lines = [f"Typ: {typ}\n", "Stärkste Verbindungen:"]
            for (a, b), v in vals:
                lines.append(f" {a} ↔ {b}: {float(v):.3f}")
            txt_ref.current.value = "\n".join(lines)
            out_ref.current.visible = True
            page.update()
            snack("✅ Social Network berechnet", SUCCESS)

        return ft.Column([
            _section_header("👥", "Social Network Analysis",
                            "Organisationsanalyse und Ressourcen-Interaktionen"),
            _card("Optionen", ft.Column([
                _infobox("Benötigt eine 'org:resource' Spalte im Event Log."),
                _lbl("Netzwerk Typ"),
                _dd(["Handover of Work", "Working Together",
                     "Subcontracting", "Similar Activities"],
                    ref=type_ref, value="Handover of Work"),
                ft.Container(height=8),
                ft.Row([_btn("Netzwerk generieren", ft.Icons.HUB, run), _spin_row(spin_ref)],
                       spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=6)),
            ft.Container(ref=out_ref, visible=False,
                content=_card("Ergebnis", ft.Column([
                    _badge("✓ Netzwerk berechnet", SUCCESS, "#0d2b1e"),
                    ft.Container(content=_mono(ref=txt_ref), bgcolor=BG3, border_radius=8, padding=14),
                ], spacing=10))),
        ], spacing=0, scroll=ft.ScrollMode.AUTO)

    # ═════════════════════════════════════════════════════════════════════
    # SIMULATION
    # ═════════════════════════════════════════════════════════════════════
    def build_simulation():
        cases_ref = ft.Ref[ft.TextField]()
        out_ref   = ft.Ref[ft.Container]()
        txt_ref   = ft.Ref[ft.Text]()
        spin_ref  = ft.Ref[ft.Container]()

        async def run(e):
            if state.net is None: err("Kein Prozessmodell vorhanden!"); return
            try: n = int(cases_ref.current.value or "100")
            except ValueError: err("Anzahl muss Ganzzahl sein!"); return

            def _run(net, im, fm, n):
                return pm4py.play_out(net, im, fm, parameters={"num_traces": n})

            if spin_ref.current:
                spin_ref.current.visible = True
                page.update()

            try:
                sim_log = await run_bg(_run, state.net, state.im, state.fm, n)
            except Exception as exc:
                traceback.print_exc()
                err(str(exc))
                return
            finally:
                if spin_ref.current:
                    spin_ref.current.visible = False
                    page.update()

            n_cases = sim_log["case:concept:name"].nunique()
            n_events = len(sim_log)
            acts = sim_log["concept:name"].value_counts().head(5)
            txt_ref.current.value = (
                f"Simulierte Cases: {n_cases:,}\n"
                f"Simulierte Events: {n_events:,}\n"
                f"Top Aktivitäten:\n"
                + "\n".join(f" {a}: {c}×" for a, c in acts.items())
            )
            out_ref.current.visible = True
            page.update()
            snack(f"✅ Simulation: {n_cases:,} Cases generiert", SUCCESS)

        return ft.Column([
            _section_header("🎲", "Process Simulation", "Simulieren Sie Prozessabläufe"),
            _card("Parameter", ft.Column([
                _infobox("Voraussetzung: Petri-Netz via Discovery erstellt."),
                _lbl("Anzahl Cases"),
                _tf(value="100", ref=cases_ref, keyboard_type=ft.KeyboardType.NUMBER),
                ft.Container(height=8),
                ft.Row([_btn("Simulation starten", ft.Icons.PLAY_ARROW, run),
                        _spin_row(spin_ref)],
                       spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=6)),
            ft.Container(ref=out_ref, visible=False,
                content=_card("Ergebnis", ft.Column([
                    _badge("✓ Simulation abgeschlossen", SUCCESS, "#0d2b1e"),
                    ft.Container(content=_mono(ref=txt_ref), bgcolor=BG3, border_radius=8, padding=14),
                ], spacing=10))),
        ], spacing=0, scroll=ft.ScrollMode.AUTO)

    # ═════════════════════════════════════════════════════════════════════
    # EXPORT
    # ═════════════════════════════════════════════════════════════════════
    def build_export():
        fmt_ref  = ft.Ref[ft.Dropdown]()
        name_ref = ft.Ref[ft.TextField]()
        out_ref  = ft.Ref[ft.Container]()
        txt_ref  = ft.Ref[ft.Text]()

        async def do_export(e):
            if state.log is None and state.net is None:
                err("Kein Log und kein Modell vorhanden!"); return
            fmt = fmt_ref.current.value
            name = name_ref.current.value.strip() or "output"

            def _export(fmt, name, log, net, im, fm):
                path = str(Path.home() / "Downloads" / name)
                if fmt == "XES" and log is not None:
                    out = path + ".xes"
                    pm4py.write_xes(log, out)
                elif fmt == "CSV" and log is not None:
                    out = path + ".csv"
                    log.to_csv(out, index=False)
                elif fmt == "PNML" and net is not None:
                    out = path + ".pnml"
                    pm4py.write_pnml(net, im, fm, out)
                elif fmt == "BPMN" and net is not None:
                    out = path + ".bpmn"
                    bpmn = pm4py.convert_to_bpmn(net, im, fm)
                    pm4py.write_bpmn(bpmn, out)
                elif fmt == "Parquet" and log is not None:
                    out = path + ".parquet"
                    log.to_parquet(out, index=False)
                else:
                    raise ValueError(f"Format '{fmt}' nicht verfügbar oder Daten fehlen.")
                return out

            try:
                out = await run_bg(_export, fmt, name, state.log, state.net, state.im, state.fm)
            except Exception as exc:
                traceback.print_exc()
                err(str(exc))
                return

            txt_ref.current.value = f"Exportiert nach:\n{out}"
            out_ref.current.visible = True
            page.update()
            snack(f"✅ Gespeichert: {out}", SUCCESS)

        available = [
            ("Event Log → XES",       "Benötigt: geladener Log"),
            ("Event Log → CSV",       "Benötigt: geladener Log"),
            ("Event Log → Parquet",   "Benötigt: geladener Log"),
            ("Petri-Netz → PNML",     "Benötigt: Discovery-Modell"),
            ("Prozessmodell → BPMN",  "Benötigt: Discovery-Modell"),
        ]

        return ft.Column([
            _section_header("💾", "Export", "Exportieren Sie Logs, Modelle und Ergebnisse"),
            _card("Export Optionen", ft.Column([
                _lbl("Export Format"),
                _dd(["XES", "CSV", "Parquet", "PNML", "BPMN"], ref=fmt_ref, value="XES"),
                ft.Container(height=6),
                _lbl("Dateiname (ohne Endung, gespeichert in ~/Downloads/)"),
                _tf(value="output", ref=name_ref),
                ft.Container(height=8),
                _btn("Exportieren", ft.Icons.DOWNLOAD, do_export, "success"),
            ], spacing=6)),
            _card("Verfügbare Exports", ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=SUCCESS, size=15),
                        ft.Column([
                            ft.Text(a[0], size=12, color=FG1, weight=ft.FontWeight.W_500),
                            ft.Text(a[1], size=11, color=FG3),
                        ], spacing=1),
                    ], spacing=8),
                    bgcolor=BG3, border_radius=6, padding=10,
                ) for a in available
            ], spacing=6)),
            ft.Container(ref=out_ref, visible=False,
                content=_card("Export Ergebnis",
                              ft.Container(content=_mono(ref=txt_ref),
                                           bgcolor=BG3, border_radius=8, padding=14))),
        ], spacing=0, scroll=ft.ScrollMode.AUTO)

    # ══════════════════════════════════════════════════════════════════════
    # NAVIGATION
    # ══════════════════════════════════════════════════════════════════════
    sections = {
        "import":      ("📂 Log Import",        build_import),
        "alpha":       ("α  Alpha Miner",        build_alpha),
        "inductive":   ("🔄 Inductive Miner",    build_inductive),
        "heuristic":   ("📊 Heuristics Miner",   build_heuristics),
        "dfg":         ("🔀 DFG Discovery",      build_dfg),
        "token":       ("🎯 Token Replay",        build_token),
        "alignments":  ("🔗 Alignments",          build_alignments),
        "filter":      ("🔍 Log Filtering",       build_filter),
        "variants":    ("📈 Variant Analysis",    build_variants),
        "statistics":  ("📊 Statistiken",         build_statistics),
        "social":      ("👥 Social Network",      build_social),
        "performance": ("⚡ Performance",         build_performance),
        "simulation":  ("🎲 Simulation",          build_simulation),
        "export":      ("💾 Export",              build_export),
    }

    nav_groups = [
        ("Daten Import",      ["import"]),
        ("Process Discovery", ["alpha", "inductive", "heuristic", "dfg"]),
        ("Conformance",       ["token", "alignments"]),
        ("Filtering",         ["filter", "variants"]),
        ("Analysis",          ["statistics", "social", "performance"]),
        ("Weitere Features",  ["simulation", "export"]),
    ]

    nav_buttons = {}

    def navigate(sid):
        for k, nb in nav_buttons.items():
            nb.bgcolor = ACCENT if k == sid else "transparent"
            nb.content.controls[0].color = BG1 if k == sid else FG2
            nb.content.controls[0].weight = (
                ft.FontWeight.W_600 if k == sid else ft.FontWeight.NORMAL)
            nb.update()
        content_area.controls.clear()
        content_area.controls.append(
            ft.Container(
                content=sections[sid][1](),
                padding=ft.Padding.only(left=28, right=28, top=22, bottom=28),
                expand=True,
            )
        )
        content_area.update()

    def make_nav_btn(sid, label):
        c = ft.Container(
            content=ft.Row([
                ft.Text(label, size=13, color=FG2, expand=1),
            ]),
            bgcolor="transparent", border_radius=7,
            padding=ft.Padding.symmetric(horizontal=11, vertical=9),
            on_click=lambda e, s=sid: navigate(s),
            ink=True,
        )
        nav_buttons[sid] = c
        return c

    sidebar_controls = [
        ft.Container(
            content=ft.Row([
                ft.Text("⚙️", size=20),
                ft.Text("PM4PY Suite", size=18,
                        weight=ft.FontWeight.BOLD, color=ACCENT),
            ], spacing=8),
            margin=ft.Margin.only(bottom=16, left=4),
        )
    ]
    for grp_title, grp_ids in nav_groups:
        sidebar_controls.append(ft.Column([
            ft.Text(grp_title.upper(), size=10, weight=ft.FontWeight.W_700,
                    color=FG3, style=ft.TextStyle(letter_spacing=0.6)),
            *[make_nav_btn(sid, sections[sid][0]) for sid in grp_ids],
            ft.Container(height=4),
        ], spacing=3))

    sidebar_controls.append(
        ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE if pm4py else ft.Icons.WARNING_AMBER_ROUNDED,
                        color=SUCCESS if pm4py else WARNING, size=14),
                ft.Text("pm4py OK" if pm4py else "pm4py fehlt!",
                        size=11, color=SUCCESS if pm4py else WARNING),
            ], spacing=6),
            margin=ft.Margin.only(top=12, left=4),
        )
    )

    sidebar = ft.Container(
        content=ft.Column(
            controls=sidebar_controls,
            scroll=ft.ScrollMode.AUTO, spacing=0,
            expand=True,
        ),
        width=240, bgcolor=BG2,
        border=ft.Border.only(right=ft.BorderSide(1, BORDER)),
        padding=ft.Padding.symmetric(horizontal=10, vertical=18),
    )

    page.add(
        ft.Row([
            sidebar,
            ft.Container(content=content_area, expand=True, bgcolor=BG1),
        ], expand=True, spacing=0,vertical_alignment=ft.CrossAxisAlignment.STRETCH)
    )

    navigate("import")

ft.run(main)
