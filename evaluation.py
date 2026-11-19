import csv
from pathlib import Path
from statistics import median

from logique import PHRASES, TARGETS, Selection, Signal


class Session:
    def __init__(self, source, layout, mode, now, targets=(), limit=10.):
        self.source, self.layout, self.mode = source, layout, mode
        self.started = self.step = now
        self.targets = list(targets)
        self.limit = limit
        self.rows = []
        self.done = False

    @property
    def target(self):
        return self.targets[len(self.rows)] if not self.done and self.mode == "guide" else None

    def advance(self, now, selected=None):
        if self.done:
            return
        if self.mode == "libre":
            if now-self.started >= self.limit:
                self.done = True
            elif selected is not None:
                self.rows.append(dict(phrase=PHRASES[selected], secondes=now-self.started,
                                      resultat="clic_involontaire"))
        elif selected is not None or now-self.step >= self.limit:
            if now-self.step >= self.limit:
                selected = None
            target = self.target
            outcome = "sans_reponse" if selected is None else (
                "correct" if selected == target else "incorrect")
            self.rows.append(dict(cible=PHRASES[target], phrase=PHRASES[selected]
                                  if selected is not None else "", secondes=now-self.step,
                                  resultat=outcome))
            self.step = now
            self.done = len(self.rows) == len(self.targets)

    def summary(self):
        if self.mode == "libre":
            return {"clics_involontaires": len(self.rows),
                    "clics_par_minute": round(len(self.rows)*60/self.limit, 3)}
        if self.mode == "cas":
            return {"cas": len(self.rows), "reussis": sum(r["resultat"] == "correct" for r in self.rows)}
        correct = [r["secondes"] for r in self.rows if r["resultat"] == "correct"]
        return {"essais": len(self.rows), "corrects": len(correct),
                "incorrects": sum(r["resultat"] == "incorrect" for r in self.rows),
                "sans_reponse": sum(r["resultat"] == "sans_reponse" for r in self.rows),
                "taux_reussite_pct": round(100*len(correct)/len(self.rows), 2) if self.rows else 0.,
                "temps_median_s": round(median(correct), 3) if correct else None}

    def export(self, path: str | Path):
        if not self.done:
            raise ValueError("Terminez la session avant l’export.")
        base = dict(source=self.source, disposition=self.layout, scenario=self.mode)
        metrics = self.summary()
        fields = [*base, "ligne", "cas", "cible", "phrase", "secondes", "resultat",
                  "detail", *[key for key in metrics if key != "cas"], "nombre_cas"]
        with open(path, "w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, delimiter=";")
            writer.writeheader()
            if "cas" in metrics:
                metrics["nombre_cas"] = metrics.pop("cas")
            writer.writerow(dict(base, ligne="resume", **metrics))
            writer.writerows(dict(base, ligne="evenement", **row) for row in self.rows)


def simulated_cases(layout):
    session = Session("simulation", layout, "cas", 0.)
    x, y = TARGETS[layout][0]
    other_x, other_y = TARGETS[layout][1]
    open_eyes = Signal(0., x, y, 1., 1.)
    wink = Signal(.1, x, y, .1, 1.)
    reopen = Signal(.35, x, y, 1., 1.)
    cases = [
        ("Clin d’œil unique", [open_eyes, wink, reopen, Signal(.4, x, y, 1., 1.)], [0]),
        ("Clignement des deux yeux", [open_eyes, wink, Signal(.14, x, y, .1, .1), reopen], []),
        ("Perte de suivi", [open_eyes, wink, None, reopen], []),
        ("Cible mémorisée", [open_eyes, Signal(.1, other_x, other_y, .1, 1.),
                             Signal(.35, other_x, other_y, 1., 1.)], [0]),
    ]
    for name, signals, expected in cases:
        selection = Selection(layout)
        clicks = [click for signal in signals if (click := selection.feed(signal)) is not None]
        session.rows.append(dict(cas=name, resultat="correct" if clicks == expected else "incorrect",
                                 detail=f"Clics attendus : {expected} | obtenus : {clicks}"))
    session.done = True
    return session
