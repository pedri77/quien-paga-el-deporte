# ¿Quién paga el deporte?

Todas las subvenciones públicas a entidades deportivas de España en 2024 y 2025, entidad a entidad,
desde la **Base de Datos Nacional de Subvenciones** (BDNS). Episodio `cci-16` de la serie
[«Construido con IA»](https://iacedemy.com/free/yt/construido-con-ia/) de IAcademy; hermano de
[¿Quién cobra?](https://pedri77.github.io/quien-cobra/) (todas las subvenciones), cuya descarga reutiliza.

- **Web:** <https://pedri77.github.io/quien-paga-el-deporte/>
- **Fuente:** BDNS, IGAE · Ministerio de Hacienda, API pública de concesiones (altas hasta septiembre de 2026).

## Qué sale de los datos (2025)

- **614,9 M€** concedidos a **17.581 entidades deportivas** en 35.692 concesiones: el 1,37 % de todas las subvenciones a entidades jurídicas.
- **Mediana por entidad: 4.726 €.** El **1 % de entidades (176) se lleva el 49,1 %**; las 10 primeras, el 15,3 %.
- Quién la da: comunidades 34,4 %, entidades locales 33,8 %, Estado 31,8 %. Los ayuntamientos hacen el 67 % de las concesiones con un tercio del dinero; el Estado, pocas y grandes (el CSD solo concede el 22,8 %).
- Quién la cobra: clubes 38,0 % (14.287 entidades), federaciones españolas 24,3 % (68), autonómicas 16,5 %, empresas deportivas 11,7 %, SAD 4,6 %.
- **Fútbol: 8,4 %** de lo identificable por nombre; las SAD de fútbol, 0,5 %. El club de fútbol que más cobra es la AD Ceuta FC (13,7 M€), una asociación. La entidad nº 1 es el Circuito del Motor (Cheste), 16,5 M€ de la Generalitat Valenciana.
- Un 6 % del importe son garantías y préstamos, no dinero entregado: separado y dicho.

## Cómo se aísla «deporte» en una base que no tiene esa categoría

La BDNS clasifica el deporte dentro de «Cultura». El clasificador identifica al beneficiario por su nombre
(federaciones, clubes, SAD, patronatos, empresas deportivas; 38 deportes) y añade como señal secundaria las
convocatorias con CNAE exclusivamente 93.1x (0,7 % del importe). **Precisión medida a mano** sobre 100 entidades
fijadas en el script: 49/50 positivos correctos; 11/50 negativos ambiguos eran deportivos (pérdida ≈ 13 M€ en dos
años, 1,2 %). Reconoce el 92,7 % de lo concedido por el Consejo Superior de Deportes. Los clubes sin palabra
deportiva en el nombre no se recuperan ni se estiman. Un 28 % del importe va a entidades deportivas cuyo deporte
no se deduce del nombre: se publica como `sin_clasificar`.

## Lo que NO es

- No es el gasto público en deporte: faltan gasto directo en instalaciones, contratos, cesiones y deporte escolar.
- Solo entidades jurídicas (la BDNS anonimiza personas físicas).
- 2025 crece sobre 2024 en buena parte por fechas de concesión (CSD: 149,6 M€ frente a 59,3 M€); no es una tendencia.
- «Fútbol» es lo que dice el nombre: «Real Zaragoza SAD» queda en SAD de otros deportes.

## Reproducirlo

```bash
# requiere la sqlite del episodio cci-09 (quien-cobra/work/bdns.sqlite), que se abre en solo lectura
python3 scripts/deporte_build.py          # -> data/*.json + data/informe.md (~2 min)
cp data/*.json site/data/                 # la web lee de site/data/
```

Informe completo, con las tres verificaciones contra la API de la BDNS: [`data/informe.md`](data/informe.md).

Código bajo **MIT** (`LICENSE`).
