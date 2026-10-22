"""Carga y dibujo de la red vial de Logística del Valle.

La matriz de adyacencia (fila = origen, columna = destino) se convierte en un
grafo dirigido de networkx donde cada arco guarda el tiempo de viaje en el
atributo ``peso`` (minutos).
"""

from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

RUTA_CSV = Path(__file__).parent.parent / "Matriz_Logistica_del_Valle_40_nodos.csv"

BODEGA = "N01"
DESTINOS = ["N08", "N19", "N34", "N40"]

# Rutas de las hojas de despacho (ida). El regreso es la misma ruta invertida.
RUTAS_ACTUALES = {
    "N08": ["N01", "N02", "N03", "N04", "N05", "N06", "N07", "N08"],
    "N19": ["N01", "N02", "N03", "N11", "N19"],
    "N34": ["N01", "N09", "N17", "N25", "N33", "N34"],
    "N40": ["N01", "N02", "N03", "N04", "N05", "N06", "N07", "N08",
            "N16", "N24", "N32", "N40"],
}

COLOR_DOBLE = "#9aa0a6"       # doble sentido, mismo tiempo
COLOR_ASIMETRICO = "#e8a33d"  # doble sentido, tiempos distintos
COLOR_UNICO = "#d93f3f"       # un solo sentido


def cargar_matriz(ruta=RUTA_CSV):
    """Lee el CSV como DataFrame; las celdas vacías quedan como NaN."""
    return pd.read_csv(ruta, index_col=0, encoding="utf-8-sig")


def construir_grafo(matriz):
    """Crea el grafo dirigido: un arco por cada celda con tiempo > 0."""
    G = nx.DiGraph()
    G.add_nodes_from(matriz.index)
    for origen, fila in matriz.iterrows():
        for destino, minutos in fila.items():
            if pd.notna(minutos) and minutos > 0:
                G.add_edge(origen, destino, peso=float(minutos))
    return G


def tipo_arco(G, u, v):
    """Clasifica el arco u->v según exista o no su inverso y con qué tiempo."""
    if not G.has_edge(v, u):
        return "unico"
    if G[u][v]["peso"] == G[v][u]["peso"]:
        return "doble"
    return "asimetrico"


def posiciones(G):
    """Cuadrícula de 8 columnas x 5 filas deducida de la numeración.

    No hay mapa: la cuadrícula es un esquema, no una ubicación geográfica.
    Se eligió porque casi todos los arcos unen nodos vecinos en ella.
    """
    pos = {}
    for n in G.nodes:
        k = int(n[1:]) - 1
        pos[n] = (k % 8, -(k // 8))
    return pos


def _cruza_nodo(pos, u, v, tolerancia=0.15):
    """True si el segmento recto u-v pasa encima de otro nodo."""
    a, b = np.array(pos[u]), np.array(pos[v])
    ab = b - a
    for n, p in pos.items():
        if n in (u, v):
            continue
        t = np.clip(np.dot(np.array(p) - a, ab) / np.dot(ab, ab), 0, 1)
        if np.linalg.norm(a + t * ab - np.array(p)) < tolerancia:
            return True
    return False


def curvatura(G, pos, u, v):
    """Curvatura del arco: separa los dos sentidos y evita tapar nodos."""
    rad = 0.0
    if tipo_arco(G, u, v) == "asimetrico":
        rad = 0.15
    if _cruza_nodo(pos, u, v):
        rad = 0.3
    return f"arc3,rad={rad}"


def _dibujar_arcos(G, pos, ax, arcos, color, ancho, etiquetas=True,
                   estilo="solid", flecha="-|>", alpha=1.0, zorder=1,
                   color_etiqueta=None, tam_etiqueta=7):
    """Dibuja arcos agrupándolos por curvatura (networkx pide una por llamada)."""
    grupos = {}
    for u, v in arcos:
        grupos.setdefault(curvatura(G, pos, u, v), []).append((u, v))
    for conn, grupo in grupos.items():
        artistas = nx.draw_networkx_edges(
            G, pos, edgelist=grupo, ax=ax, edge_color=color, width=ancho,
            style=estilo, arrowstyle=flecha, arrowsize=14, alpha=alpha,
            connectionstyle=conn, node_size=520, min_target_margin=12)
        for artista in artistas:
            artista.set_zorder(zorder)
        if etiquetas:
            nx.draw_networkx_edge_labels(
                G, pos, edge_labels={(u, v): f"{G[u][v]['peso']:g}" for u, v in grupo},
                ax=ax, connectionstyle=conn, font_size=tam_etiqueta, font_color=color_etiqueta or color,
                bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.8))


def _dibujar_nodos(G, pos, ax, resaltados=()):
    colores = []
    for n in G.nodes:
        if n == BODEGA:
            colores.append("#2b6cb0")
        elif n in DESTINOS:
            colores.append("#2f855a")
        elif n in resaltados:
            colores.append("#cfd8e3")
        else:
            colores.append("#f1f3f5")
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=520, node_color=colores,
                           edgecolors="#4a5568", linewidths=0.8)
    etiquetas_blancas = {n: n for n in G.nodes if n == BODEGA or n in DESTINOS}
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=7,
                            labels={n: n for n in G.nodes if n not in etiquetas_blancas})
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=7, font_color="white",
                            font_weight="bold", labels=etiquetas_blancas)


