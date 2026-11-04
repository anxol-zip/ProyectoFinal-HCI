import { useEffect, useRef, useState } from 'react'
import { useIdioma } from '../i18n/contexto.js'
import { COLORES, CONTRASTES, TAMANOS, usePreferencias, VOCES } from '../preferencias/contexto.js'
import IconoEstado from './IconoEstado.jsx'

const MUESTRA = ['verde', 'amarillo', 'rojo']
const HAY_VOZ = typeof window !== 'undefined' && 'speechSynthesis' in window

// Botón "Aa" de la cabecera: tamaño de letra, colores, contraste, voz e idioma, visible en todas las
// pantallas (en celular con letra grande, el idioma solo cabe aquí). Se cierra con Escape, con
// "Listo" o tocando fuera, y el foco vuelve al botón.
function OpcionesLectura() {
  const { idioma, setIdioma, t } = useIdioma()
  const { letra, setLetra, colores, setColores, contraste, setContraste, voz, setVoz } = usePreferencias()
  const [abierto, setAbierto] = useState(false)
  const boton = useRef(null)
  const panel = useRef(null)

  function cerrar() {
    setAbierto(false)
    boton.current?.focus()
  }

  useEffect(() => {
    if (!abierto) return undefined
    // Al abrir, el foco va a la opción elegida: con teclado se cambia sin buscarla.
    panel.current?.querySelector('[aria-pressed="true"]')?.focus()
    const conTecla = (e) => {
      if (e.key !== 'Escape') return
      setAbierto(false)
      boton.current?.focus()
    }
    const conToque = (e) => {
      if (!panel.current?.contains(e.target) && !boton.current?.contains(e.target)) setAbierto(false)
    }
    document.addEventListener('keydown', conTecla)
    document.addEventListener('pointerdown', conToque)
    return () => {
      document.removeEventListener('keydown', conTecla)
      document.removeEventListener('pointerdown', conToque)
    }
  }, [abierto])

  return (
    <div className="lectura">
      <button
        ref={boton}
        type="button"
        className="boton-lectura"
        aria-expanded={abierto}
        aria-controls="opciones-lectura"
        aria-label={t('lectura.boton')}
        title={t('lectura.boton')}
        onClick={() => setAbierto((a) => !a)}
      >
        <span aria-hidden="true">A<small>a</small></span>
      </button>

      {abierto && (
        <div id="opciones-lectura" ref={panel} className="opciones-lectura" role="dialog" aria-labelledby="titulo-lectura">
          <h2 id="titulo-lectura">{t('lectura.titulo')}</h2>

          <p className="etiqueta" id="etiqueta-letra">{t('lectura.letra')}</p>
          <div className="tamanos" role="group" aria-labelledby="etiqueta-letra">
            {TAMANOS.map((n) => (
              <button key={n} type="button" aria-pressed={letra === n} onClick={() => setLetra(n)}>
                <span className={`muestra-letra ${n}`} aria-hidden="true">A</span>
                {t(`lectura.${n}`)}
              </button>
            ))}
          </div>

          <p className="etiqueta" id="etiqueta-colores">{t('lectura.colores')}</p>
          <div className="paletas" role="group" aria-labelledby="etiqueta-colores">
            {COLORES.map((c) => (
              // data-colores en el botón: cada opción muestra sus propios colores, sin importar cuál esté activa.
              <button key={c} type="button" data-colores={c} aria-pressed={colores === c} onClick={() => setColores(c)}>
                <span className="muestra-colores" aria-hidden="true">
                  {MUESTRA.map((m) => <IconoEstado key={m} color={m} />)}
                </span>
                {t(`lectura.${c}`)}
              </button>
            ))}
          </div>
          <p className="ayuda">{t('lectura.ayudaColores')}</p>

          <p className="etiqueta" id="etiqueta-contraste">{t('lectura.contraste')}</p>
          <div className="idiomas" role="group" aria-labelledby="etiqueta-contraste">
            {CONTRASTES.map((c) => (
              <button key={c} type="button" aria-pressed={contraste === c} onClick={() => setContraste(c)}>
                {t(`lectura.contraste_${c}`)}
              </button>
            ))}
          </div>

          {HAY_VOZ && (
            <>
              <p className="etiqueta" id="etiqueta-voz">{t('lectura.voz')}</p>
              <div className="idiomas" role="group" aria-labelledby="etiqueta-voz">
                {VOCES.map((v) => (
                  <button key={v} type="button" aria-pressed={voz === v} onClick={() => setVoz(v)}>{t(`lectura.voz_${v}`)}</button>
                ))}
              </div>
            </>
          )}

          <p className="etiqueta" id="etiqueta-idioma">Idioma · Language</p>
          <div className="idiomas" role="group" aria-labelledby="etiqueta-idioma">
            <button type="button" lang="es" aria-pressed={idioma === 'es'} onClick={() => setIdioma('es')}>Español</button>
            <button type="button" lang="en" aria-pressed={idioma === 'en'} onClick={() => setIdioma('en')}>English</button>
          </div>

          <button type="button" className="boton primario ancho" onClick={cerrar}>{t('lectura.listo')}</button>
          <p className="nota-guardado">{t('lectura.guardado')}</p>
        </div>
      )}
    </div>
  )
}

export default OpcionesLectura
