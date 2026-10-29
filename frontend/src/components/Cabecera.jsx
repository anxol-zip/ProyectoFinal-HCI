import { NavLink } from 'react-router-dom'
import EnVivo from './EnVivo.jsx'
import { NOMBRE } from '../data/marca.js'
import { useIdioma } from '../i18n/contexto.js'

function Cabecera() {
  const { idioma, setIdioma, t } = useIdioma()
  return (
    <header className="cabecera">
      <NavLink to="/" className="marca" aria-label={t('nav.inicio')}>
        <span className="marca-logo" aria-hidden="true"><span /></span>
        <span className="marca-texto">{NOMBRE}</span>
      </NavLink>

      <nav className="navegacion" aria-label={t('nav.secciones')}>
        <NavLink to="/" end>{t('nav.explorar')}</NavLink>
        <NavLink to="/panel">{t('nav.panel')}</NavLink>
        <NavLink to="/acerca"><span className="largo">{t('nav.acerca')}</span><span className="corto">{t('nav.info')}</span></NavLink>
      </nav>

      <div className="cabecera-derecha">
        <EnVivo />
        <div className="idioma" role="group" aria-label={t('idioma.grupo')}>
          <button type="button" lang="es" aria-pressed={idioma === 'es'} onClick={() => setIdioma('es')} aria-label="Español">ES</button>
          <button type="button" lang="en" aria-pressed={idioma === 'en'} onClick={() => setIdioma('en')} aria-label="English">EN</button>
        </div>
      </div>
    </header>
  )
}

export default Cabecera
