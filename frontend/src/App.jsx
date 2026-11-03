import { useEffect, useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import { api } from './api/cliente.js'
import Cabecera from './components/Cabecera.jsx'
import { useIdioma } from './i18n/contexto.js'
import Acerca from './pages/Acerca.jsx'
import Panel from './pages/Panel.jsx'
import Turista from './pages/Turista.jsx'

function App() {
  const { t } = useIdioma()
  // Estado que comparten varias pantallas: vive aquí y baja por props (docs/05c §3.3).
  const [catalogo, setCatalogo] = useState([])
  const [errorCatalogo, setErrorCatalogo] = useState(null)
  const [sesion, setSesion] = useState(null)        // { sesionId, perfil: { intereses, horas, origenId } }

  useEffect(() => {
    api.obtenerPuntos().then(setCatalogo).catch((e) => setErrorCatalogo(e.message))
  }, [])

  return (
    <div className="app">
      {/* Primer elemento con teclado: salta la cabecera (D6) */}
      <a className="saltar" href="#contenido">{t('saltar')}</a>
      <Cabecera />
      <main className="app-principal" id="contenido" tabIndex={-1}>
        <Routes>
          <Route path="/" element={<Turista catalogo={catalogo} errorCatalogo={errorCatalogo} sesion={sesion} onSesion={setSesion} />} />
          <Route path="/panel" element={<Panel />} />
          <Route path="/acerca" element={<Acerca />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
