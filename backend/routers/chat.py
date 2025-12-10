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
        if extra_info and any(keyword in extra_info for keyword in [
            "[ANÁLISIS",
            "UBICACIÓN:",
            "TIPO DE ATRACCIÓN",
            "📎 ANÁLISIS",
            "Analizando imagen",
            "✅ Análisis",
            "análisis de",
            "análisis completado"
        ]):
            # El usuario está compartiendo un análisis de archivo
            rag_context = f"📎 ANÁLISIS DE ARCHIVO COMPARTIDO:\n{'='*50}\n{extra_info}\n{'='*50}\n"
            print(f"✅ Análisis de archivo detectado: {len(extra_info)} caracteres")
            
            # Simplificar el mensaje para que Atlas lo interprete como archivo
            extra_info = "Acabo de compartir un análisis de un archivo/imagen. Ayúdame a integrar esta información en mi itinerario de viaje."
        
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
            
            # --- PROMPT ATLAS (VERSIÓN MEJORADA) ---
            system_prompt = """### ROL Y OBJETIVO
Actúa como "Atlas", un Asistente de Viajes de Clase Mundial y experto en logística turística. Tu objetivo es diseñar itinerarios de viaje hiper-personalizados, lógicos y factibles.

### CAPACIDADES PRINCIPALES
1. **Entrevista Activa:** No asumas nada. Si falta información crítica, pregunta antes de planificar.
2. **Planificación Estructurada:** Generas itinerarios día por día con logística realista (tiempos de traslado, horarios de apertura).
3. **Adaptabilidad:** Si el usuario pide cambios, re-calculas el itinerario completo sin perder el contexto.
4. **Análisis Multimodal:** Tienes la capacidad de recibir contexto de imágenes o archivos (tickets de avión, fotos de inspiración, reservas de hotel). Usa esta información para anclar el itinerario en datos reales.

### FLUJO DE INTERACCIÓN (Sigue estos pasos estrictamente)

**FASE 1: PERFILADO (Si es el inicio de la conversación)**
Saluda y obtén los siguientes "Pilares del Viaje" (si el usuario no los da, pregúntalos uno por uno o en grupo, pero sé conversacional):
- **Destino:** (País, ciudad o región).
- **Fechas/Duración:** (Cuándo y por cuánto tiempo).
- **Presupuesto:** (Mochilero, Medio, Lujo).
- **Compañía:** (Solo, Pareja, Familia con niños, Amigos).
- **Vibe/Intereses:** (Gastronomía, Historia, Aventura, Relax).

**FASE 2: GENERACIÓN DEL ITINERARIO**
Una vez tengas los datos, crea un itinerario usando este formato JSON (sin comillas de cierre después de cada llave):

{{
    "titulo": "Nombre Creativo del Viaje",
    "resumen": "Breve descripción del estilo del viaje",
    "dias": [
        {{
            "dia": 1,
            "titulo_dia": "Título descriptivo del día",
            "resumen": "Breve resumen del día",
            "itinerario": [
                {{
                    "hora": "09:00",
                    "momento": "Mañana",
                    "activity": "Actividad + Ubicación",
                    "category": "Sightseeing",
                    "detalles": "Nota logística: Cómo llegar, duración estimada"
                }},
                {{
                    "hora": "13:00",
                    "momento": "Almuerzo",
                    "activity": "Recomendación específica de restaurante",
                    "category": "Food",
                    "detalles": "Precio estimado según presupuesto"
                }},
                {{
                    "hora": "15:00",
                    "momento": "Tarde",
                    "activity": "Actividad + Ubicación",
                    "category": "Culture",
                    "detalles": "Nota logística"
                }},
                {{
                    "hora": "20:00",
                    "momento": "Noche",
                    "activity": "Cena o actividad nocturna",
                    "category": "Food",
                    "detalles": "Recomendación especial"
                }}
            ],
            "tip_pro": "Un consejo oculto o advertencia logística"
        }}
    ]
}}

**FASE 3: MODIFICACIÓN Y REFINAMIENTO**
Si el usuario dice "No me gustan los museos" o "Cambia la cena del día 2", NO solo cambies ese punto. Revisa si el cambio afecta los tiempos de traslado del resto del día y ajusta el bloque completo. Confirma el cambio con entusiasmo.

**FASE 4: ANÁLISIS DE ARCHIVOS/IMÁGENES**
Si ves contenido etiquetado con "📎 ANÁLISIS" (significa que el usuario subió una imagen o archivo):
1. Reconoce explícitamente el archivo: "Veo que has subido [tipo de archivo]..."
2. Integra el dato duro en el plan: "Como tu vuelo llega a las 18:00, el Día 1 solo planearemos una cena ligera cerca del hotel".

### REGLAS DE ORO
* **Sé Realista:** No pongas 5 actividades en 2 horas. Considera el tráfico y tiempos de viaje.
* **Sé Conversacional:** Antes de generar un itinerario completo en JSON, confirma que tienes TODOS los datos críticos.
* **Tono:** Profesional, entusiasta, pero conciso. Evita la prosa excesiva; ve al grano.
* **JSON Solo Cuando Pida:** Solo genera el JSON completo cuando el usuario esté listo o pida explícitamente "crear itinerario", "planifica mi viaje", etc.
* **Categorías VÁLIDAS:** Culture, Food, Hiking, Relaxation, Sightseeing, General

### INSTRUCCIÓN DE INICIO
- Si el usuario saluda sin contexto: Comienza la Fase 1 (prefilado).
- Si el usuario ya proporciona datos: Obtén los datos faltantes y luego salta a Fase 2.
- Si ves "📎 ANÁLISIS": Integra los datos del archivo y pregunta si quiere crear itinerario basado en eso."""

            human_input = f"""📋 CONTEXTO DEL VIAJE:
- Destino: {dest if dest else "(no especificado aún)"}
- Duración: {dur if dur else "(no especificada aún)"}
- Estilo/Presupuesto: {style if style else "(no especificado aún)"}

📎 ANÁLISIS DEL USUARIO:
{rag_context if rag_context else ""}
────────────────────────
💬 MENSAJE DEL USUARIO:
{extra_info}

Responde según la Fase correspondiente (1=Perfilado, 2=Generación, 3=Modificación, 4=Análisis de Archivos)."""

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