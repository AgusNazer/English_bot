# src/main.py
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import random
import os
from gtts import gTTS

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
You are an expert, friendly, and highly specialized English tutor and conversation partner. Your sole mission is to help the user gain maximum fluency in Technical English for Information Technology and Software Development, with a particular focus on their role as an AI Trainer.

CRITICAL INSTRUCTIONS:
1. Always maintain the thread of the conversation. Respond directly to the user's inputs like an experienced Tech Lead, Senior Developer, or AI Team Product Owner.
2. The core conversation must revolve around technical topics: code reviews, software architecture, programming languages (Python, Java, TypeScript, etc.), frameworks, cloud environments, and specialized AI/LLM concepts.
3. Actively introduce and simulate onboarding scenarios for the IT sector, engineering daily standups, and corporate technical communication.
4. Use and teach natural, high-level industry jargon, tech vocabulary, and common software development idioms (e.g., "technical debt", "refactoring", "pull requests", "onboarding pipeline", "scalability bottlenecks").
5. Keep the interaction alive, encouraging, and highly collaborative. End every response with an open-ended technical question or a simulated workplace dilemma to keep the conversation going.
"""

@app.post("/vent")
async def process_chat(interaction: RageInteraction, db: Session = Depends(get_db)):
    text_input = interaction.detected_text
    
    # 1. Gestión del usuario y contador de interacciones en SQLite
    user = db.query(DBUserProfile).filter(DBUserProfile.user_id == interaction.user_id).first()
    if not user:
        user = DBUserProfile(user_id=interaction.user_id, rage_streak=1)
        db.add(user)
    else:
        user.rage_streak += 1
    db.commit()
    db.refresh(user)
    
    # 2. Llamada directa a Gemini para generar la respuesta dinámica
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=text_input,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
            )
        )
        reply = response.text.strip()
    except Exception as e:
        # Esto te va a mostrar el error real en la terminal donde corre Uvicorn
        print("--- ERROR DETECTADO EN GEMINI ---")
        print(e)
        print("---------------------------------")
        reply = "Hey! I had a small connection issue with my server. Could you repeat that, please?"

    # 3. Generar el archivo de audio con gTTS leyendo la respuesta de la IA
    filename = f"{interaction.user_id}_{random.randint(1000, 9999)}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)
    
    # Mandamos 'en' fijo porque la IA siempre te va a hablar en inglés
    tts = gTTS(text=reply, lang='en')
    tts.save(filepath)
    
    audio_url = f"{PUBLIC_URL}/static/{filename}"
        
    return {
        "user_id": user.user_id,
        "interaction_count": user.rage_streak,
        "user_said": text_input,
        "reply": reply,
        "audio_url": audio_url
    }