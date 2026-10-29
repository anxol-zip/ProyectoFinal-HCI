import { useEffect, useState } from 'react'
import { api } from '../api/cliente.js'
import { hora, horarioDeHoy, partesRazon, pesos, textoTraslado } from '../data/formato.js'
import { ICONO } from '../data/semaforo.js'
import { ficha } from '../i18n/backend.js'
import { useIdioma } from '../i18n/contexto.js'
import Foto from './Foto.jsx'
import Semaforo from './Semaforo.jsx'
import Semana from './Semana.jsx'

const LLUVIA = { sin: '☀️', moderada: '🌦', fuerte: '🌧' }

function confianzaTexto(e, t) {
  if (e.color === 'cerrado') return null
  if (e.color === 'sin_dato') return t('conf.sinDato')
  if (e.confianza === 'confirmado por turistas') return t('conf.confirmado', { n: e.n_reportes })
  const base = e.n_reportes ? t('conf.estimadoReportes', { n: e.n_reportes }) : t('conf.estimado')
  const normal = e.normalmente && e.normalmente !== e.color ? ` ${t('conf.normalmente', { color: t(`sem.${e.normalmente}`).toLowerCase() })}` : ''
  return base + normal
}

// "Clima de hace 12 min · tráfico de hace 5 min" (RNF_02); lo que no hay se omite.
function actualizacion(datos, t) {
  const partes = []
  if (datos?.clima_hace_min != null) partes.push(t('datos.clima', { min: datos.clima_hace_min }))
  if (datos?.trafico_hace_min != null) partes.push(t('datos.trafico', { min: datos.trafico_hace_min }))
  return partes.length ? `${t('datos.actualizado')} ${partes.join(' · ')}.` : ''
}

