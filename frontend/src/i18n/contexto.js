import { createContext, useContext } from 'react'
import { TEXTOS } from './textos.js'

export const Contexto = createContext(null)

// t('clave', { variable }) → texto en el idioma actual (o en español si falta la traducción).
export function crearT(idioma) {
  return (clave, variables = {}) => {
    const valor = TEXTOS[idioma][clave] ?? TEXTOS.es[clave] ?? clave
    if (typeof valor !== 'string') return valor
    return valor.replace(/\{(\w+)\}/g, (_, v) => variables[v] ?? '')
  }
}

// { idioma, setIdioma, t } del proveedor más cercano (i18n/Idioma.jsx).
export function useIdioma() {
  return useContext(Contexto)
}
