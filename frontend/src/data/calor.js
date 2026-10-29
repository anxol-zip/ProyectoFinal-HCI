// Rampa secuencial de un solo tono (azul, de claro a oscuro): la afluencia es una
// magnitud, así que no usa los colores del semáforo, que quedan reservados al estado.
export const RAMPA = ['#CDE2FB', '#86B6EF', '#3987E5', '#1C5CAB', '#184F95']

// nivel es la afluencia relativa que manda el backend (1.0 = una hora normal en ese lugar).
// 0.4 o menos se ve casi vacío; 1.6 o más, lleno.
export function intensidad(valor) {
  return Math.min(1, Math.max(0, (valor - 0.4) / 1.2))
}
