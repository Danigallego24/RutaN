import os
import shutil
import base64
import json
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import UploadFile
from PIL import Image
import io

# LangChain imports
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from langchain_ollama import OllamaLLM
from services.llm_engine import get_chat_model

# Directorio temporal para procesar subidas
UPLOAD_DIR = Path("./temp_uploads")
DB_DIR = Path("./chroma_db")

# Aseguramos que existan
UPLOAD_DIR.mkdir(exist_ok=True)

# Configuración de Ollama
OLLAMA_BASE_URL = "http://127.0.0.1:11434"

class RAGHandler:
    def __init__(self):
        # Usamos embeddings locales (nomic-embed-text o llama3)
        self.embeddings = OllamaEmbeddings(
            model="llama3.2:3b", 
            base_url="http://127.0.0.1:11434"
        )
        
        # Inicializamos ChromaDB
        self.vector_store = Chroma(
            collection_name="trip_documents",
            embedding_function=self.embeddings,
            persist_directory=str(DB_DIR)
        )
        
        # MODELO DE VISIÓN
        # Asegúrate de tener 'llava' descargado: ollama pull llava
        self.vision_model = OllamaLLM(model="llava", base_url="http://127.0.0.1:11434")

    def _prepare_image_for_vision(self, file_path: str) -> str:
        """
        Prepara la imagen para ser enviada al modelo de visión.
        Redimensiona si es muy grande para optimizar procesamiento.
        """
        try:
            img = Image.open(file_path)
            # Redimensionar si es muy grande (máx 1024px en el lado más largo)
            max_size = 1024
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Convertir a RGB si es necesario
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Guardar temporalmente la imagen optimizada
            optimized_path = str(file_path).replace('.jpg', '_opt.jpg').replace('.png', '_opt.jpg')
            img.save(optimized_path, 'JPEG', quality=85)
            return optimized_path
        except Exception as e:
            print(f"⚠️ Error optimizando imagen: {e}")
            return file_path

    def _analyze_image_with_ollama(self, file_path: str, filename: str) -> str:
        """
        Analiza una imagen usando la API de Ollama directamente (llava).
        Funciona enviando la imagen como base64.
        """
        print(f"👁️ Analizando imagen con Ollama: {filename}...")
        
        try:
            # Leer la imagen y convertir a base64
            with open(file_path, 'rb') as img_file:
                image_data = base64.b64encode(img_file.read()).decode('utf-8')
            
            # Prompt especializado para turismo
            prompt = (
                "Analiza esta imagen como experto en turismo. "
                "Identifica: 1) Ubicación/lugar específico, 2) Tipo de atracción, "
                "3) Actividades posibles, 4) Condiciones visuales (clima, hora, multitud), "
                "5) Recomendación para itinerario, 6) Detalles prácticos (horarios, entrada, etc.). "
                "Sé conciso y práctico. Responde en español."
            )
            
            # Llamar a Ollama con llava
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": "llava",
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False,
                    "temperature": 0.7,
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis = result.get("response", "").strip()
                print(f"✅ Análisis completado: {len(analysis)} caracteres")
                return analysis
            else:
                print(f"❌ Error Ollama: {response.status_code}")
                return f"Error analizando imagen: {response.status_code}"
                
        except Exception as e:
            print(f"❌ Error en análisis de imagen: {e}")
            return f"Error: {str(e)}"

    def _analyze_document_with_llm(self, content: str, filename: str, doc_type: str, model_name: str | None = None) -> str:
        """
        Analiza un documento usando LLM para extraer información de viaje.
        """
        print(f"📄 Analizando {doc_type}: {filename}...")
        
        try:
            prompt = (
                f"Eres un experto en análisis de documentos de viaje. "
                f"Analiza el siguiente contenido de {doc_type} y extrae información útil para crear un itinerario.\n\n"
                f"CONTENIDO:\n{content[:2000]}\n\n"
                f"Extrae: 1) Ubicaciones mencionadas, 2) Actividades sugeridas, "
                f"3) Restricciones horarias, 4) Tipos de experiencia (cultura, gastronomía, naturaleza, etc.), "
                f"5) Información práctica (precios, distancias, horarios). "
                f"Responde en español, de forma concisa."
            )

            # Obtener el LLM según la selección del frontend (ej: 'smart' -> groq70B, 'fast' -> groq8bb, 'local' -> ollama)
            selected_model = model_name or os.getenv("LLM_MODEL", "smart")
            try:
                llm, provider = get_chat_model(selected_model)
                print(f"🛰️ Analizando documento con proveedor: {provider} (modelo: {selected_model})")

                # Reutilizamos la misma técnica que en chat: construir prompt y ejecutar
                from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
                system_prompt = f"Eres un asistente experto en viajes. Analiza el siguiente documento y responde de forma concisa:\n\n"
                human_input = f"{prompt}"
                prompt_template = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("human", "{input}"),
                ])

                chain = prompt_template | llm
                response_obj = chain.invoke({"input": human_input})
                analysis_text = response_obj.content if hasattr(response_obj, "content") else str(response_obj)
                print(f"✅ Análisis completado: {len(str(analysis_text))} caracteres")
                return str(analysis_text)

            except Exception as inner_e:
                print(f"❌ Error al invocar LLM seleccionado ({selected_model}): {inner_e}")
                # Intentar fallback local a Ollama si estaba pidiendo un provider remoto
                try:
                    print("🔁 Intentando fallback a Ollama local...")
                    llm = OllamaLLM(model="llama3.2:3b", base_url=OLLAMA_BASE_URL)
                    result = llm.invoke(prompt)
                    print(f"✅ Fallback completado: {len(str(result))} caracteres")
                    return str(result)
                except Exception as fallback_e:
                    print(f"❌ Fallback también falló: {fallback_e}")
                    return f"Error analizando documento: {str(inner_e)} | Fallback: {str(fallback_e)}"

        except Exception as e:
            print(f"❌ Error analizando documento: {e}")
            return f"Error: {str(e)}"

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extrae texto de PDF y lo estructura para itinerarios.
        """
        try:
            loader = PyMuPDFLoader(str(file_path))
            docs = loader.load()
            
            # Combinar contenido con metadata
            full_text = ""
            for i, doc in enumerate(docs):
                if doc.page_content.strip():
                    full_text += f"[Página {i+1}]\n{doc.page_content}\n\n"
            
            return full_text if full_text else "PDF vacío o no procesable"
        except Exception as e:
            print(f"❌ Error extrayendo PDF: {e}")
            return f"Error leyendo PDF: {str(e)}"

    def _extract_text_from_document(self, file_path: str) -> str:
        """
        Extrae texto de documentos de texto (TXT, MD, JSON, CSV).
        """
        try:
            loader = TextLoader(str(file_path), encoding="utf-8")
            docs = loader.load()
            return docs[0].page_content if docs else "Documento vacío"
        except Exception as e:
            print(f"❌ Error extrayendo documento: {e}")
            return f"Error leyendo documento: {str(e)}"

    async def process_file(self, file: UploadFile, session_id: str, model_name: str | None = None) -> Dict[str, Any]:
        """
        Procesa el archivo (imagen o documento) y devuelve análisis detallado.
        IMPORTANTE: Realiza análisis INMEDIATO, no depende de inyección en chat.
        """
        file_path = UPLOAD_DIR / file.filename
        
        # 1. Guardar archivo temporalmente
        print(f"📥 Guardando archivo: {file.filename}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        try:
            ext = file.filename.split('.')[-1].lower()
            analysis_text = ""
            file_type = "unknown"
            display_content = ""

            # 2. PROCESAR SEGÚN TIPO
            if ext == "pdf":
                print(f"📄 Procesando PDF: {file.filename}")
                file_type = "PDF"
                # Extraer texto del PDF
                pdf_text = self._extract_text_from_pdf(str(file_path))
                # Analizar con LLM
                analysis_text = self._analyze_document_with_llm(pdf_text, file.filename, "PDF", model_name)
                display_content = analysis_text
                
            elif ext in ["txt", "md", "json", "csv"]:
                print(f"📝 Procesando documento de texto: {file.filename}")
                file_type = f"{ext.upper()} Document"
                # Extraer texto
                doc_text = self._extract_text_from_document(str(file_path))
                # Analizar con LLM
                analysis_text = self._analyze_document_with_llm(doc_text, file.filename, file_type, model_name)
                display_content = analysis_text
                
            elif ext in ["jpg", "jpeg", "png", "webp"]:
                print(f"🖼️ Procesando imagen: {file.filename}")
                file_type = "Image"
                # Optimizar imagen
                optimized_path = self._prepare_image_for_vision(str(file_path))
                # Analizar imagen directamente con Ollama/llava
                analysis_text = self._analyze_image_with_ollama(optimized_path, file.filename)
                display_content = analysis_text
                # Limpiar
                try:
                    if optimized_path != str(file_path):
                        os.remove(optimized_path)
                except:
                    pass

            else:
                return {
                    "ok": False,
                    "error": f"Formato .{ext} no soportado. Usa: PDF, TXT, MD, JSON, CSV, JPG, PNG, WEBP"
                }

            if not analysis_text or len(analysis_text.strip()) < 10:
                return {
                    "ok": False,
                    "error": f"No se pudo analizar el contenido de {file_type}"
                }

            # 3. INDEXAR EN CHROMADB PARA REFERENCIA FUTURA
            doc = Document(
                page_content=analysis_text,
                metadata={
                    "source": file.filename,
                    "type": ext,
                    "file_type": file_type,
                    "session_id": session_id
                }
            )
            
            # Chunking si el análisis es muy largo
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=2000,
                chunk_overlap=400,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            splits = text_splitter.split_documents([doc])
            
            if splits:
                self.vector_store.add_documents(documents=splits)
                print(f"✅ {len(splits)} fragmentos indexados")

            # 4. PREPARAR RESPUESTA PARA EL FRONTEND
            preview = display_content[:300] + "..." if len(display_content) > 300 else display_content
            
            return {
                "ok": True,
                "filename": file.filename,
                "file_type": file_type,
                "analysis": display_content,  # ← ANÁLISIS COMPLETO DIRECTO
                "preview": preview,
                "status": "analizado_exitosamente",
                "ready_for_chat": True,
                "message": f"✅ {file_type} analizado correctamente. Información lista para generar itinerario."
            }

        except Exception as e:
            print(f"❌ Error procesando archivo: {e}")
            import traceback
            traceback.print_exc()
            return {
                "ok": False,
                "error": f"Error: {str(e)}"
            }
            
        finally:
            # Limpiar archivo temporal
            if file_path.exists():
                try:
                    os.remove(file_path)
                    print(f"🗑️ Archivo temporal eliminado")
                except:
                    pass

    def retrieve_context(self, query: str, session_id: str, k: int = 5) -> str:
        """
        Recupera contexto relevante de archivos indexados.
        Filtrado por sesión y ordenado por relevancia.
        """
        try:
            results = self.vector_store.similarity_search(
                query, 
                k=k,
                filter={"session_id": session_id} 
            )
            
            if not results:
                return ""
            
            ctx = "\n\n📎 INFORMACIÓN DE ARCHIVOS ADJUNTOS:\n"
            ctx += "=" * 60 + "\n"
            
            for i, doc in enumerate(results, 1):
                file_type = doc.metadata.get("type", "unknown").upper()
                filename = doc.metadata.get("filename", "desconocido")
                ctx += f"\n[{i}] {file_type} - {filename}:\n"
                ctx += f"{doc.page_content[:800]}\n"
            
            ctx += "\n" + "=" * 60 + "\n"
            return ctx
            
        except Exception as e:
            print(f"❌ Error recuperando contexto: {e}")
            return ""

rag_service = RAGHandler()