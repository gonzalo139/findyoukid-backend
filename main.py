from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
import os
from twilio.rest import Client as TwilioClient

app = FastAPI()

# Configuración de CORS para que Vercel pueda comunicarse con Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo para recibir la URL de Google Maps desde el Frontend
class AlertaRequest(BaseModel):
    maps_url: str = "Ubicación no proporcionada"

# Configuración de Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

@app.get("/")
def home():
    return {"status": "Codexia API Online - GeoEnabled"}

@app.get("/nino/{nino_id}")
def obtener_nino(nino_id: str):
    response = supabase.table("perfiles_ninos").select("*").eq("id", nino_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Niño no encontrado")
        
    return response.data[0]

@app.post("/notificar/{nino_id}")
def enviar_alerta(nino_id: str, request: AlertaRequest):
    # 1. Obtener datos del niño de Supabase
    nino = obtener_nino(nino_id)
    telefono = nino['telefono_emergencia']
    nombre = nino['nombre']
    
    # 2. Credenciales de Twilio desde Variables de Entorno
    account_sid = os.environ.get("TWILIO_SID")
    auth_token = os.environ.get("TWILIO_TOKEN")
    from_number = os.environ.get("TWILIO_PHONE")
    
    client = TwilioClient(account_sid, auth_token)
    
    # 3. Construcción del mensaje con la geolocalización
    mensaje_cuerpo = (
        f"CODEXIA ALERTA: {nombre} ha sido encontrado.\n"
        f"Ver ubicación en el mapa: {request.maps_url}"
    )
    
    try:
        message = client.messages.create(
            body=mensaje_cuerpo,
            from_=from_number,
            to=telefono
        )
        return {"status": "SMS enviado con éxito", "sid": message.sid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
