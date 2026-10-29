import { useEffect, useId, useMemo, useRef, useState } from 'react'
import Foto from './Foto.jsx'

// "Taco" → "taco": para buscar sin importar acentos ni mayúsculas.
const normal = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

function agrupar(puntos, busqueda) {
  const q = normal(busqueda.trim())
  const grupos = new Map()
  for (const p of puntos) {
    if (q && !normal(`${p.nombre} ${p.destino}`).includes(q)) continue
    grupos.set(p.destino, [...(grupos.get(p.destino) ?? []), p])
  }
  return [...grupos.entries()]
}

// Selector de lugar con foto, agrupado por destino y con búsqueda (patrón combobox de WAI-ARIA).
// En escritorio se despliega bajo el botón; en celular sube como hoja inferior.
function SelectorLugar({ puntos, valor, onCambiar, etiquetaId, textos }) {
  const [abierto, setAbierto] = useState(false)
  const [busqueda, setBusqueda] = useState('')
  const [activo, setActivo] = useState(0)
  const raiz = useRef(null)
  const entrada = useRef(null)
  const lista = useRef(null)
  const base = useId()
  const elegido = puntos.find((p) => p.id === valor)

  // Grupos por destino (en el orden en que aparecen en el catálogo) y la lista plana en ese
  // mismo orden visual, que es la que recorren las flechas del teclado.
  const grupos = useMemo(() => agrupar(puntos, busqueda), [puntos, busqueda])
  const filtrados = grupos.flatMap(([, lugares]) => lugares)
  const indiceDe = new Map(filtrados.map((p, i) => [p.id, i]))

  function abrir() {
    setBusqueda('')
    const todos = agrupar(puntos, '').flatMap(([, lugares]) => lugares)
    setActivo(Math.max(0, todos.findIndex((p) => p.id === valor)))
    setAbierto(true)
  }

  function elegir(p) {
    onCambiar(p.id)
    setAbierto(false)
  }

  useEffect(() => {
    if (!abierto) return undefined
    // Con dedo, enfocar la búsqueda abriría el teclado encima de la lista: se enfoca la lista.
    if (window.matchMedia('(pointer: fine)').matches) entrada.current?.focus()
    else lista.current?.focus({ preventScroll: true })
    const fuera = (e) => { if (!raiz.current?.contains(e.target)) setAbierto(false) }
    document.addEventListener('pointerdown', fuera)
    return () => document.removeEventListener('pointerdown', fuera)
  }, [abierto])

  // La opción activa siempre a la vista al moverse con el teclado.
  useEffect(() => {
    if (abierto) lista.current?.querySelector(`[data-indice="${activo}"]`)?.scrollIntoView({ block: 'nearest' })
  }, [activo, abierto])

  function teclado(e) {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActivo((i) => Math.min(filtrados.length - 1, i + 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActivo((i) => Math.max(0, i - 1)) }
    else if (e.key === 'Enter') { e.preventDefault(); if (filtrados[activo]) elegir(filtrados[activo]) }
    else if (e.key === 'Escape') { e.preventDefault(); setAbierto(false) }
  }

  return (
    <div className="selector-lugar" ref={raiz}>
      <button
        type="button"
        className="selector-boton"
        aria-haspopup="listbox"
        aria-expanded={abierto}
        aria-labelledby={`${etiquetaId} ${base}-valor`}
        onClick={() => (abierto ? setAbierto(false) : abrir())}
      >
        {elegido && <Foto id={elegido.clave} tamano="mini" />}
        <span className="selector-texto" id={`${base}-valor`}>
          <strong>{elegido?.nombre ?? textos.elige}</strong>
          {elegido && <span>{elegido.destino}</span>}
        </span>
        <span className="selector-flecha" aria-hidden="true" />
      </button>

      {abierto && (
        <>
          <div className="selector-fondo" aria-hidden="true" onClick={() => setAbierto(false)} />
          <div className="selector-opciones">
            <input
              ref={entrada}
              className="campo"
              type="search"
              role="combobox"
              aria-expanded="true"
              aria-controls={`${base}-lista`}
              aria-activedescendant={filtrados[activo] ? `${base}-${filtrados[activo].id}` : undefined}
              aria-label={textos.buscar}
              placeholder={textos.buscar}
              value={busqueda}
              onChange={(e) => { setBusqueda(e.target.value); setActivo(0) }}
              onKeyDown={teclado}
            />
            <ul className="selector-lista" id={`${base}-lista`} role="listbox" aria-labelledby={etiquetaId} ref={lista} tabIndex={-1} onKeyDown={teclado}>
              {filtrados.length === 0 && <li className="selector-vacio">{textos.sinResultados}</li>}
              {grupos.map(([destino, lugares]) => (
                <li key={destino} role="presentation">
                  <p className="selector-grupo" aria-hidden="true">{destino}</p>
                  <ul role="presentation">
                    {lugares.map((p) => {
                      const i = indiceDe.get(p.id)
                      return (
                        <li
                          key={p.id}
                          id={`${base}-${p.id}`}
                          role="option"
                          aria-selected={p.id === valor}
                          data-indice={i}
                          className={`selector-opcion${i === activo ? ' activa' : ''}`}
                          onPointerEnter={() => setActivo(i)}
                          onClick={() => elegir(p)}
                        >
                          <Foto id={p.clave} tamano="mini" />
                          <span>{p.nombre}</span>
                          {p.id === valor && <span className="selector-marca" aria-hidden="true">✓</span>}
                        </li>
                      )
                    })}
                  </ul>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  )
}

export default SelectorLugar
