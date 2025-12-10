"use client"

import { useState, useEffect } from "react"
import { PanelRightClose, PanelRightOpen, Moon, Sun, Menu } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useTheme } from "next-themes"

// 1. DEFINIMOS QUE EL HEADER RECIBE EL MODELO Y LA FUNCIÓN DE CAMBIO
interface HeaderProps {
  showItinerary: boolean
  setShowItinerary: (show: boolean) => void
  showMobileSidebar: boolean
  setShowMobileSidebar: (show: boolean) => void
  // Estas son las "entradas" para conectar con page.tsx
  onModelChange: (model: string) => void
  selectedModel?: string
}

export function Header({ 
  showItinerary, 
  setShowItinerary, 
  showMobileSidebar, 
  setShowMobileSidebar,
  onModelChange,
  selectedModel,
}: HeaderProps) {
  
  const { setTheme, resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [setMounted])

  const isDark = mounted && resolvedTheme === "dark"

  // Definimos los modelos disponibles
  const models = [
    { key: "smart", label: "Groq 70B (Potente)" },
    { key: "fast", label: "Groq 8B (Rápido)" },
    { key: "local", label: "Ollama (Local)" },
  ]

  return (
    <header className="glass sticky top-0 z-50 flex h-14 shrink-0 items-center justify-between rounded-2xl px-3 sm:px-4 md:h-16 md:px-6">
      
      {/* IZQUIERDA: LOGO Y MENÚ */}
      <div className="flex items-center gap-2 sm:gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="glass-subtle h-9 w-9 shrink-0 rounded-xl text-foreground lg:hidden"
          onClick={() => setShowMobileSidebar(!showMobileSidebar)}
        >
          <Menu className="h-5 w-5" />
          <span className="sr-only">Toggle settings</span>
        </Button>

        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white shadow-lg shadow-gray-200/50 sm:h-10 sm:w-10 overflow-hidden">
          <img src="/logo.png" alt="RutaÑ logo" className="h-full w-full object-contain" />
        </div>
        <div className="hidden xs:block sm:block">
          <h1 className="text-base font-bold tracking-tight text-foreground sm:text-lg md:text-xl">
            Ruta<span className="font-serif text-red-500">Ñ</span>
          </h1>
          <p className="text-[9px] text-muted-foreground sm:text-[10px] md:text-xs">Your Spanish Adventure Planner</p>
        </div>
      </div>

      {/* DERECHA: SELECTOR DE MODELOS + TEMA + PANEL */}
      <div className="flex items-center gap-1.5 sm:gap-2">
          <div className="hidden sm:flex items-center gap-1 mr-2 bg-secondary/30 p-1 rounded-lg">
          {models.map((m) => (
            <button
              key={m.key}
              onClick={() => onModelChange(m.key)} // <--- ESTO CONECTA CON PAGE.TSX
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
                selectedModel === m.key 
                  ? "bg-red-500 text-white shadow-sm" 
                  : "text-muted-foreground hover:bg-background/50 hover:text-foreground"
              }`}
            >
              {m.label}
            </button>
          ))}
          </div>

        {/* BOTÓN TEMA */}
        <Button
          variant="ghost"
          size="icon"
          className="glass-subtle h-8 w-8 rounded-xl text-foreground sm:h-9 sm:w-9"
          onClick={() => setTheme(isDark ? "light" : "dark")}
        >
          {mounted ? isDark ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" /> : <div className="h-4 w-4" />}
          <span className="sr-only">Toggle theme</span>
        </Button>

        {/* BOTÓN ITINERARIO */}
        <Button
          variant="ghost"
          size="icon"
          className="glass-subtle hidden h-9 w-9 rounded-xl text-foreground md:flex xl:hidden"
          onClick={() => setShowItinerary(!showItinerary)}
        >
          {showItinerary ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
          <span className="sr-only">Toggle itinerary</span>
        </Button>

      </div>
    </header>
  )
}