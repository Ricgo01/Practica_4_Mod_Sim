"""Gráficas de resultados de la simulación (las usan el notebook y la app)."""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

from . import grafo as g
from . import simulacion as s

COLOR_POLITICA = {"Actual": "#2b6cb0", "Recomendada": "#2f855a"}
COLOR_DESTINO = {"N08": "#4c78a8", "N19": "#f58518", "N34": "#54a24b", "N40": "#b279a2"}


def _marcar_fin_recepcion(ax, p):
    ax.axvline(p.horas_recepcion * 60, color="#718096", ls=":", lw=1)
    ax.text(p.horas_recepcion * 60, ax.get_ylim()[1], " fin de recepción",
            color="#718096", fontsize=8, va="top")


def estado_en_el_tiempo(resultados, p):
    """Pedidos en cola y vehículos ocupados a lo largo de la jornada."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    for politica, res in resultados.items():
        estado = s.serie_estado(res["registros"])
        color = COLOR_POLITICA[politica]
        ax1.step(estado["t"], estado["cola"], where="post", color=color, label=politica)
        ax2.step(estado["t"], estado["ocupados"], where="post", color=color, label=politica)
    ax1.set_ylabel("pedidos en cola")
    ax2.set_ylabel("vehículos ocupados")
    ax2.axhline(p.vehiculos, color="#d93f3f", ls="--", lw=1)
    ax2.set_ylim(0, p.vehiculos + 1)
    ax2.set_xlabel("minutos desde el inicio de la jornada")
    ax1.legend(loc="upper left")
    for ax in (ax1, ax2):
        _marcar_fin_recepcion(ax, p)
        ax.grid(alpha=0.3)
    fig.suptitle("Cola y uso de la flota", fontsize=13)
    fig.tight_layout()
    return fig


def distribucion_tiempos(resultados, p):
    """Histograma del tiempo desde la solicitud hasta la entrega."""
    fig, ax = plt.subplots(figsize=(11, 4))
    maximo = max(res["registros"]["solicitud_a_entrega"].max() for res in resultados.values())
    bins = np.arange(0, max(maximo, p.umbral) + 10, 10)
    for politica, res in resultados.items():
        ax.hist(res["registros"]["solicitud_a_entrega"], bins=bins, alpha=0.6,
                color=COLOR_POLITICA[politica], label=politica)
    ax.axvline(p.umbral, color="#d93f3f", ls="--", lw=1.2)
    ax.text(p.umbral, ax.get_ylim()[1], f" umbral {p.umbral:g} min", color="#d93f3f",
            fontsize=8, va="top")
    ax.set_xlabel("minutos desde la solicitud hasta la entrega")
    ax.set_ylabel("pedidos")
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_title("Distribución del tiempo de entrega")
    fig.tight_layout()
    return fig


def gantt(reg, p, titulo=""):
    """Actividad de cada vehículo: ida (color del destino) y regreso (tenue).

    Las entregas fuera del umbral se marcan con una x roja.
    """
    fig, ax = plt.subplots(figsize=(11, 0.45 * p.vehiculos + 1.6))
    for fila in reg.itertuples():
        color = COLOR_DESTINO.get(fila.destino, "#718096")
        ax.barh(fila.vehiculo, fila.entrega - fila.inicio, left=fila.inicio,
                color=color, edgecolor="white", height=0.7)
        ax.barh(fila.vehiculo, fila.retorno - fila.entrega, left=fila.entrega,
                color=color, alpha=0.35, edgecolor="white", height=0.7)
        if fila.solicitud_a_entrega > p.umbral:
            ax.plot(fila.entrega, fila.vehiculo, "x", color="#d93f3f", ms=6, mew=1.5)
    ax.set_yticks(range(1, p.vehiculos + 1))
    ax.set_ylabel("vehículo")
    ax.set_xlabel("minutos desde el inicio de la jornada")
    ax.invert_yaxis()
    _marcar_fin_recepcion(ax, p)
    leyenda = [Patch(color=COLOR_DESTINO[d], label=d) for d in g.DESTINOS]
    leyenda.append(Patch(color="#a0aec0", alpha=0.35, label="regreso"))
    leyenda.append(plt.Line2D([], [], marker="x", ls="", color="#d93f3f", label="entrega tardía"))
    ax.legend(handles=leyenda, loc="upper center", bbox_to_anchor=(0.5, -0.18),
              ncol=len(leyenda), frameon=False, fontsize=8)
    ax.set_title(titulo)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    return fig
