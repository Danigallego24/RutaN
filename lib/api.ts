export interface TripRequest {
  destination: string;
  duration: string;
  style: string;
  extra_info?: string;
  session_id?: string;
  model?: string;
}

export async function generateItinerary(data: TripRequest): Promise<any> {
  try {
    const response = await fetch("http://localhost:8000/api/chat/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Error del servidor: ${response.status} - ${body}`);
    }

    const result = await response.json();

    // Si el backend ya devuelve la estructura final, devuélvela tal cual
    if (result && typeof result === "object") {
      // Caso 1: API ya indica si es itinerario
      if (Object.prototype.hasOwnProperty.call(result, "es_itinerario")) {
        return result;
      }

      // Caso 2: API devuelve 'itinerary' (string con JSON o texto)
      if (result.itinerary) {
        const text = result.itinerary;
        console.log("🔍 Recibido (itinerary):", text);
        if (typeof text === "string") {
          try {
            const jsonMatch = text.match(/\{[\s\S]*\}/);
            if (jsonMatch) return JSON.parse(jsonMatch[0]);
          } catch (e) {
            console.error("No es JSON válido en 'itinerary':", e);
          }
          return { es_itinerario: false, mensaje_chat: text };
        }
        // si no es string, devolvemos el objeto directamente
        return result.itinerary;
      }

      // Caso 3: API devuelve 'mensaje_chat' directo
      if (result.mensaje_chat) {
        return { es_itinerario: false, mensaje_chat: result.mensaje_chat };
      }

      // Caso 4: API devuelve campos 'titulo'/'dias' directamente
      if (result.titulo || result.dias) {
        return { es_itinerario: true, ...result };
      }
    }

    // Caso 5: si la respuesta es un string plano
    if (typeof result === "string") {
      const text = result;
      try {
        const jsonMatch = text.match(/\{[\s\S]*\}/);
        if (jsonMatch) return JSON.parse(jsonMatch[0]);
      } catch (e) {
        console.error("No es JSON válido (respuesta string):", e);
      }
      return { es_itinerario: false, mensaje_chat: text };
    }

    // Fallback genérico
    return { es_itinerario: false, mensaje_chat: "Respuesta inesperada del servidor." };

  } catch (error) {
    console.error("Error API:", error);
    throw error;
  }
}

export async function uploadFile(file: File, sessionId: string): Promise<any> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("session_id", sessionId);

  try {
    const response = await fetch("http://localhost:8000/api/files/upload", {
      method: "POST",
      body: formData, // Fetch ajusta automáticamente el Content-Type a multipart/form-data
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Error subiendo archivo: ${errorText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error en uploadFile:", error);
    throw error;
  }
}