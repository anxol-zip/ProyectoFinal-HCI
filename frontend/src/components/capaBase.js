// Mapa base: "Light Gray Canvas" de Esri, neutral y sin ruido (calles claras sobre gris
// suave), para que manden el semáforo y el calor. Lleva dos capas: el fondo y, encima,
// los nombres de calles y lugares. Atribución obligatoria (RN_13), visible en la esquina.
//
// Pendiente (2026-10-16): confirmar los términos de uso sin cuenta de Esri
// (goto.arcgisonline.com/maps/World_Light_Gray_Base). CARTO, la primera opción, ya exige
// clave de API. Si Esri no se puede usar, basta con dejar CAPAS = [OSM].
const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas'
const ATRIBUCION_ESRI = 'Esri, HERE, Garmin, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> y la comunidad GIS'

export const OSM = {
  url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  attribution: '&copy; colaboradores de <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  maxZoom: 19,
}

export const CAPAS = [
  { url: `${ESRI}/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}`, attribution: ATRIBUCION_ESRI, maxNativeZoom: 16, maxZoom: 19 },
  { url: `${ESRI}/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}`, maxNativeZoom: 16, maxZoom: 19 },
]
