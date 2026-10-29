import { useEffect, useState } from 'react'
import { api } from '../api/cliente.js'
import { hora, partesRazon, textoTraslado } from '../data/formato.js'
import { explicacionRec, ficha } from '../i18n/backend.js'
import { useIdioma } from '../i18n/contexto.js'
import Foto from './Foto.jsx'
import Semaforo from './Semaforo.jsx'

const corto = (nombre) => nombre.split(' (')[0]

// En qué se parece la alternativa a lo que el turista busca: sus intereses y el lugar que pidió.
function coincidencias(alt, pedido, intereses) {
  const buscadas = new Set([...intereses, ...(pedido?.categorias ?? [])])
  return alt.categorias.filter((c) => buscadas.has(c))
}

// Por qué la alternativa conviene: su propio estado, el traslado y si es techado.
function porque(alt, idioma, t) {
  const lista = partesRazon(alt.razon, idioma)
  const traslado = textoTraslado(alt.traslado, t)
  if (traslado) lista.push(t('rec.desde', { traslado }))
  if (alt.interior) lista.push(t('rec.techado'))
  if (alt.destino !== 'Cd. Puebla') lista.push(t('rec.comunidad'))
  return lista
}

// T4 — "Mejor ve a…" (CU_04). El backend nunca propone un lugar en rojo (RN_02), siempre da la razón
// (RN_03) y, si conviene, otra hora para el lugar pedido. En inglés, la explicación se arma aquí
// con los mismos datos (el backend la redacta en español).
function Recomendacion({ puntoId, sesionId, origenId, catalogo, intereses, onVolver, onElegir, onPropuesta }) {
  const { idioma, t } = useIdioma()
  const [rec, setRec] = useState(null)
  const [error, setError] = useState(null)
  const [aceptada, setAceptada] = useState(false)

  useEffect(() => {
    let vigente = true
    api.pedirRecomendacion({ sesionId, puntoId, origenId })
      .then((datos) => {
        if (!vigente) return
        setRec(datos)
        if (datos.alternativa) onPropuesta?.(datos.alternativa.id)
      })
      .catch((e) => { if (vigente) setError(e.message) })
    return () => { vigente = false }
  }, [puntoId, sesionId, origenId, onPropuesta])

  async function vamos() {
    // Se abre antes de esperar al servidor: Safari bloquea ventanas abiertas después de un await.
    window.open(rec.alternativa.como_llegar_url, '_blank', 'noopener')
    setAceptada(true)
    await api.responderBusqueda(rec.busqueda_id, true).catch(() => {})
  }

  async function prefieroMiPlan() {
    await api.responderBusqueda(rec.busqueda_id, false).catch(() => {})
    onVolver()
  }

  if (error) return <p className="aviso info">{error}</p>
  if (!rec) return <p className="suave">{t('rec.buscando')}</p>

  const { pedido, alternativa, otra_hora: otraHora } = rec
  const explicacion = idioma === 'en' ? explicacionRec(rec, t) : rec.razon
  const colorOtraHora = otraHora && t(`sem.${otraHora.color}`).toLowerCase()
  const volver = (
    <button type="button" className="boton-texto" onClick={onVolver}>
      {pedido ? t('rec.volverA', { lugar: corto(pedido.nombre) }) : t('rec.volver')}
    </button>
  )

  if (!alternativa) {
    return (
      <div>
        {volver}
        <h2 className="titulo-rec">{rec.motivo ? t('rec.sinAlternativa') : t('rec.estaBien', { lugar: corto(pedido.nombre) })}</h2>
        <p className="aviso info">{explicacion}</p>
        {otraHora && <p className="tip">{t('rec.otraHora', { hora: hora(otraHora.hora), color: colorOtraHora })}</p>}
      </div>
    )
  }

  const descripcion = catalogo.find((p) => p.id === alternativa.id)?.ficha
  const comunes = coincidencias(alternativa, pedido, intereses)

  return (
    <div>
      {volver}
      <h2 className="titulo-rec">{t('rec.titulo', { lugar: corto(alternativa.nombre) })}</h2>
      <p className="secundario">{explicacion}</p>

      <div className="comparacion" style={{ marginTop: 14 }}>
        {pedido && (
          <div className="opcion con-foto">
            <Foto id={pedido.clave} tamano="mini" />
            <div>
              <p className="suave">{t('rec.pediste')}</p>
              <h3>{pedido.nombre}</h3>
              <Semaforo color={pedido.color} />
              {partesRazon(pedido.razon, idioma).slice(0, 2).map((r) => <p key={r} className="secundario" style={{ marginTop: 8, fontSize: 14 }}>{r}</p>)}
            </div>
          </div>
        )}
        <div className="opcion recomendada">
          <Foto id={alternativa.clave} nombre={alternativa.nombre} credito />
          <p className="suave">{t('rec.recomendamos')}</p>
          <h3>{alternativa.nombre}</h3>
          <Semaforo color={alternativa.color} />
          {descripcion && (
            <>
              <p className="etiqueta">{t('rec.encontrar')}</p>
              <p className="descripcion" style={{ marginTop: 0 }}>{ficha(alternativa.clave, descripcion, idioma)}</p>
            </>
          )}
          {comunes.length > 0 && (
            <div className="coincide">
              <span>{t('rec.coincide')}</span>
              {comunes.map((c) => <span key={c} className="insignia">{t(`interes.${c}`)}</span>)}
            </div>
          )}
          <p className="etiqueta">{t('rec.porQue')}</p>
          <ul className="razones" style={{ marginTop: 0 }}>
            {porque(alternativa, idioma, t).map((r) => <li key={r}>{r}</li>)}
          </ul>
        </div>
      </div>

      {otraHora && pedido && (
        <p className="tip">{t('rec.prefieres', { lugar: corto(pedido.nombre), hora: hora(otraHora.hora), color: colorOtraHora })}</p>
      )}

      {aceptada
        ? <p className="aviso exito" style={{ marginTop: 16 }}>{t('rec.buenViaje')}</p>
        : (
          <div className="acciones dos">
            <button type="button" className="boton primario" onClick={vamos}>{t('rec.vamos')}</button>
            <button type="button" className="boton" onClick={prefieroMiPlan}>{t('rec.miPlan')}</button>
          </div>
        )}

      {rec.otras.length > 0 && (
        <>
          <p className="etiqueta">{t('rec.otras')}</p>
          {rec.otras.map((o) => (
            <button key={o.id} type="button" className="tarjeta-lugar con-foto" onClick={() => onElegir(o.id)}>
              <Foto id={o.clave} tamano="mini" />
              <div className="tarjeta-texto">
                <h3>{o.nombre}</h3>
                <div className="meta">
                  <Semaforo color={o.color} />
                  {o.traslado && <span className="meta-fuerte numero">{textoTraslado(o.traslado, t)}</span>}
                </div>
                <p className="detalle">{t(o.interior ? 'rec.techadoEn' : 'rec.aireLibreEn', { destino: o.destino })}</p>
              </div>
            </button>
          ))}
        </>
      )}
    </div>
  )
}

export default Recomendacion
