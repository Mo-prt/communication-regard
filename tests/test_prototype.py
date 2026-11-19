import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from evaluation import Session, simulated_cases
from logique import CALIBRATION, Calibration, Signal


class PrototypeTest(unittest.TestCase):
    def test_wink_cases(self):
        for layout in (2, 4):
            self.assertEqual(simulated_cases(layout).summary(), {"cas": 4, "reussis": 4})

    def test_calibration(self):
        for layout in (2, 4):
            groups = [[Signal(0, .2 + .55*x, .03 + .3*y, .27, .24)]
                      for x, y in CALIBRATION[layout]]
            cal = Calibration(layout, groups)
            for (x, y), group in zip(CALIBRATION[layout], groups):
                actual = cal.position(group[0].x, group[0].y)
                self.assertAlmostEqual(actual[0], x)
                self.assertAlmostEqual(actual[1], y)

    def test_guided_metrics_and_export(self):
        session = Session("simulation", 2, "guide", 0, [0, 1, 0, 1])
        session.advance(1, 0)
        session.advance(4, 1)
        session.advance(6, 1)
        session.advance(16)
        self.assertEqual(session.summary(), dict(essais=4, corrects=2, incorrects=1,
                                                 sans_reponse=1, taux_reussite_pct=50.,
                                                 temps_median_s=2))
        with TemporaryDirectory() as directory:
            path = Path(directory) / "export.csv"
            session.export(path)
            with path.open(encoding="utf-8-sig") as stream:
                rows = list(csv.DictReader(stream, delimiter=";"))
            self.assertEqual(len(rows), 5)
            self.assertTrue(all(row["source"] == "simulation" and row["disposition"] == "2"
                                for row in rows))

    def test_free_observation(self):
        session = Session("webcam", 4, "libre", 10, limit=60)
        session.advance(11, 1)
        session.advance(50, 2)
        session.advance(70, 2)
        self.assertTrue(session.done)
        self.assertEqual(session.summary(), {"clics_involontaires": 2, "clics_par_minute": 2.})


if __name__ == "__main__":
    unittest.main()
