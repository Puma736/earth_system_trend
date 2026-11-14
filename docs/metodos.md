# Métodos: qué usamos y qué queda fuera

Resume la **"Guía de algoritmos matemáticos para análisis de datos científicos"**, compartida por el equipo el 14 nov, y la cruza con lo que ya hace el backend. Decide qué métodos entran según el alcance de **sequía + focos de calor** (Santa Cruz, Bolivia).

Regla del alcance: **no inventamos un índice con pesos**. Mostramos cada evidencia por separado, que es lo que se puede defender ante el jurado.

## Resumen

| Categoría | Método | Estado en el proyecto | Dónde |
|---|---|---|---|
| Tendencias | Mann-Kendall | ✅ Usado, **con la corrección de Hamed-Rao** por autocorrelación | `backend/app/stats/trend.py` |
| Tendencias | Pendiente de Sen | ✅ Usado, expresado por década | `trend.py` |
| Tendencias | Regresión lineal | 🟡 Pendiente, **solo como control** (tarjeta B4) | — |
| Relaciones | Spearman | ✅ Usado en el puente sequía–focos | `trend.py`, `/api/link` |
| Relaciones | Pearson | ❌ No: los focos no siguen una distribución normal y hay años extremos (2019, 2024) | — |
| Relaciones | Correlación cruzada (con desfase) | 💡 Extra posible | — |
| Anomalías | Z-score, desviación del promedio histórico | 💡 Propuesto para el caso guiado "Were 2019 and 2024 dry years?" | — |
| Cambios | Puntos de cambio (CUSUM, PELT) | 💡 Extra posible | — |
| Patrones | PCA, K-means | ❌ Fuera del MVP (decidido en ALCANCE-SEQUIA-FUEGO.md §6) | — |
| Predicción | ARIMA, SARIMA, Prophet | ❌ Fuera del MVP: "tendencia no es pronóstico" | — |
| Extensión | Kriging, Monte Carlo, GEV, FFT, clasificación | ❌ Fuera del alcance de la hackatón | — |
| Varias pruebas | FDR de Benjamini-Hochberg | ✅ Usado entre los 6 indicadores de sequía. La guía no lo menciona, pero hace falta | `trend.py` |

## Lo que ya usamos

### Mann-Kendall con Hamed-Rao

La guía describe el Mann-Kendall original. Nosotros usamos la **variante de Hamed-Rao** (`pymannkendall.hamed_rao_modification_test`).

- **Por qué:** las series climáticas anuales tienen autocorrelación (un año seco suele seguir a otro seco). El Mann-Kendall original no la tiene en cuenta y da p-valores demasiado chicos, o sea, falsas "tendencias reales".
- **Respaldo:** si la serie es plana o una recta perfecta, Hamed-Rao no se puede calcular. En ese caso usamos el Mann-Kendall original.
- **Mínimo de datos:** 10 años. Con menos devolvemos `"Not enough data"`. Ojo: el ejemplo de la guía usa 5 meses, que con datos reales no alcanzan.

### Pendiente de Sen

Se calcula con la misma fórmula que la guía: la mediana de las pendientes entre todos los pares. La hace `scipy.stats.theilslopes` sobre los años reales, así que funciona aunque falte un año.
- La multiplicamos por 10 para dar el **cambio por década**.
- Pendiente (B4): el rango del 95 % que también devuelve `theilslopes`.

### Spearman

Para el puente: ¿los años más secos tienen más focos?
- Se eligió en lugar de Pearson porque solo pide que la relación sea monótona y resiste años extremos.
- Siempre va con el texto **"Relationship, not proof of cause."**

### Regresión lineal (pendiente)

Solo como control de Sen (`scipy.stats.linregress`). Si las dos dan direcciones distintas, se muestra una nota. No reemplaza a Mann-Kendall.

## Ideas de la guía que pueden sumar (extras, después del MVP)

1. **Anomalías por año (Z-score).** Para cada año, cuántas desviaciones estándar se aleja del promedio de un período base (por ejemplo 1991–2020).
   - Contesta directo el caso guiado "Were 2019 and 2024 dry years?". Por ejemplo, "2024: soil moisture −2.4σ".
   - Es barato: sale de las series que `/api/drought` ya calcula.
2. **Correlación cruzada con desfase.** ¿La lluvia de la estación húmeda (oct–mar) anticipa los focos de la estación seca siguiente? Es un desfase de 1 temporada sobre la misma serie de `/api/link`.
3. **Puntos de cambio (PELT, librería `ruptures`).** Fecha en qué año cambió el régimen de lluvia o de focos. Hay que presentarlo con cuidado: con 23 años de focos, un "quiebre" puede ser ruido.

Lo que la guía lista en Patrones, Predicción y Extensión queda fuera: no lo pide el reto y no se puede validar bien en un fin de semana.
