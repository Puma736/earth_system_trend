# Propuesta: detector de condiciones favorables para incendios

> **Estado: propuesta, "posible a ser modificado".** Viene de un documento compartido por el equipo el 14 nov. **No está en el MVP** hasta que el equipo lo decida.

## La idea

Pasar de detectar fenómenos por separado a **relacionar variables**. Se mira qué regiones tienen condiciones que favorecen la propagación del fuego.

Dos conceptos que hay que separar siempre en la app:

| Concepto | Qué es | En el proyecto |
|---|---|---|
| **Riesgo ambiental** | Condiciones de sequedad y propagación | Este módulo (propuesto) |
| **Incendio activo** | Fuego detectado por satélite | `/api/hotspots` (FIRMS, MODIS) |

Que haya condiciones favorables **no significa** que haya un incendio. Los valores funcionan como **indicadores de riesgo**, nunca como una regla de "aquí habrá fuego".

## Cómo se mide: anomalías frente a la historia local

No existe una temperatura ni un porcentaje universal a partir del cual empieza un incendio, porque depende de la región, la estación y la vegetación. Por eso cada variable se compara con **su propio promedio histórico en ese lugar y esa época del año** (Z-score o desviación, ver [metodos.md](metodos.md)).

| Variable | Unidad | Señal de alerta | ¿La tenemos? |
|---|---|---|---|
| Temperatura superficial | °C | Anomalía positiva | 🟡 Tenemos `T2M_MAX` (aire a 2 m, POWER). La de superficie (MODIS LST) sería nueva |
| Humedad del suelo | 0–1 | Anomalía negativa | ✅ `GWETTOP`, `GWETROOT` |
| NDVI | −1 a +1 | Descenso persistente frente a su ciclo estacional | ❌ Es el extra n.º 2 (MODIS vía AppEEARS o Giovanni) |
| Viento | m/s (km/h en pantalla) | Por encima de lo normal del lugar | ❌ Fácil de sumar: POWER tiene `WS2M` y `WS10M` |
| Precipitación | mm/día | Déficit acumulado frente al promedio | ✅ `PRECTOTCORR` |

**Sobre el NDVI:** un NDVI bajo no significa que la vegetación esté seca. Conviene acompañarlo con NDMI o NDWI, que miden el contenido de agua de la vegetación.

**Tres niveles por variable:** condición normal, alerta y favorable. Los cortes se definen en desviaciones estándar respecto de la historia local, por ejemplo menos de 1σ, de 1 a 2σ y más de 2σ (a decidir).

## Lo que mostraría la plataforma

- Mapa de zonas con condiciones de sequedad
- Evolución en el tiempo de cada variable
- Focos activos (ya lo da `/api/hotspots/grid`)
- Superficie quemada: sería nueva, con el producto MODIS MCD64A1
- Vegetación antes y después de un evento: necesita NDVI

## Qué choca con el alcance actual y qué no

- ✅ **Encaja:** anomalías por variable, mostradas por separado, con viento y precipitación. Reusa los datos de POWER que ya bajamos.
- ⚠️ **Cuidado:** combinar los 5 niveles en un solo "índice de riesgo" va contra la regla del alcance: no inventar un índice con pesos. Si se hace, que sea un conteo transparente, por ejemplo "4 of 5 variables in alert", como el tablero de sequía.
- ❌ **Más trabajo:** NDVI/NDMI, temperatura de superficie y superficie quemada son fuentes nuevas, cada una con su descarga y su validación.

## Si el equipo lo aprueba: menor costo primero

1. Sumar `WS2M` a los indicadores de POWER, con poco cambio en `backend/app/data/power.py`.
2. Endpoint `/api/conditions?region=&season=&year=` con el Z-score de cada variable frente a 1991–2020 y su nivel.
3. Recién después: NDVI y superficie quemada.
