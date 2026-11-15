"""Modulo de patrones: PCA y K-means.

Reduccion de dimensionalidad (PCA) y agrupamiento de regiones (K-means).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


def pca_analysis(df, n_components=None, scale: bool = True) -> dict:
    """Analisis de Componentes Principales (PCA).

    Parametros
    ----------
    df : DataFrame o array 2D
        Variables (columnas) x observaciones (filas).
    n_components : int | None
        Numero de componentes. None = min(n_samples, n_features).
    scale : bool
        Estandarizar variables antes de PCA.

    Retorna
    -------
    dict con explained_variance_ratio, cumulative_variance, components (cargas),
    transformed (scores).
    """
    if isinstance(df, pd.DataFrame):
        X = df.copy()
        feature_names = list(df.columns)
    else:
        X = pd.DataFrame(df)
        feature_names = [f"var_{i}" for i in range(X.shape[1])]
    X = X.apply(pd.to_numeric, errors="coerce")
    # imputar NaN con media de columna
    X = X.fillna(X.mean())
    if scale:
        scaler = StandardScaler()
        Xs = scaler.fit_transform(X)
    else:
        Xs = X.to_numpy(dtype=float)
    if n_components is None:
        n_components = min(Xs.shape[0], Xs.shape[1])
    n_components = max(1, min(n_components, Xs.shape[0], Xs.shape[1]))
    pca = PCA(n_components=n_components)
    scores = pca.fit_transform(Xs)
    components = pca.components_  # shape (n_components, n_features)
    loadings = pd.DataFrame(components.T, index=feature_names,
                           columns=[f"PC{i+1}" for i in range(n_components)])
    return {
        "n_components": int(n_components),
        "explained_variance_ratio": [float(v) for v in pca.explained_variance_ratio_],
        "cumulative_variance": [float(v) for v in np.cumsum(pca.explained_variance_ratio_)],
        "eigenvalues": [float(v) for v in pca.explained_variance_],
        "loadings": loadings.to_dict(),
        "scores": scores.tolist(),
    }


def kmeans_clusters(features, n_clusters: int = 3, random_state: int = 42) -> dict:
    """Agrupamiento K-means de regiones/observaciones.

    Parametros
    ----------
    features : DataFrame o array 2D (filas = regiones/obs, columnas = variables)
    n_clusters : int
    random_state : int

    Retorna
    -------
    dict con labels, centers, inertia, n_clusters.
    """
    if isinstance(features, pd.DataFrame):
        X = features.copy()
        index = list(features.index)
    else:
        X = pd.DataFrame(features)
        index = list(range(len(X)))
    X = X.apply(pd.to_numeric, errors="coerce").fillna(0)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    n = min(n_clusters, len(Xs))
    km = KMeans(n_clusters=n, random_state=random_state, n_init=10)
    labels = km.fit_predict(Xs)
    return {
        "n_clusters": int(n),
        "labels": {str(index[i]): int(labels[i]) for i in range(len(labels))},
        "centers": km.cluster_centers_.tolist(),
        "inertia": float(km.inertia_),
    }
