import { CircleMarker } from 'react-leaflet'
import { intensidad, RAMPA } from '../data/calor.js'

const ANILLOS = 9

// Capa de calor: por lugar, círculos concéntricos con radio en píxeles (como leaflet.heat),
// más grandes, oscuros y opacos cuanto más gente; donde se juntan lugares, se suman.
function CapaCalor({ puntos }) {
  return puntos
    .filter((p) => p.nivel != null)
    .flatMap((p) => {
      const t = intensidad(p.nivel)
      const color = RAMPA[Math.round(t * (RAMPA.length - 1))]
      const radio = 22 + 38 * t
      return Array.from({ length: ANILLOS }, (_, k) => (
        <CircleMarker
          key={`${p.id}-${k}`}
          center={[p.lat, p.lon]}
          radius={radio * (1 - k * 0.1)}
          interactive={false}
          pathOptions={{ stroke: false, fillColor: color, fillOpacity: 0.035 + 0.055 * t }}
        />
      ))
    })
}

export default CapaCalor
