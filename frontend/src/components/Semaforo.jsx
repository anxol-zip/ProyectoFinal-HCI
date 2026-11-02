import { useIdioma } from '../i18n/contexto.js'
import IconoEstado from './IconoEstado.jsx'

// Etiqueta del semáforo: forma + color + ícono + texto.
function Semaforo({ color, grande = false }) {
  const { t } = useIdioma()
  return (
    <span className={`sem ${color}${grande ? ' grande' : ''}`}>
      <IconoEstado color={color} />
      {t(`sem.${color}`)}
    </span>
  )
}

export default Semaforo