// T3 — Tarjeta del punto (CU_03): qué es, si conviene ir, por qué y cuándo conviene más.
function TarjetaPunto({ puntoId, origenId, onVolver, onAlternativa, onEstoyAqui }) {
  const { idioma, t } = useIdioma()
  const [estado, setEstado] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let vigente = true
    api.obtenerEstadoPunto(puntoId, origenId)
      .then((datos) => { if (vigente) setEstado(datos) })
      .catch((e) => { if (vigente) setError(e.message) })
    return () => { vigente = false }
  }, [puntoId, origenId])

  if (error) return <p className="aviso info">{error}</p>
  if (!estado || estado.id !== puntoId) return <p className="suave">{t('cargando')}</p>

  const conviene = estado.color === 'verde'
  const traslado = textoTraslado(estado.traslado, t)
  const descripcion = estado.ficha && ficha(estado.clave, estado.ficha, idioma)
  const confianza = confianzaTexto(estado, t)

  return (
    <article className="detalle-punto">
      <button type="button" className="boton-texto" onClick={onVolver}>{t('ficha.volver')}</button>
      <Foto id={estado.clave} nombre={estado.nombre} credito />
      <p className="suave" style={{ marginTop: 12 }}>{estado.destino}{estado.es_inah ? t('ficha.inah') : ''}</p>
      <h2>{estado.nombre}</h2>
      <Semaforo color={estado.color} grande />
      {estado.ajuste_manual && <p style={{ marginTop: 10 }}><span className="ajuste-etiqueta">{t('ficha.ajustado', { motivo: estado.ajuste_manual })}</span></p>}
      {(estado.vs_normal === 'mas_lleno' || estado.vs_normal === 'menos_lleno') && (
        <p style={{ marginTop: 10 }}>
          <span className={`vs-normal ${estado.vs_normal}`}>
            {t(`vs.${estado.vs_normal}`)} {estado.ajuste_manual ? t('vs.porSecretaria') : t('vs.porReportes', { n: estado.n_reportes })}
          </span>
        </p>
      )}
      {estado.espera_reportada && (
        <p className="espera">⏱ {t('espera.texto', {
          min: estado.espera_reportada.minutos, n: estado.espera_reportada.n_reportes, hace: estado.espera_reportada.ultima_hace_min,
        })}</p>
      )}
      {descripcion && <p className="descripcion">{descripcion}</p>}

      <ul className="razones">
        {partesRazon(estado.razon, idioma).map((r) => <li key={r}>{r}</li>)}
        {estado.eventos.map((e) => <li key={e}>{t('ficha.hoy', { evento: e })}</li>)}
      </ul>
      {confianza && <p className="suave" style={{ marginTop: 8 }}>{confianza}</p>}

      {estado.proximas_horas.length > 0 && (
        <>
          <p className="etiqueta">{t('ficha.proximas')}</p>
          <div className="pronostico" role="list">
            {estado.proximas_horas.slice(0, 8).map((h) => (
              <div key={h.hora} className={`franja-hora ${h.color}`} role="listitem" title={`${hora(h.hora)}: ${t(`sem.${h.color}`)}`}>
                <span className="numero">{hora(h.hora)}</span>
                <span className={`marcador mini ${h.color}`} aria-hidden="true">{ICONO[h.color]}</span>
                <span className="oculto-accesible">{t(`sem.${h.color}`)}</span>
              </div>
            ))}
          </div>
        </>
      )}
      {estado.hoy && (
        <p className="suave" style={{ marginTop: 8 }}>
          {t('hoy.resumen', { tranquila: estado.hoy.mas_tranquila.hora, llena: estado.hoy.mas_llena.hora })}
        </p>
      )}
      <Semana puntoId={estado.id} />

      {estado.clima.length > 0 && (
        <>
          <p className="etiqueta">{t('ficha.clima')}</p>
          <div className="horas">
            {estado.clima.slice(0, 6).map((c) => (
              <div key={c.hora} className={`hora${c.lluvia !== 'sin' ? ' lluvia' : ''}`}>
                {hora(c.hora)}
                <strong>{LLUVIA[c.lluvia]} {c.prob_lluvia_pct != null ? `${Math.round(c.prob_lluvia_pct)}%` : '—'}</strong>
              </div>
            ))}
          </div>
        </>
      )}

      <p className="etiqueta">{t('ficha.visita')}</p>
      <div className="datos-visita">
        <div className="dato"><span className="suave">{t('ficha.traslado')}</span><strong>{traslado ?? t('ficha.sinCalcular')}</strong></div>
        <div className="dato"><span className="suave">{t('ficha.tiempo')}</span><strong>{estado.duracion_sugerida ?? t('ficha.porConfirmar')}</strong></div>
        <div className="dato"><span className="suave">{t('ficha.horario')}</span><strong>{horarioDeHoy(estado.horario, t)}</strong></div>
        <div className="dato"><span className="suave">{t('ficha.entrada')}</span><strong>{estado.costo_mxn == null ? t('ficha.porConfirmar') : estado.costo_mxn === 0 ? t('ficha.gratis') : pesos(estado.costo_mxn)}</strong></div>
      </div>

      {estado.proximos_eventos.length > 0 && (
        <>
          <p className="etiqueta">{t('ficha.eventos')}</p>
          <ul className="razones">
            {estado.proximos_eventos.map((e) => (
              <li key={e.nombre + e.inicio}>
                <strong>{e.nombre}</strong>
                <span className="suave" style={{ display: 'block' }}>{t('ficha.eventoFechas', { inicio: e.inicio.slice(0, 10), fin: e.fin.slice(0, 10) })}</span>
              </li>
            ))}
          </ul>
        </>
      )}

      <div className={`acciones${conviene ? '' : ' dos'}`}>
        {!conviene && <button type="button" className="boton primario" onClick={onAlternativa}>{t('ficha.mejorVe')}</button>}
        <button type="button" className={`boton${conviene ? ' primario' : ''}`} onClick={onEstoyAqui}>{t('ficha.estoyAqui')}</button>
      </div>
      <a className="boton ancho" style={{ marginTop: 12 }} href={estado.como_llegar_url} target="_blank" rel="noreferrer">{t('ficha.comoLlegar')}</a>
      {estado.fuente && <p className="fuente-dato">{t('ficha.fuente', { fuente: estado.fuente })}</p>}
      <p className="fuente-dato">{actualizacion(estado.datos, t)} {t('datos.metodo')}</p>
    </article>
  )
}

export default TarjetaPunto
