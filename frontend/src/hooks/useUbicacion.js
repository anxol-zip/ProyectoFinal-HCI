import { useCallback, useEffect, useRef, useState } from 'react'

// La ubicación real del turista, una sola para toda la app (mapa, traslados, "Mejor ve a…", chat y reporte).
//
// - Lectura fresca (maximumAge 0) y de alta precisión; 10 s de espera.
// - Si falla, se niega o la página no es segura (http por IP en el stand), NO hay posición de respaldo:
//   se avisa el motivo con onError y quien la usa deja el mapa donde estaba.
// - En una PC sin GPS, Windows la calcula por Wi-Fi o IP: `precision` (metros) dice qué tan aproximada es.
// - onPosicion y onError se llaman desde la respuesta del navegador (no desde un efecto).
//
// estado: 'inactivo' | 'buscando' | 'ok' | 'error'
// posicion: { lat, lon, precision, t } — un objeto nuevo en cada lectura
// motivos de onError: 'inseguro' | 'denegado' | 'no_disponible' | 'tiempo'
export function useUbicacion({ onPosicion, onError } = {}) {
  const [estado, setEstado] = useState('inactivo')
  const [posicion, setPosicion] = useState(null)
  const manejadores = useRef({ onPosicion, onError })
  useEffect(() => { manejadores.current = { onPosicion, onError } })

  const pedir = useCallback(() => {
    const fallar = (motivo) => { setEstado('error'); manejadores.current.onError?.(motivo) }
    if (!window.isSecureContext || !navigator.geolocation) return fallar('inseguro')
    setEstado('buscando')
    navigator.geolocation.getCurrentPosition(
      (p) => {
        const nueva = { lat: p.coords.latitude, lon: p.coords.longitude, precision: p.coords.accuracy, t: Date.now() }
        setPosicion(nueva)
        setEstado('ok')
        manejadores.current.onPosicion?.(nueva)
      },
      (e) => fallar(e.code === e.PERMISSION_DENIED ? 'denegado' : e.code === e.TIMEOUT ? 'tiempo' : 'no_disponible'),
      { enableHighAccuracy: true, timeout: 10_000, maximumAge: 0 },
    )
  }, [])

  return { estado, posicion, pedir }
}
