import { cuenta, pesos } from '../../data/formato.js'

// Indicadores de hoy. La derrama va en dos cifras, cada una con su supuesto (RN_14).
function Indicadores({ hoy, derrama }) {
  const sugeridas = hoy.redirecciones_sugeridas
  const aceptadas = hoy.redirecciones_aceptadas
  const tasa = sugeridas ? Math.round((aceptadas / sugeridas) * 100) : 0
  const destinos = derrama.por_destino.length
  return (
    <>
      <div className="caja kpi">
        <h2>Redirecciones aceptadas</h2>
        <p className="valor numero">{aceptadas}</p>
        <p className="suave">{sugeridas ? `de ${cuenta(sugeridas, 'alternativa propuesta', 'alternativas propuestas')} (${tasa}%)` : 'Todavía no hay alternativas propuestas hoy'}</p>
      </div>
      <div className="caja kpi">
        <h2>Derrama redistribuida</h2>
        <p className="valor numero">{pesos(derrama.redistribuida_mxn)}</p>
        <p className="suave">{destinos ? `hacia ${destinos} ${destinos === 1 ? 'destino' : 'destinos'}, con el gasto por visitante de cada uno` : 'Gasto por visitante del Observatorio'}</p>
      </div>
      <div className="caja kpi destacado">
        <h2>Derrama nueva estimada</h2>
        <p className="valor numero">{pesos(derrama.nueva_estimada_mxn)}</p>
        <p className="suave">Paradas que los turistas sumaron a su plan</p>
      </div>
      <div className="caja kpi">
        <h2>Reportes de turistas</h2>
        <p className="valor numero">{hoy.reportes_por_estado.valido}</p>
        <p className="suave">{hoy.reportes_por_estado.valido === 1 ? 'válido' : 'válidos'}, {cuenta(hoy.reportes_por_estado.dudoso, 'dudoso', 'dudosos')} y {cuenta(hoy.reportes_por_estado.descartado, 'descartado', 'descartados')}</p>
      </div>
    </>
  )
}

export default Indicadores
