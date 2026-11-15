# Comparación de algoritmos: tablero frente a velaxd

Revisión del 14 nov 2026. Compara las estadísticas del tablero (`/`) con lo que trajo la rama `velaxd` para la pantalla `/investigation`:

- **Tablero:** [`backend/app/stats/trend.py`](../backend/app/stats/trend.py), que usa [`backend/app/services.py`](../backend/app/services.py).
- **velaxd:** la librería [`ALGORITMOS/src/sci_lab_math`](../ALGORITMOS/src/sci_lab_math) y el motor [`backend/app/investigate.py`](../backend/app/investigate.py), que tiene además una copia de las pruebas en Python puro.

## Respuesta corta

- **Iguales en la fórmula:** Mann-Kendall, la pendiente de Sen y Spearman. Pero velaxd los aplica de otra forma, y con datos que tienen mucha memoria eso cambia los resultados (ver abajo).
- **Solo en velaxd:** anomalías con Z-score, CUSUM, correlación con desfase, PCA, FFT y pronóstico. Varias funciones de la librería no las llama nadie.
- **Solo en el tablero:** la corrección de Hamed-Rao, el FDR, el rango del 95 % de Sen, el control con regresión lineal y, sobre todo, **datos reales**. `investigate.py` genera series simuladas.

**Qué motor corre hoy.** `sci_lab_math` necesita pandas, scikit-learn, statsmodels, ruptures y pykrige. Si no están instalados, `investigate.py` usa su copia en Python puro y `/health` responde `"engine": "local"`. Las dos versiones dan los mismos resultados (ver "Cómo se midió").

## Algoritmo por algoritmo

| Algoritmo | Tablero | velaxd | Veredicto |
|---|---|---|---|
| **Mann-Kendall** | Hamed-Rao (corrige la autocorrelación) sobre la media anual de la época | Original, sin corrección, sobre los **meses crudos**, con el ciclo estacional incluido | **Similar, no igual.** Su copia en Python puro da el mismo p que `pymannkendall.original_test` |
| **Pendiente de Sen** | `scipy.stats.theilslopes` sobre los años reales, por década, con rango del 95 % | Mediana de las pendientes por mes, sin rango | **Mismo cálculo.** El tablero acepta años faltantes y da el rango |
| Regresión lineal | Control: avisa si contradice a Sen | Calcula R² y lo menciona en la conclusión si pasa de 0,5 | Similar, con otro propósito |
| **FDR (Benjamini-Hochberg)** | Sí, entre los 6 indicadores de sequía | No | **Solo en el tablero** |
| **Spearman** | Sí, en el puente entre sequía y focos | Está en `relations.py`, pero `investigate.py` no lo llama | Igual, sin uso en velaxd |
| Pearson con desfase | No | Prueba 25 desfases (−12 a +12) y se queda con el de mayor \|r\| | **Solo en velaxd** |
| Anomalías (\|Z\| > 2) | No | Z-score contra la media de toda la serie | **Solo en velaxd** |
| CUSUM (fecha de cambio) | No | Mes donde la suma acumulada de desvíos es máxima | **Solo en velaxd** |
| PCA | No | Parte de la varianza que explica el primer componente | **Solo en velaxd** |
| FFT | No | Ciclo dominante de la serie | **Solo en velaxd** |
| ARIMA/SARIMA | No | Solo con statsmodels instalado. Si no, prolonga la recta de Sen | **Solo en velaxd** (hoy no corre) |
| PELT, K-means, Kriging, Monte Carlo, desviación MAD | No | Programados en la librería, pero **nadie los llama** | Sin uso |
| Datos | NASA POWER (MERRA-2) y FIRMS (MODIS) | Generador con semilla: ciclo estacional, ruido y una sequía agregada a propósito en el último 30 % del período | **Completamente distinto** |

## Hallazgos

### 1. Mann-Kendall sobre meses da falsas tendencias cuando los datos tienen memoria

Simulamos series **sin ninguna tendencia** y contamos en cuántas cada método dice "tendencia significativa" (p < 0,05). Con un método correcto, la tasa debería rondar el 5 %.

| Memoria mensual (phi) | velaxd: MK original sobre 288 meses | Tablero: Hamed-Rao sobre 24 medias de jun–oct |
|---|---|---|
| 0,6 (moderada) | 7,8 % | 8,0 % |
| 0,9 (fuerte) | **57 %** | 23 % |
| 0,97 (muy fuerte) | **73 %** | 26 % |

- Con memoria moderada, los dos métodos se parecen.
- Con memoria fuerte, que es lo típico en la humedad del suelo, el método de velaxd marca tendencia en más de la mitad de los casos sin que exista.
- El Mann-Kendall sobre meses con ciclo estacional tampoco es la prueba pensada para eso. Para datos mensuales la indicada sería el Mann-Kendall estacional.

**Limitación del tablero:** con memoria fuerte y solo 24 años, Hamed-Rao también exagera (23–26 % en lugar de 5 %). Conviene tenerlo en cuenta al leer los focos (2003–2025) y los períodos cortos.

### 2. Los resultados de `/investigation` ya vienen decididos por el generador

Como el generador agrega una sequía al final de cualquier período, en 12 consultas con regiones y períodos distintos el motor dijo que la lluvia "baja significativamente" en 10. Por eso la pantalla muestra el aviso de datos simulados.

### 3. Los desfases no corrigen las pruebas múltiples

- `best_lag` elige el mejor de 25 desfases y reporta su p como si hubiera hecho una sola prueba.
- Tampoco hay FDR entre variables ni entre pares.
- En datos mensuales, el ciclo de las estaciones domina esas correlaciones. El propio texto de velaxd lo advierte: "puede ser la estación".

