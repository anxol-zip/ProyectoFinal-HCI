import { useState } from 'react'
import { hora } from '../../data/formato.js'
import { ICONO } from '../../data/semaforo.js'
import SelectorLugar from '../SelectorLugar.jsx'
import Semaforo from '../Semaforo.jsx'

// Para la Secretaría, el nombre del color es más directo que el texto del turista.
const COLORES = [['verde', 'Verde'], ['amarillo', 'Amarillo'], ['rojo', 'Rojo']]
const DURACIONES = [
  { horas: 1, texto: '1 h' },
  { horas: 2, texto: '2 h' },
  { horas: 4, texto: '4 h' },
  { horas: 8, texto: '8 h' },
]

// "Fijar color" (RN_16): para cierres, obras o filas que el modelo no ve.
// Gana sobre el cálculo hasta la hora de fin y la app muestra el motivo.
function FijarColor({ puntos, ajustes, onFijar, onQuitar }) {
  const [puntoId, setPuntoId] = useState(puntos[0]?.id ?? '')
  const [color, setColor] = useState('rojo')
  const [motivo, setMotivo] = useState('')
  const [horas, setHoras] = useState(2)
  const [error, setError] = useState(null)

  async function enviar(evento) {
    evento.preventDefault()
    if (motivo.trim().length < 3) return
    try {
      await onFijar({ puntoId, color, motivo: motivo.trim(), horas })
      setMotivo('')
      setError(null)
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <>
      <form className="formulario" onSubmit={enviar}>
        <p className="oculto-accesible" id="etiqueta-fijar">Lugar</p>
        <SelectorLugar
          puntos={puntos}
          valor={puntoId}
          onCambiar={setPuntoId}
          etiquetaId="etiqueta-fijar"
          textos={{ elige: 'Elige un lugar', buscar: 'Busca un lugar o destino', sinResultados: 'No hay lugares con ese nombre.' }}
        />
        <div className="segmentado ancho" role="group" aria-label="Duración">
          {DURACIONES.map((d) => (
            <button key={d.horas} type="button" aria-pressed={horas === d.horas} onClick={() => setHoras(d.horas)}>{d.texto}</button>
          ))}
        </div>
        <label className="oculto-accesible" htmlFor="fijar-motivo">Motivo</label>
        <input id="fijar-motivo" className="campo" maxLength={200} placeholder="Motivo que verá el turista (ej. cerrado por obra)" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
        <div className="colores" role="group" aria-label="Color">
          {COLORES.map(([c, nombre]) => (
            <button key={c} type="button" className={`color-opcion ${c}`} aria-pressed={color === c} onClick={() => setColor(c)}>
              <span className="sem-icono" aria-hidden="true">{ICONO[c]}</span>{nombre}
            </button>
          ))}
        </div>
        <button type="submit" className="boton primario" disabled={motivo.trim().length < 3}>Fijar color</button>
        {error && <p className="aviso info">{error}</p>}
      </form>

      <p className="etiqueta">Ajustes vigentes</p>
      {ajustes.length === 0 && <p className="suave">Ninguno.</p>}
      {ajustes.map((a) => (
        <div key={a.id} className="tarjeta-lugar" style={{ cursor: 'default' }}>
          <div className="tarjeta-fila"><h3>{a.nombre}</h3><Semaforo color={a.color} /></div>
          <p className="detalle">{a.motivo}, hasta las {hora(a.hasta)}.</p>
          <button type="button" className="boton-texto" onClick={() => onQuitar(a.id)}>Quitar ajuste</button>
        </div>
      ))}
    </>
  )
}

export default FijarColor
