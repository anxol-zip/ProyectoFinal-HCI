import { useEffect, useMemo, useState } from 'react'
import { COLORES, CONTRASTES, Contexto, TAMANOS, VOCES } from './contexto.js'

// Preferencias para ver mejor: tamaño de letra, colores del semáforo, contraste y velocidad de la
// voz. Se recuerdan en este dispositivo, sin cuenta (igual que el idioma). Las visuales se aplican
// como atributos de <html> (data-letra, data-colores y data-contraste) y el CSS hace el resto.
const CLAVE = 'puebla-ahora:preferencias'
// Si el sistema ya pide más contraste (prefers-contrast), la app arranca en contraste alto.
const pideContraste = () => window.matchMedia?.('(prefers-contrast: more)').matches
const INICIALES = { letra: 'normal', colores: 'habituales', contraste: 'normal', voz: 'normal' }

function leerGuardadas() {
  try {
    const guardadas = JSON.parse(localStorage.getItem(CLAVE)) ?? {}
    return {
      letra: TAMANOS.includes(guardadas.letra) ? guardadas.letra : INICIALES.letra,
      colores: COLORES.includes(guardadas.colores) ? guardadas.colores : INICIALES.colores,
      contraste: CONTRASTES.includes(guardadas.contraste) ? guardadas.contraste : (pideContraste() ? 'alto' : 'normal'),
      voz: VOCES.includes(guardadas.voz) ? guardadas.voz : INICIALES.voz,
    }
  } catch {
    return { ...INICIALES, contraste: pideContraste() ? 'alto' : 'normal' }   // sin almacenamiento o dato dañado
  }
}

function aplicar({ letra, colores, contraste }) {
  document.documentElement.dataset.letra = letra
  document.documentElement.dataset.colores = colores
  document.documentElement.dataset.contraste = contraste
}

export function ProveedorPreferencias({ children }) {
  // Se aplican desde el primer render, para que la página no aparezca un instante con letra normal.
  const [preferencias, setPreferencias] = useState(() => {
    const guardadas = leerGuardadas()
    aplicar(guardadas)
    return guardadas
  })

  useEffect(() => {
    aplicar(preferencias)
    try { localStorage.setItem(CLAVE, JSON.stringify(preferencias)) } catch { /* sin almacenamiento */ }
  }, [preferencias])

  const valor = useMemo(() => ({
    ...preferencias,
    setLetra: (letra) => setPreferencias((p) => ({ ...p, letra })),
    setColores: (colores) => setPreferencias((p) => ({ ...p, colores })),
    setContraste: (contraste) => setPreferencias((p) => ({ ...p, contraste })),
    setVoz: (voz) => setPreferencias((p) => ({ ...p, voz })),
  }), [preferencias])

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>
}
