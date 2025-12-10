import os
import shutil
import base64
import json
import requests
from pathlib import Path
from typing import Dict, Any
from fastapi import UploadFile
from PIL import Image

# LangChain imports
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from langchain_ollama import OllamaLLM
from services.llm_engine import get_chat_model

# Directorios
UPLOAD_DIR = Path("./temp_uploads")
DB_DIR = Path("./chroma_db")

UPLOAD_DIR.mkdir(exist_ok=True)
DB_DIR.mkdir(exist_ok=True)

# Configuración de Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")


class RAGHandler:
    def __init__(self):
        # Embeddings locales (coherentes con llm_engine)
        self.embeddings = OllamaEmbeddings(
            model="llama3.2:3b",
            base_url=OLLAMA_BASE_URL,
        )

        # Inicializamos ChromaDB para documentos de viaje
        self.vector_store = Chroma(
            collection_name="trip_documents",
            embedding_function=self.embeddings,
            persist_directory=str(DB_DIR),
        )

        # Modelo de visión (no se usa directamente, pero mantenemos para compatibilidad)
        self.vision_model = OllamaLLM(model="llava", base_url=OLLAMA_BASE_URL)

    def _prepare_image_for_vision(self, file_path: str) -> str:
        """
        Prepara la imagen para ser enviada al modelo de visión.
        Redimensiona si es muy grande para optimizar procesamiento.
        """
        try:
            img = Image.open(file_path)
            max_size = 1024
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            if img.mode != "RGB":
                img = img.convert("RGB")

            optimized_path = (
                str(file_path)
                .replace(".jpg", "_opt.jpg")
                .replace(".jpeg", "_opt.jpg")
                .replace(".png", "_opt.jpg")
                .replace(".webp", "_opt.jpg")
            )
            img.save(optimized_path, "JPEG", quality=85)
            return optimized_path
        except Exception as e:
            print(f"⚠️ Error optimizando imagen: {e}")
            return file_path

    def _analyze_image_with_ollama(self, file_path: str, filename: str) -> str:
        """
        Analiza una imagen usando la API de Ollama (modelo llava).
        Envía la imagen en base64 junto con un prompt especializado.
        """
        print(f"👁️ Analizando imagen con Ollama: {filename}...")

        try:
            with open(file_path, "rb") as img_file:
                image_data = base64.b64encode(img_file.read()).decode("utf-8")

            prompt = (
                "Analiza esta imagen como experto en turismo. "
                "Identifica: 1) Ubicación/lugar específico (si se puede), "
                "2) Tipo de atracción, 3) Actividades posibles, "
                "4) Condiciones visuales (clima, hora, multitud), "
                "5) Recomendación para itinerario, 6) Detalles prácticos relevantes. "
                "Sé conciso y práctico. Responde en español."
            )

            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": "llava",
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False,
                    "temperature": 0.7,
                },
                timeout=120,
            )

            if response.status_code == 200:
                result = response.json()
                analysis = result.get("response", "").strip()
                print(f"✅ Análisis de imagen completado: {len(analysis)} caracteres")
                return analysis

            print(f"❌ Error Ollama (imagen): {response.status_code} {response.text}")
            return f"Error analizando imagen: {response.status_code}"

        except Exception as e:
            print(f"❌ Error en análisis de imagen: {e}")
            return f"Error: {str(e)}"

    def _analyze_document_with_llm(
        self, content: str, filename: str, doc_type: str, model_name: str | None = None
    ) -> str:
        """
        Analiza un documento de texto (PDF, TXT, etc.) para extraer información útil de viaje.
        """
        print(f"📄 Analizando {doc_type}: {filename}...")

        try:
            prompt = (
                f"Eres un experto en análisis de documentos de viaje. "
                f"Analiza el siguiente contenido de {doc_type} y extrae información útil para crear un itinerario.\n\n"
                f"CONTENIDO:\n{content[:4000]}\n\n"
                f"Extrae: 1) Ubicaciones mencionadas, 2) Actividades sugeridas, "
                f"3) Restricciones horarias o de fechas, 4) Tipos de experiencia (cultura, gastronomía, naturaleza, etc.), "
                f"5) Información práctica relevante (precios, distancias, horarios, reservas, vuelos, hoteles). "
                f"Responde en español, de forma concisa y estructurada."
            )

            selected_model = model_name or os.getenv("LLM_MODEL", "smart")
            try:
                llm, provider = get_chat_model(selected_model)
                print(
                    f"🛰️ Analizando documento con proveedor: {provider} (modelo: {selected_model})"
                )

                from langchain_core.prompts import ChatPromptTemplate

                system_prompt = (
                    "Eres un asistente experto en viajes. Analiza el documento y responde de forma concisa:\n\n"
                )
                human_input = prompt

                prompt_template = ChatPromptTemplate.from_messages(
                    [
                        ("system", system_prompt),
                        ("human", "{input}"),
                    ]
                )

                chain = prompt_template | llm
                response_obj = chain.invoke({"input": human_input})
                analysis_text = (
                    response_obj.content
                    if hasattr(response_obj, "content")
                    else str(response_obj)
                )
                print(
                    f"✅ Análisis de documento completado: {len(str(analysis_text))} caracteres"
                )
                return str(analysis_text)

            except Exception as inner_e:
                print(
                    f"❌ Error al invocar LLM seleccionado ({selected_model}): {inner_e}"
                )
                # Intentar fallback local a Ollama
                try:
                    print("🔁 Intentando fallback a Ollama local...")
                    llm = OllamaLLM(model="llama3.2:3b", base_url=OLLAMA_BASE_URL)
                    result = llm.invoke(prompt)
                    print(
                        f"✅ Fallback local completado: {len(str(result))} caracteres"
                    )
                    return str(result)
                except Exception as fallback_e:
                    print(f"❌ Fallback también falló: {fallback_e}")
                    return f"Error analizando documento: {str(inner_e)} | Fallback: {str(fallback_e)}"

        except Exception as e:
            print(f"❌ Error analizando documento: {e}")
            return f"Error: {str(e)}"

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extrae texto de un PDF y lo etiqueta por páginas.
        """
        try:
            loader = PyMuPDFLoader(str(file_path))
            docs = loader.load()

            full_text = ""
            for i, doc in enumerate(docs):
                if doc.page_content.strip():
                    full_text += f"[Página {i + 1}]\n{doc.page_content}\n\n"

            return full_text if full_text else "PDF vacío o no procesable"
        except Exception as e:
            print(f"❌ Error extrayendo texto de PDF: {e}")
            return f"Error leyendo PDF: {str(e)}"

    def _extract_text_from_document(self, file_path: str) -> str:
        """
        Extrae texto de documentos planos (TXT, MD, JSON, CSV).
        """
        try:
            loader = TextLoader(str(file_path), encoding="utf-8")
            docs = loader.load()
            return docs[0].page_content if docs else "Documento vacío"
        except Exception as e:
            print(f"❌ Error extrayendo texto de documento: {e}")
            return f"Error leyendo documento: {str(e)}"

    async def process_file(
        self, file: UploadFile, session_id: str, model_name: str | None = None
    ) -> Dict[str, Any]:
        """
        Procesa un archivo (imagen o documento) y devuelve un análisis de alto nivel.
        Además, indexa el contenido analizado en ChromaDB para futuras consultas RAG.
        """
        file_path = UPLOAD_DIR / file.filename

        print(f"📥 Guardando archivo: {file.filename}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            ext = file.filename.split(".")[-1].lower()
            analysis_text = ""
            file_type = "unknown"
            display_content = ""

            if ext == "pdf":
                print(f"📄 Procesando PDF: {file.filename}")
                file_type = "PDF"
                pdf_text = self._extract_text_from_pdf(str(file_path))
                analysis_text = self._analyze_document_with_llm(
                    pdf_text, file.filename, "PDF", model_name
                )
                display_content = analysis_text

            elif ext in ["txt", "md", "json", "csv"]:
                print(f"📝 Procesando documento de texto: {file.filename}")
                file_type = f"{ext.upper()} Document"
                doc_text = self._extract_text_from_document(str(file_path))
                analysis_text = self._analyze_document_with_llm(
                    doc_text, file.filename, file_type, model_name
                )
                display_content = analysis_text

            elif ext in ["jpg", "jpeg", "png", "webp"]:
                print(f"🖼️ Procesando imagen: {file.filename}")
                file_type = "Image"
                optimized_path = self._prepare_image_for_vision(str(file_path))
                analysis_text = self._analyze_image_with_ollama(
                    optimized_path, file.filename
                )
                display_content = analysis_text

                try:
                    if optimized_path != str(file_path):
                        os.remove(optimized_path)
                except Exception:
                    pass

            else:
                return {
                    "ok": False,
                    "error": f"Formato .{ext} no soportado. Usa: PDF, TXT, MD, JSON, CSV, JPG, PNG, WEBP",
                }

            if not analysis_text or len(analysis_text.strip()) < 10:
                return {
                    "ok": False,
                    "error": f"No se pudo analizar el contenido de {file_type}",
                }

            # 3. Indexar en ChromaDB para RAG
            doc = Document(
                page_content=analysis_text,
                metadata={
                    "source": file.filename,
                    "type": ext,
                    "file_type": file_type,
                    "session_id": session_id,
                },
            )

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=2000,
                chunk_overlap=400,
                separators=["\n\n", "\n", ". ", " ", ""],
            )
            splits = text_splitter.split_documents([doc])

            if splits:
                self.vector_store.add_documents(documents=splits)
                print(f"✅ {len(splits)} fragmentos indexados en ChromaDB")

            preview = (
                display_content[:300] + "..."
                if len(display_content) > 300
                else display_content
            )

            return {
                "ok": True,
                "filename": file.filename,
                "file_type": file_type,
                "analysis": display_content,
                "preview": preview,
                "status": "analizado_exitosamente",
                "ready_for_chat": True,
                "message": f"✅ {file_type} analizado correctamente. Información lista para usar en el itinerario.",
            }

        except Exception as e:
            print(f"❌ Error procesando archivo: {e}")
            import traceback

            traceback.print_exc()
            return {
                "ok": False,
                "error": f"Error: {str(e)}",
            }

        finally:
            if file_path.exists():
                try:
                    os.remove(file_path)
                    print("🗑️ Archivo temporal eliminado")
                except Exception:
                    pass

    def retrieve_context(self, query: str, session_id: str, k: int = 5) -> str:
        """
        Recupera contexto relevante de archivos previamente analizados,
        filtrando por session_id y ordenando por similitud.
        """
        try:
            results = self.vector_store.similarity_search(
                query, k=k, filter={"session_id": session_id}
            )

            if not results:
                return ""

            ctx = "\n\n📎 INFORMACIÓN DE ARCHIVOS ADJUNTOS:\n" + "=" * 60 + "\n"

            for i, doc in enumerate(results, 1):
                file_type = str(doc.metadata.get("file_type", "unknown"))
                filename = doc.metadata.get("source") or doc.metadata.get(
                    "filename", "desconocido"
                )
                ctx += f"\n[{i}] {file_type} - {filename}:\n"
                ctx += f"{doc.page_content[:800]}\n"

            ctx += "\n" + "=" * 60 + "\n"
            return ctx

        except Exception as e:
            print(f"❌ Error recuperando contexto RAG: {e}")
            return ""


rag_service = RAGHandler()
