import { useEffect, useRef } from 'react'

const ENFOCABLES = 'button:not([disabled]), [href], input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])'

// Teclado en ventanas y paneles (D6): al abrir, el foco entra a la ventana; Escape la cierra y, al
// cerrar, el foco vuelve a donde estaba. Con `atrapar`, Tab da la vuelta dentro de la ventana
// (ventana modal: lo de atrás no se puede usar mientras está abierta). `respaldo` es a dónde va el
// foco si el elemento de antes ya no existe (p. ej. la ficha se recargó después de un reporte).
export function useDialogo(ref, onCerrar, { atrapar = false, inicial = null, respaldo = null } = {}) {
  // onCerrar cambia en cada render del padre; la ventana siempre llama a la versión más reciente.
  const cerrar = useRef(onCerrar)
  useEffect(() => { cerrar.current = onCerrar })

  useEffect(() => {
    const anterior = document.activeElement
    const caja = ref.current
    const primero = (inicial && caja?.querySelector(inicial)) || caja?.querySelector(ENFOCABLES)
    primero?.focus()

    function conTecla(e) {
      if (e.key === 'Escape') {
        e.stopPropagation()
        cerrar.current()
        return
      }
      if (!atrapar || e.key !== 'Tab' || !caja) return
      const lista = [...caja.querySelectorAll(ENFOCABLES)]
      if (lista.length === 0) return
      const [inicio, fin] = [lista[0], lista[lista.length - 1]]
      if (e.shiftKey && document.activeElement === inicio) { e.preventDefault(); fin.focus() }
      else if (!e.shiftKey && document.activeElement === fin) { e.preventDefault(); inicio.focus() }
    }
    document.addEventListener('keydown', conTecla)
    return () => {
      document.removeEventListener('keydown', conTecla)
      if (anterior instanceof HTMLElement && anterior.isConnected) anterior.focus()
      else if (respaldo) document.querySelector(respaldo)?.focus()
    }
  }, [ref, atrapar, inicial, respaldo])
}
