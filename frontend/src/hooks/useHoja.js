import { useEffect, useRef, useState } from 'react'

// Hoja inferior del celular, como la de Apple Maps: se arrastra desde la manija o el
// encabezado y se acomoda en tres alturas. En escritorio no hace nada (panel lateral).
const MOVIL = '(max-width: 820px)'
const ORDEN = ['plegada', 'media', 'alta']
const ASOMADA = 136          // manija + encabezado: se sigue viendo cuántos lugares hay
const UMBRAL_MOVIMIENTO = 6  // px antes de considerar que es arrastre y no toque
const VELOCIDAD_RAPIDA = 0.5 // px/ms: un deslizamiento rápido avanza un paso aunque sea corto

function medir() {
  const alto = window.innerHeight
  return { plegada: ASOMADA, media: Math.round(alto * 0.58), alta: alto - 64 - 56 }
}

const limitar = (v, min, max) => Math.min(max, Math.max(min, v))

export function useHoja() {
  const [movil, setMovil] = useState(() => window.matchMedia(MOVIL).matches)
  const [alturas, setAlturas] = useState(medir)
  const [estado, setEstado] = useState('media')
  const [arrastre, setArrastre] = useState(null)   // alto en px mientras el dedo la mueve
  const gesto = useRef(null)

  useEffect(() => {
    const consulta = window.matchMedia(MOVIL)
    const actualizar = () => { setMovil(consulta.matches); setAlturas(medir()) }
    consulta.addEventListener('change', actualizar)
    window.addEventListener('resize', actualizar)
    return () => {
      consulta.removeEventListener('change', actualizar)
      window.removeEventListener('resize', actualizar)
    }
  }, [])

  function soltar(evento, cancelado) {
    const g = gesto.current
    gesto.current = null
    if (!g?.movido) return
    const dy = evento.clientY - g.y
    const velocidad = dy / Math.max(1, evento.timeStamp - g.t)
    const final = g.alto - dy
    let destino
    if (!cancelado && Math.abs(velocidad) > VELOCIDAD_RAPIDA) {
      const paso = velocidad > 0 ? -1 : 1
      destino = ORDEN[limitar(ORDEN.indexOf(estado) + paso, 0, ORDEN.length - 1)]
    } else {
      destino = ORDEN.reduce((a, b) => (Math.abs(alturas[b] - final) < Math.abs(alturas[a] - final) ? b : a))
    }
    setEstado(destino)
    setArrastre(null)
  }

  const zona = {
    onPointerDown(evento) {
      if (!movil || (evento.pointerType === 'mouse' && evento.button !== 0)) return
      gesto.current = { y: evento.clientY, t: evento.timeStamp, alto: alturas[estado], id: evento.pointerId, movido: false }
    },
    onPointerMove(evento) {
      const g = gesto.current
      if (!g) return
      const dy = evento.clientY - g.y
      if (!g.movido) {
        if (Math.abs(dy) < UMBRAL_MOVIMIENTO) return
        // Se captura hasta aquí para que un toque simple siga llegando a la manija como clic.
        g.movido = true
        evento.currentTarget.setPointerCapture(g.id)
      }
      setArrastre(limitar(g.alto - dy, alturas.plegada, alturas.alta))
    },
    onPointerUp: (evento) => soltar(evento, false),
    onPointerCancel: (evento) => soltar(evento, true),
  }

  return {
    movil,
    estado,
    alto: arrastre ?? alturas[estado],
    arrastrando: arrastre !== null,
    plegada: estado === 'plegada' && arrastre === null,
    // La manija alterna entre plegada y media; también funciona con teclado.
    alternar: () => setEstado((e) => (e === 'plegada' ? 'media' : 'plegada')),
    mostrar: () => setEstado((e) => (e === 'plegada' ? 'media' : e)),
    zona,
    asistenteVisible: estado !== 'alta' || arrastre !== null,
  }
}
