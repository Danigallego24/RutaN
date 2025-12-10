"use client"

import { useState } from "react"
import type React from "react"
import { MapPin, Clock, Mountain, Sparkles, History, ChevronRight, Trash } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { cn } from "@/lib/utils"

interface TripSidebarProps {
  destination: string
  setDestination: (value: string) => void
  duration: number
  setDuration: (value: number) => void
  difficulty: string
  setDifficulty: (value: string) => void
  onGenerate: () => void
  isGenerating: boolean
  // optional props for history
  conversations?: any[]
  onOpenConversation?: (c: any) => void
  onNewConversation?: () => void
  onDeleteConversation?: (id: string) => void
}

export function TripSidebar({
  destination,
  setDestination,
  duration,
  setDuration,
  difficulty,
  setDifficulty,
  onGenerate,
  isGenerating,
  conversations = [],
  onOpenConversation,
  onNewConversation,
  onDeleteConversation,
}: TripSidebarProps) {
  const [activeCard, setActiveCard] = useState<number | null>(null)

  const handleCardClick = (id: number) => {
    setActiveCard(id)
    setTimeout(() => setActiveCard(null), 150)
  }

  // Helper para manejar la apertura segura
  const handleOpen = (chat: any) => {
    if (onOpenConversation) {
      onOpenConversation(chat)
    } else {
      handleCardClick(chat.id)
    }
  }

  return (
    <aside className="glass custom-scrollbar hidden w-64 shrink-0 flex-col overflow-y-auto rounded-2xl lg:flex xl:w-72">
      <div className="p-4 xl:p-5">
        {/* Trip Settings Section */}
        <div className="mb-4 xl:mb-5">
          <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <MapPin className="h-4 w-4 text-red-500" />
            Trip Settings
          </h2>
        </div>

        <div className="space-y-4 xl:space-y-5">
          <div className="space-y-2">
            <Label htmlFor="destination" className="text-sm font-medium text-foreground">
              Destination in Spain
            </Label>
            <Input
              id="destination"
              placeholder="Madrid, Asturias, Sevilla..."
              value={destination}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setDestination(e.target.value)
              }
              className="h-10 rounded-xl border-border bg-secondary/50 text-foreground transition-colors placeholder:text-muted-foreground focus:bg-secondary xl:h-11"
            />
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="flex items-center gap-2 text-sm font-medium text-foreground">
                <Clock className="h-4 w-4 text-muted-foreground" />
                Duration
              </Label>
              <span className="rounded-lg bg-red-500/15 px-2.5 py-1 text-xs font-semibold text-red-600 dark:text-red-400 xl:px-3 xl:text-sm">
                {duration} {duration === 1 ? "Day" : "Days"}
              </span>
            </div>
            <Slider
              value={[duration]}
              onValueChange={(value: number[]) => setDuration(value[0])}
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
                  type="button"
                  onClick={() => setDifficulty(option.value)}
                  className={cn(
                    "flex w-full cursor-pointer items-center gap-3 rounded-xl border-2 border-transparent bg-secondary/50 p-2.5 text-left transition-all hover:bg-secondary xl:p-3",
                    difficulty === option.value &&
                      "border-red-500 bg-red-500/10 dark:bg-red-500/15",
                  )}
                >
                  <div
                    className={cn(
                      "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2 transition-colors xl:h-5 xl:w-5",
                      difficulty === option.value
                        ? "border-red-500 bg-red-500"
                        : "border-muted-foreground/40",
                    )}
                  >
                    {difficulty === option.value && (
                      <div className="h-1.5 w-1.5 rounded-full bg-white xl:h-2 xl:w-2" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground">{option.label}</p>
                    <p className="truncate text-xs text-muted-foreground">{option.desc}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

          <Button
            onClick={onGenerate}
            disabled={!destination || isGenerating}
            className="w-full gap-2 rounded-xl bg-gradient-to-r from-red-500 to-red-600 py-5 text-white shadow-lg shadow-red-500/25 transition-all hover:from-red-600 hover:to-red-700 hover:shadow-xl disabled:opacity-50 xl:py-6"
          >
            <Sparkles className={cn("h-4 w-4", isGenerating && "animate-pulse")} />
            {isGenerating ? "Generating..." : "Generate Itinerary"}
          </Button>
        </div>

        <div className="mt-5 border-t border-border/30 pt-5 xl:mt-6 xl:pt-6">
          <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <History className="h-3.5 w-3.5" />
            History
          </h3>
          <div className="space-y-2">
            <div className="mb-2 flex gap-2">
              <button
                type="button"
                onClick={() => onNewConversation && onNewConversation()}
                className="w-full rounded-md bg-secondary px-3 py-2 text-center text-xs font-medium text-foreground transition-colors hover:bg-secondary/80"
              >
                + New Chat
              </button>
            </div>
            {conversations.length === 0 && (
              <p className="py-2 text-center text-xs italic text-muted-foreground">
                No conversations yet.
              </p>
            )}
            {conversations.map((chat: any) => (
              <div
                key={chat.id}
                className={cn(
                  "history-card group relative glass-subtle flex w-full cursor-pointer items-center justify-between rounded-xl p-2.5 xl:p-3",
                  activeCard === chat.id && "animate-press",
                )}
                onClick={() => handleOpen(chat)}
              >
                <div className="min-w-0 flex-1 pr-2">
                  <p className="truncate text-sm font-medium text-foreground">{chat.title}</p>
                  <p className="text-xs text-muted-foreground">{chat.date}</p>
                </div>

                <div className="flex items-center gap-1">
                  {/* Botón DELETE con stopPropagation crítico */}
                  <button
                    type="button"
                    aria-label={`Delete ${chat.title}`}
                    onClick={(e: React.MouseEvent<HTMLButtonElement>) => {
                      e.stopPropagation()
                      e.preventDefault()
                      if (onDeleteConversation) onDeleteConversation(chat.id)
                    }}
                    className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-red-100 hover:text-red-600 focus:opacity-100 dark:hover:bg-red-900/30 dark:hover:text-red-400 group-hover:opacity-100"
                    title="Delete conversation"
                  >
                    <Trash className="h-4 w-4" />
                  </button>

                  <ChevronRight className="h-4 w-4 text-muted-foreground/50" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </aside>
  )
}
