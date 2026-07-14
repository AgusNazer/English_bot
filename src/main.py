# src/main.py
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import random
import os
import time
from gtts import gTTS
import edge_tts

# Importaciones locales
from src.schemas import RageInteraction
from src.database import engine, Base, get_db
from src.models import DBUserProfile
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pyngrok import ngrok

load_dotenv()

# Importaciones locales
from src.schemas import RageInteraction
from src.database import engine, Base, get_db
from src.models import DBUserProfile

# Creamos las tablas de SQLite al iniciar la app
Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = [
    "http://localhost:3000",
    "https://english-bot.anuarnazer.com",  
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUDIO_DIR = "src/static"
os.makedirs(AUDIO_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=AUDIO_DIR), name="static")

# Variables globales para manejar la URL dinámica de Ngrok
PUBLIC_URL = "http://127.0.0.1:8000"

# Evento de FastAPI que corre justo cuando arranca el servidor
@app.on_event("startup")
async def startup_event():
    global PUBLIC_URL
    
    # 1. Render setea automáticamente la variable 'RENDER' en sus servidores.
    # Si esa variable existe, significa que estamos en producción.
    if os.getenv("RENDER") == "true":
        # Leemos la URL definitiva de Render que vas a poner en el panel
        PUBLIC_URL = os.getenv("PRODUCTION_URL", "https://tu-app.onrender.com")
        print(f"\n🚀 CORRIENDO EN PRODUCCIÓN - URL: {PUBLIC_URL}\n")
        return # Cortamos acá para que NO intente levantar pyngrok

    # 2. Si NO estamos en Render, significa que estás en tu Mac. Corre pyngrok:
    ngrok_token = os.getenv("NGROK_AUTHTOKEN")
    if ngrok_token:
        try:
            ngrok.set_auth_token(ngrok_token)
            tunnel = ngrok.connect(8000)
            PUBLIC_URL = tunnel.public_url
            print(f"\n🚀 ¡TÚNEL NGROK LEVANTADO CON ÉXITO!")
            print(f"🔗 URL Pública para tu iPhone: {PUBLIC_URL}\n")
        except Exception as e:
            print(f"⚠️ No se pudo levantar Ngrok local: {e}")

# Inicializamos el cliente de Gemini (toma automáticamente la variable GEMINI_API_KEY)
client = genai.Client()

SYSTEM_PROMPT = """
You are an expert, friendly, and highly adaptable English tutor and conversation partner. Your mission is to help the user gain maximum fluency in English, with a massive focus on professional development for their role as an AI Trainer and Software Engineer.

CRITICAL LANGUAGE & CONVERSATION RULES:
1. You MUST respond 100% in natural, professional, and clear English. NEVER reply in Spanish under any circumstances.
2. ALWAYS maintain the exact thread of the conversation. Respond directly and intelligently to the user's specific inputs like a real human peer.
3. ADAPT TO THE TOPIC COMPLETELY: 
   - If the user wants to talk about casual topics (like football, the World Cup, or movies), engage deeply and naturally in that specific topic using real data. Do NOT force IT terminology or software concepts into a casual conversation.
   - If the user brings up technical topics (code reviews, software architecture, Python, Java, frameworks, or tech onboarding), immediately pivot to your tech persona and use high-level industry jargon and corporate software idioms.
4. End every response with an open-ended question in English to keep the dialogue moving forward naturally.
"""

@app.post("/vent")
async def process_chat(interaction: RageInteraction, db: Session = Depends(get_db)):
    t0 = time.time()
    text_input = interaction.detected_text

    user = db.query(DBUserProfile).filter(DBUserProfile.user_id == interaction.user_id).first()
    if not user:
        user = DBUserProfile(user_id=interaction.user_id, rage_streak=1)
        db.add(user)
    else:
        user.rage_streak += 1
    db.commit()
    db.refresh(user)
    t1 = time.time()
    print(f"⏱️ DB: {t1-t0:.2f}s", flush=True)

#agregar mnemoria para contexto en el siguiente bloque
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=text_input,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        reply = response.text.strip()
    except Exception as e:
        print("--- ERROR DETECTADO EN GEMINI ---", flush=True)
        print(repr(e), flush=True)
        print("---------------------------------", flush=True)
        reply = "Hey! I had a small connection issue with my server. Could you repeat that, please?"
    t2 = time.time()  # 👈 ahora esto está SIEMPRE, sea éxito o error
    print(f"⏱️ Gemini: {t2-t1:.2f}s", flush=True)

    filename = f"{interaction.user_id}_{random.randint(1000, 9999)}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)

    communicate = edge_tts.Communicate(reply, voice="en-US-AriaNeural")
    await communicate.save(filepath)

    t3 = time.time()
    print(f"⏱️ TTS: {t3-t2:.2f}s", flush=True)

    audio_url = f"{PUBLIC_URL}/static/{filename}"
    print(f"⏱️ TOTAL: {t3-t0:.2f}s", flush=True)

    return {
        "user_id": user.user_id,
        "interaction_count": user.rage_streak,
        "user_said": text_input,
        "reply": reply,
        "audio_url": audio_url
    }