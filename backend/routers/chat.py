from fastapi import APIRouter, HTTPException, Request
import os
import json
import re
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from services.llm_engine import get_chat_model
from services import memory

try:
    from services.rag_handler import rag_service
except ImportError:
    rag_service = None
    print("⚠️ RAG Handler no encontrado.")

router = APIRouter()


def parse_user_message(text: str) -> dict:
    out = {"destination": "", "duration": "", "style": ""}
    if not text:
        return out

    text_low = text.lower()

    m = re.search(r"(\d+)\s*d[ií]a", text_low)
    if m:
        out["duration"] = m.group(1) + " días"

    styles = [
        "relax",
        "aventura",
        "cultural",
        "gastronómico",
        "familia",
        "lujo",
        "explorer",
        "low",
        "medium",
        "high",
    ]
    for s in styles:
        if s in text_low:
            out["style"] = s
            break

    cities = [
        "madrid",
        "barcelona",
        "sevilla",
        "valencia",
        "granada",
        "bilbao",
        "malaga",
        "málaga",
        "cordoba",
        "córdoba",
        "zaragoza",
        "santiago",
        "san sebastian",
        "san sebastián",
        "ibiza",
        "mallorca",
        "tenerife",
    ]
    for c in cities:
        if c in text_low:
            out["destination"] = c.title()
            break

    if not out["destination"]:
        m2 = re.search(r"\bviaje a ([A-Za-zÁÉÍÓÚÑáéíóúñ]+)\b", text_low)
        if m2:
            out["destination"] = m2.group(1).title()

    return out


