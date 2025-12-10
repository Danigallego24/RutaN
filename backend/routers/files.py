from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from services.rag_handler import rag_service
import json

router = APIRouter()

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    model: str | None = Form(None)
):
    """
    Recibe un archivo (PDF, Imagen, TXT, etc.) y lo analiza INMEDIATAMENTE.
    
    Soporta:
    - Imágenes: JPG, JPEG, PNG, WEBP → Análisis con visión (llava)
    - PDFs: Extrae texto y analiza con LLM
    - Documentos: TXT, MD, JSON, CSV → Análisis directo
    
    Devuelve el análisis COMPLETO listo para usar en chat/itinerario.
    """
    try:
        print(f"\n{'='*60}")
        print(f"📥 PROCESANDO ARCHIVO: {file.filename}")
        print(f"{'='*60}\n")
        
        # Procesamos el archivo con análisis inmediato (se puede pasar modelo seleccionado)
        result = await rag_service.process_file(file, session_id, model)
        
        print(f"{'='*60}")
        if not result.get("ok"):
            print(f"❌ ERROR: {result.get('error')}")
            print(f"{'='*60}\n")
            raise HTTPException(
                status_code=400, 
                detail=result.get("error", "Error desconocido")
            )
        
        print(f"✅ ANÁLISIS COMPLETADO")
        print(f"Tipo: {result.get('file_type')}")
        print(f"Estado: {result.get('status')}")
        print(f"{'='*60}\n")
        
        # Devolvemos análisis DIRECTO
        return {
            "ok": True,
            "filename": result.get("filename"),
            "file_type": result.get("file_type"),
            "message": result.get("message"),
            "analysis": result.get("analysis"),  # ← ANÁLISIS COMPLETO
            "preview": result.get("preview"),
            "status": result.get("status"),
            "ready_for_chat": result.get("ready_for_chat")
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ ERROR EN UPLOAD: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Error: {str(e)}"
        )