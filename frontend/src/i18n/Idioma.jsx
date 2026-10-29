import { useContext, useEffect, useMemo, useState } from 'react'
import { Contexto, crearT } from './contexto.js'

// Idioma de la interfaz (español o inglés). Se recuerda en este navegador; la primera vez
// se toma del idioma del celular, para que un turista extranjero vea inglés desde el inicio.
const CLAVE = 'puebla-ahora:idioma'

function idiomaInicial() {
  try {
    const guardado = localStorage.getItem(CLAVE)
    if (guardado === 'es' || guardado === 'en') return guardado
  } catch { /* sin almacenamiento (ventana privada): se usa el del navegador */ }
  return (navigator.language ?? 'es').toLowerCase().startsWith('es') ? 'es' : 'en'
}

export function ProveedorIdioma({ children }) {
  const [idioma, setIdioma] = useState(idiomaInicial)
  useEffect(() => {
    document.documentElement.lang = idioma
    try { localStorage.setItem(CLAVE, idioma) } catch { /* sin almacenamiento */ }
  }, [idioma])
  const valor = useMemo(() => ({ idioma, setIdioma, t: crearT(idioma) }), [idioma])
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>
}

// Para una parte de la app que se queda en un solo idioma (el panel de la Secretaría).
export function IdiomaFijo({ idioma, children }) {
  const exterior = useContext(Contexto)
  const valor = useMemo(() => ({ ...exterior, idioma, t: crearT(idioma) }), [exterior, idioma])
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>
}
