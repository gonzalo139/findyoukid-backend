from fastapi import FastAPI, HTTPException
from supabase import create_client, Client
import os
from twilio.rest import Client as TwilioClient

app = FastAPI()

# Configuración de Supabase (las pondremos en variables de entorno)
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

@app.get("/")
def home():
    return {"status": "Codexia API Online"}

@app.get("/nino/{nino_id}")
def obtener_nino(nino_id: str):
    # Buscamos en la tabla que creamos en Supabase
    response = supabase.table("perfiles_ninos").select("*").eq("id", nino_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Niño no encontrado")
        
    return response.data[0]

@app.post("/notificar/{nino_id}")
def enviar_alerta(nino_id: str):
    # 1. Traer datos del niño y teléfono del padre
    nino = obtener_nino(nino_id)
    telefono = nino['telefono_emergencia']
    nombre = nino['nombre']
    
    # 2. Configuración de Twilio
    account_sid = os.environ.get("TWILIO_SID")
    auth_token = os.environ.get("TWILIO_TOKEN")
    from_number = os.environ.get("TWILIO_PHONE")
    
    client = TwilioClient(account_sid, auth_token)
    
    # 3. Enviar SMS
    message = client.messages.create(
        body=f"CODEXIA ALERTA: Tu hijo {nombre} ha sido escaneado. Por favor revisa la web.",
        from_=from_number,
        to=telefono
    )
    
    return {"status": "SMS enviado", "sid": message.sid}