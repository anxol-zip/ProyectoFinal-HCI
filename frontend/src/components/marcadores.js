import L from 'leaflet'
import { ICONO } from '../data/semaforo.js'

// Marcador del semáforo: color + ícono (nunca solo color, WCAG). Lo usan el mapa
// del turista y el del panel.
// "propuesto" es la alternativa de "Mejor ve a…": borde rosa para distinguirla del lugar pedido.
export function iconoSemaforo(color, { seleccionado = false, propuesto = false, tamano = 34 } = {}) {
  const t = seleccionado ? Math.round(tamano * 1.3) : tamano
  const clases = `marcador ${color}${seleccionado ? ' seleccionado' : ''}${propuesto ? ' propuesto' : ''}`
  return L.divIcon({
    className: '',
    html: `<div class="${clases}" style="width:${t}px;height:${t}px">${ICONO[color]}</div>`,
    iconSize: [t, t],
    iconAnchor: [t / 2, t / 2],
  })
}
