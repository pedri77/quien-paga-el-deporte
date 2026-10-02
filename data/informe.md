# ¿Quién paga el deporte? — Informe de datos (BDNS 2024-2025)

Generado por `scripts/deporte_build.py` a partir de `quien-cobra/work/bdns.sqlite` (episodio cci-09, sólo lectura).
Todas las cifras de este informe salen de `data/agregados.json`, `data/top_beneficiarios.json`, `data/organos.json`
y `data/deportes.json`; no hay ninguna cifra escrita a mano.

## 1. Cifras principales

| | 2024 | 2025 |
|---|---:|---:|
| Importe concedido a beneficiarios deportivos | **475,1 M€** | **614,9 M€** |
| Concesiones | 34.493 | 35.692 |
| Entidades beneficiarias distintas | 17.435 | 17.581 |
| Convocatorias distintas | 6.629 | 6.438 |
| % sobre todas las subvenciones a entidades jurídicas en BDNS | 1,17 % | 1,37 % |
| Mediana por entidad y año | 4.787 € | 4.726 € |

Reparto por administración concedente (importe):

| Administración | 2024 | 2025 |
|---|---:|---:|
| Entidades locales | 217,5 M€ (45,8 %) | 208,0 M€ (33,8 %) |
| Comunidades autónomas | 168,6 M€ (35,5 %) | 211,4 M€ (34,4 %) |
| Estado | 88,6 M€ (18,7 %) | 195,3 M€ (31,8 %) |
| Otros | 0,4 M€ | 0,2 M€ |

Reparto por tipo de beneficiario (suma = total; comprobado en el script con `assert`):

| Tipo | 2024 entidades / importe | 2025 entidades / importe |
|---|---:|---:|
| Federaciones españolas | 67 / 59,3 M€ (12,5 %) | 68 / 149,6 M€ (24,3 %) |
| Federaciones autonómicas o territoriales | 892 / 94,8 M€ (20,0 %) | 923 / 101,4 M€ (16,5 %) |
| Clubes y asociaciones deportivas | 14.343 / 218,1 M€ (45,9 %) | 14.287 / 233,8 M€ (38,0 %) |
| SAD y clubes con forma mercantil | 279 / 16,1 M€ (3,4 %) | 263 / 28,2 M€ (4,6 %) |
| Empresas deportivas (gestión, instalaciones, gimnasios, eventos) | 1.072 / 62,1 M€ (13,1 %) | 1.108 / 71,9 M€ (11,7 %) |
| Entidades públicas deportivas (patronatos, institutos, CAR…) | 180 / 4,5 M€ (1,0 %) | 305 / 7,4 M€ (1,2 %) |
| Otras (fundaciones, COE/CPE, asociaciones sin forma de club) | 602 / 20,2 M€ (4,3 %) | 627 / 22,5 M€ (3,7 %) |

Concentración: el 1 % de entidades que más cobra (174 en 2024, 176 en 2025) se lleva el **37,5 %** del importe en 2024
y el **49,1 %** en 2025. Las 10 primeras: 9,8 % y 15,3 %. El salto de 2025 lo explica casi por completo el Consejo
Superior de Deportes: 53,8 M€ concedidos con fecha 2024 frente a 153,2 M€ con fecha 2025 (la convocatoria anual a
federaciones de 2025 —60,0 M€, 64 federaciones— está fechada el 11/07/2025; la de 2024 aparece en noviembre de 2024 con
47,3 M€). Es una diferencia de fechas de concesión, no necesariamente de presupuesto.

Fútbol profesional frente al resto: las entidades con forma mercantil cuyo nombre indica fútbol (SAD/SA/SL) suman
1,7 M€ (0,37 %) en 2024 y 3,1 M€ (0,50 %) en 2025. El fútbol en todas sus formas (clubes, federaciones, SAD) suma
43,1 M€ (9,1 %) y 51,8 M€ (8,4 %). El club de fútbol más subvencionado no es una SAD: la **Agrupación Deportiva Ceuta
Fútbol Club** (asociación, NIF G) recibe 5,3 M€ en 2024 y 13,7 M€ en 2025 de la Ciudad Autónoma de Ceuta (ver
verificación 2). Cuidado: una SAD sin la palabra «fútbol» en el nombre («REAL ZARAGOZA SAD») queda en «SAD otros deportes».

Instrumento: el 94,2 % (2024) y 92,3 % (2025) son subvenciones dinerarias. El resto son sobre todo **garantías**
(25,6 M€ y 37,6 M€: avales de CERSA e ICO a clubes y empresas deportivas, que no son dinero entregado) y algún
préstamo o ventaja fiscal. `agregados.json` → `por_instrumento`.

