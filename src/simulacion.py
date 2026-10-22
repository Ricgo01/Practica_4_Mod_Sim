"""Simulación de eventos discretos de la operación diaria de entregas.

Modelo:

- Los pedidos llegan según un proceso de Poisson: los tiempos entre llegadas son
  exponenciales con media 60 / (pedidos por hora) minutos. Solo se reciben
  pedidos durante la jornada de recepción.
- Cada pedido va a uno de los destinos con la misma probabilidad.
- Hay una flota fija de vehículos idénticos. Cada vehículo toma un pedido, viaja
  al destino, entrega y regresa a la bodega antes de tomar otro.
- Si no hay vehículos libres, los pedidos esperan en una cola FIFO.
- La simulación sigue después de la jornada hasta atender todos los pedidos.

Los pedidos se generan una sola vez por semilla y se reutilizan en ambas
políticas de rutas (números aleatorios comunes), así la diferencia entre
políticas se debe solo a las rutas.
"""

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
import simpy

from . import grafo as g
from . import rutas as r

ESCENARIOS = {"Normal": 4, "Semana Santa": 6, "Navidad": 10}
POLITICAS = ["Actual", "Recomendada"]


@dataclass
class Parametros:
    pedidos_por_hora: float = 4
    vehiculos: int = 8
    horas_recepcion: float = 8
    semilla: int = 1
    tiempo_entrega: float = 0.0  # minutos de descarga en el destino (supuesto)
    umbral: float = 75.0         # minutos para que una entrega sea puntual


def generar_pedidos(pedidos_por_hora, horas_recepcion, semilla, destinos=g.DESTINOS):
    """Instantes de llegada (min) y destino de cada pedido de la jornada."""
    rng = np.random.default_rng(semilla)
    media = 60 / pedidos_por_hora
    fin = horas_recepcion * 60

    llegadas = []
    t = rng.exponential(media)
    while t < fin:
        llegadas.append(t)
        t += rng.exponential(media)
    asignados = rng.choice(destinos, size=len(llegadas))

    return pd.DataFrame({"pedido": np.arange(1, len(llegadas) + 1),
                         "llegada": llegadas, "destino": asignados})


def rutas_politica(G, politica):
    """Rutas de ida y regreso que usa cada política en la red ``G``.

    - "Actual": las hojas de despacho (regreso = ida invertida). Si un tramo
      está cerrado, ese viaje se reemplaza por la ruta de menor tiempo.
    - "Recomendada": Dijkstra, recalculado sobre la red actual.

    Devuelve ({destino: {"ida": (camino, min), "regreso": (camino, min)}}, avisos).
    """
    if politica == "Recomendada":
        rutas, avisos = r.rutas_optimas(G), []
    else:
        rutas, avisos = {}, []
        for d, ida in g.RUTAS_ACTUALES.items():
            rutas[d] = {}
            for tramo, camino, o, t in [("ida", ida, g.BODEGA, d),
                                        ("regreso", ida[::-1], d, g.BODEGA)]:
                minutos = r.costo_ruta(G, camino)
                if math.isinf(minutos):
                    camino, minutos = r.dijkstra(G, o, t)
                    avisos.append(f"La ruta actual de {tramo} de {d} usa un tramo cerrado; "
                                  f"se reemplaza por la de menor tiempo ({minutos:g} min).")
                rutas[d][tramo] = (camino, minutos)

    for d, rr in rutas.items():
        for tramo, (camino, _) in rr.items():
            if camino is None:
                raise ValueError(f"No existe ninguna ruta de {tramo} para {d} con la red actual.")
    return rutas, avisos


