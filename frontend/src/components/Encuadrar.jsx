import { useEffect, useRef } from 'react'
import { useMap } from 'react-leaflet'

// Ajusta la vista para que se vean todos los lugares, dejando libre lo que tapan
// el panel flotante (escritorio) o la hoja inferior (celular). Solo la primera vez.
function Encuadrar({ puntos, margenes }) {
  const mapa = useMap()
  const hecho = useRef(false)
  useEffect(() => {
    if (hecho.current || puntos.length === 0) return
    hecho.current = true
    const { arribaIzq, abajoDer } = margenes(mapa.getSize())
    mapa.fitBounds(puntos.map((p) => [p.lat, p.lon]), { paddingTopLeft: arribaIzq, paddingBottomRight: abajoDer, maxZoom: 13 })
  }, [puntos, mapa, margenes])
  return null
}

export default Encuadrar
