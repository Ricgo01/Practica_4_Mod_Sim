"""Búsqueda de rutas: Dijkstra (ruta de menor tiempo) y Yen (k mejores rutas).

Implementación propia sobre el grafo dirigido de ``grafo.py``: solo se usa
networkx como contenedor de nodos y arcos, no sus algoritmos.
"""

import heapq
import math

from . import grafo as g


def costo_ruta(G, camino):
    """Minutos totales de un camino; inf si algún tramo no existe."""
    total = 0.0
    for u, v in zip(camino, camino[1:]):
        if not G.has_edge(u, v):
            return math.inf
        total += G[u][v]["peso"]
    return total


def dijkstra(G, origen, destino, arcos_excluidos=frozenset(),
             nodos_excluidos=frozenset(), registro=None):
    """Ruta de menor tiempo de ``origen`` a ``destino`` en un grafo dirigido.

    Solo recorre arcos salientes, así que respeta el sentido de las calles.
    ``arcos_excluidos`` y ``nodos_excluidos`` permiten ignorar partes de la red
    sin copiarla (lo usa Yen). Si se pasa una lista en ``registro``, se agrega
    un paso por cada nodo extraído de la cola, para poder mostrar la traza.

    Devuelve (camino, minutos) o (None, inf) si el destino es inalcanzable.
    """
    distancia = {origen: 0.0}
    predecesor = {origen: None}
    visitados = set()
    cola = [(0.0, origen)]

    while cola:
        d, u = heapq.heappop(cola)
        if u in visitados:
            continue  # entrada vieja: ya se encontró una distancia menor
        visitados.add(u)

        actualizados = []
        if u != destino:
            for v, datos in G.succ[u].items():
                if v in visitados or v in nodos_excluidos or (u, v) in arcos_excluidos:
                    continue
                nueva = d + datos["peso"]
                if nueva < distancia.get(v, math.inf):
                    distancia[v] = nueva
                    predecesor[v] = u
                    heapq.heappush(cola, (nueva, v))
                    actualizados.append(f"{v}={nueva:g}")

        if registro is not None:
            registro.append({"paso": len(registro) + 1, "nodo fijado": u,
                             "distancia": d, "vecinos actualizados": ", ".join(actualizados)})
        if u == destino:
            break

    if destino not in visitados:
        return None, math.inf

    camino = [destino]
    while predecesor[camino[-1]] is not None:
        camino.append(predecesor[camino[-1]])
    return camino[::-1], distancia[destino]


def yen(G, origen, destino, k):
    """Las ``k`` rutas sin ciclos de menor tiempo, ordenadas (Yen, 1971).

    Devuelve una lista de (camino, minutos); puede tener menos de ``k``
    elementos si la red no admite más rutas distintas.
    """
    primero, costo = dijkstra(G, origen, destino)
    if primero is None:
        return []

    encontradas = [(primero, costo)]
    candidatas = []          # montículo de (minutos, camino)
    vistas = {tuple(primero)}

    while len(encontradas) < k:
        anterior = encontradas[-1][0]
        for i in range(len(anterior) - 1):
            desvio = anterior[i]
            raiz = anterior[:i + 1]

            # Arcos que ya usan las rutas encontradas con esta misma raíz.
            arcos = {(c[i], c[i + 1]) for c, _ in encontradas
                     if len(c) > i + 1 and c[:i + 1] == raiz}
            # Los nodos de la raíz (salvo el desvío) no pueden repetirse.
            nodos = set(raiz[:-1])

            espuela, _ = dijkstra(G, desvio, destino, arcos, nodos)
            if espuela is None:
                continue
            candidata = raiz[:-1] + espuela
            if tuple(candidata) not in vistas:
                vistas.add(tuple(candidata))
                heapq.heappush(candidatas, (costo_ruta(G, candidata), candidata))

        if not candidatas:
            break
        costo, camino = heapq.heappop(candidatas)
        encontradas.append((camino, costo))

    return encontradas


def rutas_optimas(G, bodega=g.BODEGA, destinos=g.DESTINOS):
    """Ruta de menor tiempo de ida y de regreso para cada destino.

    Devuelve {destino: {"ida": (camino, min), "regreso": (camino, min)}}.
    """
    return {d: {"ida": dijkstra(G, bodega, d), "regreso": dijkstra(G, d, bodega)}
            for d in destinos}


def aplicar_incidente(G, origen, destino, minutos=None):
    """Copia de la red con un tramo congestionado o cerrado.

    Con ``minutos`` se cambia el tiempo del arco (congestión); con ``None``
    se elimina (cierre). Solo afecta el sentido ``origen -> destino``.
    """
    H = G.copy()
    if minutos is None:
        H.remove_edge(origen, destino)
    else:
        H[origen][destino]["peso"] = float(minutos)
    return H
