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

// Contraste (propuesta §5.2): el alto quita transparencias y oscurece textos y bordes.
export const CONTRASTES = ['normal', 'alto']

// Velocidad de la lectura en voz alta: la lenta ayuda a quien no oye bien o no lee el idioma.
export const VOCES = ['normal', 'lenta']
export const VELOCIDAD_VOZ = { normal: 1, lenta: 0.8 }

// { letra, colores, contraste, voz } y sus set… del proveedor (preferencias/Preferencias.jsx).
export function usePreferencias() {
  return useContext(Contexto)
}
