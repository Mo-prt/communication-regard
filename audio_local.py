from base64 import b64encode
import shutil
import subprocess
import sys


class Speaker:
    def __init__(self):
        self.process = None
        self.command = shutil.which("espeak-ng") or shutil.which("espeak")

    def say(self, phrase):
        self.stop()
        if sys.platform == "win32":
            literal = phrase.replace("'", "''")
            script = ("Add-Type -AssemblyName System.Speech; "
                      "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                      "$s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::NotSet,"
                      "[System.Speech.Synthesis.VoiceAge]::NotSet,0,"
                      "[System.Globalization.CultureInfo]::GetCultureInfo('fr-FR')); "
                      f"$s.Speak('{literal}')")
            command = ["powershell.exe", "-NoProfile", "-EncodedCommand",
                       b64encode(script.encode("utf-16-le")).decode("ascii")]
            self.process = subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW)
            return
        if sys.platform == "darwin":
            command = ["say", "-v", "Thomas", phrase]
        elif self.command:
            command = [self.command, "-v", "fr", phrase]
        else:
            raise OSError("Installez espeak-ng pour activer la voix.")
        self.process = subprocess.Popen(command, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL)

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=.15)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process = None
