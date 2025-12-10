"use client"

import type React from "react"
import { useState, useRef, useEffect } from "react"
import { Send, Paperclip, Bot, User, FileText, ImageIcon, Link as LinkIcon, File, X, Globe } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import ReactMarkdown from "react-markdown"

interface Message {
  role: "user" | "ai"
  content: string
}

interface ChatAreaProps {
  messages: Message[]
  isGenerating: boolean
  // CAMBIO CLAVE: onSendMessage ahora acepta un segundo argumento opcional (el archivo/url)
  onSendMessage: (message: string, attachment?: File | string) => void
  onFileSelect?: (file: File) => void
  onUrlSubmit?: (url: string) => void
}

type AttachmentType = "file" | "image" | "url"

interface PendingAttachment {
  type: AttachmentType
  content: File | string 
  preview?: string 
}

function LoadingSkeleton() {
  return (
    <div className="flex gap-2 sm:gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary shadow-sm sm:h-9 sm:w-9">
        <Bot className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="glass-subtle max-w-[85%] space-y-2 rounded-2xl rounded-tl-md p-3 sm:space-y-2.5 sm:p-4">
        <div className="h-3 w-32 animate-pulse rounded-full bg-muted sm:h-4 sm:w-48" />
        <div className="h-3 w-48 animate-pulse rounded-full bg-muted sm:h-4 sm:w-64" />
        <div className="h-3 w-24 animate-pulse rounded-full bg-muted sm:h-4 sm:w-32" />
      </div>
    </div>
  )
}

