import queue, json
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import pyttsx3




q = queue.Queue()

def record_audio(duration=5):
    model = Model("vosk-model-small-en-us-0.15")
    rec = KaldiRecognizer(model, 16000)

    def callback(indata, frames, time, status):
        q.put(bytes(indata))

    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=callback):
        for _ in range(int(16000 / 8000 * duration)):
            data = q.get()
            if rec.AcceptWaveform(data):
                break
        result = json.loads(rec.FinalResult())
        return result.get("text", "")

def speak_text(text, voice="Female"):
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')

    if voice == "Male":
        engine.setProperty('voice', voices[0].id)
    else:
        engine.setProperty('voice', voices[1].id)

    engine.say(text)
    engine.runAndWait()
    



