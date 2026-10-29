import { useEffect, useRef } from 'react'
import L from 'leaflet'
import { useMap } from 'react-leaflet'

// Botones de acercar, alejar y (en Explorar) centrar en tu ubicación: no todos saben
// usar los gestos del mapa. Van dentro del mapa, así que sus clics no lo arrastran.
function ControlesMapa({ onUbicar, buscando = false, textos }) {
  const mapa = useMap()
  const caja = useRef(null)

  useEffect(() => {
    if (!caja.current) return
    L.DomEvent.disableClickPropagation(caja.current)
    L.DomEvent.disableScrollPropagation(caja.current)
  }, [])

  return (
    <div className="controles-mapa" ref={caja}>
      {onUbicar && (
        <button type="button" className={`control-mapa ubicar${buscando ? ' buscando' : ''}`} onClick={onUbicar}
          disabled={buscando} aria-busy={buscando} aria-label={buscando ? textos.buscando : textos.ubicar}
          title={buscando ? textos.buscando : textos.ubicar}>
          <span aria-hidden="true" />
        </button>
      )}
      <div className="control-grupo">
        <button type="button" className="control-mapa" onClick={() => mapa.zoomIn()} aria-label={textos.acercar} title={textos.acercar}>+</button>
        <button type="button" className="control-mapa" onClick={() => mapa.zoomOut()} aria-label={textos.alejar} title={textos.alejar}>−</button>
      </div>
    </div>
  )
}

export default ControlesMapa