def simular(pedidos, rutas, vehiculos, tiempo_entrega=0.0):
    """Ejecuta la simulación y devuelve un registro por pedido.

    ``rutas`` es la salida de ``rutas_politica``; solo se usan los minutos.
    """
    env = simpy.Environment()
    flota = simpy.Store(env, capacity=vehiculos)
    flota.items = list(range(1, vehiculos + 1))
    registros = []

    def atender(pedido):
        ida = rutas[pedido.destino]["ida"][1]
        regreso = rutas[pedido.destino]["regreso"][1]

        vehiculo = yield flota.get()       # espera en cola FIFO si no hay vehículos
        inicio = env.now
        yield env.timeout(ida + tiempo_entrega)
        entrega = env.now
        yield env.timeout(regreso)
        retorno = env.now
        yield flota.put(vehiculo)

        registros.append({"pedido": pedido.pedido, "destino": pedido.destino,
                          "vehiculo": vehiculo, "llegada": pedido.llegada,
                          "inicio": inicio, "entrega": entrega, "retorno": retorno})

    def llegadas():
        for pedido in pedidos.itertuples():
            yield env.timeout(pedido.llegada - env.now)
            env.process(atender(pedido))

    env.process(llegadas())
    env.run()  # sin límite: continúa hasta atender todos los pedidos

    columnas = ["pedido", "destino", "vehiculo", "llegada", "inicio", "entrega", "retorno"]
    reg = pd.DataFrame(registros, columns=columnas).sort_values("pedido").reset_index(drop=True)
    reg["espera"] = reg["inicio"] - reg["llegada"]
    reg["solicitud_a_entrega"] = reg["entrega"] - reg["llegada"]
    return reg


def metricas(reg, p):
    """Indicadores de una corrida (punto 7 del enunciado)."""
    fin_recepcion = p.horas_recepcion * 60
    if reg.empty:
        return {"pedidos": 0, "entregas puntuales": 0, "puntualidad (%)": np.nan,
                "espera promedio (min)": np.nan, "espera máxima (min)": np.nan,
                "solicitud→entrega promedio (min)": np.nan,
                "solicitud→entrega máximo (min)": np.nan, "utilización (%)": 0.0,
                "tiempo adicional (min)": 0.0, "fin de la operación (min)": fin_recepcion}

    puntuales = int((reg["solicitud_a_entrega"] <= p.umbral).sum())
    fin_operacion = reg["retorno"].max()
    horizonte = max(fin_recepcion, fin_operacion)
    ocupado = (reg["retorno"] - reg["inicio"]).sum()
    return {
        "pedidos": len(reg),
        "entregas puntuales": puntuales,
        "puntualidad (%)": 100 * puntuales / len(reg),
        "espera promedio (min)": reg["espera"].mean(),
        "espera máxima (min)": reg["espera"].max(),
        "solicitud→entrega promedio (min)": reg["solicitud_a_entrega"].mean(),
        "solicitud→entrega máximo (min)": reg["solicitud_a_entrega"].max(),
        "utilización (%)": 100 * ocupado / (p.vehiculos * horizonte),
        # Minutos después del cierre de recepción hasta entregar el último pedido.
        "tiempo adicional (min)": max(0.0, reg["entrega"].max() - fin_recepcion),
        "fin de la operación (min)": fin_operacion,
    }


def comparar(p, G=None):
    """Corre ambas políticas con los mismos pedidos.

    Devuelve (pedidos, {política: {"rutas", "registros", "metricas"}}, avisos).
    """
    if G is None:
        G = g.construir_grafo(g.cargar_matriz())
    pedidos = generar_pedidos(p.pedidos_por_hora, p.horas_recepcion, p.semilla)

    resultados, avisos = {}, []
    for politica in POLITICAS:
        rutas, av = rutas_politica(G, politica)
        avisos += av
        reg = simular(pedidos, rutas, p.vehiculos, p.tiempo_entrega)
        resultados[politica] = {"rutas": rutas, "registros": reg, "metricas": metricas(reg, p)}
    return pedidos, resultados, avisos


def tabla_metricas(resultados):
    """DataFrame con las métricas de cada política y la diferencia."""
    tabla = pd.DataFrame({pol: res["metricas"] for pol, res in resultados.items()})
    tabla["Diferencia"] = tabla["Recomendada"] - tabla["Actual"]
    return tabla


def serie_estado(reg):
    """Pedidos en cola y vehículos ocupados a lo largo del tiempo (función escalón)."""
    eventos = pd.concat([
        pd.DataFrame({"t": reg["llegada"], "cola": 1, "ocupados": 0}),
        pd.DataFrame({"t": reg["inicio"], "cola": -1, "ocupados": 1}),
        pd.DataFrame({"t": reg["retorno"], "cola": 0, "ocupados": -1}),
    ]).sort_values("t", kind="stable")
    eventos = eventos.groupby("t", as_index=False).sum()
    eventos[["cola", "ocupados"]] = eventos[["cola", "ocupados"]].cumsum()
    inicio = pd.DataFrame({"t": [0.0], "cola": [0], "ocupados": [0]})
    return pd.concat([inicio, eventos], ignore_index=True)
