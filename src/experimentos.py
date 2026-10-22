"""Experimentos con repeticiones (punto 7 del enunciado).

Cada repetición usa una semilla distinta; dentro de una repetición ambas
políticas reciben los mismos pedidos (números aleatorios comunes), así que las
diferencias se analizan por pares.
"""

import numpy as np
import pandas as pd
from scipy import stats

from . import grafo as g
from . import simulacion as s

METRICAS = [
    "pedidos",
    "entregas puntuales",
    "puntualidad (%)",
    "espera promedio (min)",
    "solicitud→entrega promedio (min)",
    "utilización (%)",
    "tiempo adicional (min)",
]


def correr(escenarios=s.ESCENARIOS, repeticiones=30, vehiculos=8, horas=8.0, G=None,
           semilla_inicial=1):
    """Una fila por (escenario, semilla, política) con sus métricas."""
    if G is None:
        G = g.construir_grafo(g.cargar_matriz())
    filas = []
    for escenario, tasa in escenarios.items():
        for semilla in range(semilla_inicial, semilla_inicial + repeticiones):
            p = s.Parametros(pedidos_por_hora=tasa, vehiculos=vehiculos,
                             horas_recepcion=horas, semilla=semilla)
            _, resultados, _ = s.comparar(p, G)
            for politica, res in resultados.items():
                filas.append({"escenario": escenario, "pedidos por hora": tasa,
                              "vehículos": vehiculos, "semilla": semilla,
                              "política": politica, **res["metricas"]})
    return pd.DataFrame(filas)


def intervalo(valores, confianza=0.95):
    """Media y semiancho del intervalo de confianza t de Student."""
    valores = np.asarray(valores, dtype=float)
    n = len(valores)
    media = valores.mean()
    if n < 2:
        return media, np.nan
    semiancho = stats.t.ppf((1 + confianza) / 2, n - 1) * valores.std(ddof=1) / np.sqrt(n)
    return media, semiancho


def resumen(df, metricas=METRICAS, por=("escenario", "política")):
    """Tabla 'media ± IC95' por grupo, y otra con los valores numéricos."""
    filas_txt, filas_num = {}, {}
    for clave, grupo in df.groupby(list(por), sort=False):
        filas_txt[clave], filas_num[clave] = {}, {}
        for m in metricas:
            media, semiancho = intervalo(grupo[m])
            filas_num[clave][m] = media
            filas_num[clave][m + " ±"] = semiancho
            filas_txt[clave][m] = f"{media:.1f} ± {semiancho:.1f}"
    return (pd.DataFrame(filas_txt).T.rename_axis(list(por)),
            pd.DataFrame(filas_num).T.rename_axis(list(por)))


def diferencias_pareadas(df, metricas=METRICAS[1:]):
    """Recomendada − Actual por semilla, con IC95 y prueba t pareada."""
    filas = {}
    for escenario, grupo in df.groupby("escenario", sort=False):
        pares = grupo.pivot(index="semilla", columns="política")
        filas[escenario] = {}
        for m in metricas:
            diferencia = pares[(m, "Recomendada")] - pares[(m, "Actual")]
            media, semiancho = intervalo(diferencia)
            if diferencia.std(ddof=1) > 0:
                p_valor = stats.ttest_1samp(diferencia, 0).pvalue
            else:
                p_valor = 0.0 if media != 0 else 1.0
            filas[escenario][m] = f"{media:+.1f} ± {semiancho:.1f}"
            filas[escenario][m + " (p)"] = p_valor
    tabla = pd.DataFrame(filas).T.rename_axis("escenario")
    return tabla[[c for c in tabla.columns if not c.endswith("(p)")]], \
        tabla[[c for c in tabla.columns if c.endswith("(p)")]].astype(float)


def barrido(tasas, vehiculos, repeticiones=30, horas=8.0, G=None):
    """Métricas medias para cada combinación de tasa de pedidos y tamaño de flota."""
    if G is None:
        G = g.construir_grafo(g.cargar_matriz())
    partes = []
    for k in vehiculos:
        df = correr({t: t for t in tasas}, repeticiones, vehiculos=k, horas=horas, G=G)
        partes.append(df)
    df = pd.concat(partes, ignore_index=True)
    return (df.groupby(["pedidos por hora", "vehículos", "política"])[METRICAS[2:]]
              .mean().reset_index())


def flota_minima(barrido_df, metrica="puntualidad (%)", objetivo=90.0):
    """Menor número de vehículos que alcanza el objetivo en promedio."""
    ok = barrido_df[barrido_df[metrica] >= objetivo]
    return (ok.groupby(["pedidos por hora", "política"])["vehículos"].min()
              .unstack("política"))
