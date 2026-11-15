"""Motor cientifico generico: DataAnalyzer.

Agnostico al dominio: funciona con cualquier conjunto de datos numericos
temporales (clima, ventas, sensores, salud, finanzas, etc.).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from . import trends, anomalies, relations, changepoints, patterns, forecasting, extensions, domains


class DataAnalyzer:
    def __init__(self, data: Any, entity_name: Optional[str] = None,
                 date_col: Optional[str] = None, target_cols: Optional[List[str]] = None,
                 domain: str = "general", non_negative: Union[bool, List[str], Dict[str, bool]] = False,
                 forecast_steps: int = 12):
        self.entity_name = entity_name or "Entidad"
        self.domain = domain or "general"
        self.date_col = date_col
        self.target_cols = target_cols
        self.non_negative = non_negative
        self.forecast_steps = forecast_steps
        self.df = self._to_dataframe(data)
        self._prepare()
        self.frequency = self._infer_frequency()
        self.seasonal_period = self._infer_seasonal_period()

    # ---- compatibilidad hacia atras ----
    @property
    def region(self):
        return self.entity_name

    # ---- conversion ----
    def _to_dataframe(self, data: Any) -> pd.DataFrame:
        if isinstance(data, pd.DataFrame):
            return data.copy()
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                # podria ser CSV
                return pd.read_csv(data)
        if isinstance(data, dict):
            if "variables" in data and "dates" in data:
                df = pd.DataFrame(data["variables"])
                df.insert(0, "date", pd.to_datetime(data["dates"]))
                if "entity_name" in data or "region" in data:
                    self.entity_name = data.get("entity_name", data.get("region", self.entity_name))
                if "domain" in data:
                    self.domain = data.get("domain", self.domain)
                return df
            if "data" in data and isinstance(data["data"], dict):
                df = pd.DataFrame(data["data"])
                if "entity_name" in data or "region" in data:
                    self.entity_name = data.get("entity_name", data.get("region", self.entity_name))
                if "domain" in data:
                    self.domain = data.get("domain", self.domain)
                return df
            df = pd.DataFrame(data)
            return df
        if isinstance(data, list):
            return pd.DataFrame(data)
        raise ValueError("Formato de datos no soportado.")

    def _prepare(self):
        if self.date_col is None:
            candidates = [c for c in self.df.columns if any(k in str(c).lower() for k in ("date", "fecha", "time", "datetime", "timestamp"))]
            if candidates:
                self.date_col = candidates[0]
            else:
                for c in self.df.columns:
                    if not pd.api.types.is_numeric_dtype(self.df[c]):
                        self.date_col = c
                        break
        if self.date_col is not None and self.date_col in self.df.columns:
            try:
                self.df[self.date_col] = pd.to_datetime(self.df[self.date_col])
            except Exception:
                pass
            self.df = self.df.sort_values(self.date_col).reset_index(drop=True)
        # variables
        self.variables = []
        for c in self.df.columns:
            if c == self.date_col:
                continue
            if pd.api.types.is_numeric_dtype(self.df[c]):
                self.variables.append(c)
        if self.target_cols:
            self.variables = [v for v in self.variables if v in self.target_cols]

    def _dates(self) -> List[str]:
        if self.date_col is not None and self.date_col in self.df.columns:
            return [str(d) for d in self.df[self.date_col].tolist()]
        return [str(i) for i in range(len(self.df))]

    def _infer_frequency(self) -> str:
        if self.date_col is None or self.date_col not in self.df.columns:
            return "N"  # sin fecha
        try:
            freq = pd.infer_freq(self.df[self.date_col])
        except Exception:
            freq = None
        if not freq:
            return "N"
        f = freq.upper()
        if f.startswith("D"):
            return "D"
        if f.startswith("W"):
            return "W"
        if f.startswith("M") or f.startswith("MS") or f.startswith("ME"):
            return "M"
        if f.startswith("Q"):
            return "Q"
        if f.startswith("Y") or f.startswith("A"):
            return "Y"
        if f.startswith("H"):
            return "H"
        return f

    def _infer_seasonal_period(self) -> int:
        mapping = {"D": 7, "W": 52, "M": 12, "Q": 4, "Y": 1, "H": 24}
        s = mapping.get(self.frequency, 0)
        n = len(self.df)
        if s >= 2 and n < 2 * s:
            return 0
        return s

    def _is_non_negative(self, var: str) -> bool:
        if isinstance(self.non_negative, bool):
            return self.non_negative
        if isinstance(self.non_negative, list):
            return var in self.non_negative
        if isinstance(self.non_negative, dict):
            return bool(self.non_negative.get(var, False))
        return False

    def analyze(self, forecast_steps: Optional[int] = None) -> Dict[str, Any]:
        if forecast_steps is None:
            forecast_steps = self.forecast_steps
        results: Dict[str, Any] = {
            "entity_name": self.entity_name,
            "domain": self.domain,
            "n_observations": int(len(self.df)),
            "date_range": {
                "start": self._dates()[0] if self._dates() else None,
                "end": self._dates()[-1] if self._dates() else None,
            },
            "frequency": self.frequency,
            "seasonal_period": self.seasonal_period,
            "variables": self.variables,
            "trends": {},
            "anomalies": {},
            "relations": {},
            "changepoints": {},
            "forecast": {},
            "patterns": {},
            "extensions": {},
            "series": {},
        }

        for v in self.variables:
            s = self.df[v]
            results["trends"][v] = {
                "linear_regression": trends.linear_regression(s),
                "mann_kendall": trends.mann_kendall(s),
                "sens_slope": trends.sens_slope(s),
            }

        for v in self.variables:
            z = anomalies.z_score(self.df[v])
            anom_df = anomalies.detect_anomalies(self.df[v], threshold=2.0)
            n_anom = int(anom_df["is_anomaly"].sum()) if "is_anomaly" in anom_df else 0
            last_z = float(z.iloc[-1]) if len(z) else None
            nn = pd.to_numeric(self.df[v], errors="coerce")
            results["anomalies"][v] = {
                "n_anomalies_z2": n_anom,
                "last_z_score": last_z,
                "mean": float(nn.mean()),
                "std": float(nn.std()),
                "min": float(nn.min()),
                "max": float(nn.max()),
            }

        for i, a in enumerate(self.variables):
            for b in self.variables[i + 1:]:
                key = f"{a}__vs__{b}"
                results["relations"][key] = {
                    "pearson": relations.pearson(self.df[a], self.df[b]),
                    "spearman": relations.spearman(self.df[a], self.df[b]),
                    "best_lag": relations.best_lag(self.df[a], self.df[b], max_lag=min(12, len(self.df) // 4)),
                    "cross_correlation": relations.cross_correlation(self.df[a], self.df[b], max_lag=min(6, len(self.df) // 4)).to_dict(orient="records"),
                }

        for v in self.variables:
            results["changepoints"][v] = {
                "pelt": changepoints.pelt(self.df[v]),
                "cusum": changepoints.cusum(self.df[v]),
            }

        for v in self.variables:
            nn = self._is_non_negative(v)
            # usar SARIMA con s dinamico
            fc = forecasting.sarima_forecast(self.df[v], order=(1, 1, 1), steps=forecast_steps,
                                            s=self.seasonal_period, non_negative=nn)
            results["forecast"][v] = fc

        # Extensiones: FFT sobre la primera variable
        results["extensions"] = {}
        if self.variables:
            try:
                results["extensions"]["fft"] = extensions.fft_frequencies(self.df[self.variables[0]])
            except Exception as e:
                results["extensions"]["fft"] = {"error": str(e)}

        try:
            pca_df = self.df[self.variables].copy()
            pca_res = patterns.pca_analysis(pca_df, n_components=min(len(self.variables), 5))
            results["patterns"]["pca"] = {
                "explained_variance_ratio": pca_res["explained_variance_ratio"],
                "cumulative_variance": pca_res["cumulative_variance"],
                "loadings": pca_res["loadings"],
            }
        except Exception as e:
            results["patterns"]["pca"] = {"error": str(e)}

        results["series"] = {
            "dates": self._dates(),
            "values": {v: [None if pd.isna(x) else float(x) for x in pd.to_numeric(self.df[v], errors="coerce")] for v in self.variables},
        }
        results["conclusiones_cientificas"] = self._build_conclusions(results, forecast_steps)
        return results

    def _build_conclusions(self, results, forecast_steps) -> List[str]:
        concl = []
        concl.append(f"Analisis de '{self.entity_name}' (dominio: {self.domain}) con {len(self.df)} observaciones y {len(self.variables)} variables: {', '.join(self.variables)}.")

        for v in self.variables:
            mk = results["trends"][v]["mann_kendall"]
            lr = results["trends"][v]["linear_regression"]
            if isinstance(mk, dict) and "error" not in mk:
                trend = mk.get("trend", "sin tendencia")
                p = mk.get("p_value", 1.0)
                slope = mk.get("sens_slope", 0.0)
                if p is not None and p < 0.05:
                    concl.append(f"- {v}: tendencia {trend} significativa (p={p:.4f}), pendiente de Sen={slope:.4f} por periodo.")
                else:
                    concl.append(f"- {v}: sin tendencia monotónica significativa (p={p:.4f}).")
            if isinstance(lr, dict) and "error" not in lr:
                r2 = lr.get("r_squared")
                if r2 is not None and r2 > 0.5:
                    concl.append(f"  Regresion lineal explica {r2*100:.1f}% de la varianza (R2={r2:.3f}).")

        for v in self.variables:
            a = results["anomalies"][v]
            n = a.get("n_anomalies_z2", 0)
            lz = a.get("last_z_score")
            if n and n > 0:
                concl.append(f"- {v}: {n} anomalias (|Z|>2). Ultimo Z-score={lz:.2f}." if lz is not None else f"- {v}: {n} anomalias (|Z|>2).")
            else:
                concl.append(f"- {v}: sin anomalias extremas. Ultimo Z-score={lz:.2f}." if lz is not None else f"- {v}: sin anomalias extremas.")

        # alertas de dominio
        for v in self.variables:
            domains.apply_alerts(self.domain, v, results["trends"][v], results["anomalies"][v], concl)

        for v in self.variables:
            cp = results["changepoints"][v]
            pelt = cp.get("pelt", {})
            bks = pelt.get("breakpoints", [])
            if bks:
                idx = bks[0]
                fecha = self._dates()[idx] if idx < len(self._dates()) else idx
                concl.append(f"- {v}: punto de cambio alrededor del indice {idx} (fecha aprox. {fecha}).")
            else:
                cus = cp.get("cusum", {})
                if cus.get("change_index") is not None:
                    idx = cus["change_index"]
                    fecha = self._dates()[idx] if idx < len(self._dates()) else idx
                    concl.append(f"- {v}: CUSUM sugiere cambio alrededor del indice {idx} (fecha aprox. {fecha}).")

        for key, val in results["relations"].items():
            p = val["pearson"]
            bl = val["best_lag"]
            if isinstance(p, dict) and p.get("r") is not None and abs(p["r"]) > 0.5 and p.get("p_value", 1) < 0.05:
                concl.append(f"- Relacion fuerte entre {key.replace('__vs__', ' y ')}: Pearson r={p['r']:.3f} (p={p['p_value']:.4f}).")
            if isinstance(bl, dict) and bl.get("lag") not in (None, 0) and bl.get("correlation") is not None and abs(bl["correlation"]) > 0.4:
                concl.append(f"  Mejor desfase temporal: lag={bl['lag']} (r={bl['correlation']:.3f}).")

        for v in self.variables:
            fc = results["forecast"][v]
            if isinstance(fc, dict) and "error" not in fc and fc.get("forecast"):
                nn = pd.to_numeric(self.df[v], errors="coerce")
                hist_mean = float(nn.mean())
                fc_mean = float(np.mean(fc["forecast"]))
                if hist_mean != 0:
                    pct = (fc_mean - hist_mean) / abs(hist_mean) * 100
                    concl.append(f"- Pronostico {v} ({forecast_steps} pasos): media proyectada={fc_mean:.3f} vs historica={hist_mean:.3f} ({pct:+.1f}%).")

        pca = results["patterns"].get("pca", {})
        if isinstance(pca, dict) and "explained_variance_ratio" in pca:
            ev = pca["explained_variance_ratio"]
            if ev:
                concl.append(f"- PCA: el primer componente explica {ev[0]*100:.1f}% de la varianza total.")

        concl.append("Nota: correlacion y sucesion temporal no implican causalidad; controlar estacionalidad y factores externos.")
        return concl

    def to_dict(self) -> Dict[str, Any]:
        return self.analyze()


# alias de compatibilidad
RegionAnalyzer = DataAnalyzer