export function ChatArea({ messages, isGenerating, onSendMessage }: ChatAreaProps) {
  const [input, setInput] = useState("")
  const [showAttachMenu, setShowAttachMenu] = useState(false)
  const [showUrlDialog, setShowUrlDialog] = useState(false)
  const [urlInput, setUrlInput] = useState("")
  
  // ESTADO PARA EL ADJUNTO PENDIENTE
  const [pendingAttachment, setPendingAttachment] = useState<PendingAttachment | null>(null)

  const attachMenuRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [acceptedFileTypes, setAcceptedFileTypes] = useState("")

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isGenerating])

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + "px"
    }
  }, [input])

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (attachMenuRef.current && !attachMenuRef.current.contains(event.target as Node)) {
        setShowAttachMenu(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  // --- MANEJO DE ENVÍO CORREGIDO ---
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validar si hay algo que enviar (texto O adjunto)
    if (!input.trim() && !pendingAttachment) return

    let finalMessage = input.trim()
    // Variable para guardar el archivo/url real y pasarlo al padre
    let attachmentPayload: File | string | undefined = undefined;

    // Si hay un adjunto, preparamos el mensaje visual Y el payload
    if (pendingAttachment) {
      let attachmentPrefix = ""
      
      if (pendingAttachment.type === "url") {
        attachmentPrefix = `🔗 **Enlace Referencia:** ${pendingAttachment.content}\n\n`
        attachmentPayload = pendingAttachment.content // URL como string
      } else {
        const file = pendingAttachment.content as File
        const icon = pendingAttachment.type === "image" ? "🖼️" : "📎"
        attachmentPrefix = `${icon} **Archivo Adjunto:** ${file.name} (${(file.size / 1024).toFixed(1)} KB)\n\n`
        attachmentPayload = file // OBJETO FILE REAL
      }

      // Combinamos el prefijo visual con el mensaje del usuario
      finalMessage = attachmentPrefix + (finalMessage || "(Analiza este adjunto)")
    }

    // AQUÍ ESTÁ LA CORRECCIÓN:
    // Pasamos el texto Y el objeto archivo a onSendMessage.
    // Ya NO llamamos a onFileSelect/onUrlSubmit para evitar duplicados.
    onSendMessage(finalMessage, attachmentPayload)
    
    // Limpiar estados
    setInput("")
    setPendingAttachment(null)
    if (textareaRef.current) textareaRef.current.style.height = "auto"
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  // --- SELECCIÓN DE ADJUNTOS ---

  const handleAttachOption = (type: AttachmentType) => {
    setShowAttachMenu(false)

    if (type === "url") {
      setShowUrlDialog(true)
      setTimeout(() => document.getElementById("url-input-field")?.focus(), 100)
    } else {
      let filter = ""
      if (type === "image") filter = "image/*"
      else filter = ".pdf,.doc,.docx,.txt,application/pdf,text/plain"
      
      setAcceptedFileTypes(filter)
      fileInputRef.current?.setAttribute("data-type", type)
      setTimeout(() => fileInputRef.current?.click(), 50)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    const type = fileInputRef.current?.getAttribute("data-type") as AttachmentType || "file"
    
    if (file) {
      let previewUrl = undefined
      if (type === "image") {
        previewUrl = URL.createObjectURL(file)
      }

      setPendingAttachment({
        type,
        content: file,
        preview: previewUrl
      })
    }
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  const handleUrlSubmitInternal = (e: React.FormEvent) => {
    e.preventDefault()
    if (urlInput.trim()) {
      setPendingAttachment({
        type: "url",
        content: urlInput.trim()
      })
      setShowUrlDialog(false)
      setUrlInput("")
    }
  }

  const clearAttachment = () => {
    setPendingAttachment(null)
  }

  return (
    <div className="glass flex min-w-0 flex-1 flex-col overflow-hidden rounded-2xl relative">
      
      <input 
        type="file" 
        ref={fileInputRef} 
        className="hidden" 
        accept={acceptedFileTypes}
        onChange={handleFileChange}
      />

      {showUrlDialog && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="glass w-full max-w-md rounded-xl p-4 shadow-2xl scale-100 animate-in zoom-in-95 duration-200">
            <h3 className="mb-3 text-sm font-semibold text-foreground">Añadir enlace</h3>
            <form onSubmit={handleUrlSubmitInternal} className="space-y-3">
              <input
                id="url-input-field"
                type="url"
                placeholder="https://ejemplo.com"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                className="w-full rounded-lg border border-border/50 bg-secondary/50 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-red-500/50 focus:outline-none focus:ring-2 focus:ring-red-500/20"
                autoFocus
              />
              <div className="flex justify-end gap-2">
                <Button 
                  type="button" 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => setShowUrlDialog(false)}
                  className="h-8 text-xs hover:bg-secondary"
                >
                  Cancelar
                </Button>
                <Button 
                  type="submit" 
                  size="sm" 
                  className="h-8 bg-red-600 text-xs text-white hover:bg-red-700"
                  disabled={!urlInput.trim()}
                >
                  Adjuntar
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="custom-scrollbar flex-1 overflow-y-auto p-3 sm:p-4 md:p-6">
        <div className="mx-auto max-w-2xl space-y-4 sm:space-y-5">
          {messages.map((message, index) => (
            <div key={index} className={cn("flex gap-2 sm:gap-3", message.role === "user" && "flex-row-reverse")}>
              <div
                className={cn(
                  "flex h-8 w-8 shrink-0 items-center justify-center rounded-full shadow-md sm:h-9 sm:w-9",
                  message.role === "user"
                    ? "bg-gradient-to-br from-red-500 to-red-600 text-white"
                    : "bg-secondary text-secondary-foreground",
                )}
              >
                {message.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
              </div>
              <div
                className={cn(
                  "max-w-[85%] rounded-2xl p-3 shadow-sm sm:p-4",
                  message.role === "user"
                    ? "rounded-tr-md bg-gradient-to-br from-red-500 to-red-600 text-white"
                    : "glass-subtle rounded-tl-md",
                )}
              >
                {message.role === "ai" ? (
                  <div className="prose prose-sm max-w-none text-foreground prose-headings:font-semibold prose-headings:text-foreground prose-p:text-foreground prose-strong:text-foreground prose-li:text-foreground dark:prose-invert">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>
                ) : (
                  <div className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</div>
                )}
              </div>
            </div>
          ))}

          {isGenerating && <LoadingSkeleton />}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="shrink-0 border-t border-border/30 p-2 sm:p-3 md:p-4">
        <form onSubmit={handleSubmit} className="mx-auto max-w-2xl">
          <div className="glass-subtle flex flex-col rounded-2xl p-1.5 transition-all focus-within:ring-2 focus-within:ring-red-500/20 sm:p-2">
            
            {pendingAttachment && (
              <div className="mb-2 flex px-2 pt-1">
                <div className="group relative flex items-center gap-2 rounded-lg border border-border/50 bg-background/50 p-2 pr-8 shadow-sm transition-all hover:bg-background">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-secondary text-red-500">
                    {pendingAttachment.type === "image" && <ImageIcon className="h-4 w-4" />}
                    {pendingAttachment.type === "file" && <File className="h-4 w-4" />}
                    {pendingAttachment.type === "url" && <Globe className="h-4 w-4" />}
                  </div>
                  
                  <div className="flex flex-col overflow-hidden">
                    <span className="truncate text-xs font-medium text-foreground max-w-[150px] sm:max-w-[200px]">
                      {pendingAttachment.type === "url" 
                        ? pendingAttachment.content as string
                        : (pendingAttachment.content as File).name}
                    </span>
                    <span className="text-[10px] text-muted-foreground uppercase">
                      {pendingAttachment.type}
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={clearAttachment}
                    className="absolute -top-1.5 -right-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-muted text-muted-foreground opacity-0 shadow-sm transition-all hover:bg-destructive hover:text-white group-hover:opacity-100"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              </div>
            )}

            <div className="flex items-end gap-1.5 sm:gap-2">
              <div className="relative" ref={attachMenuRef}>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowAttachMenu(!showAttachMenu)}
                  className={cn(
                    "h-8 w-8 shrink-0 rounded-xl text-muted-foreground transition-all hover:bg-secondary hover:text-foreground sm:h-9 sm:w-9",
                    showAttachMenu && "bg-secondary text-foreground",
                  )}
                >
                  {showAttachMenu ? (
                    <X className="h-4 w-4 sm:h-5 sm:w-5" />
                  ) : (
                    <Paperclip className="h-4 w-4 sm:h-5 sm:w-5" />
                  )}
                  <span className="sr-only">Attach file</span>
                </Button>

                {showAttachMenu && (
                  <div className="absolute bottom-full left-0 mb-2 w-48 animate-in fade-in slide-in-from-bottom-2 duration-200 z-20">
                    <div className="glass overflow-hidden rounded-xl border border-border/50 shadow-xl">
                      <div className="border-b border-border/30 px-3 py-2">
                        <p className="text-xs font-medium text-foreground">Adjuntar</p>
                      </div>
                      <div className="p-1.5">
                        <button
                          type="button"
                          onClick={() => handleAttachOption("image")}
                          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm text-foreground transition-colors hover:bg-secondary"
                        >
                          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/10">
                            <ImageIcon className="h-4 w-4 text-blue-500" />
                          </div>
                          <div>
                            <p className="font-medium">Imagen</p>
                            <p className="text-xs text-muted-foreground">JPG, PNG</p>
                          </div>
                        </button>
                        <button
                          type="button"
                          onClick={() => handleAttachOption("file")}
                          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm text-foreground transition-colors hover:bg-secondary"
                        >
                          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-500/10">
                            <File className="h-4 w-4 text-red-500" />
                          </div>
                          <div>
                            <p className="font-medium">Documento</p>
                            <p className="text-xs text-muted-foreground">PDF, TXT</p>
                          </div>
                        </button>
                        <button
                          type="button"
                          onClick={() => handleAttachOption("url")}
                          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm text-foreground transition-colors hover:bg-secondary"
                        >
                          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-green-500/10">
                            <LinkIcon className="h-4 w-4 text-green-500" />
                          </div>
                          <div>
                            <p className="font-medium">Enlace</p>
                            <p className="text-xs text-muted-foreground">Web URL</p>
                          </div>
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Pregunta sobre tu viaje..."
                rows={1}
                className="max-h-[120px] min-h-[36px] flex-1 resize-none bg-transparent py-2 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground focus:outline-none sm:min-h-[40px]"
              />
              <Button
                type="submit"
                size="icon"
                disabled={(!input.trim() && !pendingAttachment) || isGenerating}
                className="h-8 w-8 shrink-0 rounded-xl bg-gradient-to-r from-red-500 to-red-600 text-white shadow-md transition-all hover:from-red-600 hover:to-red-700 hover:shadow-lg disabled:opacity-50 sm:h-9 sm:w-9"
              >
                <Send className="h-4 w-4" />
                <span className="sr-only">Send message</span>
              </Button>
            </div>
          </div>
          <div className="mt-1.5 flex items-center justify-center gap-1.5 text-center text-[10px] text-muted-foreground sm:mt-2 sm:text-xs">
            <FileText className="h-3 w-3" />
            <span className="hidden sm:inline">Adjunta PDFs o enlaces para personalizar tu itinerario</span>
            <span className="sm:hidden">Adjunta PDFs o enlaces</span>
          </div>
        </form>
      </div>
    </div>
  )
}