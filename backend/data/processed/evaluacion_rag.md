# Evaluación del asistente (RAG)

Modelo `qwen3:8b`, embeddings `bge-m3`, momento 2026-10-16 13:00, corrida 2026-10-16 01:07.

## Resumen

- Recuperación (hit): 23/23
- Fidelidad (sin números inventados): 28/28
- 'No tengo ese dato' cuando no hay dato: 5/5
- Citas válidas: 28/28
- Atributos correctos (techado, color, tranquilo): 28/28
- Tiempo: promedio 4.7 s, máximo 21.9 s

## 1. ¿A qué hora abre la Biblioteca Palafoxiana y cuánto cuesta?

- Recuperación: acierto (esperado ['punto-3'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['punto-3']
- Tiempo: 6.6 s · recuperados: ['punto-3', 'punto-7', 'punto-10', 'punto-20', 'evento-2', 'evento-1', 'obs-2', 'obs-11', 'metodo-semaforo', 'obs-19']

> La Biblioteca Palafoxiana abre martes a jueves a 10:00 y viernes a domingo a 10:00 [punto-3]. El costo es $48.

## 2. ¿Qué puedo visitar techado si llueve en el centro de Puebla?

- Recuperación: acierto (esperado ['punto-1', 'punto-10', 'punto-2', 'punto-22', 'punto-3', 'punto-7'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['punto-11', 'punto-1', 'punto-7']
- Tiempo: 5.6 s · recuperados: ['punto-23', 'punto-1', 'punto-11', 'evento-1', 'evento-2', 'fuentes', 'metodo-semaforo', 'obs-3', 'obs-17']

> Si llueve en el centro de Puebla, puedes visitar:  
> 1) [punto-11] Estrella de Puebla: VERDE (tranquilo), techado, visita sugerida: 45 min.  
> 2) [punto-1] Catedral de Puebla: AMARILLO, techado, visita sugerida: 1-2 h.  
> 3) [punto-7] Casa del Alfeñique: AMARILLO, techado, visita sugerida: 45 min.

## 3. ¿Cómo está la Pirámide de Cholula ahora?

- Recuperación: acierto (esperado ['punto-12'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['punto-12']
- Tiempo: 3.5 s · recuperados: ['punto-12', 'punto-13', 'punto-14', 'punto-16', 'evento-1', 'evento-2', 'obs-15', 'inah-3110009', 'obs-13', 'obs-4']

> La Pirámide de Cholula está en AMARILLO (movimiento normal) [punto-12]. La hora más tranquila es las 16:00 (VERDE) y la más llena las 14:00 (VERDE).

## 4. Estoy en el Zócalo y tengo 3 horas, ¿qué me recomiendas?

- Recuperación: acierto (esperado ['punto-21'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['punto-1', 'punto-11']
- Tiempo: 3.7 s · recuperados: ['punto-21', 'punto-1', 'punto-10', 'evento-2', 'evento-1', 'metodo-recomendador', 'metodo-semaforo', 'metodo-reportes', 'fuentes']

> Te recomiendo: [punto-1] Catedral de Puebla (techado, visita sugerida 1-2 h, 4 min a pie) y [punto-11] Estrella de Puebla (techado, visita sugerida 45 min, 12 min en coche).

## 5. ¿Cuándo es el Valle de Catrinas?

- Recuperación: acierto (esperado ['evento-1'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['evento-1']
- Tiempo: 2.8 s · recuperados: ['punto-17', 'punto-9', 'evento-1', 'evento-2', 'inah-2403400', 'obs-21', 'obs-6', 'metodo-recomendador']

> El Valle de Catrinas es del 2026-10-02 al 2026-11-09 [evento-1].

## 6. ¿Qué días hay funciones de Catrinia?

- Recuperación: acierto (esperado ['evento-2'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['evento-2']
- Tiempo: 3.3 s · recuperados: ['punto-16', 'punto-17', 'evento-2', 'evento-1', 'fuentes', 'metodo-recomendador', 'metodo-semaforo', 'inah-2403100']

> Las funciones de Catrinia son los días 3, 4, 10, 11, 17, 18, 24, 25 y 31 de octubre, así como el 1 de noviembre de 2026 [evento-2].

## 7. ¿Cuántos turistas llegan a Atlixco?

- Recuperación: acierto (esperado ['obs-2'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['obs-2']
- Tiempo: 3.0 s · recuperados: ['punto-18', 'punto-16', 'punto-11', 'punto-12', 'evento-1', 'evento-2', 'obs-2', 'obs-1', 'obs-20', 'obs-19']

> Según el Observatorio Turístico de Puebla, de julio 2025 a junio 2026, llegaron 217,090 turistas a Atlixco [obs-2].

## 8. ¿Qué porcentaje de las visitas a recintos del INAH en Puebla tuvo la zona arqueológica de Cholula en 2025?

- Recuperación: acierto (esperado ['inah-3110009'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['inah-3110009']
- Tiempo: 2.5 s · recuperados: ['punto-12', 'punto-1', 'punto-11', 'punto-16', 'evento-1', 'evento-2', 'inah-3110009', 'inah-2301400', 'inah-4100017', 'inah-3120128']

> La Zona Arqueológica de Cholula tuvo el 39.7 % de las visitas a recintos del INAH en Puebla en 2025 [inah-3110009].

## 9. ¿Cómo sabe la app que un lugar está lleno?

- Recuperación: acierto (esperado ['metodo-semaforo'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['metodo-semaforo']
- Tiempo: 3.3 s · recuperados: ['punto-12', 'punto-20', 'punto-1', 'evento-2', 'evento-1', 'metodo-semaforo', 'metodo-recomendador', 'metodo-reportes', 'fuentes']

> La app estima la afluencia de cada lugar por hora a partir de datos oficiales mensuales, factores de día, hora, festivos, eventos verificados y clima. El color del semáforo indica si está más lleno que en el 60 % o 85 % de sus horas abiertas de 2023 a 2025. [metodo-semaforo]

## 10. ¿Para qué sirve el botón ¿Cómo está?

- Recuperación: acierto (esperado ['metodo-reportes'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['metodo-reportes']
- Tiempo: 2.4 s · recuperados: ['punto-3', 'punto-7', 'evento-2', 'evento-1', 'metodo-recomendador', 'metodo-reportes', 'metodo-semaforo', 'fuentes']

> El botón ¿Cómo está? permite a los turistas reportar la ocupación de un lugar en tiempo real (vacío, normal o lleno), lo cual ayuda a la app a calcular el color del semáforo y mejorar la recomendación. [metodo-reportes]

## 11. ¿Qué hay para ir con niños?

- Recuperación: acierto (esperado ['punto-11', 'punto-20', 'punto-23', 'punto-9'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['punto-23', 'punto-20', 'punto-11']
- Tiempo: 2.9 s · recuperados: ['punto-20', 'punto-17', 'punto-23', 'evento-1', 'evento-2', 'metodo-recomendador', 'metodo-semaforo', 'metodo-reportes', 'fuentes']

> Para ir con niños, te recomendamos:  
> 1) [punto-23] Acuario Michin Puebla: techado, visita sugerida: sin dato.  
> 2) [punto-20] Africam Safari: al aire libre, visita sugerida: 3-4 h.  
> 3) [punto-11] Estrella de Puebla: techado, visita sugerida: 45 min.

## 12. ¿Abre hoy el Museo Amparo?

- Recuperación: acierto (esperado ['punto-4'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['punto-4']
- Tiempo: 1.7 s · recuperados: ['punto-4', 'punto-10', 'punto-22', 'punto-9', 'evento-2', 'evento-1', 'metodo-semaforo', 'inah-4100014', 'fuentes', 'inah-4100015']

> No, el Museo Amparo está cerrado hoy [punto-4].

## 13. ¿Cuánto cuesta entrar a Africam Safari?

- Recuperación: acierto (esperado ['punto-20'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['punto-20']
- Tiempo: 1.8 s · recuperados: ['punto-20', 'punto-12', 'punto-23', 'evento-2', 'evento-1', 'metodo-recomendador', 'obs-1', 'obs-4', 'obs-8']

> La entrada a Africam Safari cuesta $550 [punto-20].

## 14. ¿Dónde puedo comprar artesanías y Talavera?

- Recuperación: acierto (esperado ['punto-6'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['punto-6', 'punto-16']
- Tiempo: 2.3 s · recuperados: ['punto-6', 'punto-16', 'punto-7', 'evento-2', 'evento-1', 'fuentes', 'inah-4100015', 'inah-4100014', 'inah-2403400']

> En [punto-6] Barrio del Artista y El Parián, es al aire libre, movimiento normal, visita sugerida 1 h. También puedes visitar [punto-16] San Francisco Acatepec, techado, visita sugerida 30 min.

## 15. ¿De dónde salen los datos de la app?

- Recuperación: acierto (esperado ['fuentes'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['fuentes']
- Tiempo: 2.7 s · recuperados: ['punto-20', 'punto-12', 'punto-3', 'evento-2', 'evento-1', 'fuentes', 'metodo-recomendador', 'metodo-reportes', 'metodo-semaforo']

> Los datos de la app provienen del Observatorio Turístico de Puebla, INAH, DENUE, Catálogo de la zona piloto, OpenRouteService, Open-Meteo y otros colaboradores. [fuentes]

## 16. ¿Dónde puedo comer cerca de la Pirámide de Cholula?

- Recuperación: acierto (esperado ['denue-*'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['denue-21140722330000151000000000U8', 'denue-21140722511000672001000000U8']
- Tiempo: 5.1 s · recuperados: ['denue-21140722330000151000000000U8', 'denue-21140722511000672001000000U8', 'denue-21119722511004211000000000U5', 'evento-1']

> Puedes comer en Cholulquliza, servicios de preparación de alimentos en unidades móviles (0 a 5 personas), a 308 m en línea recta [denue-21140722330000151000000000U8]. También en Chez Marie, restaurantes con servicio de preparación de alimentos a la carta o de comida corrida (0 a 5 personas), a 466 m en línea recta [denue-21140722511000672001000000U8].

## 17. Estoy en el Zócalo, ¿dónde puedo desayunar?

- Recuperación: acierto (esperado ['denue-*'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['denue-21114722110003543001000000U4', 'denue-21114722110003323001000000U1', 'denue-21114722219033132001000000U9']
- Tiempo: 3.7 s · recuperados: ['denue-21114722110003543001000000U4', 'denue-21114722110003323001000000U1', 'denue-21114722219033132001000000U9', 'evento-1']

> En el Zócalo, puedes desayunar en The Italian Coffee [denue-21114722110003543001000000U4], a 194 m en línea recta. También en The Italian Coffee [denue-21114722110003323001000000U1], a 103 m en línea recta. Y en The Italian Coffee Company [denue-21114722219033132001000000U9], a 55 m en línea recta.

## 18. ¿Hay hoteles en el centro de Atlixco?

- Recuperación: acierto (esperado ['denue-*'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['denue-21019721112000021001000000U2', 'denue-21019721112000271000000000U3', 'denue-21019721111000211000000000U1']
- Tiempo: 9.4 s · recuperados: ['denue-21019721112000021001000000U2', 'denue-21019721112000271000000000U3', 'denue-21019721111000211000000000U1', 'evento-1']

> Hay hoteles en el centro de Atlixco. [denue-21019721112000021001000000U2] Hotel Atlixco. Hospedaje: hoteles sin otros servicios integrados (0 a 5 personas), a 112 m en línea recta. [denue-21019721112000271000000000U3] Hotel Atlix. Hospedaje: hoteles sin otros servicios integrados (0 a 5 personas), a 540 m en línea recta. [denue-21019721111000211000000000U1] Hotel Casa Flora. Hospedaje: hoteles con otros servicios integrados (11 a 30 personas), a 819 m en línea recta.

## 19. ¿Qué restaurante me recomiendas para comer mole?

- Recuperación: acierto (esperado ['denue-*'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['denue-21114722511010602001000000U8', 'denue-21119722511004621000000000U5', 'denue-21119722511001371000000000U0']
- Tiempo: 6.5 s · recuperados: ['denue-21114722511010602001000000U8', 'denue-21119722511004621000000000U5', 'denue-21119722511001371000000000U0', 'evento-1']

> No tengo ese dato. Puedo recomendarte estos restaurantes: [denue-21114722511010602001000000U8] Restaurant Come Bien Mr Loro, tipo: restaurantes con servicio de preparación de alimentos a la carta o de comida corrida (0 a 5 personas), a 847 m en línea recta de Capilla del Rosario (Templo de Santo Domingo). [denue-21119722511004621000000000U5] Mosto Voi, tipo: restaurantes con servicio de preparación de alimentos a la carta o de comida corrida (0 a 5 personas), a 960 m en línea recta de Museo Internacional del Barroco. [denue-21119722511001371000000000U0] Postres y Helados Dolce Mio, tipo: restaurantes con servicio de preparación de alimentos a la carta o de comida corrida (0 a 5 personas), a 507 m en línea recta de Santuario de la Virgen de los Remedios.

## 20. Tengo 4 horas y va a llover, ¿qué hago?

- Recuperación: acierto (esperado ['punto-*'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['punto-11', 'punto-1', 'punto-17']
- Tiempo: 3.2 s · recuperados: ['punto-23', 'punto-1', 'punto-20', 'punto-11', 'evento-1', 'evento-2', 'metodo-recomendador', 'metodo-semaforo', 'metodo-reportes', 'fuentes']

> Con lluvia fuerte, te recomendamos: [punto-11] Estrella de Puebla (VERDE, 45 min), [punto-1] Catedral de Puebla (AMARILLO, 1-2 h) y [punto-17] Exconvento de Huejotzingo (VERDE, 1-2 h).

## 21. Tengo 4 horas y va a llover, ¿qué hago?

- Recuperación: acierto (esperado ['punto-*'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['punto-11', 'punto-1', 'punto-3']
- Tiempo: 3.9 s · recuperados: ['punto-23', 'punto-1', 'punto-20', 'punto-11', 'evento-1', 'evento-2', 'metodo-recomendador', 'metodo-semaforo', 'metodo-reportes', 'fuentes']

> Con lluvia fuerte, te recomendamos: [punto-11] Estrella de Puebla (VERDE, 45 min, 12 min en coche) o [punto-1] Catedral de Puebla (AMARILLO, 1-2 h, 4 min a pie). También [punto-3] Biblioteca Palafoxiana (AMARILLO, 30-60 min, 4 min a pie).

## 22. ¿Qué hay tranquilo cerca de mí?

- Recuperación: acierto (esperado ['punto-*'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['punto-9', 'punto-11']
- Tiempo: 6.0 s · recuperados: ['punto-20', 'punto-13', 'evento-1', 'evento-2', 'metodo-recomendador', 'fuentes', 'metodo-semaforo', 'metodo-reportes']

> Hay tranquilo en [punto-9] Zona de los Fuertes (Loreto y Guadalupe) y en [punto-11] Estrella de Puebla. Ambos son al aire libre y techado respectivamente, y están a pocos minutos en coche o a pie desde el Zócalo.

## 23. ¿Cuándo conviene ir a la pirámide?

- Recuperación: acierto (esperado ['punto-12'])
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['punto-12']
- Tiempo: 2.9 s · recuperados: ['punto-12', 'punto-13', 'punto-20', 'punto-1', 'evento-1', 'evento-2', 'metodo-recomendador', 'metodo-semaforo', 'metodo-reportes', 'obs-20']

> La hora más tranquila es las 16:00 [punto-12]. O regresa a las 10:00 [punto-12].

## 24. ¿Cuánto cuesta un taxi del Zócalo a Cholula?

- Sin dato en la base: dijo No tengo ese dato
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['punto-21', 'punto-12']
- Tiempo: 2.3 s · recuperados: ['punto-14', 'punto-16', 'punto-12', 'punto-21', 'evento-1', 'evento-2', 'obs-13', 'obs-15', 'inah-3110009', 'obs-21']

> No tengo ese dato. Puedo decirte que el Zócalo de Puebla está en rojo [punto-21] y la Zona Arqueológica de Cholula (Gran Pirámide) está en amarillo [punto-12].

## 25. ¿Cuál es el restaurante mejor calificado de Puebla?

- Sin dato en la base: dijo No tengo ese dato
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['denue-21114722511002323000000000U1', 'denue-21114722511018285000017979S4', 'denue-21114722110000941003003155S3']
- Tiempo: 21.9 s · recuperados: ['denue-21114722511002323000000000U1', 'denue-21114722511018285000017979S4', 'denue-21114722110000941003003155S3', 'evento-1']

> No tengo ese dato. Puedo decirte que hay tres restaurantes denue- en el contexto: Restaurant Bar Sabor a Puebla, Domu Sushi Bar Puebla y 81046 Vips Puebla Centro. [denue-21114722511002323000000000U1], [denue-21114722511018285000017979S4], [denue-21114722110000941003003155S3].

## 26. ¿A qué hora sale el último tren a Cholula?

- Sin dato en la base: dijo No tengo ese dato
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['punto-12']
- Tiempo: 8.9 s · recuperados: ['punto-12', 'punto-14', 'punto-13', 'punto-16', 'evento-2', 'evento-1', 'obs-15', 'obs-13', 'inah-3110009', 'fuentes']

> No tengo ese dato. Puedo decirte que la Zona Arqueológica de Cholula (Gran Pirámide) tiene su última hora de visita estimada a las 17:00 [punto-12].

## 27. ¿Hay estacionamiento en el Museo Amparo?

- Sin dato en la base: dijo No tengo ese dato
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['punto-4']
- Tiempo: 5.7 s · recuperados: ['punto-4', 'punto-10', 'punto-20', 'punto-13', 'evento-2', 'evento-1', 'metodo-recomendador', 'metodo-semaforo', 'inah-4100017', 'fuentes']

> No tengo ese dato. Puedo decirte que el Museo Amparo está cerrado a esta hora [punto-4].

## 28. ¿Cuántas personas visitaron la Pirámide de Cholula el sábado pasado?

- Sin dato en la base: dijo No tengo ese dato
- Números que no estaban en el contexto: ninguno
- Atributos incorrectos (techado, color, tranquilo): ninguno
- Citas inválidas: ninguna · fuentes: ['inah-3110009']
- Tiempo: 3.4 s · recuperados: ['punto-12', 'punto-13', 'punto-16', 'punto-14', 'evento-1', 'evento-2', 'obs-13', 'obs-15', 'inah-3110009', 'obs-4']

> No tengo ese dato. Puedo decirte que en julio 2025 a junio 2026, la Zona Arqueológica de Cholula tuvo 188,555 visitas en 2025 y 123,474 en lo que va de 2026 [inah-3110009].
