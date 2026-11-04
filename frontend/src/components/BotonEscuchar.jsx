import { useEffect, useState } from 'react'
import { useIdioma } from '../i18n/contexto.js'
import { usePreferencias, VELOCIDAD_VOZ } from '../preferencias/contexto.js'

const HAY_VOZ = typeof window !== 'undefined' && 'speechSynthesis' in window

// Elige una voz del idioma de la app: primero la de México o EE. UU., luego cualquiera del idioma.
function vozPara(idioma) {
  const voces = window.speechSynthesis.getVoices()
  const preferida = idioma === 'en' ? 'en-US' : 'es-MX'
  return voces.find((v) => v.lang.replace('_', '-') === preferida)
    ?? voces.find((v) => v.lang.toLowerCase().startsWith(idioma))
}

// Une las frases con un solo punto entre ellas, aunque alguna ya termine en punto.
const unir = (partes) => partes.filter(Boolean).map((p) => p.trim().replace(/[.\s]+$/, '')).join('. ') + '.'

// "Escuchar" (propuesta §5.2): lee las frases en voz alta con la voz del navegador, sin internet ni
// servicios externos. Si el navegador no tiene síntesis de voz, el botón no aparece.
function BotonEscuchar({ partes }) {
  const texto = unir(partes)
  const { idioma, t } = useIdioma()
  const { voz } = usePreferencias()
  const [hablando, setHablando] = useState(false)

  // Al cambiar de lugar o salir de la pantalla, se calla.
  useEffect(() => () => window.speechSynthesis?.cancel(), [texto])

  if (!HAY_VOZ) return null

  function alternar() {
    const sintesis = window.speechSynthesis
    sintesis.cancel()
    if (hablando) {
      setHablando(false)
      return
    }
    const frase = new SpeechSynthesisUtterance(texto)
    frase.lang = idioma === 'en' ? 'en-US' : 'es-MX'
    frase.voice = vozPara(idioma) ?? null
    frase.rate = VELOCIDAD_VOZ[voz]
    frase.onend = () => setHablando(false)
    frase.onerror = () => setHablando(false)
    setHablando(true)
    sintesis.speak(frase)
  }

  return (
    <button type="button" className="boton escuchar" aria-pressed={hablando} onClick={alternar}>
      <span aria-hidden="true">{hablando ? '■' : '🔊'}</span> {hablando ? t('voz.detener') : t('voz.escuchar')}
    </button>
  )
}

export default BotonEscuchar
