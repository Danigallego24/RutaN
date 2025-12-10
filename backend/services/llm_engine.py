import os
from langchain_groq import ChatGroq
from langchain_ollama import OllamaLLM
from dotenv import load_dotenv

load_dotenv()


def get_chat_model(model_name: str = "smart"):
    """Return a tuple (llm_instance, provider_name).

    For Groq models, this function requires a valid `GROQ_API_KEY` env var.
    If the key is missing and a Groq model is requested, it raises RuntimeError so
    the caller can surface a clear error to the user instead of silently falling
    back to a different provider.
    """
    print(f"🎛️  LLM_ENGINE RECIBIÓ: '{model_name}'")

    groq_api_key = os.getenv("GROQ_API_KEY")

    # Fast -> Groq 8B
    if model_name == "fast" or model_name == "llama3.2:7b":
        print("⚡ Modo seleccionado: Groq 8B (rápido)")
        if not groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY no encontrada en el entorno. No se puede usar Groq 8B. "
                "Por favor configura GROQ_API_KEY o selecciona 'local'."
            )
        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.0, api_key=groq_api_key)
        return llm, "groq_8b"

    # Smart -> Groq 70B
    if model_name == "smart" or model_name == "gpt-4o":
        print("🧠 Modo seleccionado: Groq 70B (potente)")
        if not groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY no encontrada en el entorno. No se puede usar Groq 70B. "
                "Por favor configura GROQ_API_KEY o selecciona 'local'."
            )
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.0, api_key=groq_api_key)
        return llm, "groq_70b"

    # Local -> Ollama
    if model_name == "local" or model_name == "llama3.2:3b":
        print("🏠 Modo seleccionado: Ollama local")
        llm = _fallback_local()
        return llm, "ollama_local"

    # Unknown -> error
    raise RuntimeError(f"Modelo desconocido: '{model_name}'. Selecciona 'smart'|'fast'|'local'.")


def _fallback_local():
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    return OllamaLLM(model="llama3.2:3b", temperature=0.0, base_url=base_url)