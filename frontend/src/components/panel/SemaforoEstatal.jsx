import Semaforo from '../Semaforo.jsx'

// Los destinos del Observatorio en el mes, cada uno contra su propia historia (capa estructural).
function SemaforoEstatal({ destinos }) {
  return (
    <div className="estatal">
      {destinos.map((d) => (
        <div key={d.destino_id}>
          <span>{d.destino}{d.tipo === 'estimado' && <span className="suave"> (estimado)</span>}</span>
          <Semaforo color={d.color} />
        </div>
      ))}
    </div>
  )
}

export default SemaforoEstatal
