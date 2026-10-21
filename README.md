# Práctica 4 — Logística del Valle

CC2017 Modelación y Simulación · Universidad del Valle de Guatemala · Ciclo 2, 2026

Optimización de rutas y simulación de la operación de entregas desde la bodega **N01** hacia los destinos **N08, N19, N34 y N40**, a partir de la matriz de tiempos `Matriz_Logistica_del_Valle_40_nodos.csv`.

## Objetivo general

Desarrollar una aplicación que determine las rutas más convenientes de ida y regreso entre la bodega N01 y los cuatro destinos, y que simule la operación diaria de entregas, para evaluar si conviene cambiar las rutas actuales y si la flota de 8 vehículos es suficiente para cumplir entregas en 75 minutos o menos bajo distintos escenarios de demanda e incidentes viales.

## Objetivos específicos

1. Construir el grafo dirigido de la red a partir de la matriz de tiempos y validar si las rutas actuales son transitables tanto de ida como de regreso.
2. Implementar un algoritmo de búsqueda de rutas que obtenga, por separado, los caminos de ida y de regreso de menor tiempo, y compararlos con la ruta actual y al menos otra alternativa por destino.
3. Simular la llegada aleatoria de pedidos, la cola y el uso de los vehículos para comparar el desempeño de las rutas actuales contra las rutas propuestas, usando los mismos pedidos en ambos casos.
4. Evaluar la puntualidad, la espera y la utilización de la flota en los escenarios normal, Semana Santa y Navidad, para identificar a partir de qué demanda los 8 vehículos se vuelven una limitación.

## Archivos

- `Práctica_4.pdf` — enunciado de la práctica.
- `Matriz_Logistica_del_Valle_40_nodos.csv` — matriz de adyacencia (minutos de viaje; celda vacía = sin conexión directa).
