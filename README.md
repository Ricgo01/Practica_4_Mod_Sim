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

## Algoritmos de búsqueda de rutas

### Características de la red que condicionan la elección

- **Grafo dirigido y ponderado:** 40 nodos y 144 arcos. Hay 18 calles de un solo sentido y 14 pares de puntos con tiempos distintos según el sentido, así que la ida y el regreso se calculan por separado.
- **Pesos positivos:** todos los tiempos están entre 4 y 11 minutos. No hay pesos negativos.
- **Sin coordenadas:** la matriz no trae ubicación de los puntos, así que no hay una distancia geométrica que sirva de heurística.
- **Red pequeña:** con 40 nodos cualquier algoritmo exacto responde en milisegundos. El criterio decisivo es la **exactitud** y que se pueda **recalcular al cambiar la red** (congestión o cierre de un tramo).

### Algoritmos elegidos

#### Dijkstra — rutas de menor tiempo

Algoritmo voraz que encuentra el camino de menor costo desde un origen hacia los demás nodos de un grafo con pesos no negativos (Dijkstra, 1959).

**Funcionamiento**

1. Asigna distancia 0 al origen e infinito al resto.
2. Toma de una cola de prioridad el nodo no visitado con menor distancia acumulada y lo marca como definitivo.
3. Para cada arco saliente `u → v` con peso `w`, si `d(u) + w < d(v)`, actualiza `d(v)` y guarda a `u` como predecesor de `v` (relajación).
4. Repite hasta llegar al destino. El camino se reconstruye siguiendo los predecesores.

**Por qué lo elegimos**

- Es **exacto**: con pesos no negativos garantiza el camino de menor tiempo.
- Respeta el **sentido de los arcos** sin ningún ajuste: solo recorre arcos salientes, así que `N01 → destino` y `destino → N01` dan rutas distintas cuando la red es asimétrica.
- Complejidad **O((V + E) log V)** con cola de prioridad (montículo binario). Para V = 40 y E = 144 es instantáneo.
- Ante un **incidente vial**, basta con modificar el peso del arco (congestión) o eliminarlo (cierre) y volver a ejecutarlo. Si el destino queda inalcanzable, lo detecta.

**Limitaciones**

- No admite pesos negativos (no aplica aquí).
- Solo devuelve **una** ruta: la óptima. Para el punto 4 necesitamos alternativas, y para eso usamos Yen.

#### Yen — k rutas más cortas sin ciclos

Genera, en orden de tiempo, las `k` mejores rutas simples (sin repetir nodos) entre dos puntos, usando Dijkstra como subrutina (Yen, 1971).

**Funcionamiento**

1. `A[0]` es la ruta óptima, obtenida con Dijkstra.
2. Para obtener `A[k]`, recorre cada nodo de `A[k-1]` como **nodo de desvío**:
   - La **raíz** es el tramo de `A[k-1]` desde el origen hasta el nodo de desvío.
   - Se eliminan temporalmente los arcos que salen del nodo de desvío y que ya usan las rutas encontradas con esa misma raíz, y también los nodos de la raíz (para evitar ciclos).
   - Con Dijkstra se calcula la **espuela**: el mejor camino desde el nodo de desvío hasta el destino en esa red reducida.
   - Raíz + espuela es una candidata y se guarda en una cola de prioridad.
3. `A[k]` es la candidata de menor tiempo. Se repite hasta tener `k` rutas o quedarse sin candidatas.

**Por qué lo elegimos**

- El punto 4 pide **al menos dos rutas alternativas válidas** por destino. Yen las entrega ordenadas por tiempo y garantiza que sean **distintas y sin ciclos**.
- Reutiliza la implementación de Dijkstra, así que no agrega un método independiente que haya que validar.
- Permite cuantificar **cuánto se pierde** si la ruta óptima no se puede usar (por ejemplo, la diferencia entre la 1.ª y la 2.ª ruta), lo cual sirve para el análisis de incidentes viales.

**Limitaciones**

- Complejidad **O(k · V · (V + E) log V)**, porque ejecuta Dijkstra una vez por cada nodo de desvío. Con 40 nodos y k pequeño sigue siendo inmediato.
- Las alternativas pueden diferir de la óptima en un solo tramo. Si se buscan rutas muy distintas, habría que penalizar los arcos ya usados.

