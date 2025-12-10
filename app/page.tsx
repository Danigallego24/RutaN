"use client"

import { useState, useEffect } from "react"
import { Header } from "@/components/header"
import { TripSidebar } from "@/components/trip-sidebar"
import { ChatArea } from "@/components/chat-area"
import { ItineraryPanel } from "@/components/itinerary-panel"
import { ThemeProvider } from "@/components/theme-provider"
import { MobileSidebar } from "@/components/mobile-sidebar"
import { generateItinerary } from "@/lib/api"

export default function RutaNDashboard() {
  
  // --- ESTADOS ---
  const [destination, setDestination] = useState("")
  const [duration, setDuration] = useState(7)
  const [difficulty, setDifficulty] = useState("Explorer")
  const [isGenerating, setIsGenerating] = useState(false)
  const [showItinerary, setShowItinerary] = useState(true)
  const [showMobileSidebar, setShowMobileSidebar] = useState(false)
  
  // Estado para el Modelo de IA (Controlado desde el Header)
  const [selectedModel, setSelectedModel] = useState("smart")

  const [itineraryResult, setItineraryResult] = useState<any>(null)
  const [sessionId, setSessionId] = useState<string>("")
  type Message = { role: 'user'|'ai'; content: string }
  const DEFAULT_GREETING: Message = { role: 'ai', content: "**¡Hola!** Soy RutaÑ, tu experto en viajes por España. 🇪🇸\n\nCuéntame tu plan o usa el menú de la izquierda." }
  const [conversations, setConversations] = useState<Array<any>>([])
  const [activeConversationId, setActiveConversationId] = useState<string>("")
  const [messages, setMessages] = useState<Message[]>([])

  // currentConversation is stored as separate state for easy editing
  const [currentConversation, setCurrentConversation] = useState<any>(null)

  const normalizeMessages = (arr: any): Message[] => {
    if (!arr || !Array.isArray(arr)) return []
    return arr.map((m: any) => ({ role: m?.role === 'user' ? 'user' : 'ai', content: String(m?.content || '') }))
  }

  const dedupeMessages = (arr: any): Message[] => {
    const msgs = normalizeMessages(arr)
    const out: Message[] = []
    for (const m of msgs) {
      if (out.length === 0) out.push(m)
      else {
        const prev = out[out.length - 1]
        if (prev.role !== m.role || prev.content !== m.content) out.push(m)
      }
    }
    return out
  }

  const extractTitleFromMessage = (text: string): string | null => {
    if (!text || typeof text !== 'string') return null
    const patterns = [/quiero ir a\s+([A-Za-zÀ-ÿ\s]+)/i, /viaje a\s+([A-Za-zÀ-ÿ\s]+)/i, /voy a\s+([A-Za-zÀ-ÿ\s]+)/i, /a\s+([A-Za-zÀ-ÿ\s]+)\s+por\s+/, /a\s+([A-Za-zÀ-ÿ\s]+)\b/i]
    for (const p of patterns) {
      const m = text.match(p)
      if (m && m[1]) {
        const city = m[1].trim().split(/[\.\,\n]/)[0]
        if (city.length > 0 && city.length < 40) return city.charAt(0).toUpperCase() + city.slice(1)
      }
    }
    return null
  }

  // --- INICIALIZACIÓN ---
  useEffect(() => {
    try {
      const keySession = 'rutaN_session'
      let sid = localStorage.getItem(keySession)
      if (!sid) {
        sid = `${Date.now()}-${Math.floor(Math.random()*100000)}`
        localStorage.setItem(keySession, sid)
      }
      setSessionId(sid)

      const savedModel = localStorage.getItem("rutaN_model")
      if (savedModel) setSelectedModel(savedModel)
      
      const storedConv = localStorage.getItem('rutaN_conversations')
      if (storedConv) {
        try {
          const parsed = JSON.parse(storedConv)
          setConversations(parsed)
          if (parsed && parsed.length > 0) {
            const last = parsed[0]
            setActiveConversationId(last.id)
            setCurrentConversation({ ...last, messages: dedupeMessages(last.messages) })
            setMessages(dedupeMessages(last.messages).length ? dedupeMessages(last.messages) : [DEFAULT_GREETING])
            setItineraryResult(last.itinerary || null)
            if (last.session_id) setSessionId(last.session_id)
          } else {
            createEmptyChat(sessionId)
          }
        } catch (e) { 
          setConversations([])
          createEmptyChat(sessionId)
        }
      } else {
        createEmptyChat(sessionId)
      }
    } catch (e) {
      // ignore
    }
  }, [])

  const createEmptyChat = (sid: string) => {
      const id = `${Date.now()}-${Math.floor(Math.random()*100000)}`
      const conv = { id, title: "Nuevo chat", date: new Date().toLocaleString(), session_id: sid, messages: [DEFAULT_GREETING], itinerary: null }
      setCurrentConversation(conv)
      setActiveConversationId(id)
      setMessages(conv.messages)
  }

  const handleModelChange = (model: string) => {
    setSelectedModel(model)
    localStorage.setItem("rutaN_model", model)
    const infoMsg: Message = { role: 'ai', content: `🔁 Modelo cambiado a **${model}**` }
    setMessages((prev) => {
      const next = [...prev, infoMsg]
      setCurrentConversation((c:any) => c ? { ...c, messages: dedupeMessages([...(c.messages||[]), infoMsg]) } : c)
      return next
    })

    try {
      fetch("http://127.0.0.1:8000/api/chat/model_check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model }),
      })
        .then((res) => res.json())
        .then((info) => {
          const msg = info && info.ok ? `🔍 Provider: **${info.provider}** (conectado)` : `⚠️ No se pudo comprobar el proveedor: ${info?.message || 'error'}`
          const obj: Message = { role: 'ai', content: msg }
          setMessages((prev) => {
             const next = [...prev, obj]
             setCurrentConversation((c:any) => c ? { ...c, messages: dedupeMessages([...(c.messages||[]), obj]) } : c)
             return next
          })
        })
        .catch((e) => { /* ignore */ })
    } catch (e) { /* ignore */ }
  }

  const processResponse = (data: any) => {
      if (data.es_itinerario) {
          setItineraryResult(data);
          const title = data.titulo || `Viaje a ${data.destino || 'España'}`
          
          // Si hay mensaje_chat narrativo, lo mostramos primero
          const narrativeMessage = data.mensaje_chat || `¡Listo! He diseñado tu viaje a **${title}**. 👉 Míralo en el panel de la derecha.`
          const aiMsg: Message = { role: 'ai', content: narrativeMessage }
          
          setCurrentConversation((c:any) => {
            if (!c) return c
            const updated = { ...c, title, itinerary: data, messages: [...(c.messages||[]), aiMsg], date: new Date().toLocaleString(), session_id: sessionId }
            setConversations((prev) => {
              const exists = prev.findIndex((p:any)=>p.id === updated.id)
              let next
              if (exists >= 0) {
                next = [updated, ...prev.filter((p:any)=>p.id !== updated.id)]
              } else {
                next = [updated, ...prev]
              }
              try { localStorage.setItem('rutaN_conversations', JSON.stringify(next)) } catch(e){}
              return next
            })
            return updated
          })
          setMessages((prev) => [...prev, aiMsg]);
          if (window.innerWidth < 768) setShowItinerary(true);
      } else {
          const aiMsg: Message = { role: 'ai', content: data.mensaje_chat }
            setMessages((prev) => {
              const next = [...prev, aiMsg]
              setCurrentConversation((c:any) => c ? { ...c, messages: dedupeMessages([...(c.messages||[]), aiMsg]) } : c)
              return next
            })
      }
  };

  const handleNewChat = () => {
    const key = 'rutaN_session'
    let newSid = sessionId
    try {
      newSid = `${Date.now()}-${Math.floor(Math.random()*100000)}`
      localStorage.setItem(key, newSid)
      setSessionId(newSid)
    } catch (e) {}

    // Save current if needed before switching
    if (currentConversation) {
      const hasContent = (currentConversation.messages && currentConversation.messages.length > 1) || currentConversation.itinerary
      if (hasContent) {
        const updated = { ...currentConversation, date: new Date().toLocaleString(), session_id: currentConversation.session_id || sessionId }
        setConversations((prev) => {
           // check if already exists to update or push
           const exists = prev.findIndex(p => p.id === updated.id)
           let next
           if (exists >= 0) {
             const copy = [...prev]
             copy[exists] = updated
             next = copy
           } else {
             next = [updated, ...prev]
           }
           try { localStorage.setItem('rutaN_conversations', JSON.stringify(next)) } catch(e){}
           return next
        })
      }
    }

    createEmptyChat(newSid)
    setItineraryResult(null)
  }

  const handleOpenConversation = (conv: any) => {
    try {
      setCurrentConversation(conv)
      setActiveConversationId(conv.id)
      setItineraryResult(conv.itinerary || null)
      if (conv.session_id) setSessionId(conv.session_id);
      setMessages(normalizeMessages(conv.messages || []));
    } catch (e) { }
  }

  const handleGenerate = async () => {
    setIsGenerating(true)
    const userMsg = destination ? `Genera un viaje a ${destination}...` : "Quiero generar un viaje...";
    const userObj: Message = { role: 'user', content: userMsg }
    
    setMessages((prev) => {
      const next = [...prev, userObj]
      setCurrentConversation((c:any) => c ? { ...c, messages: [...(c.messages||[]), userObj] } : c)
      return next
    })

    try {
      const data = await generateItinerary({
        destination, duration: `${duration} días`, style: difficulty,
        extra_info: "El usuario ha pulsado el botón 'Generar'.",
        session_id: sessionId,
        model: selectedModel,
      });
      processResponse(data);
    } catch (error) {
       // ... error handling
    } finally {
        setIsGenerating(false)
    }
  }

  const handleSendMessage = async (message: string, attachment?: File | string) => {
    const newTitle = extractTitleFromMessage(message)
    if (newTitle) {
      setCurrentConversation((c:any)=> c ? { ...c, title: `Viaje a ${newTitle}` } : c)
    }
    const userObj: Message = { role: 'user', content: message }
    setMessages((prev) => {
      const next = [...prev, userObj]
      setCurrentConversation((c:any) => c ? { ...c, messages: [...(c.messages||[]), userObj] } : c)
      return next
    })
    setIsGenerating(true)

    let finalMessage = message
    let fileAnalysis = ""

    try {
      // Si hay un archivo, primero subirlo y obtener el análisis
      if (attachment) {
      if (attachment instanceof File) {
          console.log(`📁 Subiendo archivo: ${attachment.name}`)
          const uploadResult = await fetch("http://localhost:8000/api/files/upload", {
            method: "POST",
            body: (() => {
              const formData = new FormData()
              formData.append("file", attachment)
              formData.append("session_id", sessionId)
              formData.append("model", selectedModel)
              return formData
            })(),
          }).then(r => r.json())
          
          if (uploadResult.ok && uploadResult.analysis) {
            fileAnalysis = uploadResult.analysis
            console.log(`✅ Análisis recibido: ${fileAnalysis.substring(0, 100)}...`)
            // Agregar el análisis al mensaje
            finalMessage = message + `\n\n[ANÁLISIS DEL ARCHIVO COMPARTIDO]:\n${fileAnalysis}`
          }
        } else if (typeof attachment === 'string') {
          // Es una URL
          finalMessage = message + `\n\n🔗 URL: ${attachment}`
        }
      }

      const data = await generateItinerary({
        destination: "", duration: "", style: "", 
        extra_info: finalMessage,
        session_id: sessionId,
        model: selectedModel, 
      });
      processResponse(data);
    } catch (error) {
        console.error("Error en handleSendMessage:", error)
        const errorMsg: Message = { role: 'ai', content: `❌ Error: ${error instanceof Error ? error.message : 'Error desconocido'}` }
        setMessages((prev) => [...prev, errorMsg])
    } finally {
        setIsGenerating(false)
    }
  }

  const handleDeleteConversation = (idToDelete: string) => {
    try {
      // 1. Crear la nueva lista sin el elemento borrado
      const nextConversations = conversations.filter((c:any) => c.id !== idToDelete)
      setConversations(nextConversations)
      try { localStorage.setItem('rutaN_conversations', JSON.stringify(nextConversations)) } catch(e){}

      // 2. Comprobar si hemos borrado la conversación que estamos viendo ahora mismo
      if (currentConversation && currentConversation.id === idToDelete) {
        if (nextConversations.length > 0) {
          // Si quedan otras, saltamos a la primera disponible (la más reciente)
          const first = nextConversations[0]
          handleOpenConversation(first)
        } else {
          // Si no queda ninguna, creamos un chat limpio
          const newSid = `${Date.now()}-${Math.floor(Math.random()*100000)}`
          createEmptyChat(newSid)
          setItineraryResult(null)
          // Aseguramos que el estado de sesión también se actualice
          setSessionId(newSid)
        }
      }
    } catch (e) {
      // ignore
    }
  }

  const sidebarProps = {
    destination, setDestination, duration, setDuration, difficulty, setDifficulty,
    onGenerate: handleGenerate, isGenerating,
  }

  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem disableTransitionOnChange>
      <div className="flex h-[100dvh] flex-col bg-background p-2 sm:p-3 md:p-4 lg:p-5">
        
        <Header
          showItinerary={showItinerary} setShowItinerary={setShowItinerary}
          showMobileSidebar={showMobileSidebar} setShowMobileSidebar={setShowMobileSidebar}
          selectedModel={selectedModel}
          onModelChange={handleModelChange} 
        />

        <div className="mt-2 flex min-h-0 flex-1 gap-2 sm:mt-3 sm:gap-3 md:mt-4 md:gap-4">
          <TripSidebar 
            {...sidebarProps} 
            conversations={conversations} 
            onOpenConversation={handleOpenConversation} 
            onNewConversation={handleNewChat} 
            onDeleteConversation={handleDeleteConversation} 
          />
          <MobileSidebar open={showMobileSidebar} onOpenChange={setShowMobileSidebar} {...sidebarProps} />
          
          <div className="flex flex-1 flex-col min-w-0">
            <ChatArea messages={messages} isGenerating={isGenerating} onSendMessage={handleSendMessage} />
          </div>
          
          <div className={`hidden md:flex ${showItinerary ? "md:flex" : "md:hidden"} xl:flex`}>
            <ItineraryPanel
              destination={itineraryResult?.titulo || destination || ""}
              duration={itineraryResult?.dias?.length || duration}
              itineraryData={itineraryResult?.dias || []}
              isGenerating={isGenerating && !itineraryResult}
            />
          </div>
        </div>
      </div>
    </ThemeProvider>
  )
}