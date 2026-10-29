import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import '@fontsource-variable/inter'
import 'leaflet/dist/leaflet.css'
import './index.css'
import App from './App.jsx'
import { ProveedorIdioma } from './i18n/Idioma.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <ProveedorIdioma>
        <App />
      </ProveedorIdioma>
    </BrowserRouter>
  </StrictMode>,
)