### Otros algoritmos considerados

| Algoritmo | Idea | Ventajas en esta red | Limitaciones en esta red | Decisión |
|---|---|---|---|---|
| **A\*** (Hart et al., 1968) | Dijkstra guiado por una heurística `h(n)` que estima el costo restante | Explora menos nodos si `h` es informativa | No hay coordenadas para una heurística geométrica. Una opción admisible es `h(n)` = (mínimo de tramos de `n` al destino, por BFS) × 4 min (el arco más corto). Con `h = 0` se reduce exactamente a Dijkstra | Descartado: en 40 nodos no hay ganancia apreciable y la heurística añade complejidad |
| **Bellman-Ford** (Bellman, 1958) | Relaja todos los arcos V − 1 veces | Admite pesos negativos y detecta ciclos negativos | O(V · E), más lento, y sus ventajas no aplican porque todos los tiempos son positivos | Descartado |
| **Floyd-Warshall** (Floyd, 1962) | Programación dinámica que calcula los caminos más cortos entre todos los pares | Una sola ejecución da la tabla completa de ida y regreso | O(V³) en tiempo y O(V²) en memoria; calcula 1 560 pares cuando solo se necesitan 8 | Descartado; útil como verificación cruzada |
| **BFS** | Recorrido por niveles | Encuentra la ruta con menos tramos | Ignora los tiempos, así que no minimiza minutos | Solo como apoyo (heurística de A\*) |
| **Algoritmo genético** (Holland, 1975) | Metaheurística evolutiva: población de rutas, cruce y mutación | Útil en problemas NP-difíciles, como el ruteo con varias paradas | No garantiza el óptimo, depende de parámetros y es aleatorio. El camino más corto entre dos puntos tiene solución exacta en tiempo polinomial | Descartado: cada vehículo lleva un solo pedido, así que no hay un problema combinatorio que lo justifique |

## Roadmap

| Fase | Contenido | Punto del enunciado | Estado |
|---|---|---|---|
| 0 | Objetivos, datos, decisiones y supuestos | 1 | Objetivos ✅ |
| 1 | Grafo dirigido, visualización y validación de rutas actuales (`01_grafo.ipynb`) | 2 | ✅ |
| 2 | Investigación de algoritmos | 3 | ✅ |
| 3 | Implementación propia de Dijkstra y Yen (`src/rutas.py`, `02_rutas.ipynb`) | 3 | ✅ |
| 4 | Tabla comparativa por destino: actual vs. Dijkstra vs. alternativas de Yen (`02_rutas.ipynb`) | 4 | ✅ |
| 5 | Simulación de eventos discretos con dos políticas de rutas (`src/simulacion.py`, `03_simulacion.ipynb`) | 5 | ✅ |
| 6 | Aplicación configurable: escenarios, flota, semilla, incidentes viales (`app.py`) | 6 | ✅ |
| 7 | Experimentos: ≥5 repeticiones por escenario con números aleatorios comunes | 7 | Pendiente |
| 8 | Análisis e informe | 8 | Pendiente |

## Modelo de simulación

