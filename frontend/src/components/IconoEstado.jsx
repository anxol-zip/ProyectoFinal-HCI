import { FORMA } from '../data/formas.js'
import { ICONO } from '../data/semaforo.js'

// Ícono de un estado del semáforo: forma + color + símbolo. Es decorativo (aria-hidden):
// el nombre del estado siempre va en texto al lado. Su tamaño lo da el CSS de quien lo usa.
function IconoEstado({ color, className = '' }) {
  const f = FORMA[color] ?? FORMA.sin_dato
  return (
    <svg className={`forma ${color} ${className}`} viewBox="0 0 40 40" aria-hidden="true" focusable="false">
      <path d={f.d} />
      <text x="20" y={f.y}>{ICONO[color]}</text>
    </svg>
  )
}

export default IconoEstado
