import { useEffect, useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import { api } from './api/cliente.js'
import Cabecera from './components/Cabecera.jsx'
import Acerca from './pages/Acerca.jsx'
import Panel from './pages/Panel.jsx'
import Turista from './pages/Turista.jsx'

function App() {
  // Estado que comparten varias pantallas: vive aquí y baja por props (docs/05c §3.3).
  const [catalogo, setCatalogo] = useState([])
  const [errorCatalogo, setErrorCatalogo] = useState(null)
  const [sesion, setSesion] = useState(null)        // { sesionId, perfil: { intereses, horas, origenId } }

  useEffect(() => {
    api.obtenerPuntos().then(setCatalogo).catch((e) => setErrorCatalogo(e.message))
  }, [])

  return (
    <div className="app">
      <Cabecera />
      <main className="app-principal">
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
