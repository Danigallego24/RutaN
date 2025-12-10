from fastapi import APIRouter, HTTPException, Request
import os
import json
import urllib.request
import urllib.error
import re
import difflib
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from services.llm_engine import get_chat_model
from services import memory

# --- INTEGRACIÓN RAG ---
try:
    from services.rag_handler import rag_service
except ImportError:
    rag_service = None
    print("⚠️ RAG Handler no encontrado.")

router = APIRouter()

def parse_user_message(text: str) -> dict:
    """Extrae datos básicos del texto usando heurística."""
    out = {"destination": "", "duration": "", "style": ""}
    if not text: return out
    text_low = text.lower()
    
    # 1. Duración
    m = re.search(r"(\d+)\s*d[ií]a", text_low)
    if m: out["duration"] = m.group(1) + " días"
    
    # 2. Estilos
    styles = ["relax", "aventura", "cultural", "gastronómico", "familia", "lujo", "explorer", "low", "high", "medium"]
    for s in styles:
        if s in text_low:
            out["style"] = s
            break
            
    # 3. Ciudades (Lista básica)
    cities = ["madrid", "barcelona", "sevilla", "valencia", "granada", "bilbao", "malaga", "cordoba", "zaragoza", "santiago", "san sebastian", "ibiza", "mallorca", "tenerife"]
    for c in cities:
        if c in text_low:
            out["destination"] = c.title()
            break
            
    if not out["destination"]:
        m2 = re.search(r"\bviaje a ([A-Za-zÁÉÍÓÚÑáéíóúñ]+)\b", text_low)
        if m2: out["destination"] = m2.group(1).title()

    return out