@router.post("/generate")
async def generate_itinerary(request: Request) -> dict:
    try:
        try:
            payload = await request.json()
        except Exception:
            raw = await request.body()
            payload = {"extra_info": raw.decode("utf-8", errors="ignore")}

        extra_info = (payload.get("extra_info") or payload.get("message") or "").strip()
        dest_in = (payload.get("destination") or "").strip()
        dur_in = payload.get("duration")
        style_in = (payload.get("style") or payload.get("difficulty") or "").strip()

        model_in = (
            payload.get("model")
            or payload.get("model_name")
            or os.getenv("LLM_MODEL", "smart")
        )
        session_id = payload.get("session_id") or "user_1"

        session = memory.get_session_data(session_id)
        _ = session.setdefault(
            "memory", {"destination": "", "duration": "", "style": ""}
        )

        if dest_in:
            memory.update_trip_memory(session_id, dest=dest_in)
        if dur_in is not None and dur_in != "":
            memory.update_trip_memory(session_id, dur=dur_in)
        if style_in:
            memory.update_trip_memory(session_id, style=style_in)

        parsed = parse_user_message(extra_info)
        if parsed["destination"] and not dest_in:
            memory.update_trip_memory(session_id, dest=parsed["destination"])
        if parsed["duration"] and not dur_in:
            memory.update_trip_memory(session_id, dur=parsed["duration"])
        if parsed["style"] and not style_in:
            memory.update_trip_memory(session_id, style=parsed["style"])

        trip_ctx = memory.get_trip_context(session_id)
        raw_dest = trip_ctx.get("destination")
        raw_dur = trip_ctx.get("duration")
        raw_style = trip_ctx.get("style")

        dest = str(raw_dest).strip() if raw_dest is not None else ""
        dur = str(raw_dur).strip() if raw_dur is not None else ""
        style = str(raw_style).strip() if raw_style is not None else ""

        rag_context = ""
        is_file_analysis = False

        if extra_info and any(
            keyword in extra_info
            for keyword in [
                "[ANÁLISIS",
                "UBICACIÓN:",
                "TIPO DE ATRACCIÓN",
                "📎 ANÁLISIS",
                "Analizando imagen",
                "✅ Análisis",
                "análisis completado",
            ]
        ):
            is_file_analysis = True
            rag_context = (
                "📎 ANÁLISIS DE ARCHIVO COMPARTIDO:\n"
                + "=" * 50
                + f"\n{extra_info}\n"
                + "=" * 50
                + "\n"
            )
            print(f"✅ Análisis de archivo detectado: {len(extra_info)} caracteres")
            extra_info += (
                "\n\nTen en cuenta que el bloque anterior es un análisis de "
                "archivo/imagen relacionado con el viaje."
            )

        elif rag_service and extra_info:
            try:
                retrieved = rag_service.retrieve_context(extra_info, session_id, k=3)
                if retrieved and len(retrieved.strip()) > 20:
                    rag_context += retrieved
                    print("✅ Contexto histórico recuperado desde RAG")
            except Exception as e:
                print(f"⚠️ RAG Error: {e}")

        existing_itinerary = memory.get_itinerary(session_id)
        phase = 1

        if is_file_analysis:
            phase = 4
        elif dest and dur:
            phase = 3 if existing_itinerary else 2

        session_history = memory.get_chat_history(session_id)
        response_text: str | None = None

        try:
            llm, provider = get_chat_model(model_in)
            print(f"🛰️ Usando proveedor: {provider} (modelo: {model_in})")

            # IMPORTANTE: llaves del JSON de ejemplo escapadas con {{ }}
            system_prompt = """### ROL Y OBJETIVO
Actúa como "Atlas", un Asistente de Viajes de Clase Mundial y experto en logística turística. Tu objetivo es diseñar itinerarios de viaje hiper-personalizados, lógicos y factibles.

SIEMPRE recibirás una variable `FASE_ACTUAL` en el mensaje del usuario. Debes comportarte así:

- FASE_ACTUAL = 1 (Perfilado):
  - Tu tarea es SOLO hacer preguntas y completar los "Pilares del Viaje".
  - No generes todavía un itinerario completo ni devuelvas JSON.
  - Sé muy concreto y no alargues la respuesta.

- FASE_ACTUAL = 2 (Generación de Itinerario):
  - Si faltan datos críticos (destino o duración), pide esos datos primero, de forma breve.
  - Si ya tienes información suficiente, GENERA un itinerario completo.
  - La respuesta debe ser EXCLUSIVAMENTE un JSON válido, sin ningún texto antes ni después.

- FASE_ACTUAL = 3 (Modificación / Regeneración):
  - Asume que ya existe un itinerario previo (presente en el historial).
  - El usuario puede pedir cambios ("quita museos", "añade más playa", etc.).
  - Devuelve SIEMPRE un itinerario COMPLETO en formato JSON, ya ajustado, sin texto adicional.

- FASE_ACTUAL = 4 (Análisis de Archivos/Imágenes):
  - Integra el contenido del bloque etiquetado como análisis de archivo/imágenes en la lógica del viaje (vuelos, reservas, fotos...).
  - Puedes hacer preguntas adicionales si faltan datos críticos.
  - Cuando generes itinerario, hazlo igual que en FASE 2/3: SOLO JSON.

### PILARES DEL VIAJE
Debes conocer y usar:
- Destino (ciudad/región).
- Duración (número de días).
- Presupuesto/estilo (mochilero, medio, lujo, relaxed, adventure...).
- Compañía (solo, pareja, familia con niños, amigos).
- Intereses (gastronomía, historia, aventura, relax, etc.).

### FORMATO JSON DEL ITINERARIO
Cuando generes el itinerario (FASE 2, 3 o 4), tu respuesta debe ser SOLO este JSON:

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
          "detalles": "Nota logística: cómo llegar, duración aproximada"
        }},
        {{
          "hora": "13:00",
          "momento": "Almuerzo",
          "activity": "Recomendación específica de restaurante",
          "category": "Food",
          "detalles": "Precio estimado en función del estilo/presupuesto"
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
          "activity": "Cena o plan nocturno",
          "category": "Food",
          "detalles": "Recomendación especial"
        }}
      ],
      "tip_pro": "Consejo logístico o local"
    }}
  ]
}}

Categorías válidas en "category": "Culture", "Food", "Hiking", "Relaxation", "Sightseeing", "General".

### REGLAS DE ORO
- Sé realista: evita meter demasiadas actividades en poco tiempo.
- Ten en cuenta desplazamientos y cansancio.
- Tono: profesional y directo, evita la prosa larga.
- Respeta SIEMPRE FASE_ACTUAL:
  - FASE 1: NUNCA JSON.
  - FASE 2, 3, 4 cuando generes itinerario: SOLO JSON.
"""

            human_input = f"""FASE_ACTUAL: {phase}

📋 CONTEXTO DEL VIAJE (MEMORIA):
- Destino: {dest or "NO_ESPECIFICADO"}
- Duración: {dur or "NO_ESPECIFICADA"}
- Estilo/Presupuesto: {style or "NO_ESPECIFICADO"}

📎 CONTEXTO ADICIONAL:
{rag_context or "(sin contexto externo adicional)"}

💬 MENSAJE DEL USUARIO:
{extra_info}
"""

            prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("human", "{input}"),
                ]
            )

            chain = prompt_template | llm
            response_obj = chain.invoke(
                {"input": human_input, "chat_history": session_history}
            )
            response_text = (
                response_obj.content
                if hasattr(response_obj, "content")
                else str(response_obj)
            )

        except Exception as e:
            print(f"⚠️ Llamada al LLM falló: {e}")
            response_text = None

        if not response_text:
            return {
                "es_itinerario": False,
                "mensaje_chat": "Error técnico en el cerebro del asistente.",
            }

        cleaned = response_text.replace("```json", "").replace("```", "").strip()
        memory.add_message_to_history(session_id, "user", extra_info)
        memory.add_message_to_history(session_id, "ai", cleaned)

        json_obj = None
        try:
            json_obj = json.loads(cleaned)
        except Exception:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                candidate = cleaned[start : end + 1]
                try:
                    json_obj = json.loads(candidate)
                except Exception as e:
                    print(f"⚠️ Error parseando JSON de itinerario: {e}")

        if json_obj is not None and isinstance(json_obj, dict):
            memory.set_itinerary(session_id, json_obj)
            return {"es_itinerario": True, **json_obj}

        return {"es_itinerario": False, "mensaje_chat": cleaned}

    except Exception as e:
        print(f"❌ Error en /generate: {e}")
        raise HTTPException(status_code=500, detail=str(e))
