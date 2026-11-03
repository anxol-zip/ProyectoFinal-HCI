import { partesRazon, textoTraslado } from '../data/formato.js'
import { useIdioma } from '../i18n/contexto.js'
import IconoEstado from './IconoEstado.jsx'

// Grupos de la vista ampliada, en el orden en que conviene leerlos. Sin dato y cerrado van juntos:
// ninguno de los dos es una opción para ir ahora.
const GRUPOS = [
  { id: 'verde', colores: ['verde'] },
  { id: 'amarillo', colores: ['amarillo'] },
  { id: 'rojo', colores: ['rojo'] },
  { id: 'otros', colores: ['sin_dato', 'cerrado'] },
]

// Vista ampliada de la barra lateral (D4 de la propuesta): todos los lugares a la vez, agrupados
// por estado, para comparar sin hacer scroll ni recordar lo que ya se vio (Nielsen: reconocer antes
// que recordar; Gestalt: proximidad y similitud).
function TodosLosLugares({ puntos, seleccionadoId, onSeleccionar }) {
  const { idioma, t } = useIdioma()
  return (
    <div className="todos">
      {GRUPOS.map((g) => {
        const lugares = puntos.filter((p) => g.colores.includes(p.color))
        if (lugares.length === 0) return null
        const titulo = g.id === 'otros' ? t('todos.otros') : t(`sem.${g.id}`)
        return (
          <section key={g.id} className={`grupo-estado ${g.id}`} aria-labelledby={`grupo-${g.id}`}>
            <h3 id={`grupo-${g.id}`}>
              <IconoEstado color={g.colores[0]} />
              {titulo} <span className="cuenta">{lugares.length}</span>
            </h3>
            <ul>
              {lugares.map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    className={`lugar-compacto${p.color === 'cerrado' ? ' apagado' : ''}`}
                    data-punto={p.id}
                    aria-current={p.id === seleccionadoId}
                    title={p.nombre}
                    onClick={() => onSeleccionar(p.id)}
                  >
                    {g.id === 'otros' && <IconoEstado color={p.color} />}
                    <span className="lugar-texto">
                      <strong>{p.nombre}</strong>
                      <span className="lugar-meta">
                        {p.traslado ? `${textoTraslado(p.traslado, t)} · ` : ''}{p.destino}
                      </span>
                      <span className="oculto-accesible">{t(`sem.${p.color}`)}. {partesRazon(p.razon, idioma)[0]}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )
      })}
    </div>
  )
}

export default TodosLosLugares
