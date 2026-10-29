import { FOTOS, rutaFoto } from '../data/fotos.js'
import { useIdioma } from '../i18n/contexto.js'

// Foto de un lugar. "mini" es decorativa (el nombre va al lado); "grande" lleva texto
// alternativo y, si se pide, el crédito que exige la licencia.
function Foto({ id, nombre, tamano = 'grande', credito = false }) {
  const { t } = useIdioma()
  const foto = FOTOS[id]
  if (!foto) return <div className={`foto ${tamano} sin-foto`} aria-hidden="true" />
  const [ancho, alto] = tamano === 'mini' ? [200, 200] : [900, 600]
  return (
    <figure className={`foto ${tamano}`}>
      <img src={rutaFoto(id, tamano)} alt={tamano === 'mini' ? '' : t('foto.alt', { nombre })} width={ancho} height={alto} loading="lazy" decoding="async" />
      {credito && (
        <figcaption>
          <a href={foto.pagina} target="_blank" rel="noreferrer">{t('foto.credito', { autor: foto.autor, licencia: foto.licencia })}</a>
        </figcaption>
      )}
    </figure>
  )
}

export default Foto
