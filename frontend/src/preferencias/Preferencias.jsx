import { useEffect, useMemo, useState } from 'react'
import { COLORES, Contexto, TAMANOS } from './contexto.js'

// Preferencias para ver mejor: tamaño de letra y colores del semáforo. Se recuerdan en este
// dispositivo, sin cuenta (igual que el idioma). Se aplican como atributos de <html>
// (data-letra y data-colores) y el CSS hace el resto.
const CLAVE = 'puebla-ahora:preferencias'
const INICIALES = { letra: 'normal', colores: 'habituales' }

function leerGuardadas() {
  try {
    const guardadas = JSON.parse(localStorage.getItem(CLAVE)) ?? {}
    return {
      letra: TAMANOS.includes(guardadas.letra) ? guardadas.letra : INICIALES.letra,
      colores: COLORES.includes(guardadas.colores) ? guardadas.colores : INICIALES.colores,
    }
  } catch {
    return INICIALES          // sin almacenamiento (ventana privada) o dato dañado
  }
}

function aplicar({ letra, colores }) {
  document.documentElement.dataset.letra = letra
  document.documentElement.dataset.colores = colores
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
  }), [preferencias])

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>
}
