from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware # IMPORTANTE
from supabase import create_client, Client
import os
from twilio.rest import Client as TwilioClient

app = FastAPI()

# Configuración de CORS para permitir que Vercel se conecte
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción podés poner la URL de Vercel para más seguridad
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

@app.get("/")
def home():
    return {"status": "Codexia API Online"}

@app.get("/nino/{nino_id}")
def obtener_nino(nino_id: str):
    response = supabase.table("perfiles_ninos").select("*").eq("id", nino_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Niño no encontrado")
        
    return response.data[0]

@app.post("/notificar/{nino_id}")
def enviar_alerta(nino_id: str):
    nino = obtener_nino(nino_id)
    telefono = nino['telefono_emergencia']
    nombre = nino['nombre']
    
    account_sid = os.environ.get("TWILIO_SID")
    auth_token = os.environ.get("TWILIO_TOKEN")
    from_number = os.environ.get("TWILIO_PHONE")
    
    client = TwilioClient(account_sid, auth_token)
    
    message = client.messages.create(
        body=f"CODEXIA ALERTA: Tu hijo {nombre} ha sido encontrado. Revisa la app para más info.",
        from_=from_number,
        to=telefono
    )
    
    return {"status": "SMS enviado", "sid": message.sid}
