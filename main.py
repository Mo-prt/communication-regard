import argparse
from pathlib import Path
import tkinter as tk

from interface import App


def main():
    parser = argparse.ArgumentParser(description="Tableau de communication piloté par le regard")
    parser.add_argument("--model", type=Path,
                        default=Path(__file__).parent / "modeles" / "face_landmarker.task")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--wink-min", type=float, default=.15, help="Durée minimale en secondes")
    parser.add_argument("--wink-max", type=float, default=.8, help="Durée maximale en secondes")
    parser.add_argument("--muet", action="store_true")
    args = parser.parse_args()
    if not 0 < args.wink_min <= args.wink_max:
        parser.error("La durée minimale du clin d’œil doit être positive et ≤ au maximum.")
    root = tk.Tk()
    App(root, args)
    root.mainloop()


if __name__ == "__main__":
    main()
