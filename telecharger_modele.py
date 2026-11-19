from pathlib import Path
from urllib.request import urlretrieve

folder = Path(__file__).parent / "modeles"
folder.mkdir(exist_ok=True)
temporary = folder / "face_landmarker.part"
url = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/"
       "face_landmarker/float16/1/face_landmarker.task")
try:
    urlretrieve(url, temporary)
    destination = temporary.with_suffix(".task")
    temporary.replace(destination)
    print(destination)
finally:
    temporary.unlink(missing_ok=True)