@router.post("/generate")
async def generate_itinerary(request: Request) -> dict:
    try:
        # 1. Leer Payload
        try:
            payload = await request.json()
        except:
            raw = await request.body()
            payload = {"extra_info": raw.decode("utf-8", errors="ignore")}

        # 2. Normalizar campos
        extra_info = (payload.get("extra_info") or payload.get("message") or "").strip()
        dest_in = (payload.get("destination") or "").strip()
        dur_in = (payload.get("duration") or "").strip()
        style_in = (payload.get("style") or "").strip()
        model_in = (payload.get("model") or payload.get("model_name") or None)
        session_id = payload.get("session_id") or "user_1"

        # 3. Gestión de Memoria
        session = memory.get_session_data(session_id)
        memory_dict = session.setdefault("memory", {"destination": "", "duration": "", "style": ""})
        
        # Actualizar memoria
        if dest_in: memory.update_trip_memory(session_id, dest=dest_in)
        if dur_in: memory.update_trip_memory(session_id, dur=dur_in)
        if style_in: memory.update_trip_memory(session_id, style=style_in)

        # Analizar texto libre para extraer datos
        parsed = parse_user_message(extra_info)
        if parsed["destination"] and not dest_in: memory.update_trip_memory(session_id, dest=parsed["destination"])
        if parsed["duration"] and not dur_in: memory.update_trip_memory(session_id, dur=parsed["duration"])

        # Recuperar estado actual
        dest = (memory_dict.get("destination") or "").strip()
        dur = (memory_dict.get("duration") or "").strip()
        style = (memory_dict.get("style") or "").strip()

        # --- LÓGICA DE CONTEXTO RAG INTELIGENTE ---
        rag_context = ""
        
        # A. DETECTAR SI EL MENSAJE CONTIENE ANÁLISIS DE ARCHIVO
        # El frontend puede enviar el análisis directamente en extra_info
        if extra_info and ("[ANÁLISIS" in extra_info or "UBICACIÓN:" in extra_info or "TIPO DE ATRACCIÓN" in extra_info):
            # El usuario está compartiendo un análisis de archivo
            rag_context = f"\n📎 ANÁLISIS DEL ARCHIVO COMPARTIDO:\n{extra_info}\n"
            print(f"✅ Análisis de archivo detectado: {len(extra_info)} caracteres")
            
            # Simplificar el mensaje para el LLM
            extra_info = "He compartido un archivo/imagen. Por favor, analízalo según la información proporcionada arriba y sugiéreme actividades para el itinerario."
        
        # B. BÚSQUEDA VECTORIAL (Fallback)
        elif rag_service and extra_info:
            try:
                retrieved = rag_service.retrieve_context(extra_info, session_id, k=3)
                if retrieved and len(retrieved.strip()) > 20:
                    rag_context += f"\n📎 INFORMACIÓN HISTÓRICA:\n{retrieved}"
                    print(f"✅ Contexto histórico recuperado")
            except Exception as e:
                print(f"⚠️ RAG Error: {e}")

        # 5. GENERAR RESPUESTA (LLM)
        session_history = memory.get_chat_history(session_id)
        response_text = None

        try:
            llm, provider = get_chat_model(model_in)
            print(f"🛰️ Usando proveedor: {provider}")
            
            # --- PROMPT ANTIBLOQUEO ---
            system_prompt = """Eres RutaÑ, experto en viajes por España con acceso a análisis avanzado de imágenes mediante visión artificial.

REGLAS CRÍTICAS SOBRE IMÁGENES Y ARCHIVOS:
===========================================
✅ SI VES CONTENIDO CON ETIQUETA "📎 ANÁLISIS DE LA IMAGEN":
   - El usuario HA compartido una imagen/archivo
   - La sección "📎 ANÁLISIS" contiene la descripción visual de lo que se ve
   - DEBES actuar como si HUBIERAS visto la imagen (porque tienes la descripción exacta)
   - Responde: "Veo que...", "Según la imagen...", "En la foto observo..."
   - NUNCA digas "no puedo ver imágenes" o "no tengo acceso a visión"

✅ SI NO VES "📎 ANÁLISIS":
   - El usuario NO ha compartido archivo todavía
   - Solicita más información sobre destino/fecha/tipo de viaje

LÓGICA DE CONVERSACIÓN:
=======================
PASO 1 - USUARIO COMPARTE IMAGEN:
   → Tú: "Veo una foto de [lugar]. ¿Quieres planificar un viaje allí?"
   → Extrae: ubicación, tipo de atracción, actividades

PASO 2 - USUARIO DICE "SÍ, HAZLO":
   → Genera el JSON del itinerario (ver formato abajo)
   → Incluye actividades basadas en la imagen
   
PASO 3 - USUARIO DICE OTRA COSA:
   → Continúa la conversación naturalmente
   → Usa la información de la imagen como contexto

FORMATO JSON PARA ITINERARIOS (Genera SOLO cuando pida "crear ruta"):
=====================================================================
{{
    "titulo": "Viaje a [Lugar]",
    "dias": [
        {{
            "dia": 1,
            "resumen": "Exploración y primeras impresiones",
            "actividades": [
                {{"activity": "Visita al [Lugar específico]", "category": "Sightseeing"}},
                {{"activity": "[Actividad gastronómica]", "category": "Food"}},
                {{"activity": "[Actividad de relajación]", "category": "Relaxation"}}
            ]
        }}
    ]
}}

Categorías VÁLIDAS (usa EXACTAMENTE estas):
- Culture: museos, monumentos, galerías, iglesias
- Food: restaurantes, mercados, gastronomía
- Hiking: senderismo, montaña, naturaleza activa
- Relaxation: spa, descanso, playas tranquilas
- Sightseeing: miradores, paseos, tours generales
- General: otra actividad

IMPORTANTE: En Modo Itinerario (JSON), NO añadas texto fuera del JSON.
En Modo Chat, responde naturalmente como un asistente conversacional."""

            human_input = f"""Información del sistema:
{rag_context if rag_context else ""}
───────────────────────
ESTADO: Destino='{dest}', Duración='{dur}', Estilo='{style}'
USUARIO: {extra_info}

Responde naturalmente. Si ves "📎 ANÁLISIS", confirma que viste la imagen."""

            prompt_template = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
            ])

            if llm:
                chain = prompt_template | llm
                response_obj = chain.invoke({"input": human_input, "chat_history": session_history})
                response_text = response_obj.content if hasattr(response_obj, "content") else str(response_obj)

        except Exception as e:
            print(f"⚠️ LLM call failed: {e}")
            response_text = None

        if not response_text:
            return {"es_itinerario": False, "mensaje_chat": "Error técnico en el cerebro del asistente."}

        cleaned = response_text.replace("```json", "").replace("```", "").strip()
        m = re.search(r"\{[\s\S]*\}", cleaned)
        
        # Historial (guardamos el mensaje limpio, no el técnico enorme)
        memory.add_message_to_history(session_id, "user", extra_info)
        memory.add_message_to_history(session_id, "ai", cleaned)

        if m:
            try:
                return {"es_itinerario": True, **json.loads(m.group(0))}
            except:
                pass
        
        return {"es_itinerario": False, "mensaje_chat": cleaned}

    except Exception as e:
        print(f"❌ Error in /generate: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/model_check")
async def model_check(request: Request) -> dict:
    # Endpoint que comprueba el proveedor/resolve del modelo solicitado
    try:
        try:
            payload = await request.json()
        except:
            payload = {}

        model = payload.get("model") or payload.get("model_name") or os.getenv("LLM_MODEL", "smart")
        try:
            llm, provider = get_chat_model(model)
            # No devolvemos el objeto llm. Solo el nombre del proveedor/modelo resuelto.
            return {"ok": True, "provider": provider, "model": model}
        except Exception as e:
            return {"ok": False, "message": str(e)}
    except Exception as e:
        return {"ok": False, "message": str(e)}