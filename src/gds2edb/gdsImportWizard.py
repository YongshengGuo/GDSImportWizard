import sys,os
import queue
import shutil
import subprocess
import sys
import threading
import logging
import ctypes
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox


appPath = os.path.realpath(__file__)
appDir = os.path.split(appPath)[0] 
if appDir not in sys.path:
    sys.path.insert(0, appDir)
sys.path.append(r"C:\work\Study\Script\Ansys\quickAnalyze\FastSim")


TARGET_EDB = "EDB"
TARGET_XML = "XML"
TARGET_CSV = "CSV"

SIMPLIFY_CHOICES = [
    "0:NoSimplify",
    "1:MergeThinLayer",
    "2:BlockMerge",
    "3:MergeByLayer",
]


def resolve_working_directory(tech_file: str, gds_file: str) -> Path:
    if gds_file:
        return Path(gds_file).resolve().parent
    if tech_file:
        return Path(tech_file).resolve().parent
    return Path.cwd()


def ensure_working_cfg(work_dir: Path, template_cfg: Path) -> Path:
    work_cfg = work_dir / "gds2edb.cfg"
    if not work_cfg.exists():
        shutil.copy(template_cfg, work_cfg)
    return work_cfg


def discover_ansysem_roots(env: dict[str, str] | None = None) -> list[str]:
    source = env or os.environ
    keys = [key for key in source.keys() if key.startswith("ANSYSEM_ROOT")]

    def _sort_key(name: str) -> tuple[int, str]:
        suffix = name[len("ANSYSEM_ROOT") :]
        digits = "".join(ch for ch in suffix if ch.isdigit())
        number = int(digits) if digits else -1
        return number, suffix

    return sorted(keys, key=_sort_key, reverse=True)


def latest_ansysem_root_key(keys: list[str]) -> str:
    return keys[0] if keys else ""


def format_aedt_display_items(keys: list[str], env: dict[str, str] | None = None) -> list[str]:
    source = env or os.environ
    return [f"{key}={source.get(key, '')}" for key in keys]


def extract_aedt_env_key(display_value: str) -> str:
    text = (display_value or "").strip()
    if not text:
        return ""
    if "=" not in text:
        return text
    return text.split("=", 1)[0].strip()


def simplify_label_to_value(label: str) -> str:
    text = (label or "").strip()
    if not text:
        return "3"
    return text.split(":", 1)[0].strip()


def target_requires_gds_file(target: str) -> bool:
    return (target or "").strip() == TARGET_EDB


def derive_edb_out_from_gds(gds_file: str) -> str:
    text = (gds_file or "").strip()
    if not text:
        return ""
    return str(Path(text).with_suffix(".aedb"))


def open_with_default_text_editor(file_path: Path) -> None:
    if os.name == "nt":
        os.startfile(str(file_path))  # type: ignore[attr-defined]
        return
    if os.name == "posix":
        opener = "open" if "darwin" in os.uname().sysname.lower() else "xdg-open"
        subprocess.Popen([opener, str(file_path)])
        return
    raise RuntimeError("Unsupported platform for opening external editor")


def set_windows_app_user_model_id(app_id: str = "synopsys.gds2edb.wizard") -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def apply_wizard_runtime_options(
    runtime_options,
    tech_file: str,
    gds_file: str,
    layermap_file: str,
    xml_path: Path,
    edb_path: Path,
    csv_path: Path,
    simplify_label: str,
    create_via_groups: bool,
    generate_component: bool,
    open_in_aedt: bool,
) -> None:
    # Keep both historical key variants to match existing parser/runtime code paths.
    runtime_options["TechFile"] = tech_file
    runtime_options["techFile"] = tech_file
    runtime_options["GdsFile"] = gds_file
    runtime_options["gdsFile"] = gds_file
    runtime_options["ControlXmlPath"] = str(xml_path)
    runtime_options["controlXmlPath"] = str(xml_path)
    runtime_options["EdbPath"] = str(edb_path)
    runtime_options["edbPath"] = str(edb_path)
    runtime_options["CsvOutPath"] = str(csv_path)
    runtime_options["CsvOut"] = str(csv_path)
    runtime_options["layerMap"] = layermap_file
    runtime_options["SimplifyDieletricMethod"] = simplify_label_to_value(simplify_label)
    runtime_options["CreatViaGroups"] = str(create_via_groups)
    runtime_options["GenerateComponent"] = str(generate_component)
    runtime_options["OpenInAedt"] = str(open_in_aedt)


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


