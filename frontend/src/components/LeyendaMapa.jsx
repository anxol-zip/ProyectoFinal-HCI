import { RAMPA } from '../data/calor.js'
import { ICONO, TEXTO } from '../data/semaforo.js'

const ESTADOS = ['verde', 'amarillo', 'rojo', 'cerrado', 'sin_dato']
const TEXTOS_ES = { titulo: 'Gente ahora', menos: 'Menos', mas: 'Más', semaforo: TEXTO }

// Leyenda corta: qué significa el calor (cuánta gente) y qué significa cada marcador (si conviene ir).
function LeyendaMapa({ className = '', textos = TEXTOS_ES }) {
  return (
    <div className={`leyenda-mapa ${className}`}>
      <p className="leyenda-titulo">{textos.titulo}</p>
      <div className="leyenda-rampa" style={{ background: `linear-gradient(90deg, ${RAMPA.join(', ')})` }} aria-hidden="true" />
      <div className="leyenda-extremos"><span>{textos.menos}</span><span>{textos.mas}</span></div>
      <ul className="leyenda-estados">
        {ESTADOS.map((c) => (
          <li key={c}><span className={`marcador mini ${c}`} aria-hidden="true">{ICONO[c]}</span>{textos.semaforo[c]}</li>
        ))}
      </ul>
    </div>
  )
}

export default LeyendaMapa
