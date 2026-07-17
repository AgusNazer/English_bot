from pydantic import BaseModel
from typing import Optional

# Modelo para el usuario / sesión
class UserProfile(BaseModel):
    username: str
    selected_voice: str = "default"  # Ej: "gordon", "sergeant", "sarcastic"
    rage_streak: int = 0             # esto no va mas
    

# Modelo para procesar la interacción de audio/texto
class RageInteraction(BaseModel):
    user_id: str
    detected_text: str               # Lo que el usuario dijo
    audio_duration_seconds: Optional[float] = None