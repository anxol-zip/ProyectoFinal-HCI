const MOTIVO = { afluencia: 'Mucha gente', lluvia: 'Lluvia', cerrado: 'Cerrado', intereses: 'Sus intereses', sin_cambio: 'Sin cambio' }

// ¿A dónde se fueron los turistas? Solo agregados (RN_12).
function Redirecciones({ filas }) {
  if (filas.length === 0) return <p className="suave">Todavía no hay redirecciones hoy. Aparecen cuando un turista pide "Mejor ve a…".</p>
  const maximo = Math.max(1, ...filas.map((f) => f.sugeridas))
  return (
    <div className="tabla-desplazable">
    <table>
      <thead>
        <tr><th>De</th><th>A</th><th>Aceptadas</th><th>Motivo</th></tr>
      </thead>
      <tbody>
        {filas.map((f) => (
          <tr key={`${f.desde_id}-${f.hacia_id}-${f.motivo}`}>
            <td>{f.desde ?? 'Sin lugar pedido'}</td>
            <td>{f.hacia}</td>
            <td style={{ minWidth: 110 }}>
              <span className="numero">{f.aceptadas} de {f.sugeridas}</span>
              <div className="barra" style={{ marginTop: 4 }}><span style={{ width: `${(f.aceptadas / maximo) * 100}%` }} /></div>
            </td>
            <td>{MOTIVO[f.motivo] ?? f.motivo}</td>
          </tr>
        ))}
      </tbody>
    </table>
    </div>
  )
}

export default Redirecciones
