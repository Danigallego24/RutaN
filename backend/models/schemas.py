from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# CLASE 1: La "Hoja de Pedido" (Input)
# Esto define QUÉ necesita el bot para poder trabajar.
class TripRequest(BaseModel):
    destination: Optional[str] = None # OPCIONAL: Puede venir texto o estar vacío (None)
    duration: Optional[str] = None    # OPCIONAL: Puede venir texto o estar vacío (None)
    style: Optional[str] = None       # OPCIONAL: Puede venir texto o estar vacío (None)
    extra_info: Optional[str] = None # OPCIONAL: Puede venir texto o estar vacío (None)

# CLASE 2: La "Caja del Producto" (Output)
# Esto define QUÉ va a devolver el bot a la web.
class TripResponse(BaseModel):
    itinerary: str                # OBLIGATORIO: El bot devolverá texto (el JSON de la ruta)