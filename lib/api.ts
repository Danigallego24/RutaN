export interface TripRequest {
  destination?: string
  /** Puede ser número de días o string tipo "3 días" */
  duration?: number | string
  /** Estilo/presupuesto ("low" | "medium" | "high" | "relax" | ...) */
  style?: string
  /** Alias de style, por si lo usas desde el front como difficulty */
  difficulty?: string
  extra_info?: string
  session_id?: string
  /** "smart" | "fast" | "local" */
  model?: string
}

export async function generateItinerary(data: TripRequest): Promise<any> {
  try {
    const {
      destination,
      duration,
      style,
      difficulty,
      extra_info,
      session_id,
      model,
    } = data

    // Normalizamos estilo/dificultad para el backend
    const mergedStyle = style ?? difficulty ?? ""

    const payload = {
      session_id: session_id ?? "user_1",
      destination: destination ?? "",
      duration: duration ?? "",
      style: mergedStyle,
      difficulty: mergedStyle, // el backend también admite "difficulty"
      extra_info: extra_info ?? "",
      model: model,
    }

    const response = await fetch("http://localhost:8000/api/chat/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      const body = await response.text()
      throw new Error(`Error del servidor: ${response.status} - ${body}`)
    }

    const result: any = await response.json()

    // Caso 1: backend ya indica explícitamente si es itinerario
    if (result && typeof result === "object") {
      if (Object.prototype.hasOwnProperty.call(result, "es_itinerario")) {
        return result
      }

      // Caso 2: API devuelve 'itinerary' (por compatibilidad antigua)
      if (result.itinerary) {
        const text = result.itinerary
        console.log("🔍 Recibido (itinerary):", text)
        if (typeof text === "string") {
          try {
            const jsonMatch = text.match(/\{[\s\S]*\}/)
            if (jsonMatch) return JSON.parse(jsonMatch[0])
          } catch (e) {
            console.error("No es JSON válido en 'itinerary':", e)
          }
          return { es_itinerario: false, mensaje_chat: text }
        }
        return result.itinerary
      }

      // Caso 3: mensaje plano
      if (result.mensaje_chat) {
        return { es_itinerario: false, mensaje_chat: result.mensaje_chat }
      }

      // Caso 4: backend devuelve directamente 'titulo'/'dias'
      if (result.titulo || result.dias) {
        return { es_itinerario: true, ...result }
      }
    }

    // Caso 5: respuesta string
    if (typeof result === "string") {
      const text = result
      try {
        const jsonMatch = text.match(/\{[\s\S]*\}/)
        if (jsonMatch) return JSON.parse(jsonMatch[0])
      } catch (e) {
        console.error("No es JSON válido (respuesta string):", e)
      }
      return { es_itinerario: false, mensaje_chat: text }
    }

    // Fallback
    return {
      es_itinerario: false,
      mensaje_chat: "Respuesta inesperada del servidor.",
    }
  } catch (error) {
    console.error("Error API:", error)
    throw error
  }
}

export async function uploadFile(
  file: File,
  sessionId: string,
  model?: string,
): Promise<any> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("session_id", sessionId)
  if (model) {
    formData.append("model", model)
  }

  try {
    const response = await fetch("http://localhost:8000/api/files/upload", {
      method: "POST",
      body: formData, // Fetch ajusta automáticamente el Content-Type a multipart/form-data
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`Error subiendo archivo: ${errorText}`)
    }

    return await response.json()
  } catch (error) {
    console.error("Error en uploadFile:", error)
    throw error
  }
}
