"use client"

import { MapPin, Clock, Mountain, Sparkles, History, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { cn } from "@/lib/utils"

interface MobileSidebarProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  destination: string
  setDestination: (value: string) => void
  duration: number
  setDuration: (value: number) => void
  difficulty: string
  setDifficulty: (value: string) => void
  onGenerate: () => void
  isGenerating: boolean
}

const chatHistory = [
  { id: 1, title: "Barcelona & Costa Brava", date: "2 days ago" },
  { id: 2, title: "Camino de Santiago", date: "1 week ago" },
  { id: 3, title: "Andalucia Road Trip", date: "2 weeks ago" },
]

export function MobileSidebar({
  open,
  onOpenChange,
  destination,
  setDestination,
  duration,
  setDuration,
  difficulty,
  setDifficulty,
  onGenerate,
  isGenerating,
}: MobileSidebarProps) {
  const handleGenerate = () => {
    onGenerate()
    onOpenChange(false)
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="left"
        className="w-[300px] overflow-y-auto border-r-0 bg-background p-0 backdrop-blur-2xl sm:w-[350px]"
      >
        <SheetHeader className="sticky top-0 z-10 border-b border-border bg-background/95 px-4 py-4 backdrop-blur-sm sm:px-5">
          <div className="flex items-center justify-between">
            <SheetTitle className="flex items-center gap-2 text-base font-semibold text-foreground">
              <MapPin className="h-4 w-4 text-red-500" />
              Trip Settings
            </SheetTitle>
          </div>
        </SheetHeader>

        <div className="space-y-5 p-4 sm:space-y-6 sm:p-5">
          <div className="space-y-2">
            <Label htmlFor="mobile-destination" className="text-sm font-medium text-foreground">
              Destination in Spain
            </Label>
            <Input
              id="mobile-destination"
              placeholder="Madrid, Asturias, Sevilla..."
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              className="h-11 rounded-xl border-border bg-secondary/50 text-foreground transition-colors placeholder:text-muted-foreground focus:bg-secondary"
            />
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="flex items-center gap-2 text-sm font-medium text-foreground">
                <Clock className="h-4 w-4 text-muted-foreground" />
                Duration
              </Label>
              <span className="rounded-lg bg-red-500/15 px-3 py-1 text-sm font-semibold text-red-600 dark:text-red-400">
                {duration} {duration === 1 ? "Day" : "Days"}
              </span>
            </div>
            <Slider
              value={[duration]}
              onValueChange={(value) => setDuration(value[0])}
              min={1}
              max={15}
              step={1}
              className="py-2"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>1 day</span>
              <span>15 days</span>
            </div>
          </div>

          <div className="space-y-3">
            <Label className="flex items-center gap-2 text-sm font-medium text-foreground">
              <Mountain className="h-4 w-4 text-muted-foreground" />
              Difficulty Level
            </Label>
            <div className="space-y-2">
              {[
                { value: "low", label: "Relaxed", desc: "Easy pace, comfort focus" },
                { value: "medium", label: "Explorer", desc: "Balanced activities" },
                { value: "high", label: "Adventure", desc: "Active & challenging" },
              ].map((option) => (
                <button
                  key={option.value}
                  onClick={() => setDifficulty(option.value)}
                  className={cn(
                    "flex w-full cursor-pointer items-center gap-3 rounded-xl border-2 border-transparent bg-secondary/50 p-3 text-left transition-all hover:bg-secondary sm:p-3.5",
                    difficulty === option.value && "border-red-500 bg-red-500/10 dark:bg-red-500/15",
                  )}
                >
                  <div
                    className={cn(
                      "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 transition-colors",
                      difficulty === option.value ? "border-red-500 bg-red-500" : "border-muted-foreground/40",
                    )}
                  >
                    {difficulty === option.value && <div className="h-2 w-2 rounded-full bg-white" />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground">{option.label}</p>
                    <p className="text-xs text-muted-foreground">{option.desc}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

          <Button
            onClick={handleGenerate}
            disabled={!destination || isGenerating}
            className="w-full gap-2 rounded-xl bg-gradient-to-r from-red-500 to-red-600 py-6 text-white shadow-lg shadow-red-500/25 transition-all hover:from-red-600 hover:to-red-700 hover:shadow-xl disabled:opacity-50"
          >
            <Sparkles className={cn("h-4 w-4", isGenerating && "animate-pulse")} />
            {isGenerating ? "Generating..." : "Generate Itinerary"}
          </Button>
        </div>

        <div className="border-t border-border p-4 sm:p-5">
          <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <History className="h-3.5 w-3.5" />
            History
          </h3>
          <div className="space-y-2">
            {chatHistory.map((chat) => (
              <button
                key={chat.id}
                className="flex w-full items-center justify-between rounded-xl bg-secondary/50 p-3 text-left transition-all hover:bg-secondary"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">{chat.title}</p>
                  <p className="text-xs text-muted-foreground">{chat.date}</p>
                </div>
                <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
              </button>
            ))}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