Simulación de eventos discretos con [SimPy](https://simpy.readthedocs.io/) (`src/simulacion.py`).

- **Llegadas:** proceso de Poisson. Los tiempos entre pedidos son exponenciales con media 60/λ minutos (λ = 4 normal, 6 Semana Santa, 10 Navidad) y solo se reciben pedidos durante la jornada.
- **Destinos:** cada pedido va a N08, N19, N34 o N40 con probabilidad 1/4.
- **Flota:** 8 vehículos idénticos por defecto. Cada uno toma un pedido, hace la ida, entrega y regresa a N01 antes de tomar otro.
- **Cola:** FIFO cuando no hay vehículos libres.
- **Fin:** la simulación continúa después de la jornada hasta atender todos los pedidos recibidos.
- **Políticas:** *Actual* (hojas de despacho, regreso = ida invertida) y *Recomendada* (Dijkstra, ida y regreso por separado). Ambas se simulan con **los mismos pedidos** generados con la misma semilla.

### Supuestos

1. La tasa de llegadas es constante durante la jornada.
2. Los tiempos de viaje son deterministas e iguales a los de la matriz.
3. El tiempo de descarga en el destino es 0 min por defecto (configurable en la app).
4. Los vehículos no tienen averías, descansos ni turnos, y asignar un pedido no toma tiempo.
5. Una entrega es puntual si se completa en 75 min o menos desde la solicitud, incluida la espera.

### Métricas

Entregas puntuales, puntualidad, espera promedio y máxima, tiempo de la solicitud a la entrega, utilización de la flota (tiempo ocupado / (vehículos × duración total)) y tiempo adicional después del cierre de recepción hasta la última entrega.

## Aplicación

```bash
streamlit run app.py
```

- **Parámetros:** escenario (Normal, Semana Santa, Navidad o personalizado), pedidos por hora, número de vehículos, horas de recepción, semilla, tiempo de descarga y umbral de puntualidad.
- **Incidentes viales:** congestionar (nuevo tiempo) o cerrar uno o varios tramos.
- **Actualización de rutas:** cada incidente modifica una copia del grafo. La política recomendada vuelve a ejecutar Dijkstra sobre esa red, así que siempre usa la mejor ruta disponible. La política actual mantiene las rutas de las hojas de despacho con los tiempos nuevos; si una usa un tramo cerrado, ese viaje se reemplaza por la ruta de menor tiempo y la app lo avisa. Si un destino queda incomunicado, la app lo indica.
- **Resultados:** métricas de ambas políticas, cola y vehículos ocupados en el tiempo, distribución del tiempo de entrega, actividad de cada vehículo, rutas vigentes y red con los incidentes aplicados.

## Cómo ejecutar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook          # notebooks 01 a 03
streamlit run app.py      # aplicación
```

## Archivos

- `Práctica_4.pdf` — enunciado de la práctica.
- `Matriz_Logistica_del_Valle_40_nodos.csv` — matriz de adyacencia (minutos de viaje; celda vacía = sin conexión directa).
- `src/grafo.py` — carga de la matriz, construcción del grafo dirigido, dibujo y validación de rutas.
- `src/rutas.py` — implementación propia de Dijkstra y Yen, rutas óptimas de ida y regreso, e incidentes viales (congestión o cierre de un tramo).
- `src/simulacion.py` — generación de pedidos, simulación de eventos discretos y métricas.
- `src/graficas.py` — gráficas de la simulación (cola, uso de la flota, tiempos de entrega, actividad por vehículo).
- `app.py` — aplicación configurable en Streamlit.
- `01_grafo.ipynb` — construcción del grafo, red completa, validación de las rutas actuales y comparación de ida y regreso por destino.
- `02_rutas.ipynb` — selección del algoritmo, implementación y verificación de Dijkstra y Yen, tabla comparativa de rutas por destino y efecto de incidentes viales.
- `03_simulacion.ipynb` — descripción del modelo, validación del generador de pedidos, corrida de ejemplo y comparación de escenarios.
- `requirements.txt` — dependencias de Python.

## Referencias

Bellman, R. (1958). On a routing problem. *Quarterly of Applied Mathematics, 16*(1), 87–90. https://doi.org/10.1090/qam/102435

Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2022). *Introduction to algorithms* (4th ed.). MIT Press.

Dijkstra, E. W. (1959). A note on two problems in connexion with graphs. *Numerische Mathematik, 1*(1), 269–271. https://doi.org/10.1007/BF01386390

Floyd, R. W. (1962). Algorithm 97: Shortest path. *Communications of the ACM, 5*(6), 345. https://doi.org/10.1145/367766.368168

Hart, P. E., Nilsson, N. J., & Raphael, B. (1968). A formal basis for the heuristic determination of minimum cost paths. *IEEE Transactions on Systems Science and Cybernetics, 4*(2), 100–107. https://doi.org/10.1109/TSSC.1968.300136

Holland, J. H. (1975). *Adaptation in natural and artificial systems*. University of Michigan Press.

Law, A. M. (2015). *Simulation modeling and analysis* (5th ed.). McGraw-Hill Education.

Team SimPy. (2024). *SimPy: Discrete event simulation for Python* (Version 4.1) [Software]. https://simpy.readthedocs.io/

Yen, J. Y. (1971). Finding the K shortest loopless paths in a network. *Management Science, 17*(11), 712–716. https://doi.org/10.1287/mnsc.17.11.712
