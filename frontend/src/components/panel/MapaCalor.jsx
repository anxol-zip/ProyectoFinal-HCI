import { MapContainer, Marker, TileLayer } from 'react-leaflet'
import { TEXTO } from '../../data/semaforo.js'
import { CAPAS } from '../capaBase.js'
import CapaCalor from '../CapaCalor.jsx'
import ControlesMapa from '../ControlesMapa.jsx'
import Encuadrar from '../Encuadrar.jsx'
import LeyendaMapa from '../LeyendaMapa.jsx'
import { iconoSemaforo } from '../marcadores.js'

// La leyenda ocupa la esquina superior derecha en escritorio.
const margenesPanel = (t) => (t.x <= 520 ? { arribaIzq: [24, 24], abajoDer: [24, 90] } : { arribaIzq: [24, 24], abajoDer: [230, 24] })

// Afluencia ahora (estimada + reportes): la misma capa de calor y el mismo semáforo que ve el turista.
function MapaCalor({ puntos }) {
  return (
    <div className="mapa-caja">
      <div className="mapa">
        <MapContainer center={[19.04, -98.27]} zoom={11} zoomControl={false} scrollWheelZoom={false} style={{ height: '100%', width: '100%' }}>
          {CAPAS.map((c) => <TileLayer key={c.url} {...c} />)}
          <CapaCalor puntos={puntos} />
          {puntos.map((p) => (
            <Marker
              key={p.id}
              position={[p.lat, p.lon]}
              icon={iconoSemaforo(p.color, { tamano: 24 })}
              title={`${p.nombre}: ${TEXTO[p.color]}${p.nivel != null ? ` (${p.nivel.toFixed(2)} veces lo normal)` : ''}`}
              alt={`${p.nombre}: ${TEXTO[p.color]}`}
            />
          ))}
          <Encuadrar puntos={puntos} margenes={margenesPanel} />
          <ControlesMapa textos={{ acercar: 'Acercar', alejar: 'Alejar' }} />
        </MapContainer>
        <LeyendaMapa className="en-caja" />
      </div>
    </div>
  )
}

export default MapaCalor
