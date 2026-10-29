// Distancias en el celular: la ubicación del turista nunca sale del navegador (RN_07).

// Distancia en línea recta en metros (haversine), igual que backend/turismo_core/conocimiento.distancia_m.
export function distanciaM(lat1, lon1, lat2, lon2) {
  const rad = (g) => (g * Math.PI) / 180
  const a = Math.sin(rad(lat2 - lat1) / 2) ** 2 + Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(rad(lon2 - lon1) / 2) ** 2
  return 2 * 6_371_000 * Math.asin(Math.sqrt(a))
}

// El punto del catálogo más cercano a una posición: { punto, distancia } o null.
export function masCercano(puntos, lat, lon) {
  let mejor = null
  for (const p of puntos) {
    const d = distanciaM(lat, lon, p.lat, p.lon)
    if (!mejor || d < mejor.distancia) mejor = { punto: p, distancia: d }
  }
  return mejor
}
