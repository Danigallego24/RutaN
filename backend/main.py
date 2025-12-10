from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware  # <--- Importación necesaria

# Import the chat router implemented in `backend/routers/chat.py`
from routers import chat as chat_router
from routers import files as files_router

app = FastAPI()

# --- AQUÍ ESTÁ EL ARREGLO (CORS) ---
# Esto le dice al backend: "Acepta peticiones que vengan de localhost:3000"
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Attach CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (POST, GET, OPTIONS...)
    allow_headers=["*"],  # Permite todos los headers
)
# -----------------------------------
# Register the chat router which exposes `/api/chat/generate`
app.include_router(chat_router.router, prefix="/api/chat")
app.include_router(files_router.router, prefix="/api/files")



@app.post("/api/debug")
async def _debug_body(request: Request):
    raw = await request.body()
    try:
        text = raw.decode("utf-8")
    except Exception:
        text = repr(raw)
    return {"raw": text, "length": len(raw)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)