Por deporte (del nombre del beneficiario): fútbol 9 %, baloncesto 7 %, natación 4 %… y un **34 % (2024) / 28 % (2025)
«sin_clasificar»**: nombres deportivos sin disciplina reconocible («CLUB DEPORTIVO X», «LOGROÑO DEPORTE SA»). Esa
cifra se publica tal cual; no se reparte.

## 2. Método

1. **Universo.** La sqlite de cci-09 contiene 2,18 M concesiones de 2024-2025 a entidades jurídicas (las personas
   físicas, incluidos deportistas becados, se descartaron en esa carga; aquí no se cuentan ni se estiman).
2. **La BDNS no tiene «Deporte» como finalidad** (va dentro de «Cultura»), y el CNAE 93 de la convocatoria es
   demasiado ancho (93.2 es ocio; las convocatorias multisector meten universidades). Por eso el criterio principal es
   el **nombre del beneficiario**: expresiones regulares multilingües (ES/CA/EU/GL) sobre el nombre normalizado
   (sin acentos ni puntuación) que detectan federaciones, clubes (CLUB, CD/CF/UD/SD/CB…, KIROL TALDEA, UNIÓ ESPORTIVA…),
   SAD, patronatos/institutos municipales de deportes, empresas con DEPORT*/SPORT* en el nombre, y una lista de 38
   deportes. Palabras ambiguas (VELA, TIRO, MOTOR, CAZA, MONTAÑA, LUCHA…) sólo cuentan con contexto deportivo
   (DEPORT*, FEDERACIÓN o CLUB). Se excluyen explícitamente prensa deportiva, hostelería (beach club), talleres,
   comercio textil, clubes de jubilados, cofradías de pescadores, caza/pesca sin «deportivo» en el nombre y las
   consejerías/administraciones generales que reciben transferencias.
3. **Clasificación por entidad (NIF)**: basta que uno de los nombres con que aparece sea deportivo; todas sus
   concesiones cuentan. El tipo y el deporte se toman del nombre con mayor importe.
4. **Señal secundaria: convocatorias con sectores CNAE exclusivamente 93.1x** (actividades deportivas): 227
   convocatorias. Decisión: **se incluye**, porque es limpia (ninguna multisector) y aporta beneficiarios de nombre no
   evidente, sobre todo ayuntamientos que reciben ayudas deportivas de diputaciones y cabildos. Aporta poco: 3,8 M€
   (0,8 %) en 2024 y 4,2 M€ (0,7 %) en 2025 (`agregados.json` → `por_senal`). A estas entidades se les asigna tipo
   «entidad pública» si su NIF es P/Q/S y «otro» en caso contrario, y deporte «sin_clasificar».
5. **Determinismo**: sin marcas de tiempo; dos ejecuciones seguidas producen ficheros byte a byte idénticos
   (comprobado con `diff -r`). Tiempo de ejecución: ~100 s.

## 3. Precisión del clasificador (medida, no estimada)

Muestra fija de 100 entidades (`random.Random(18)`), publicada en `data/muestra_validacion.json` y fijada por NIF en
el script (`VALIDACION`), juzgada a mano una sola vez con el criterio «entidad cuya actividad principal es practicar u
organizar un deporte reconocido/federado»:

- **50 positivos al azar → 49 correctos (98 %)**. El fallo: «ASOC VECINAL CULTURAL DEPORTIVA DE BOVED» (asociación
  vecinal). Dos de los 49 son clubes de caza con «deportivo» en el nombre; si no se consideran deporte, 94 %.
- **50 negativos «ambiguos»** (nombres rechazados que contienen DEPORT*, CLUB, SPORT* o ESPORT*) → **11 (22 %) sí eran
  entidades deportivas** (p. ej. «CLUB AGUAMARINA SINCRO», «PATI CLUB VILA-SECA», «CLUB DEPOR ELEMENT CONTACT
  WEIGHTLIFTING», «PINATARIUS WRESTLING CLUB», «CLUB ARQUEIROS DO SIL»). Los otros 39 eran clubes de jubilados, fan
  clubs, cine clubs, bares, consultoras… o nombres que no permiten saberlo («CLUB O PANASCO», «CLUB TAMARAN»).
- Tamaño de ese «pool ambiguo»: 1.950 entidades y 59,0 M€ (2024+2025). Aplicando el 22 %, el orden de magnitud de lo
  que se pierde por ahí es de ~430 entidades y ~13 M€ en dos años (≈1,2 % del total). **No se puede medir** lo que se
  pierde entre entidades cuyo nombre no contiene ninguna palabra deportiva («CLUB VICTORIA», un «REAL CLUB X»
  sin más).
