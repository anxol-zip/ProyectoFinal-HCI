import { useEffect, useState } from 'react'
import { useIdioma } from '../i18n/contexto.js'

const reloj = () => new Date().toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', hour12: false })

// La demo es en vivo (sin escenarios): el semáforo es el de esta hora, así que se dice cuál.
function EnVivo() {
  const { t } = useIdioma()
  const [ahora, setAhora] = useState(reloj)
  useEffect(() => {
    const id = setInterval(() => setAhora(reloj()), 15000)
    return () => clearInterval(id)
  }, [])
  return (
    <p className="en-vivo" title={`${t('envivo')} ${ahora}: ${t('envivo.titulo')}`}>
      <span className="punto-vivo" aria-hidden="true" />
      <span>{t('envivo')}</span>
      <span className="numero en-vivo-hora">{ahora}</span>
    </p>
  )
}

export default EnVivo
