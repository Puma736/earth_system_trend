"""Año de cambio con la prueba de Pettitt (no paramétrica).

Busca el punto donde la serie pasa a tener otro nivel y da un p-valor aproximado,
a diferencia del CUSUM, que siempre devuelve una fecha aunque no haya cambio.
Pettitt (1979): U_t = suma de sign(x_j - x_i) para i <= t < j; K = max |U_t|;
p ≈ 2·exp(-6K² / (n³ + n²)).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ChangePoint:
    # Primer año del nuevo nivel.
    year: int
    p_value: float
    mean_before: float
    mean_after: float


def pettitt(years: list[int], values: list[float]) -> ChangePoint | None:
    n = len(values)
    if n < 4:
        return None
    x = np.asarray(values, dtype=float)
    signs = np.sign(x[None, :] - x[:, None])  # signs[i, j] = sign(x_j - x_i)
    # U_t para t = 0..n-2: pares con i <= t < j.
    u = np.array([signs[: t + 1, t + 1 :].sum() for t in range(n - 1)])
    t = int(np.argmax(np.abs(u)))
    k = float(abs(u[t]))
    if k == 0:
        return None
    p = min(1.0, 2 * math.exp(-6 * k * k / (n**3 + n**2)))
    return ChangePoint(
        year=years[t + 1],
        p_value=p,
        mean_before=float(x[: t + 1].mean()),
        mean_after=float(x[t + 1 :].mean()),
    )
