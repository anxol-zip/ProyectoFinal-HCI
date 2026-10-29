import { ICONO } from '../data/semaforo.js'
import { useIdioma } from '../i18n/contexto.js'

// Etiqueta del semáforo: color + ícono + texto.
function Semaforo({ color, grande = false }) {
  const { t } = useIdioma()
  return (
    <span className={`sem ${color}${grande ? ' grande' : ''}`}>
      <span className="sem-icono" aria-hidden="true">{ICONO[color]}</span>
      {t(`sem.${color}`)}
    </span>
  )
}

export default Semaforo
