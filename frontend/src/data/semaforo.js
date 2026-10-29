// Textos, íconos y orden del semáforo. Los colores son los que manda el backend
// (verde · amarillo · rojo · sin_dato · cerrado). El color nunca va solo (WCAG):
// siempre con su ícono y su texto (docs/12 §3).
export const TEXTO = {
  verde: 'Buen momento',
  amarillo: 'Con precaución',
  rojo: 'Mejor después',
  sin_dato: 'Sin dato',
  cerrado: 'Cerrado',
}

export const ICONO = { verde: '✓', amarillo: '!', rojo: '✕', sin_dato: '?', cerrado: '–' }

// Para ordenar la lista: primero lo que más conviene; lo cerrado, al final.
export const ORDEN = { verde: 0, amarillo: 1, rojo: 2, sin_dato: 3, cerrado: 4 }
