import { useState } from 'react'
import { api } from '../api/cliente.js'
import { useIdioma } from '../i18n/contexto.js'

// "¿Cuándo me conviene ir?" — tabla día × hora de los próximos días, como el pronóstico de Kioto
// (docs: nota 15 de la bóveda). Es la estimación sin reportes (GET /api/puntos/{id}/semana) y se carga
// solo al pedirla.
function Semana({ puntoId }) {
  const { idioma, t } = useIdioma()
  const [semana, setSemana] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState(null)

  async function ver() {
    setCargando(true)
    try { setSemana(await api.obtenerSemana(puntoId)) } catch (e) { setError(e.message) }
    setCargando(false)
  }

  if (!semana) {
    return (
      <>
        <button type="button" className="boton ancho" style={{ marginTop: 12 }} onClick={ver} disabled={cargando}>
          {cargando ? t('cargando') : t('semana.ver')}
        </button>
        {error && <p className="aviso info">{error}</p>}
      </>
    )
  }

  const horas = [...new Set(semana.dias.flatMap((d) => d.horas.map((h) => h.hora)))].sort()
  const dia = (fecha) => new Date(`${fecha}T12:00`).toLocaleDateString(idioma === 'en' ? 'en-US' : 'es-MX', { weekday: 'short', day: 'numeric' })

  return (
    <section className="semana" aria-label={t('semana.titulo')}>
      <p className="etiqueta">{t('semana.titulo')}</p>
      {horas.length === 0 ? <p className="suave">{t('semana.sinDatos')}</p> : (
        <div className="semana-tabla" role="table">
          <div className="semana-fila encabezado" role="row">
            <span role="columnheader" />
            {horas.map((h) => <span key={h} role="columnheader" className="numero">{h.slice(0, 2)}</span>)}
          </div>
          {semana.dias.map((d) => {
            const porHora = Object.fromEntries(d.horas.map((h) => [h.hora, h]))
            return (
              <div key={d.fecha} className="semana-fila" role="row">
                <span role="rowheader" className="semana-dia">{dia(d.fecha)}</span>
                {horas.map((h) => {
                  const celda = porHora[h]
                  const clase = celda ? `${celda.color}${celda.pasada ? ' pasada' : ''}` : 'cerrado'
                  const texto = celda ? t(`sem.${celda.color}`) : t('sem.cerrado')
                  return <span key={h} role="cell" className={`semana-celda ${clase}`} title={`${dia(d.fecha)} ${h}: ${texto}`}>
                    <span className="oculto-accesible">{h} {texto}</span>
                  </span>
                })}
              </div>
            )
          })}
        </div>
      )}
      <ul className="semana-resumen">
        {semana.dias.filter((d) => d.resumen).slice(0, 3).map((d) => (
          <li key={d.fecha}>
            <strong>{dia(d.fecha)}:</strong> {t('semana.tranquila', { hora: d.resumen.mas_tranquila.hora })} · {t('semana.llena', { hora: d.resumen.mas_llena.hora })}
          </li>
        ))}
      </ul>
      <p className="fuente-dato">{t('semana.nota')}</p>
    </section>
  )
}

export default Semana
