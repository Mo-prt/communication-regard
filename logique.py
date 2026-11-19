from dataclasses import dataclass
from statistics import median

PHRASES = ("Oui", "Non", "J’ai mal", "Aidez-moi à changer de position")
TARGETS = {
    2: ((.25, .5), (.75, .5)),
    4: ((.25, .25), (.75, .25), (.25, .75), (.75, .75)),
}
CALIBRATION = {2: TARGETS[2], 4: (*TARGETS[4], (.5, .5))}


@dataclass(frozen=True)
class Signal:
    time: float
    x: float
    y: float
    left: float
    right: float


def solve(matrix, values):
    """Solve the small calibration system by elimination with pivoting."""
    rows = [list(row) + [value] for row, value in zip(matrix, values)]
    size = len(rows)
    for col in range(size):
        pivot = max(range(col, size), key=lambda i: abs(rows[i][col]))
        rows[col], rows[pivot] = rows[pivot], rows[col]
        scale = rows[col][col]
        if abs(scale) < 1e-9:
            raise ValueError("Les mesures ne distinguent pas assez les cibles.")
        rows[col] = [n / scale for n in rows[col]]
        for i in range(size):
            if i != col:
                factor = rows[i][col]
                rows[i] = [a - factor * b for a, b in zip(rows[i], rows[col])]
    return [row[-1] for row in rows]


class Calibration:
    def __init__(self, layout, samples):
        measured = [(median(s.x for s in group), median(s.y for s in group))
                    for group in samples]
        self.layout = layout
        self.left = .62 * median(s.left for group in samples for s in group)
        self.right = .62 * median(s.right for group in samples for s in group)
        if min(self.left, self.right) < .035:
            raise ValueError("Gardez les deux yeux ouverts pendant la calibration.")
        if layout == 2:
            self.start, self.end = (point[0] for point in measured)
            if abs(self.end - self.start) < .025:
                raise ValueError("Écart horizontal insuffisant. Réessayez.")
        else:
            rows = [(1, x, y) for x, y in measured]
            columns = list(zip(*rows))
            matrix = [[sum(a*b for a, b in zip(u, v)) for v in columns]
                      for u in columns]
            self.coefficients = [
                solve(matrix, [sum(a*b for a, b in zip(col, goal))
                               for col in columns])
                for goal in zip(*CALIBRATION[layout])
            ]
            if any(max(abs(a-b) for a, b in zip(self.position(x, y), target)) > .16
                   for (x, y), target in zip(measured, CALIBRATION[layout])):
                raise ValueError("Calibration verticale instable. Réessayez ou choisissez deux boutons.")

    def position(self, x, y):
        if self.layout == 2:
            return .25 + .5 * (x - self.start) / (self.end - self.start), .5
        return tuple(a + b*x + d*y for a, b, d in self.coefficients)


def hit(layout, point):
    if point is None:
        return None
    x, y = point
    for i, (cx, cy) in enumerate(TARGETS[layout]):
        if abs(x-cx) <= .215 and abs(y-cy) <= (.34 if layout == 2 else .19):
            return i
    return None


class Selection:
    def __init__(self, layout=2, calibration=None, min_wink=.15, max_wink=.8):
        if not 0 < min_wink <= max_wink:
            raise ValueError("Durée du clin d’œil invalide.")
        self.layout = layout
        self.calibration = calibration
        self.min_wink, self.max_wink = min_wink, max_wink
        self.point = None
        self.last_time = None
        self.cancel()

    @property
    def hovered(self):
        return hit(self.layout, self.point)

    def cancel(self):
        self.started = None
        self.target = None
        self.armed = False

    def feed(self, signal):
        if signal is None:
            self.cancel()
            self.point = None
            self.last_time = None
            return None
        if self.last_time is not None and not 0 < signal.time-self.last_time <= .35:
            self.cancel()
            self.point = None
        self.last_time = signal.time
        cal = self.calibration
        left_closed = signal.left < (cal.left if cal else .5)
        right_closed = signal.right < (cal.right if cal else .5)
        if right_closed:
            self.cancel()
            return None
        if left_closed:
            if self.armed and self.started is None:
                self.started, self.target = signal.time, self.hovered
            if self.started is not None and signal.time-self.started > self.max_wink:
                self.cancel()
            return None
        clicked = None
        if self.started is not None and self.min_wink <= signal.time-self.started <= self.max_wink:
            clicked = self.target
        self.started = self.target = None
        self.armed = True
        raw = cal.position(signal.x, signal.y) if cal else (signal.x, signal.y)
        x, y = (min(1., max(0., item)) for item in raw)
        self.point = ((x, y) if self.point is None else
                      (.55*self.point[0]+.45*x, .55*self.point[1]+.45*y))
        return clicked
