import { useIdioma } from '../i18n/contexto.js'

// Filtros a la vista (D4): botones, no menús escondidos. El filtro se aplica a la lista y al mapa.
function FiltrosLugares({ destinos, filtro, onFiltro, hayGustos }) {
  const { t } = useIdioma()
  return (
    <div className="filtros" role="group" aria-label={t('filtros.grupo')}>
      <button type="button" className="chip" aria-pressed={filtro.destino === null} onClick={() => onFiltro({ ...filtro, destino: null })}>
        {t('filtros.todos')}
      </button>
      {destinos.map((d) => (
        <button key={d} type="button" className="chip" aria-pressed={filtro.destino === d} onClick={() => onFiltro({ ...filtro, destino: d })}>
          {d}
        </button>
      ))}
      {hayGustos && (
        <button type="button" className="chip gustos" aria-pressed={filtro.gustos} onClick={() => onFiltro({ ...filtro, gustos: !filtro.gustos })}>
          {t('filtros.gustos')}
        </button>
      )}
    </div>
  )
}

export default FiltrosLugares
