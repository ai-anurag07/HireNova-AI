import os
import edge_tts
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()
groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

async def text_to_speech(text: str) -> bytes:
    """Takes text and converts it into a highly realistic human voice MP3."""
    # "en-US-AriaNeural" is a very professional, clear female voice. 
    # (You can also use "en-US-GuyNeural" for a male voice)
    communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
    
    audio_bytes = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes += chunk["data"]
            
    return audio_bytes

async def speech_to_text(audio_bytes: bytes, filename="user_answer.wav") -> str:
    """Sends your voice recording to Groq's Whisper API to transcribe instantly."""
    try:
        # Groq's Whisper requires a file-like tuple
        transcription = await groq_client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model="whisper-large-v3", # Groq's super fast transcription model
            response_format="json",
            language="en"
        )
        return transcription.text
    except Exception as e:
        print(f"Transcription error: {e}")
        return ""