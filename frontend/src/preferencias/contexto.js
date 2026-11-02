import { createContext, useContext } from 'react'

export const Contexto = createContext(null)

// Tamaños de letra (decisión D1 de la propuesta): cuánto crece el texto respecto al tamaño que
// la persona ya eligió en su navegador. Toda la hoja de estilos está en rem, así que escala junta.
export const TAMANOS = ['normal', 'grande', 'muy_grande']
export const ESCALA_TEXTO = { normal: 1, grande: 1.25, muy_grande: 1.5 }
// Los marcadores del mapa crecen menos que el texto, para que no se encimen.
export const ESCALA_MARCADOR = { normal: 1, grande: 1.15, muy_grande: 1.3 }

// Colores del semáforo (decisión D3): los habituales o una paleta que se distingue con daltonismo.
export const COLORES = ['habituales', 'daltonismo']

// { letra, setLetra, colores, setColores } del proveedor (preferencias/Preferencias.jsx).
export function usePreferencias() {
  return useContext(Contexto)
}
