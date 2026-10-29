import { useState } from 'react'
import { api } from '../api/cliente.js'
import Semaforo from './Semaforo.jsx'
import { ICONO } from '../data/semaforo.js'
import { mensajeReporte } from '../i18n/backend.js'
import { useIdioma } from '../i18n/contexto.js'

const NIVELES = [
  { nivel: 1, color: 'verde', texto: 'rep.vacio' },
  { nivel: 2, color: 'amarillo', texto: 'rep.normal' },
  { nivel: 3, color: 'rojo', texto: 'rep.lleno' },
]

// T5 — "¿Cómo está?" (CU_05). Se abre después de "Estoy aquí" (RN_04). El backend aplica los
// filtros (RN_04 a RN_06) y manda el mensaje para el turista y el estado nuevo del punto.
function BotonReporte({ punto, sesionId, distanciaM = null, onCerrar, onReportado }) {
  const { idioma, t } = useIdioma()
  const [resultado, setResultado] = useState(null)
  const [error, setError] = useState(null)
  const [enviando, setEnviando] = useState(false)

  async function reportar(nivel) {
    setEnviando(true)
    try {
      const r = await api.enviarReporte({ sesionId, puntoId: punto.id, nivel, distanciaM })
      setResultado(r)
      if (r.reporte.estado !== 'descartado') onReportado()
    } catch (e) {
      setError(e.message)
    }
    setEnviando(false)
  }

  const aceptado = resultado && resultado.reporte.estado !== 'descartado'

  return (
    <div className="modal-fondo" role="dialog" aria-modal="true" aria-labelledby="titulo-reporte" onClick={onCerrar}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <p className="suave">{t('rep.estasEn')}</p>
        <h2 id="titulo-reporte" style={{ fontSize: 24, margin: '2px 0 6px' }}>{punto.nombre}</h2>

        {!resultado && (
          <>
            <p className="secundario">{t('rep.pregunta')}</p>
            <div className="niveles">
              {NIVELES.map((n) => (
                <button key={n.nivel} type="button" className={`nivel ${n.color}`} disabled={enviando} onClick={() => reportar(n.nivel)}>
                  <span className="sem-icono" aria-hidden="true">{ICONO[n.color]}</span>
                  {t(n.texto)}
                </button>
              ))}
            </div>
          </>
        )}

        {aceptado && (
          <p className="aviso exito" style={{ marginTop: 16 }}>
            {mensajeReporte(resultado.reporte, idioma)} {t('rep.ahora')} <Semaforo color={resultado.punto.color} />
          </p>
        )}
        {resultado && !aceptado && <p className="aviso info" style={{ marginTop: 16 }}>{mensajeReporte(resultado.reporte, idioma)}</p>}
        {error && <p className="aviso info" style={{ marginTop: 16 }}>{error}</p>}

        <div className="acciones">
          <button type="button" className="boton" onClick={onCerrar}>{resultado ? t('rep.listo') : t('rep.cancelar')}</button>
        </div>
      </div>
    </div>
  )
}

export default BotonReporte