class _QueueLogHandler(logging.Handler):
    """Redirect logging output to a queue for UI display."""
    def __init__(self, log_queue: queue.Queue[str]) -> None:
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.log_queue.put(msg)
        except Exception:
            self.handleError(record)


class GdsImportWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GDS Import Wizard")
        self.geometry("980x620")
        self.minsize(860, 520)

        self._app_dir = Path(__file__).resolve().parent
        self._template_cfg = self._app_dir / "gds2edb.cfg"

        self._log_queue: queue.Queue[str] = queue.Queue()
        self._setup_log_capture()
        self._setup_window_icon()
        
        self._worker: threading.Thread | None = None
        self._process: subprocess.Popen | None = None
        self._cancel_requested = False

        self.tech_file_var = tk.StringVar()
        self.gds_file_var = tk.StringVar()
        self.edb_out_var = tk.StringVar()
        self.layermap_file_var = tk.StringVar()
        self.target_var = tk.StringVar(value=TARGET_EDB)
        self.aedt_version_keys = discover_ansysem_roots()
        self.aedt_version_choices = format_aedt_display_items(self.aedt_version_keys)
        default_key = latest_ansysem_root_key(self.aedt_version_keys)
        self.aedt_version_var = tk.StringVar(value=f"{default_key}={os.environ.get(default_key, '')}" if default_key else "")
        self.simplify_var = tk.StringVar(value=SIMPLIFY_CHOICES[-1])
        self.create_via_groups_var = tk.BooleanVar(value=True)
        self.generate_component_var = tk.BooleanVar(value=True)
        self.open_in_aedt_var = tk.BooleanVar(value=True)
        self._target_check_vars: dict[str, tk.BooleanVar] = {
            TARGET_EDB: tk.BooleanVar(value=True),
            TARGET_CSV: tk.BooleanVar(value=False),
            TARGET_XML: tk.BooleanVar(value=False),
        }

        self._build_ui()
        self._sync_target_checks()
        self._apply_target_state()
        self.protocol("WM_DELETE_WINDOW", self.on_close_window)
        self.after(120, self._drain_logs)

    def _setup_log_capture(self) -> None:
        """Attach UI log queue to pyLayout.log and root logger to capture backend logs."""
        try:
            from pyLayout import log as pyLayout_log  # type: ignore
            handler = _QueueLogHandler(self._log_queue)
            handler.setFormatter(logging.Formatter("%(message)s"))
            if hasattr(pyLayout_log, "addHandler"):
                pyLayout_log.addHandler(handler)
            if hasattr(pyLayout_log, "setLevel"):
                pyLayout_log.setLevel(logging.INFO)
        except Exception:
            pass  # If pyLayout.log setup fails, UI logging still works independently.
        
        # Also attach to root logger and gds2edb-related loggers.
        root_logger = logging.getLogger()
        handler = _QueueLogHandler(self._log_queue)
        handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

    def _setup_window_icon(self) -> None:
        icon_dir = self._app_dir
        ico_path = icon_dir / "gds-import-wizard-icon.ico"
        png_path = icon_dir / "gds-import-wizard-icon.png"

        try:
            if os.name == "nt" and ico_path.exists():
                self.iconbitmap(default=str(ico_path))
                return
            if png_path.exists():
                self._window_icon_image = tk.PhotoImage(file=str(png_path))
                self.iconphoto(True, self._window_icon_image)
        except Exception as exc:  # noqa: BLE001
            self._log(f"WARN set window icon failed: {exc}")

    def _build_ui(self) -> None:
        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=(10, 6))
        tk.Label(top, text="GDS Import Wizard", font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Button(
            top,
            text="Help",
            width=12,
            command=self.open_help,
            font=("Segoe UI", 10, "bold"),
            fg="white",
            bg="#1769aa",
            activeforeground="white",
            activebackground="#0d4f82",
            relief="flat",
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2",
        ).pack(side="right")

        file_box = tk.LabelFrame(self, text="Input Files")
        file_box.pack(fill="x", padx=10, pady=6)

        tk.Label(file_box, text="Aedt Version", width=12, anchor="w").grid(row=0, column=0, padx=8, pady=8)
        self.aedt_version_combo = ttk.Combobox(
            file_box,
            textvariable=self.aedt_version_var,
            values=self.aedt_version_choices,
            state="readonly" if self.aedt_version_choices else "disabled",
        )
        self.aedt_version_combo.grid(row=0, column=1, sticky="ew", padx=4, pady=8)

        tk.Label(file_box, text="Tech File", width=12, anchor="w").grid(row=1, column=0, padx=8, pady=8)
        tk.Entry(file_box, textvariable=self.tech_file_var).grid(row=1, column=1, sticky="ew", padx=4, pady=8)
        tk.Button(file_box, text="Browse...", command=self.browse_tech).grid(row=1, column=2, padx=8, pady=8)

        self.gds_label = tk.Label(file_box, text="GDSFile", width=12, anchor="w")
        self.gds_label.grid(row=2, column=0, padx=8, pady=8)
        self.gds_entry = tk.Entry(file_box, textvariable=self.gds_file_var)
        self.gds_entry.grid(row=2, column=1, sticky="ew", padx=4, pady=8)
        self.gds_browse_btn = tk.Button(file_box, text="Browse...", command=self.browse_gds)
        self.gds_browse_btn.grid(row=2, column=2, padx=8, pady=8)

        tk.Label(file_box, text="EdbOut", width=12, anchor="w").grid(row=3, column=0, padx=8, pady=8)
        self.edb_out_entry = tk.Entry(file_box, textvariable=self.edb_out_var)
        self.edb_out_entry.grid(row=3, column=1, sticky="ew", padx=4, pady=8)
        self.edb_out_browse_btn = tk.Button(file_box, text="Browse...", command=self.browse_edb_out)
        self.edb_out_browse_btn.grid(row=3, column=2, padx=8, pady=8)

        tk.Label(file_box, text="LayerMap File", width=12, anchor="w").grid(row=4, column=0, padx=8, pady=8)
        self.layermap_entry = tk.Entry(file_box, textvariable=self.layermap_file_var)
        self.layermap_entry.grid(row=4, column=1, sticky="ew", padx=4, pady=8)
        self.layermap_browse_btn = tk.Button(file_box, text="Browse...", command=self.browse_layermap)
        self.layermap_browse_btn.grid(row=4, column=2, padx=8, pady=8)

        file_box.grid_columnconfigure(1, weight=1)

        target_box = tk.LabelFrame(self, text="Target")
        target_box.pack(fill="x", padx=10, pady=6)
        tk.Checkbutton(
            target_box,
            text="Output EDB",
            variable=self._target_check_vars[TARGET_EDB],
            command=lambda: self._select_target(TARGET_EDB),
        ).grid(row=0, column=0, sticky="w", padx=8, pady=6)
        tk.Checkbutton(
            target_box,
            text="Output CSV",
            variable=self._target_check_vars[TARGET_CSV],
            command=lambda: self._select_target(TARGET_CSV),
        ).grid(row=0, column=1, sticky="w", padx=8, pady=6)
        tk.Checkbutton(
            target_box,
            text="Output XML",
            variable=self._target_check_vars[TARGET_XML],
            command=lambda: self._select_target(TARGET_XML),
        ).grid(row=0, column=2, sticky="w", padx=8, pady=6)

        options_box = tk.LabelFrame(self, text="Options")
        options_box.pack(fill="x", padx=10, pady=6)
        tk.Label(options_box, text="SimplifyDieletricMethod", width=22, anchor="w").grid(row=0, column=0, padx=8, pady=8)
        self.simplify_combo = ttk.Combobox(
            options_box,
            textvariable=self.simplify_var,
            values=SIMPLIFY_CHOICES,
            state="readonly",
        )
        self.simplify_combo.grid(row=0, column=1, sticky="w", padx=4, pady=8)

        tk.Checkbutton(options_box, text="CreatViaGroups", variable=self.create_via_groups_var).grid(
            row=0, column=2, sticky="w", padx=8, pady=8
        )
        tk.Checkbutton(options_box, text="GenerateComponent", variable=self.generate_component_var).grid(
            row=0, column=3, sticky="w", padx=8, pady=8
        )
        tk.Checkbutton(options_box, text="OpenInAedt", variable=self.open_in_aedt_var).grid(
            row=0, column=4, sticky="w", padx=8, pady=8
        )
        options_box.grid_columnconfigure(5, weight=1)
        tk.Button(options_box, text="MoreOptions", width=12, command=self.open_more_options).grid(
            row=0, column=5, sticky="e", padx=8, pady=8
        )

        actions = tk.Frame(self)
        actions.pack(fill="x", padx=10, pady=(2, 6))
        self.translate_btn = tk.Button(actions, text="Start", width=12, command=self.start_translate)
        self.translate_btn.pack(side="right")
        self.cancel_btn = tk.Button(actions, text="Cancel", width=12, command=self.cancel_translate, state="normal")
        self.cancel_btn.pack(side="right", padx=(0, 8))

        log_box = tk.LabelFrame(self, text="Logs")
        log_box.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        self.log_text = tk.Text(log_box, wrap="word", state="disabled")
        scroll = tk.Scrollbar(log_box, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)

        self.log_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def browse_tech(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Tech File",
            filetypes=[("Tech Files", "*.csv *.ircx *.itf"), ("All Files", "*.*")],
        )
        if path:
            self.tech_file_var.set(path)

    def browse_gds(self) -> None:
        if not self._requires_gds_file():
            return
        path = filedialog.askopenfilename(
            title="Select GDSII File",
            filetypes=[("GDSII", "*.gds *.gdsii *.sf *.strm *.oas"), ("All Files", "*.*")],
        )
        if path:
            self.gds_file_var.set(path)
            self.edb_out_var.set(derive_edb_out_from_gds(path))

    def browse_layermap(self) -> None:
        path = filedialog.askopenfilename(
            title="Select LayerMap File",
            filetypes=[("LayerMap Files", "*.layermap *.map *.txt"), ("All Files", "*.*")],
        )
        if path:
            self.layermap_file_var.set(path)

    def browse_edb_out(self) -> None:
        current_path = self.edb_out_var.get().strip()
        initial_file = Path(current_path).name if current_path else "output.aedb"
        initial_dir = str(Path(current_path).parent) if current_path and Path(current_path).parent.exists() else ""
        
        path = filedialog.asksaveasfilename(
            title="Select EDB Output Path",
            filetypes=[("AEDB Files", "*.aedb"), ("All Files", "*.*")],
            initialfile=initial_file,
            initialdir=initial_dir if initial_dir else None,
        )
        if path:
            self.edb_out_var.set(path)

    def open_help(self) -> None:
        help_index = self._app_dir / ".." / ".." / "Help" / "index.html"
        if not help_index.exists():
            self._log(f"ERROR help file not found: {help_index}")
            messagebox.showerror("Help Missing", f"Help file not found:\n{help_index}", parent=self)
            return
        self._log(f"Open help: {help_index}")
        try:
            open_with_default_text_editor(help_index)
        except Exception as exc:  # noqa: BLE001
            self._log(f"ERROR opening help: {exc}")
            messagebox.showerror("Open Help Failed", str(exc), parent=self)

    def _requires_gds_file(self) -> bool:
        return target_requires_gds_file(self.target_var.get())

    def _select_target(self, target: str) -> None:
        self.target_var.set(target)
        self._sync_target_checks()
        self._apply_target_state()

    def _sync_target_checks(self) -> None:
        selected = self.target_var.get().strip()
        for key, var in self._target_check_vars.items():
            var.set(key == selected)

    def _apply_target_state(self) -> None:
        enabled = self._requires_gds_file()
        entry_state = "normal" if enabled else "disabled"
        button_state = "normal" if enabled else "disabled"

        self.gds_entry.configure(state=entry_state)
        self.gds_browse_btn.configure(state=button_state)
        self.edb_out_entry.configure(state=entry_state)

        if not enabled:
            self.gds_file_var.set("")
            self.edb_out_var.set("")

    def _log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log_queue.put(f"[{timestamp}] {message}")

    def _drain_logs(self) -> None:
        while True:
            try:
                line = self._log_queue.get_nowait()
            except queue.Empty:
                break
            self.log_text.configure(state="normal")
            self.log_text.insert(tk.END, line + "\n")
            self.log_text.see(tk.END)
            self.log_text.configure(state="disabled")
        self.after(120, self._drain_logs)

    def _set_running(self, running: bool) -> None:
        self.translate_btn.configure(state="disabled" if running else "normal")
        self.cancel_btn.configure(state="normal", text="Abort" if running else "Cancel")

    def _is_running(self) -> bool:
        return bool(self._worker and self._worker.is_alive())

    def _abort_running_task(self, reason: str = "Abort requested.") -> None:
        self._cancel_requested = True
        proc = self._process
        if proc and proc.poll() is None:
            proc.terminate()
            self._log(f"{reason} Translator process terminated.")
        else:
            self._log(reason)

    def on_close_window(self) -> None:
        if self._is_running():
            should_abort = messagebox.askyesno(
                "Task Running",
                "A conversion task is still running. Abort task and close window?",
                parent=self,
            )
            if not should_abort:
                return
            self._abort_running_task("Abort requested via window close.")
        self.destroy()

    def open_more_options(self) -> None:
        tech_file = self.tech_file_var.get().strip()
        if not tech_file or not Path(tech_file).exists():
            messagebox.showwarning("TechFile Required", "Please select a valid TechFile first.", parent=self)
            return

        work_dir = Path(tech_file).resolve().parent
        cfg_path = ensure_working_cfg(work_dir, self._template_cfg)
        self._log(f"MoreOptions cfg: {cfg_path}")
        try:
            open_with_default_text_editor(cfg_path)
        except Exception as exc:  # noqa: BLE001
            self._log(f"ERROR opening cfg in editor: {exc}")
            messagebox.showerror("Open Failed", str(exc), parent=self)

    def start_translate(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._cancel_requested = False
        self._set_running(True)
        self._worker = threading.Thread(target=self._run_translate, daemon=True)
        self._worker.start()

    def cancel_translate(self) -> None:
        if self._is_running():
            self._abort_running_task("Abort requested.")
        else:
            self.destroy()

    def _run_translate(self) -> None:
        try:
            # Lazy imports keep module importable even when external runtime deps are absent.
            from gds2edb import GDS2Edb  # type: ignore
            from options import options  # type: ignore

            tech_file = self.tech_file_var.get().strip()
            gds_file = self.gds_file_var.get().strip()
            layermap_file = self.layermap_file_var.get().strip()
            target = self.target_var.get().strip()

            if not tech_file or not Path(tech_file).exists():
                raise FileNotFoundError("Tech File is required.")

            if self._requires_gds_file() and (not gds_file or not Path(gds_file).exists()):
                raise FileNotFoundError("GDSFile is required for Output EDB target.")

            if layermap_file and not Path(layermap_file).exists():
                raise FileNotFoundError("LayerMapFile path does not exist.")

            work_dir = resolve_working_directory(tech_file, gds_file)
            cfg_path = ensure_working_cfg(work_dir, self._template_cfg)
            self._log(f"Working directory: {work_dir}")
            self._log(f"Config file: {cfg_path}")

            xml_path = Path(gds_file).with_suffix(".xml") if gds_file else Path(tech_file).with_suffix(".xml")
            #如果xml_path存在，则先删除  20260910
            if xml_path.exists():
                self._log(f"Removing existing XML Control File: {xml_path}")
                xml_path.unlink()
            
            edb_out_text = self.edb_out_var.get().strip()
            if target == TARGET_EDB and edb_out_text:
                edb_path = Path(edb_out_text)
            elif gds_file:
                edb_path = Path(derive_edb_out_from_gds(gds_file))
            else:
                edb_path = Path(tech_file).with_suffix(".aedb")
            csv_path = Path(tech_file).with_suffix(".csv")
            if Path(tech_file).suffix.lower() == ".csv":
                csv_path = Path(tech_file).with_name(Path(tech_file).stem + "_out.csv")

            g2e = GDS2Edb()
            g2e.readOptions(str(cfg_path))

            apply_wizard_runtime_options(
                options,
                tech_file=tech_file,
                gds_file=gds_file,
                layermap_file=layermap_file,
                xml_path=xml_path,
                edb_path=edb_path,
                csv_path=csv_path,
                simplify_label=self.simplify_var.get(),
                create_via_groups=self.create_via_groups_var.get(),
                generate_component=self.generate_component_var.get(),
                open_in_aedt=self.open_in_aedt_var.get(),
            )

            aedt_root_key = extract_aedt_env_key(self.aedt_version_var.get())
            if aedt_root_key and aedt_root_key in os.environ:
                options["AedtVersion"] = aedt_root_key
                options["AedtInstallDir"] = os.environ[aedt_root_key]
                self._log(f"Selected AEDT root: {aedt_root_key}")

            if target == TARGET_CSV:
                self._run_csv_only(g2e)
            elif target == TARGET_XML:
                self._run_xml_only(g2e)
            else:
                self._run_edb(g2e)

            if self._cancel_requested:
                self._log("Task cancelled.")
            else:
                self._log("Task completed.")
        except Exception as exc:  # noqa: BLE001
            self._log(f"ERROR: {exc}")
        finally:
            self._process = None
            try:
                self.after(0, lambda: self._set_running(False))
            except tk.TclError:
                pass

    def _run_xml_only(self, g2e) -> None:
        if self._cancel_requested:
            return
        self._log("Generating XML Control File...")
        g2e.tech2xml()
        self._log("XML generation completed.")

    def _run_csv_only(self, g2e) -> None:
        if self._cancel_requested:
            return
        self._log("Generating CSV Tech...")
        g2e.tech2csv()
        self._log("CSV generation completed.")

    def _run_edb(self, g2e) -> None:
        if self._cancel_requested:
            return
        self._log("Generating EDB...")
        g2e.generateEBD()
        self._log("EDB generation completed.")
        

def main() -> int:
    set_windows_app_user_model_id()
    app = GdsImportWizard()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
