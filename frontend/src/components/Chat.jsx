import { useState } from 'react'
import { api } from '../api/cliente.js'
import { useIdioma } from '../i18n/contexto.js'
import Semaforo from './Semaforo.jsx'

// El modelo cita sus fuentes como [punto-12]; en pantalla se numeran [1], [2]… en el orden
// de la lista de fuentes que arma el backend (RN_10).
function numerarCitas(texto, fuentes) {
  const numero = Object.fromEntries(fuentes.map((f, i) => [f.id, i + 1]))
  return texto.replace(/\s?\[([\w.-]+)\]/g, (cita, id) => (numero[id] ? ` [${numero[id]}]` : ''))
}

// T6 — Asistente (CU_06). Solo responde con los datos que le pasa el backend y cita sus fuentes (RN_10).
function Chat({ sesionId, origenId, onCerrar }) {
  const { t } = useIdioma()
  const [mensajes, setMensajes] = useState([{ de: 'asistente', clave: 'chat.hola' }])
  const [texto, setTexto] = useState('')
  const [pensando, setPensando] = useState(false)

  async function preguntar(pregunta) {
    if (pregunta.trim().length < 3 || pensando) return
    setMensajes((m) => [...m, { de: 'usuario', texto: pregunta }])
    setTexto('')
    setPensando(true)
    try {
      const r = await api.preguntarAsistente({ sesionId, pregunta, origenId })
      setMensajes((m) => [...m, { de: 'asistente', texto: numerarCitas(r.respuesta, r.fuentes), fuentes: r.fuentes, estado: r.estado_usado }])
    } catch (e) {
      // 503: Ollama apagado o sin el modelo en la laptop. El detalle técnico va a la consola, no al turista.
      console.warn('Asistente:', e.message)
      const disponible = !e.message.startsWith('El asistente no está disponible')
      setMensajes((m) => [...m, disponible ? { de: 'asistente', texto: e.message, error: true } : { de: 'asistente', clave: 'chat.noDisponible', error: true }])
    }
    setPensando(false)
  }

  function enviar(evento) {
    evento.preventDefault()
    preguntar(texto)
  }

  return (
    <aside className="chat" aria-label="Asistente">
      <div className="chat-encabezado">
        <span className="orbe" aria-hidden="true" />
        <div>
          <h2>{t('chat.titulo')}</h2>
          <p className="suave">{t('chat.sub')}</p>
        </div>
        <button type="button" className="boton-icono" style={{ marginLeft: 'auto' }} onClick={onCerrar} aria-label={t('chat.cerrar')}>✕</button>
      </div>

      {t('chat.nota') && <p className="chat-nota">{t('chat.nota')}</p>}
      <div className="mensajes" aria-live="polite">
        {mensajes.map((m, i) => (
          <div key={i} className={`mensaje ${m.de}${m.error ? ' con-error' : ''}`}>
            {m.clave ? t(m.clave) : m.texto}
            {m.fuentes?.length > 0 && (
              <ol className="fuentes">
                {m.fuentes.map((f) => (
                  <li key={f.id}>{f.url ? <a href={f.url} target="_blank" rel="noreferrer">{f.titulo}</a> : f.titulo}</li>
                ))}
              </ol>
            )}
            {m.estado?.length > 0 && (
              <details>
                <summary>{t('chat.datos')}</summary>
                <table>
                  <thead><tr><th>{t('chat.lugar')}</th><th>{t('chat.estado')}</th></tr></thead>
                  <tbody>
                    {m.estado.map((e) => (
                      <tr key={e.id}><td>{e.nombre}</td><td><Semaforo color={e.color} /></td></tr>
                    ))}
                  </tbody>
                </table>
              </details>
            )}
          </div>
        ))}
        {pensando && <div className="mensaje asistente suave">{t('chat.pensando')}</div>}
      </div>

      <div className="sugerencias">
        {t('chat.sugerencias').map((s) => <button key={s} type="button" disabled={pensando} onClick={() => preguntar(s)}>{s}</button>)}
      </div>
      <form className="chat-entrada" onSubmit={enviar}>
        <label htmlFor="pregunta" className="oculto-accesible">{t('chat.pregunta')}</label>
        <input id="pregunta" value={texto} maxLength={500} onChange={(e) => setTexto(e.target.value)} placeholder={t('chat.placeholder')} />
        <button type="submit" aria-label={t('chat.enviar')} disabled={pensando}>↑</button>
      </form>
    </aside>
  )
}

export default Chat
