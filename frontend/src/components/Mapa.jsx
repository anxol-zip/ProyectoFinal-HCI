import { useCallback, useEffect, useMemo, useRef } from 'react'
import L from 'leaflet'
import { Circle, MapContainer, Marker, TileLayer, Tooltip, useMap } from 'react-leaflet'
import { CAPAS } from './capaBase.js'
import CapaCalor from './CapaCalor.jsx'
import ControlesMapa from './ControlesMapa.jsx'
import LeyendaMapa from './LeyendaMapa.jsx'
import { iconoSemaforo } from './marcadores.js'

const RADIO_INICIAL_M = 2000     // al entrar: tu ubicación y lo que hay alrededor
const RADIO_CERCA_M = 800        // el lugar elegido está donde ya estás
const ZOOM_GPS = 16              // al centrar en tu ubicación real
const ICONO_YO = L.divIcon({ className: '', html: '<div class="marcador-yo"></div>', iconSize: [22, 22], iconAnchor: [11, 11] })

// Lo que tapan el panel (escritorio) o la hoja inferior (celular), para encuadrar en lo que se ve.
function margenes(tamano, margenInferior) {
  if (tamano.x <= 820) return { paddingTopLeft: [32, 96], paddingBottomRight: [64, margenInferior + 32] }
  return { paddingTopLeft: [456, 64], paddingBottomRight: [96, 64] }
}

// Mueve la cámara: al entrar, a tu ubicación; al elegir un lugar, a ti y al lugar (y a la
// alternativa, si la hay); con una lectura nueva del GPS, a esa posición. Al volver a la lista
// se queda donde está. Si el GPS falla no se mueve: no hay posición de respaldo.
function Camara({ yo, enfoque, margenInferior, gps }) {
  const mapa = useMap()
  // La hoja cambia de alto al arrastrarla: se guarda en un ref para usar el valor más
  // reciente al encuadrar, sin volver a encuadrar cada vez que se mueve.
  const inferior = useRef(margenInferior)
  useEffect(() => { inferior.current = margenInferior }, [margenInferior])
  const inicio = useRef(false)

  const encuadrar = useCallback((latlngs, animar) => {
    let limites = latlngs.length === 1 ? L.latLng(latlngs[0]).toBounds(RADIO_INICIAL_M) : L.latLngBounds(latlngs)
    // Si el lugar elegido es donde ya estás, no hay nada que encuadrar: se muestran sus alrededores.
    if (limites.getNorthEast().distanceTo(limites.getSouthWest()) < 300) limites = limites.getCenter().toBounds(RADIO_CERCA_M)
    const opciones = { ...margenes(mapa.getSize(), inferior.current), maxZoom: 16 }
    if (animar) mapa.flyToBounds(limites, { ...opciones, duration: 0.8 })
    else mapa.fitBounds(limites, opciones)
  }, [mapa])

  useEffect(() => {
    if (!yo || inicio.current) return
    inicio.current = true
    encuadrar([yo], false)
  }, [yo, encuadrar])

  useEffect(() => {
    if (yo && enfoque.length > 0) encuadrar([yo, ...enfoque], true)
  }, [enfoque, yo, encuadrar])

  // Una lectura nueva del GPS (cada lectura es un objeto nuevo): se centra ahí. Si es aproximada, se
  // encuadra su círculo de precisión completo en vez de acercarse como si fuera exacta.
  useEffect(() => {
    if (!gps) return
    const centro = L.latLng(gps.lat, gps.lon)
    const opciones = { ...margenes(mapa.getSize(), inferior.current), maxZoom: ZOOM_GPS, duration: 0.8 }
    if (gps.precision > 150) mapa.flyToBounds(centro.toBounds(gps.precision * 2), opciones)
    else mapa.flyToBounds(centro.toBounds(RADIO_CERCA_M / 2), opciones)
  }, [gps, mapa])

  return null
}

// Mapa del turista: calor de afluencia abajo, semáforo encima y tu ubicación.
// "Tu ubicación" es la del GPS si el turista la pidió y el navegador la dio con buena precisión
// (`gps`, ya filtrado en Turista); si no, el lugar que eligió en el inicio. Una ubicación aproximada
// (Wi-Fi o IP, kilómetros de error) no mueve el mapa: es lo que lo mandaba "a otro lado".
// Las coordenadas se quedan en el celular: nunca se envían (RN_07).
function Mapa({ puntos, seleccionadoId, destacadoId, origen, gps, buscando, onUbicar, aviso, margenInferior, onSeleccionar, textos }) {
  const yo = gps ? [gps.lat, gps.lon] : (origen ? [origen.lat, origen.lon] : null)
  const seleccionado = puntos.find((p) => p.id === seleccionadoId)
  const destacado = puntos.find((p) => p.id === destacadoId)
  // Depende solo de coordenadas: recargar el semáforo cada minuto no vuelve a mover la cámara.
  const [sLat, sLon, dLat, dLon] = [seleccionado?.lat, seleccionado?.lon, destacado?.lat, destacado?.lon]
  const enfoque = useMemo(
    () => [[sLat, sLon], [dLat, dLon]].filter(([lat]) => lat != null),
    [sLat, sLon, dLat, dLon],
  )

  return (
    <div className="mapa" aria-label={textos.etiqueta}>
      <MapContainer center={[19.04, -98.2]} zoom={13} zoomControl={false} style={{ height: '100%', width: '100%' }}>
        {CAPAS.map((c) => <TileLayer key={c.url} {...c} />)}
        <CapaCalor puntos={puntos} />
        {puntos.map((p) => {
          const elegido = p.id === seleccionadoId
          const propuesto = p.id === destacadoId
          return (
            <Marker
              key={p.id}
              position={[p.lat, p.lon]}
              icon={iconoSemaforo(p.color, { seleccionado: elegido || propuesto, propuesto })}
              title={`${p.nombre}: ${textos.semaforo[p.color]}`}
              alt={`${p.nombre}: ${textos.semaforo[p.color]}`}
              zIndexOffset={elegido || propuesto ? 1000 : 0}
              eventHandlers={{ click: () => onSeleccionar(p.id) }}
            >
              {(elegido || propuesto) && (
                <Tooltip permanent direction="top" offset={[0, -24]} className={`etiqueta-mapa${propuesto ? ' propuesta' : ''}`}>
                  {p.nombre.split(' (')[0]}
                </Tooltip>
              )}
            </Marker>
          )
        })}
        {gps && (
          <Circle
            center={[gps.lat, gps.lon]}
            radius={gps.precision}
            className="precision-gps"
            pathOptions={{ color: '#e4007c', weight: 1, fillOpacity: 0.08 }}
            interactive={false}
          />
        )}
        {yo && (
          <Marker position={yo} icon={ICONO_YO} title={gps ? textos.tu : textos.elegido} alt={gps ? textos.tu : textos.elegido}
            zIndexOffset={2000} interactive={false} keyboard={false} />
        )}
        <Camara yo={yo} enfoque={enfoque} margenInferior={margenInferior} gps={gps} />
        <ControlesMapa onUbicar={onUbicar} buscando={buscando} textos={textos.controles} />
      </MapContainer>
      <LeyendaMapa textos={textos.leyenda} />
      {aviso && <p key={aviso.id} className="aviso-mapa" role="status">{aviso.texto}</p>}
    </div>
  )
}

export default Mapa