- Antes de fijar la muestra se hicieron dos rondas de desarrollo con semillas 16 y 17 (92 % y 94 % de precisión; 32 %
  de falsos negativos ambiguos en la segunda), cuyos errores mecánicos se corrigieron (siglas «C F» al final,
  «MULTIDEPORTIVO», «SKI», Ñ mal codificada como «&XD1A», federaciones con deporte ambiguo como «FED. ESP. DE VELA»).
  La cifra publicada es la de la muestra final, no la de desarrollo. Si el clasificador cambia, el script recalcula
  la precisión sobre la misma muestra y publica cuántas entidades cambiaron de grupo (`entidades_cuya_clasificacion_cambio_desde_el_muestreo`, ahora 0).

Contraste con un órgano puramente deportivo: de los 207,0 M€ concedidos por el **Consejo Superior de Deportes** en
2024-2025, el clasificador reconoce como deportivos 191,8 M€ (**92,7 %**). Lo que falta son sobre todo transferencias
a comunidades autónomas y universidades (Xunta, Comunidad de Madrid, Universidad de Castilla-La Mancha…), que se
excluyen a propósito, y «CIRCUITS DE CATALUNYA SL» y «UNIPUBLIC SA» (organizadora de La Vuelta).

## 4. Verificaciones manuales contra la BDNS pública

Hechas con la API pública de infosubvenciones.es (`/bdnstrans/api/concesiones/busqueda`, filtrando por número de
convocatoria y fecha) el día de generación de este informe.

1. **Convocatoria 823716** — «Resolución de la Presidencia del CSD por la que se convocan ayudas a las Federaciones
   Deportivas Españolas para el año 2025» (presupuesto 60.013.920 €). Concesiones fechadas el 11/07/2025: la BDNS
   devuelve **64 concesiones, 60.011.917,55 €**; la sqlite local tiene exactamente 64 y 60.011.917,55 €. Las 64 las
   clasifica el script como «federación española». Entre ellas, FED. ESP. DE NATACIÓN (Q2878029D): 4.749.000,55 € en
   ambos sitios. Ficha: https://www.infosubvenciones.es/bdnstrans/GE/es/convocatoria/823716
2. **Agrupación Deportiva Ceuta Fútbol Club (G11902475), 2025** — top 2 del ranking con 13.658.837,46 € en 4
   concesiones. Las cuatro verificadas una a una en la API: 5.363.837,46 € (conv. 842543, 03/06/2025, Consejería de
   Comercio, Turismo, Empleo y Deporte), 2.000.000 € (869322, 26/06/2025), 4.495.000 € (874676, 21/04/2025, Instituto
   Ceutí de Deportes) y 1.800.000 € (813804, 03/07/2025, **garantía** de CERSA, no subvención dineraria). Suma idéntica.
3. **Club Voleibol Melilla (G52009750), 2024** — 1.288.540,66 € en 12 concesiones según `top_beneficiarios.json`. La
   mayor, 1.000.000 € (conv. 764067, 18/04/2024, Consejería de Educación, Juventud y Deportes de Melilla), aparece en la
   API con el mismo beneficiario, importe, fecha y órgano.

## 5. Lo que NO se puede decir con estos datos

- **No es el gasto público en deporte.** Faltan los contratos (gestión de instalaciones, organización de eventos), las
  cesiones de instalaciones y suelo, el gasto directo de ayuntamientos (polideportivos, escuelas municipales con
  personal propio), los patrocinios de empresas públicas y las subvenciones que no se publican en la BDNS. Las
  subvenciones a beneficiarios deportivos son el 1,2-1,4 % de lo que la BDNS registra para entidades jurídicas.
- **No incluye a las personas físicas** (becas a deportistas, ayudas a técnicos): la sqlite de origen sólo carga
  entidades jurídicas.
- **Sólo dos ejercicios**, por fecha de concesión, y la BDNS se completa con retraso (hay altas de septiembre de 2026
  para concesiones de 2024): las cifras pueden crecer. La diferencia 2024→2025 del CSD es en buena parte de fechas.
- **No todo es dinero entregado**: 5-6 % son garantías (avales) y préstamos; están identificados en `por_instrumento`.
- **El clasificador es por nombre**: 98 % de precisión medida y una pérdida no medible de clubes con nombre no evidente,
  además de ~22 % de pérdida en el pool de nombres ambiguos. Las categorías «empresa deportiva» y «otro» mezclan
  gestoras municipales con forma de SA (Logroño Deporte SA, Circuito del Motor y Promoción Deportiva SA) con empresas
  privadas; se publican separadas de clubes y federaciones precisamente por eso.
- **El deporte inferido** está sin clasificar en un 28-34 % del importe; los repartos por deporte son cotas inferiores.
- **Caza y pesca** se cuentan sólo cuando el nombre lleva «deportivo» o es una federación (3-3,6 M€/año, línea
  `caza_pesca` en `deportes.json`); quien no los considere deporte puede restarlos.
