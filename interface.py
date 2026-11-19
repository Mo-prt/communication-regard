import random
from queue import Empty
from time import monotonic
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from audio_local import Speaker
from evaluation import Session, simulated_cases
from logique import CALIBRATION, PHRASES, TARGETS, Calibration, Selection, Signal
from vision import Camera

INK = "#18312d"
TEAL = "#007762"
PAPER = "#eef6f3"
WHITE = "#ffffff"


class App:
    def __init__(self, root, args):
        self.root, self.args = root, args
        self.root.title("Communication au chevet")
        self.root.geometry("960x740")
        self.root.minsize(660, 620)
        self.root.configure(bg=PAPER)
        self.layout = tk.IntVar(value=2)
        self.source = tk.StringVar(value="Simulation")
        self.status = tk.StringVar()
        self.last_phrase = tk.StringVar(value="—")
        self.instructions = tk.StringVar(value="Choisissez un scénario.")
        self.results = tk.StringVar()
        self.speaker = Speaker()
        self.session = self.camera = self.cal_groups = None
        self.synthetic = []
        self.cal_samples = []
        self.last_signal = None
        self.camera_error = False
        self.closing = False
        self.selection = self.engine()
        self.board = None

        header = tk.Frame(root, bg=WHITE, padx=22, pady=12)
        header.pack(fill="x")
        tk.Label(header, text="Communication au chevet", font=("TkDefaultFont", 20, "bold"),
                 fg=INK, bg=WHITE).pack(anchor="w")
        controls = tk.Frame(header, bg=WHITE)
        controls.pack(fill="x", pady=(8, 0))
        for val, title in ((2, "2 phrases"), (4, "4 phrases")):
            ttk.Radiobutton(controls, text=title, variable=self.layout, value=val,
                            command=self.layout_changed).pack(side="left", padx=(0, 8))
        chooser = ttk.Combobox(controls, state="readonly", textvariable=self.source,
                               values=("Simulation", "Webcam"), width=12)
        chooser.pack(side="left", padx=8)
        chooser.bind("<<ComboboxSelected>>", self.change_source)
        ttk.Button(controls, text="Recalibrer", command=self.calibrate).pack(side="left")
        tk.Label(header, textvariable=self.status, fg=TEAL, bg=WHITE,
                 justify="left", wraplength=610).pack(anchor="w", pady=(8, 0))
        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill="both", expand=True, padx=18, pady=12)
        self.communication = ttk.Frame(self.tabs, padding=12)
        self.evaluation = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(self.communication, text="Communication")
        self.tabs.add(self.evaluation, text="Évaluation")
        tk.Label(self.communication, textvariable=self.last_phrase, bg=PAPER, fg=INK,
                 font=("TkDefaultFont", 22, "bold"), wraplength=580, pady=9).pack(fill="x", side="bottom")
        ttk.Label(self.communication, text="Dernière phrase sélectionnée").pack(side="bottom")

        tools = ttk.Frame(self.evaluation)
        tools.pack(fill="x")
        for title, action in (
            ("Sélection guidée", lambda: self.start_session("guide")),
            ("Observation libre", lambda: self.start_session("libre")),
            ("Cas simulés", self.run_cases),
            ("Exporter CSV", self.export),
        ):
            ttk.Button(tools, text=title, command=action).pack(side="left", padx=(0, 7))
        ttk.Label(self.evaluation, textvariable=self.instructions, wraplength=590).pack(anchor="w", pady=8)
        ttk.Label(self.evaluation, textvariable=self.results, wraplength=590,
                  justify="left").pack(anchor="w", side="bottom", pady=5)
        self.tabs.bind("<<NotebookTabChanged>>", self.tab_changed)
        self.make_board(self.communication)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.status.set("Simulation · déplacez la souris, puis appuyez sur Espace.")
        self.root.bind("<space>", self.simulate_wink)
        self.root.after(20, self.tick)

    def engine(self, calibration=None):
        return Selection(self.layout.get(), calibration, self.args.wink_min, self.args.wink_max)

    def make_board(self, parent):
        if self.board is not None:
            self.board.destroy()
        self.board = tk.Canvas(parent, background=PAPER, highlightthickness=0,
                               height=260, takefocus=True)
        self.board.pack(fill="both", expand=True)
        self.board.bind("<Configure>", lambda event: self.draw())
        self.board.bind("<Motion>", self.simulate_position)
        self.board.bind("<Leave>", self.leave_board)
        self.board.bind("<Button-1>", self.simulate_click)

    def tab_changed(self, event=None):
        parent = self.communication if self.tabs.index("current") == 0 else self.evaluation
        if self.board is not None and self.board.master is parent:
            return
        if self.session and not self.session.done:
            self.cancel_session()
        self.synthetic.clear()
        self.selection.feed(None)
        self.make_board(parent)
        if self.source.get() == "Webcam":
            self.calibrate()

    def draw(self):
        canvas = self.board
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        layout = self.layout.get()
        for i, (x, y) in enumerate(TARGETS[layout]):
            half_height = .34 if layout == 2 else .19
            active = self.selection.hovered == i and self.cal_groups is None
            canvas.create_rectangle((x-.215)*w, (y-half_height)*h,
                                    (x+.215)*w, (y+half_height)*h,
                                    fill="#d5f4e9" if active else WHITE,
                                    outline=TEAL if active else "#a5c9bd", width=3 if active else 1)
            canvas.create_text(x*w, y*h, text=PHRASES[i], fill=INK,
                               width=max(40, int(.39*w)), font=("TkDefaultFont", 24, "bold"))
        if self.cal_groups is not None:
            x, y = CALIBRATION[layout][len(self.cal_groups)]
            canvas.create_oval(x*w-13, y*h-13, x*w+13, y*h+13,
                               fill="#ad4029", outline=WHITE, width=2)
        elif self.selection.point is not None:
            x, y = self.selection.point
            canvas.create_oval(x*w-6, y*h-6, x*w+6, y*h+6, fill=TEAL, outline=WHITE)

    def cancel_session(self):
        if self.session and not self.session.done:
            self.session = None
            self.results.set("")
            self.instructions.set("Session interrompue. Choisissez un scénario.")

    def layout_changed(self):
        self.cancel_session()
        self.synthetic.clear()
        self.selection = self.engine()
        self.cal_groups = None
        if self.source.get() == "Webcam":
            self.calibrate()
        self.draw()

    def change_source(self, event=None):
        self.cancel_session()
        self.synthetic.clear()
        self.cal_groups = None
        self.selection = self.engine()
        self.last_signal = None
        self.camera_error = False
        if self.source.get() == "Webcam":
            self.calibrate()
        else:
            if self.camera:
                self.camera.stop.set()
            self.status.set("Simulation · déplacez la souris, puis appuyez sur Espace.")
        self.draw()

    def calibrate(self):
        self.cancel_session()
        self.selection = self.engine()
        self.synthetic.clear()
        if self.source.get() == "Simulation":
            self.status.set("Simulation · calibration automatique.")
            self.draw()
            return
        if self.camera and self.camera.stop.is_set() and self.camera.worker.is_alive():
            self.status.set("Webcam · fermeture en cours. Réessayez dans un instant.")
            return
        if self.camera is None or not self.camera.worker.is_alive():
            self.camera = Camera(self.args.model, self.args.camera)
        self.camera_error = False
        self.cal_groups = []
        self.next_target()

    def next_target(self):
        self.cal_samples = []
        self.collect_after = monotonic() + .85
        self.status.set(f"Webcam · fixez la cible rouge, yeux ouverts "
                        f"({len(self.cal_groups)+1}/{len(CALIBRATION[self.layout.get()])}).")
        self.draw()

    def receive(self, sample):
        if self.source.get() == "Webcam":
            self.last_signal = sample.time if sample else None
            if sample is None:
                self.selection.feed(None)
                if self.cal_groups is not None:
                    self.cal_samples.clear()
                self.status.set("Webcam · Suivi interrompu. Replacez le visage dans le cadre.")
                self.draw()
                return
            if self.cal_groups is not None:
                self.status.set(f"Webcam · fixez la cible rouge, yeux ouverts "
                                f"({len(self.cal_groups)+1}/{len(CALIBRATION[self.layout.get()])}).")
                if sample.time >= self.collect_after and min(sample.left, sample.right) > .10:
                    self.cal_samples.append(sample)
                    if (len(self.cal_samples) >= 8 and
                            sample.time-self.cal_samples[0].time >= .45):
                        self.cal_groups.append(self.cal_samples)
                        if len(self.cal_groups) < len(CALIBRATION[self.layout.get()]):
                            self.next_target()
                        else:
                            try:
                                self.selection = self.engine(Calibration(self.layout.get(), self.cal_groups))
                                self.status.set("Webcam · calibration terminée.")
                            except ValueError as error:
                                self.status.set(f"Webcam · {error} Cliquez sur Recalibrer.")
                            finally:
                                self.cal_groups = None
                                self.draw()
                return
            if self.selection.calibration is None:
                return
            self.status.set("Webcam · suivi actif.")
        selected = self.selection.feed(sample)
        if selected is not None:
            self.activate(selected)
        self.draw()

    def simulate_position(self, event):
        if self.source.get() == "Simulation" and not self.synthetic:
            self.receive(Signal(monotonic(), event.x/self.board.winfo_width(),
                                event.y/self.board.winfo_height(), 1., 1.))

    def leave_board(self, event):
        if self.source.get() == "Simulation" and not self.synthetic:
            self.receive(None)

    def simulate_click(self, event):
        self.board.focus_set()
        self.simulate_position(event)
        return self.simulate_wink()

    def simulate_wink(self, event=None):
        if self.source.get() != "Simulation" or self.synthetic or self.selection.point is None:
            return
        if event is not None and self.root.focus_get() not in (self.board, self.root, None):
            return
        now = monotonic()
        x, y = self.selection.point
        self.synthetic = [Signal(now+offset, x, y, side, 1.) for offset, side in
                          ((0, 1.), (.03, .1), (.12, .1), (.23, .1), (.29, 1.))]
        return "break"

    def tick(self):
        if self.closing:
            return
        if self.camera and self.source.get() == "Webcam" and not self.camera.stop.is_set():
            try:
                for _ in range(16):
                    kind, value = self.camera.messages.get_nowait()
                    if kind == "error":
                        self.camera_error = True
                        self.receive(None)
                        self.status.set(f"Webcam · {value}")
                    else:
                        self.receive(value if value is None or monotonic()-value.time <= .35 else None)
            except Empty:
                pass
            if self.last_signal is not None and monotonic()-self.last_signal > .45 and not self.camera_error:
                self.receive(None)
        while self.synthetic and self.synthetic[0].time <= monotonic():
            self.receive(self.synthetic.pop(0))
        if self.session and not self.session.done:
            self.advance()
        self.root.after(25, self.tick)

    def activate(self, selected):
        phrase = PHRASES[selected]
        self.last_phrase.set(phrase)
        if self.session and not self.session.done:
            self.advance(selected)
        if not self.args.muet:
            try:
                self.speaker.say(phrase)
            except OSError as error:
                self.status.set(f"{self.source.get()} · audio indisponible : {error}")

    def start_session(self, mode):
        if self.source.get() == "Webcam" and (self.selection.calibration is None or self.last_signal is None):
            self.instructions.set("Terminez la calibration webcam avant le test.")
            return
        self.selection.feed(None)
        self.synthetic.clear()
        choices = list(range(self.layout.get())) * (10//self.layout.get()+1)
        random.shuffle(choices)
        self.session = Session(self.source.get().lower(), self.layout.get(), mode, monotonic(),
                               choices[:10], limit=60. if mode == "libre" else 10.)
        self.results.set("")
        self.board.focus_set()
        self.advance()

    def advance(self, selected=None):
        now = monotonic()
        self.session.advance(now, selected)
        if self.session.done:
            self.show_results()
        elif self.session.mode == "guide":
            self.instructions.set(f"Essai {len(self.session.rows)+1}/10 · Sélectionnez « "
                                  f"{PHRASES[self.session.target]} » · "
                                  f"{max(0, int(10-(now-self.session.step)))} s")
        else:
            self.instructions.set("Regardez librement sans sélectionner · "
                                  f"{max(0, int(60-(now-self.session.started)))} s")

    def run_cases(self):
        self.synthetic.clear()
        self.selection.feed(None)
        self.session = simulated_cases(self.layout.get())
        self.show_results()

    def show_results(self):
        result = self.session.summary()
        self.instructions.set(f"Session terminée · {self.session.source} · {self.session.layout} phrases")
        if self.session.mode == "guide":
            median = result["temps_median_s"]
            speed = f"{median} s" if median is not None else "—"
            self.results.set(f"{result['essais']} essais · {result['corrects']} corrects · "
                             f"{result['incorrects']} incorrects · {result['sans_reponse']} sans réponse\n"
                             f"Réussite {result['taux_reussite_pct']} % · Temps médian {speed}")
        elif self.session.mode == "libre":
            self.results.set(f"{result['clics_involontaires']} clics involontaires · "
                             f"{result['clics_par_minute']} par minute")
        else:
            self.results.set("\n".join(f"{row['cas']} — "
                                       f"{'réussi' if row['resultat'] == 'correct' else 'échoué'}"
                                       for row in self.session.rows))

    def export(self):
        if not self.session or not self.session.done:
            self.instructions.set("Terminez une session avant l’export.")
            return
        filename = filedialog.asksaveasfilename(parent=self.root, defaultextension=".csv",
                                               filetypes=[("CSV", "*.csv")])
        if filename:
            try:
                self.session.export(filename)
            except OSError as error:
                messagebox.showerror("Export CSV", str(error), parent=self.root)
            else:
                self.instructions.set(f"Rapport exporté · {self.session.source}")

    def close(self):
        self.closing = True
        self.speaker.stop()
        if self.camera:
            self.camera.stop.set()
        self.finish_close(monotonic()+2)

    def finish_close(self, deadline):
        if self.camera and self.camera.worker.is_alive() and monotonic() < deadline:
            self.root.after(40, self.finish_close, deadline)
        else:
            self.root.destroy()