def dibujar_red(G, ax=None, titulo="Red vial completa"):
    """Grafo completo: doble sentido (gris, una flecha doble), asimétrico
    (naranja, dos arcos curvos) y un solo sentido (rojo)."""
    if ax is None:
        _, ax = plt.subplots(figsize=(18, 11))
    pos = posiciones(G)

    dobles = [(u, v) for u, v in G.edges if tipo_arco(G, u, v) == "doble" and u < v]
    asimetricos = [(u, v) for u, v in G.edges if tipo_arco(G, u, v) == "asimetrico"]
    unicos = [(u, v) for u, v in G.edges if tipo_arco(G, u, v) == "unico"]

    _dibujar_arcos(G, pos, ax, dobles, COLOR_DOBLE, 1.4, flecha="<|-|>")
    _dibujar_arcos(G, pos, ax, asimetricos, COLOR_ASIMETRICO, 1.4)
    _dibujar_arcos(G, pos, ax, unicos, COLOR_UNICO, 1.6)
    _dibujar_nodos(G, pos, ax)

    leyenda = [
        plt.Line2D([], [], color=COLOR_DOBLE, lw=2, label="Doble sentido, mismo tiempo"),
        plt.Line2D([], [], color=COLOR_ASIMETRICO, lw=2, label="Doble sentido, tiempo distinto"),
        plt.Line2D([], [], color=COLOR_UNICO, lw=2, label="Un solo sentido"),
        plt.Line2D([], [], marker="o", ls="", ms=10, color="#2b6cb0", label="Bodega N01"),
        plt.Line2D([], [], marker="o", ls="", ms=10, color="#2f855a", label="Destinos"),
    ]
    ax.legend(handles=leyenda, loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=5,
              frameon=False)
    ax.set_title(titulo, fontsize=14)
    ax.axis("off")
    return ax


def dibujar_rutas(G, rutas, ax=None, titulo=""):
    """Red en el fondo (tenue) y encima una o varias rutas resaltadas.

    ``rutas`` es una lista de (camino, color, etiqueta, estilo).
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(12, 7))
    pos = posiciones(G)

    _dibujar_arcos(G, pos, ax, list(G.edges), "#d5d9de", 0.8, etiquetas=False,
                   flecha="-", alpha=0.7, zorder=0)
    resaltados = set()
    leyenda = []
    for i, (camino, color, etiqueta, estilo) in enumerate(rutas):
        arcos = list(zip(camino, camino[1:]))
        ancho = 4.5 if i == 0 else 2.2
        _dibujar_arcos(G, pos, ax, arcos, color, ancho, estilo=estilo, zorder=2 + i,
                       color_etiqueta="#1a202c", tam_etiqueta=10)
        resaltados.update(camino)
        leyenda.append(plt.Line2D([], [], color=color, lw=ancho, ls=estilo, label=etiqueta))
    _dibujar_nodos(G, pos, ax, resaltados)

    ax.legend(handles=leyenda, loc="upper center", bbox_to_anchor=(0.5, -0.01),
              ncol=len(leyenda), frameon=False, fontsize=9)
    ax.set_title(titulo, fontsize=12)
    ax.axis("off")
    return ax


def validar_ruta(G, camino):
    """Revisa tramo por tramo si existe el arco y acumula el tiempo.

    Devuelve (es_valida, tiempo_total, tabla_de_tramos).
    """
    filas = []
    total = 0.0
    valida = True
    for u, v in zip(camino, camino[1:]):
        existe = G.has_edge(u, v)
        minutos = G[u][v]["peso"] if existe else np.nan
        valida &= existe
        total += minutos if existe else 0
        filas.append({"tramo": f"{u} → {v}", "existe": existe, "minutos": minutos})
    return valida, (total if valida else np.nan), pd.DataFrame(filas)
