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
# Agrega este modelo de datos arriba junto a AlertaRequest
class ActualizarNino(BaseModel):
    telefono_emergencia: str = None
    condicion_medica: str = None

# Nueva ruta para actualizar datos desde el Panel Admin
@app.patch("/nino/{nino_id}")
async def actualizar_nino(nino_id: str, datos: dict):
    # 1. Extraer los datos del JSON
    nuevo_tel = datos.get("telefono_emergencia")
    nuevas_alergias = datos.get("alergias")
    nuevo_calma = datos.get("protocolo_calma")
    current_user_id = datos.get("user_id") # El ID del padre logueado

    if not current_user_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")

    # 2. Consultar quién es el dueño actual en la DB
    res = supabase.table("perfiles_ninos").select("user_id").eq("id", nino_id).execute()
    
    if not res.data:
        raise HTTPException(status_code=404, detail="ID de pulsera no encontrado")
    
    dueno_actual = res.data[0].get("user_id")

    # 3. Lógica de "Dueño Único"
    if dueno_actual is None:
        # CASO A: Está huérfana, la vinculamos al primer valiente
        print(f"Vinculando pulsera {nino_id} al usuario {current_user_id}")
        supabase.table("perfiles_ninos").update({"user_id": current_user_id}).eq("id", nino_id).execute()
    elif str(dueno_actual) != str(current_user_id):
        # CASO B: Ya tiene dueño y NO es este usuario
        raise HTTPException(status_code=403, detail="Acceso Denegado: Esta pulsera ya tiene un dueño registrado.")

    # 4. Si pasó los filtros, actualizamos los datos médicos
    update_data = {
        "telefono_emergencia": nuevo_tel,
        "alergias": nuevas_alergias,
        "protocolo_calma": nuevo_calma
    }
    
    # Limpiamos los None para no borrar datos por error
    update_data = {k: v for k, v in update_data.items() if v is not None}
    
    result = supabase.table("perfiles_ninos").update(update_data).eq("id", nino_id).execute()
    
    return {"status": "success", "message": "Datos actualizados correctamente"}
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
