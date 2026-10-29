import Semaforo from '../Semaforo.jsx'

const METODO = { percentil: 'Su historia', general: 'General', manual: 'Manual' }

// Umbrales por lugar: explican por qué un punto está en ese color (turismo_core/semaforo.py).
function Umbrales({ filas }) {
  return (
    <div className="tabla-desplazable">
    <table>
      <thead><tr><th>Lugar</th><th>Verde bajo</th><th>Rojo sobre</th><th>Método</th></tr></thead>
      <tbody>
        {filas.map((u) => (
          <tr key={u.punto_id}>
            <td>{u.nombre}</td>
            {u.bajo == null
              ? <td colSpan={3}><Semaforo color="sin_dato" /> sin historia de afluencia</td>
              : (
                <>
                  <td className="numero">{u.bajo.toFixed(2)}</td>
                  <td className="numero">{u.alto.toFixed(2)}</td>
                  <td>{METODO[u.metodo] ?? u.metodo}{u.n_muestras ? ` (${u.n_muestras.toLocaleString('es-MX')} horas)` : ''}</td>
                </>
              )}
          </tr>
        ))}
      </tbody>
    </table>
    </div>
  )
}

export default Umbrales
