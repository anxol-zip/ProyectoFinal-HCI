import { useEffect, useState } from 'react'
import { api } from '../api/cliente.js'
import { hora } from '../data/formato.js'
import { useIdioma } from '../i18n/contexto.js'
import { IdiomaFijo } from '../i18n/Idioma.jsx'
import FijarColor from '../components/panel/FijarColor.jsx'
import Indicadores from '../components/panel/Indicadores.jsx'
import MapaCalor from '../components/panel/MapaCalor.jsx'
import Redirecciones from '../components/panel/Redirecciones.jsx'
import SemaforoEstatal from '../components/panel/SemaforoEstatal.jsx'
import Umbrales from '../components/panel/Umbrales.jsx'

const RECARGA_MS = 30_000
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

// G1 — Panel de gobierno (CU_07): saturación, a dónde se van los turistas y cuánto dinero llegó.
// Solo agregados (RN_12). En el stand se cuenta la actividad de los evaluadores, rotulada (RN_11).
// Su público es la Secretaría: se queda en español aunque el turista haya elegido inglés.
function Panel() {
  const { t } = useIdioma()
  const nota = t('panel.soloEspanol')
  return (
    <IdiomaFijo idioma="es">
      <ContenidoPanel nota={nota} />
    </IdiomaFijo>
  )
}

function ContenidoPanel({ nota }) {
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)
  const [incluirDemo, setIncluirDemo] = useState(true)
  const [version, setVersion] = useState(0)

  useEffect(() => {
    let vigente = true
    async function cargar() {
      try {
        const d = await api.obtenerPanel({ incluirDemo })
        if (vigente) { setDatos(d); setError(null) }
      } catch (e) {
        if (vigente) setError(e.message)
      }
    }
    cargar()
    const id = setInterval(cargar, RECARGA_MS)
    return () => { vigente = false; clearInterval(id) }
  }, [incluirDemo, version])

  async function fijar(ajuste) {
    await api.fijarColor(ajuste)
    setVersion((v) => v + 1)
  }

  async function quitar(id) {
    await api.quitarAjuste(id)
    setVersion((v) => v + 1)
  }

  if (!datos) return <div className="gobierno"><p className="suave">{error ?? 'Cargando panel…'}</p></div>

  const { afluencia, redirecciones, derrama, estatal, umbrales, ajustes } = datos

  return (
    <div className="gobierno">
      <div className="gobierno-titulo">
        <div>
          <p className="suave">Secretaría de Turismo, zona piloto Puebla–Cholula–Atlixco</p>
          <h1>Panel de hoy</h1>
        </div>
        <div className="gobierno-opciones">
          <label className="interruptor">
            <input type="checkbox" checked={incluirDemo} onChange={(e) => setIncluirDemo(e.target.checked)} />
            Contar la demo del stand
          </label>
          <p className="suave">Solo totales por lugar y hora. Actualizado a las {hora(afluencia.datos.ahora)}.</p>
        </div>
      </div>
      {nota && <p className="aviso info" lang="en" style={{ marginBottom: 16 }}>{nota}</p>}
      {error && <p className="aviso info" style={{ marginBottom: 16 }}>{error}</p>}

      <div className="rejilla">
        <Indicadores hoy={afluencia.hoy} derrama={derrama} />

        <div className="caja c-7">
          <h2>Afluencia ahora</h2>
          <p className="subtitulo">Estimada con datos oficiales y corregida con reportes de turistas</p>
          <MapaCalor puntos={afluencia.puntos} />
        </div>
        <div className="caja c-5">
          <h2>¿A dónde se fueron los turistas?</h2>
          <p className="subtitulo">Alternativas que la app propuso hoy y cuántos turistas las aceptaron</p>
          <Redirecciones filas={redirecciones.filas} />
        </div>

        <div className="caja c-5">
          <h2>Fijar el color de un lugar</h2>
          <p className="subtitulo">Para cierres, obras o filas que el modelo no ve. Gana sobre el cálculo hasta la hora de fin.</p>
          <FijarColor puntos={afluencia.puntos} ajustes={ajustes} onFijar={fijar} onQuitar={quitar} />
        </div>
        <div className="caja c-7">
          <h2>Semáforo estatal de {MESES[estatal.mes - 1]}</h2>
          <p className="subtitulo">{estatal.metodo}</p>
          <SemaforoEstatal destinos={estatal.destinos} />
          <p className="fuente-dato">Fuente: {estatal.fuente}</p>
        </div>

        <div className="caja c-7">
          <h2>Umbrales por lugar</h2>
          <p className="subtitulo">Cada lugar se compara con su propia historia: verde debajo del percentil 60 de sus horas, rojo arriba del 85</p>
          <Umbrales filas={umbrales} />
        </div>
        <div className="caja c-5">
          <h2>Cómo leer la derrama</h2>
          <p className="subtitulo">Dos cifras distintas, cada una con su supuesto</p>
          <p><strong>Redistribuida:</strong> dinero que llegó a otro destino porque el turista aceptó la alternativa.</p>
          <p style={{ marginTop: 10 }}><strong>Nueva estimada:</strong> el turista aceptó la alternativa y después también visitó el lugar que había pedido; esa parada se sumó a su plan.</p>
          <p className="suave" style={{ marginTop: 12 }}>{derrama.supuesto}</p>
          <p className="fuente-dato">Fuente: {derrama.fuente}</p>
        </div>
      </div>
    </div>
  )
}

export default Panel
