"use client"

import type React from "react"
import { MapPin, Sun, Utensils, Camera, Coffee, Footprints, Map, Navigation, FileDown, Loader2, Home} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { generateItineraryPDFFromBackend } from "@/lib/pdf-generator"
import { cn } from "@/lib/utils"

// 1. Definimos la estructura exacta que esperamos recibir
// Activity shape (flexible): either a simple string or an object with category
export interface Activity {
  activity?: string
  category?: "Culture" | "Food" | "Hiking" | "Relaxation" | "Sightseeing" | string
}

export type DayItinerary =
  | ({ day: number } & Record<string, any>)
  | ({ dia: number } & Record<string, any>)

interface ItineraryPanelProps {
  destination: string
  duration: number
  itineraryData?: DayItinerary[] 
  isGenerating?: boolean
}

const categoryIcons: Record<string, React.ElementType> = {
  Culture: Camera,
  Food: Utensils,
  Hiking: Footprints,
  Relaxation: Coffee,
  Sightseeing: Sun,
  General: Home
}

const categoryColors: Record<string, string> = {
  Culture: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  Food: "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300",
  Hiking: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  Relaxation: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  Sightseeing: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  General: "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300"
}

export function ItineraryPanel({ destination, duration, itineraryData = [], isGenerating = false }: ItineraryPanelProps) {
  
  const visibleDays = itineraryData.slice(0, Math.max(duration, itineraryData.length))

  const handleDownloadPDF = () => {
    try {
      if (!itineraryData || itineraryData.length === 0) {
        alert("No itinerary data available")
        return
      }
      generateItineraryPDFFromBackend(destination || "Trip", duration, itineraryData)
    } catch (e) {
      console.error('PDF generation failed', e)
      alert('No se pudo generar el PDF.')
    }
  }

  const hasData = itineraryData && itineraryData.length > 0

  return (
    <aside className="glass flex w-64 shrink-0 flex-col overflow-hidden rounded-2xl xl:w-80">
      {/* Header del Panel (Mapa y destino) */}
      <div className="relative h-28 shrink-0 overflow-hidden rounded-t-2xl bg-gradient-to-br from-red-500/10 via-red-500/5 to-secondary xl:h-36">
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-red-500/10 xl:h-12 xl:w-12">
            <Map className="h-5 w-5 text-red-500/60 xl:h-6 xl:w-6" />
          </div>
          <p className="text-xs font-medium text-foreground xl:text-sm">{destination ? "Map" : ""}</p>
          <p className="flex items-center gap-1 text-[10px] text-muted-foreground xl:text-xs">
            <Navigation className="h-3 w-3" />
            {destination || ""}
          </p>
        </div>
        {duration > 0 && (
          <div className="absolute bottom-2 right-2 xl:bottom-3 xl:right-3">
            <Badge variant="secondary" className="glass-subtle text-foreground shadow-sm">
              <MapPin className="mr-1 h-3 w-3 text-red-500" />
              {duration} Days
            </Badge>
          </div>
        )}
      </div>

      <div className="shrink-0 border-b border-border/30 px-3 py-2 xl:px-4 xl:py-3">
        <h2 className="text-sm font-semibold text-foreground xl:text-base">Your Itinerary</h2>
        <p className="text-[10px] text-muted-foreground xl:text-xs">
          {destination ? `Trip to ${destination}` : "Plan your trip"}
        </p>
      </div>

      {/* Cuerpo del Itinerario (Scrollable) */}
      <div className="custom-scrollbar flex-1 overflow-y-auto p-2 xl:p-3">
        <div className="space-y-2 xl:space-y-3">
          
          {/* ESTADO 1: Cargando / Generando */}
          {isGenerating && !hasData && (
             <div className="flex flex-col items-center justify-center py-10 text-center">
                <Loader2 className="h-8 w-8 animate-spin text-red-500/50" />
                <p className="mt-2 text-xs text-muted-foreground">AI is crafting your trip...</p>
             </div>
          )}

          {/* ESTADO 2: Sin Datos (Esperando input) */}
          {!isGenerating && !hasData && (
            <div className="rounded-xl border border-dashed border-border p-4 text-center">
              <p className="text-xs text-muted-foreground">
                Chat with the AI to generate your personalized itinerary here.
              </p>
            </div>
          )}

          {/* ESTADO 3: Mostrando Datos Dinámicos */}
          {hasData && visibleDays.map((dayData, index) => {
            const dayNum = (dayData && (dayData.day || dayData.dia)) || (index + 1)
            return (
              <DayCard key={index} day={dayNum} dayData={dayData} />
            )
          })}

          {/* Si hay más días de los que mostramos (lógica opcional) */}
          {hasData && duration > visibleDays.length && (
            <div className="rounded-xl border border-dashed border-red-500/30 bg-red-500/5 p-2 text-center xl:p-3">
              <p className="text-[10px] text-muted-foreground xl:text-xs">
                +{duration - visibleDays.length} more days planned
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Footer (Botón PDF) */}
      <div className="shrink-0 border-t border-border/30 p-2 xl:p-3">
        <Button
          onClick={handleDownloadPDF}
          disabled={!hasData} // Deshabilitar si no hay itinerario
          className="w-full gap-2 rounded-xl bg-gradient-to-r from-red-500 to-red-600 text-white shadow-md transition-all hover:from-red-600 hover:to-red-700 hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <FileDown className="h-4 w-4" />
          <span className="text-sm font-medium">Download PDF</span>
        </Button>
      </div>
    </aside>
  )
}

// --- Componentes Auxiliares (Sin cambios grandes, solo types) ---

interface DayCardProps {
  day: number
  dayData?: DayItinerary | any
}

function DayCard({ day, dayData }: DayCardProps) {
  // Backend may return { dia, resumen, actividades: [] } or the older morning/lunch/afternoon shape
  const resumen = (dayData && (dayData.resumen || dayData.summary || dayData.resumen)) || null
  const actividades = (dayData && (dayData.actividades || dayData.actividades || dayData.activities)) || null

  return (
    <div className="glass-subtle overflow-hidden rounded-xl">
      <div className="bg-red-500/10 px-2.5 py-1.5 xl:px-3 xl:py-2">
        <h3 className="text-xs font-semibold text-foreground xl:text-sm">Day {day}</h3>
      </div>
      <div className="space-y-2 p-2 xl:space-y-2.5 xl:p-3">
        {resumen && <p className="text-sm text-muted-foreground">{resumen}</p>}

        {actividades && Array.isArray(actividades) && (
          <div className="space-y-2">
            {actividades.map((a: any, idx: number) => {
              // Normalize activity object or string
              const actText = typeof a === "string" ? a : (a.activity || a.nombre || a.name || String(a))
              const rawCat = typeof a === "object" ? (a.category || a.categoria || a.type) : undefined
              // Normalize category to expected keys
              const normalizeCategory = (c: any) => {
                if (!c) return undefined
                const s = String(c).toLowerCase()
                if (s.includes('cultur')) return 'Culture'
                if (s.includes('gastr') || s.includes('food') || s.includes('tapa')) return 'Food'
                if (s.includes('hike') || s.includes('trek') || s.includes('sender')) return 'Hiking'
                if (s.includes('relax')) return 'Relaxation'
                if (s.includes('sight') || s.includes('tour') || s.includes('view')) return 'Sightseeing'
                return 'General'
              }
              const catKey = normalizeCategory(rawCat)
              const LeftIcon = (catKey && categoryIcons[catKey]) ? categoryIcons[catKey] : Camera

              return (
                <ActivityItem
                  key={idx}
                  icon={LeftIcon}
                  label={`Activity ${idx + 1}`}
                  activity={actText}
                  category={catKey}
                />
              )
            })}
          </div>
        )}

        {/* Fallback: try morning/lunch/afternoon if present */}
        {!resumen && !actividades && (
          <div className="space-y-2">
            {dayData?.morning && <ActivityItem icon={Sun} label="Morning" {...(dayData.morning || {})} />}
            {dayData?.lunch && <ActivityItem icon={Utensils} label="Lunch" {...(dayData.lunch || {})} />}
            {dayData?.afternoon && <ActivityItem icon={Camera} label="Afternoon" {...(dayData.afternoon || {})} />}
            {(!dayData?.morning && !dayData?.lunch && !dayData?.afternoon) && (
              <p className="text-[10px] text-muted-foreground italic">Planning activities...</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

interface ActivityItemProps extends Activity {
  icon: React.ElementType
  label: string
}

function ActivityItem({ icon: Icon, label, activity, category }: ActivityItemProps) {
  // Fallback seguro si la categoría viene vacía o no existe en el mapa
  const CategoryIcon = category && categoryIcons[category] ? categoryIcons[category] : Camera
  const categoryColor = category && categoryColors[category] ? categoryColors[category] : "bg-secondary text-secondary-foreground"

  return (
    <div className="flex items-start gap-2">
      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-secondary xl:h-7 xl:w-7">
        <Icon className="h-3 w-3 text-muted-foreground xl:h-3.5 xl:w-3.5" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[9px] font-medium uppercase tracking-wider text-muted-foreground xl:text-[10px]">{label}</p>
        <p className="truncate text-[11px] font-medium text-foreground xl:text-xs">{activity}</p>
        <Badge
          variant="secondary"
          className={cn(
            "mt-0.5 h-4 gap-0.5 px-1 text-[9px] font-medium xl:mt-1 xl:h-5 xl:gap-1 xl:px-1.5 xl:text-[10px]",
            categoryColor,
          )}
        >
          <CategoryIcon className="h-2 w-2 xl:h-2.5 xl:w-2.5" />
          {category || "General"}
        </Badge>
      </div>
    </div>
  )
}