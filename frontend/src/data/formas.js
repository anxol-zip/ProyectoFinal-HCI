import { ICONO } from './semaforo.js'

// Silueta de cada estado del semáforo (decisión D2 de la propuesta). Además del color, el ícono
// y el texto, cada estado tiene su forma: así se distingue aunque no se perciba ningún color
// (WCAG 1.4.1). Las formas siguen convenciones conocidas: el triángulo de las señales de
// precaución y el octágono del alto.
// Coordenadas en un cuadro de 40 × 40; `y` es la altura a la que va el ícono dentro de la forma.
export const FORMA = {
  verde: { d: 'M20 2.5a17.5 17.5 0 1 1 0 35a17.5 17.5 0 1 1 0-35Z', y: 20.5 },                       // círculo
  amarillo: { d: 'M20 2.5 38.5 36H1.5Z', y: 25.5 },                                                   // triángulo
  rojo: { d: 'M13.2 2.5h13.6l9.7 9.7v15.6l-9.7 9.7H13.2l-9.7-9.7V12.2Z', y: 20.5 },                 // octágono
  sin_dato: { d: 'M20 1.5 38.5 20 20 38.5 1.5 20Z', y: 20.5 },                                        // rombo
  cerrado: { d: 'M7 4h26a3 3 0 0 1 3 3v26a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3Z', y: 20.5 }, // cuadrado
}

// La misma forma como texto HTML, para los marcadores de Leaflet (L.divIcon no recibe JSX).
export function svgForma(color) {
  const f = FORMA[color] ?? FORMA.sin_dato
  return `<svg class="forma ${color}" viewBox="0 0 40 40" aria-hidden="true" focusable="false">`
    + `<path d="${f.d}"/><text x="20" y="${f.y}">${ICONO[color] ?? ''}</text></svg>`
}
