from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from services.rag_handler import rag_service

router = APIRouter()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    model: str | None = Form(None),
):
    """
    Recibe un archivo (PDF, Imagen, TXT, etc.) y lo analiza INMEDIATAMENTE.

    Soporta:
    - Imágenes: JPG, JPEG, PNG, WEBP → Análisis con visión (llava).
    - PDFs: extrae texto y analiza con LLM.
    - Documentos: TXT, MD, JSON, CSV → Análisis directo.

    Devuelve el análisis COMPLETO listo para utilizar en el chat/itinerario.
    """
    try:
        print("\n" + "=" * 60)
        print(f"📥 PROCESANDO ARCHIVO: {file.filename}")
        print("=" * 60 + "\n")

        # Procesamos el archivo con análisis inmediato (se puede pasar modelo seleccionado)
        result = await rag_service.process_file(file, session_id, model)

        print("=" * 60)
        if not result.get("ok"):
            print(f"❌ ERROR: {result.get('error')}")
            print("=" * 60 + "\n")
            raise HTTPException(
                status_code=400, detail=result.get("error", "Error desconocido")
            )

        print("✅ ANÁLISIS COMPLETADO")
        print(f"Tipo: {result.get('file_type')}")
        print(f"Estado: {result.get('status')}")
        print("=" * 60 + "\n")

        # Devolvemos análisis DIRECTO
        return {
            "ok": True,
            "filename": result.get("filename"),
            "file_type": result.get("file_type"),
            "message": result.get("message"),
            "analysis": result.get("analysis"),  # análisis completo
            "preview": result.get("preview"),
            "status": result.get("status"),
            "ready_for_chat": result.get("ready_for_chat"),
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ ERROR EN /upload: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
