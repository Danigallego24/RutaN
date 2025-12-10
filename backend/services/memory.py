from langchain_core.messages import HumanMessage, AIMessage

# Aquí vivirá la memoria de todos los usuarios (en RAM)
# Estructura: { "user_1": { "history": [], "memory": {...} } }
_store = {}

def get_session_data(session_id: str):
    if session_id not in _store:
        _store[session_id] = {
            "history": [], 
            "memory": {"destination": "", "duration": "", "style": ""},
            "pending": {},
            "itinerary": None,
        }
    return _store[session_id]

def reset_session_history(session_id: str):
    """Borra el chat pero mantiene los datos de memoria si quisieras (aquí borramos chat)."""
    if session_id in _store:
        _store[session_id]["history"] = []


def get_pending(session_id: str):
    data = get_session_data(session_id)
    return data.get("pending", {})


def set_pending(session_id: str, pending: dict):
    data = get_session_data(session_id)
    data["pending"] = pending


def clear_pending(session_id: str):
    data = get_session_data(session_id)
    data["pending"] = {}


def set_itinerary(session_id: str, itinerary_obj: dict):
    data = get_session_data(session_id)
    data["itinerary"] = itinerary_obj


def get_itinerary(session_id: str):
    data = get_session_data(session_id)
    return data.get("itinerary")

def update_trip_memory(session_id: str, dest=None, dur=None, style=None):
    """Actualiza los datos fijos del viaje (Ciudad, Días, Estilo)."""
    data = get_session_data(session_id)
    if dest: data["memory"]["destination"] = dest
    if dur: data["memory"]["duration"] = dur
    if style: data["memory"]["style"] = style

def add_message_to_history(session_id: str, role: str, content: str):
    """Guarda un mensaje en el historial de chat."""
    data = get_session_data(session_id)
    if role == "user":
        data["history"].append(HumanMessage(content=content))
    elif role == "ai":
        data["history"].append(AIMessage(content=content))

def get_chat_history(session_id: str):
    """Devuelve la lista de mensajes de LangChain."""
    return get_session_data(session_id)["history"]

def get_trip_context(session_id: str):
    """Devuelve el diccionario con destino, duración y estilo."""
    return get_session_data(session_id)["memory"]