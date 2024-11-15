import speech_recognition as sr
import os
from pydub import AudioSegment
import tempfile

class VoiceHandler:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 20000
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = 0.8
    
    def process_audio_file(self, audio_path: str, language: str) -> str:
        try:
            if not audio_path.endswith('.wav'):
                audio = AudioSegment.from_file(audio_path)
                temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                audio.export(temp_wav.name, format='wav')
                audio_path = temp_wav.name

            with sr.AudioFile(audio_path) as source:
                audio = self.recognizer.record(source)
                
                if language == "Arabic":
                    return self.recognizer.recognize_google(audio, language="ar-SA")
                elif language == "Mixed (Arabic/English)":
                    try:
                        return self.recognizer.recognize_google(audio, language="ar-SA")
                    except sr.UnknownValueError:
                        return self.recognizer.recognize_google(audio, language="en-US")
                else:  # English
                    return self.recognizer.recognize_google(audio, language="en-US")
                    
        except sr.RequestError as e:
            return f"Error: Could not request results from speech service: {str(e)}"
        except sr.UnknownValueError:
            return "Error: Could not understand audio. Please speak clearly and try again."
        except Exception as e:
            return f"Error: {str(e)}"
        finally:
            if 'temp_wav' in locals():
                os.unlink(temp_wav.name)

    def check_microphone_access(self) -> bool:
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.1)
                return True
        except (OSError, AttributeError, sr.RequestError):
            return False