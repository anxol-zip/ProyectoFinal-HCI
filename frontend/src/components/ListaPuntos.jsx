import { partesRazon, textoTraslado } from '../data/formato.js'
import { useIdioma } from '../i18n/contexto.js'
import Foto from './Foto.jsx'
import Semaforo from './Semaforo.jsx'

// Lista ordenada por conveniencia (T2): primero lo que está en buen momento,
// luego lo que coincide con tus intereses; lo cerrado, al final.
function ListaPuntos({ puntos, seleccionadoId, onSeleccionar }) {
  const { idioma, t } = useIdioma()
  return (
    <div>
      {puntos.map((p) => (
        <button
          key={p.id}
          type="button"
          className={`tarjeta-lugar con-foto${p.color === 'cerrado' ? ' apagada' : ''}`}
          aria-current={p.id === seleccionadoId}
          onClick={() => onSeleccionar(p.id)}
        >
          <Foto id={p.clave} tamano="mini" />
          <div className="tarjeta-texto">
            <h3>{p.nombre}</h3>
            <div className="meta">
              <Semaforo color={p.color} />
              {p.traslado && <span className="meta-fuerte numero">{textoTraslado(p.traslado, t)}</span>}
              <span>{p.destino}</span>
            </div>
            <p className="detalle">{partesRazon(p.razon, idioma)[0]}</p>
            {(p.confianza === 'confirmado por turistas' || p.ajuste_manual) && (
              <div className="meta">
                {p.confianza === 'confirmado por turistas' && <span className="insignia">{t('lista.confirmado')}</span>}
                {p.ajuste_manual && <span className="ajuste-etiqueta">{t('lista.ajustado')}</span>}
              </div>
            )}
          </div>
        </button>
      ))}
    </div>
  )
}

export default ListaPuntos
