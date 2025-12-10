import os
from langchain_groq import ChatGroq
from langchain_ollama import OllamaLLM
from dotenv import load_dotenv

load_dotenv()


def get_chat_model(model_name: str | None = None):
    """Devuelve una tupla (llm_instance, provider_name).

    - Si `model_name` es None o cadena vacía, se toma de la variable de entorno
      LLM_MODEL o se usa "smart" por defecto.
    - Para modelos Groq, se requiere GROQ_API_KEY; si falta, se lanza RuntimeError
      para que el caller pueda mostrar un error claro.
    """
    # Normalizar modelo
    if not model_name:
        model_name = os.getenv("LLM_MODEL", "smart")

    print(f"🎛️  LLM_ENGINE RECIBIÓ: '{model_name}'")

    groq_api_key = os.getenv("GROQ_API_KEY")

    # Fast -> Groq 8B
    if model_name in ("fast", "llama3.2:7b", "groq_8b"):
        print("⚡ Modo seleccionado: Groq 8B (rápido)")
        if not groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY no encontrada en el entorno. No se puede usar Groq 8B. "
                "Configura GROQ_API_KEY o selecciona 'local'."
            )
        llm = ChatGroq(
            model="llama-3.1-8b-instant", temperature=0.0, api_key=groq_api_key
        )
        return llm, "groq_8b"

    # Smart -> Groq 70B
    if model_name in ("smart", "gpt-4o", "groq_70b"):
        print("🧠 Modo seleccionado: Groq 70B (potente)")
        if not groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY no encontrada en el entorno. No se puede usar Groq 70B. "
                "Configura GROQ_API_KEY o selecciona 'local'."
            )
        llm = ChatGroq(
            model="llama-3.3-70b-versatile", temperature=0.0, api_key=groq_api_key
        )
        return llm, "groq_70b"

    # Local -> Ollama
    if model_name in ("local", "llama3.2:3b", "ollama_local"):
        print("🏠 Modo seleccionado: Ollama local")
        llm = _fallback_local()
        return llm, "ollama_local"

    # Modelo desconocido
    raise RuntimeError(
        f"Modelo desconocido: '{model_name}'. Selecciona 'smart'|'fast'|'local'."
    )


def _fallback_local():
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    return OllamaLLM(model="llama3.2:3b", temperature=0.0, base_url=base_url)
