from gtts import gTTS
import io

def play_text(text: str) -> tuple[str, str]:
    try:
        tts = gTTS(text=text, lang='en')
        audio_path = "temp_audio.mp3"
        tts.save(audio_path)
        return audio_path, None
    except Exception as e:
        return None, f"Error generating audio: {str(e)}"