### 4. Detalles menores

- **Z-score:** se calcula contra la media de toda la serie, sin quitar la tendencia. El final de una serie con tendencia siempre sale como anomalía.
- **CUSUM:** siempre devuelve una fecha, aunque no haya cambio, porque no tiene prueba de significancia.
- **Mann-Kendall en Python puro:** no corrige los empates. El efecto es chico.
- **Errores silenciosos:** si `sci_lab_math` falla, `investigate.py` atrapa el error y pasa al modo local sin avisar.

## Conclusión

- **El tablero es más riguroso en lo que hace:** tendencia y relación sobre datos reales, con corrección por autocorrelación y por pruebas múltiples.
- **velaxd es más amplio**, pero hoy sus conclusiones no valen: usa datos simulados, y la tendencia sobre meses crudos y los desfases sin corregir pueden dar falsos positivos incluso con datos reales.

### Qué conviene llevar al tablero

Sobre las series reales que ya calcula el backend, de más a menos valor. **Estado (15 nov):** los 4 ya están en el tablero; el detalle está en [metodos.md](metodos.md).

1. **Anomalía y puesto de cada año.** Cuánto se aparta un año como 2019 o 2024 de lo normal (período base 1991–2020, en σ, y en la lluvia también como % de lo normal), más su puesto ("el 2.º año con más focos de 23"). Contesta directo "¿fueron años secos?".
2. **Desfase de una temporada.** ¿Una época húmeda (oct–mar) pobre anticipa más focos en la época seca siguiente? Un solo desfase fijado de antemano, con Spearman y FDR, no 25 elegidos después.
3. **Aviso de autocorrelación.** Una nota cuando la serie es corta y tiene mucha memoria, porque ahí Hamed-Rao también exagera.
4. **Año de cambio con p-valor (Pettitt)**, en lugar de un CUSUM que siempre devuelve una fecha. Solo si p < 0,05 y con un texto prudente.

### Qué no conviene llevar al tablero, y por qué

| De velaxd | Por qué no |
|---|---|
| Mann-Kendall sobre meses crudos | Ya usamos medias anuales por época, que quitan el ciclo estacional. Sobre meses da falsas tendencias (57–73 % con memoria fuerte) |
| Pearson | Los focos tienen años extremos (2019, 2024) y no son normales. Spearman, que ya usamos, es el adecuado |
| Correlación cruzada con 25 desfases | En datos mensuales la domina el ciclo de las estaciones. Elegir el mejor de 25 sin corregir fabrica relaciones. Lo útil es el desfase de una temporada (punto 2) |
| CUSUM | Siempre devuelve una fecha, aunque no haya cambio. Lo reemplaza Pettitt (punto 4) |
| PELT (ruptures) | La penalización es arbitraria, no da p-valor y con 23–45 puntos encuentra quiebres de ruido. Y suma una dependencia pesada |
| PCA | Que los 6 indicadores se mueven juntos ya se sabe: lluvia, suelo y evapotranspiración dependen del agua. El "% de varianza del PC1" no contesta ninguna pregunta del tablero y empuja hacia un índice combinado, que está fuera del alcance |
| K-means | Solo hay 3 regiones: no hay nada que agrupar |
| FFT | Sobre meses siempre da 12 meses, el ciclo anual que ya conocemos. Sobre 45 años no alcanza para detectar ciclos como El Niño con confianza |
| ARIMA/SARIMA | "Tendencia no es pronóstico": con 23–45 valores anuales, un pronóstico tendría intervalos enormes y se leería como una predicción |
| Kriging | POWER ya viene en grilla (MERRA-2) y FIRMS son conteos por celda. Interpolar conteos no tiene sentido físico |
| Monte Carlo | Es un movimiento browniano geométrico, un modelo de precios financieros, no de clima |
| R², desviación MAD, alertas de "finanzas" e "industria" | El R² no agrega nada a Sen y su p. El MAD queda cubierto por la anomalía y el puesto. Las alertas son de otros dominios |
| Generador de series y conclusiones automáticas | Son datos inventados. El tablero solo muestra datos reales |

## Cómo se midió

Todo con el entorno del backend (numpy, scipy y pymannkendall). Sin red y sin datos reales.

- **Equivalencia de fórmulas.** En 200 series al azar de 24 valores, la copia en Python puro de `investigate.py` frente a las librerías:

  | Función | Diferencia máxima |
  |---|---|
  | Sen frente a `scipy.stats.theilslopes` | 0 |
  | p de Mann-Kendall frente a `pymannkendall.original_test` | 1,5 × 10⁻⁷ |
  | Primer componente de PCA frente a los autovalores de numpy | 4 × 10⁻¹⁶ |
  | p de Pearson (aproximación de Fisher) frente a `scipy.stats.pearsonr` | 0,004 |

- **Falsas tendencias.**
  - Serie mensual de 24 años (288 meses): ciclo estacional `3·sin(2πt/12)` más ruido AR(1) con phi de 0,6, 0,9 y 0,97. Sin tendencia.
  - velaxd: `pymannkendall.original_test` sobre los 288 meses.
  - Tablero: `trend()` de `stats/trend.py` sobre la media de junio a octubre de cada año.
  - 400 repeticiones con phi 0,6 y 300 con phi 0,9 y 0,97.
- **Motor de velaxd.**
  - Llamamos a `run_investigation` con la variable precipitación.
  - Regiones: `bolivia`, `la_paz`, `santa_cruz` y `chaco`.
  - Períodos: 2001–2024, 2010–2015 y 2001–2005.
  - Contamos en cuántas la dirección salió `"down"`.
