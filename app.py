"""Aplicación para estudiar cambios de ruta, flota e incidentes viales.

Ejecutar con:  streamlit run app.py
"""

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from src import grafo as g
from src import graficas as gr
from src import rutas as r
from src import simulacion as s

matplotlib.use("Agg")
st.set_page_config(page_title="Logística del Valle", layout="wide")


@st.cache_data
def red_original():
    return g.construir_grafo(g.cargar_matriz())


G0 = red_original()
ARCOS = {f"{u} → {v} ({G0[u][v]['peso']:g} min)": (u, v) for u, v in sorted(G0.edges)}


def mostrar(fig):
    st.pyplot(fig, clear_figure=True)
    plt.close(fig)


# ---------------------------------------------------------------- parámetros
with st.sidebar:
    st.header("Operación")
    escenario = st.selectbox("Escenario", [*s.ESCENARIOS, "Personalizado"])
    tasa = st.number_input(
        "Pedidos por hora (promedio)", min_value=0.5, max_value=40.0, step=0.5,
        value=float(s.ESCENARIOS.get(escenario, 4)), key=f"tasa_{escenario}",
        disabled=escenario != "Personalizado",
        help="Cada escenario fija su tasa; elige «Personalizado» para escribir otra.")
    vehiculos = st.slider("Número de vehículos", 1, 30, 8)
    horas = st.slider("Horas de recepción de pedidos", 1.0, 16.0, 8.0, step=0.5)
    semilla = st.number_input("Semilla aleatoria", min_value=0, value=1, step=1)

    with st.expander("Supuestos"):
        descarga = st.number_input("Tiempo de descarga en el destino (min)", 0.0, 60.0, 0.0, step=1.0)
        umbral = st.number_input("Umbral de puntualidad (min)", 10.0, 300.0, 75.0, step=5.0)

    st.header("Incidentes viales")
    st.caption("Cada incidente afecta un tramo en un solo sentido.")
    if "incidentes" not in st.session_state:
        st.session_state.incidentes = {}   # (origen, destino) -> minutos, o None si está cerrado

    tramo = st.selectbox("Tramo", list(ARCOS))
    accion = st.radio("Acción", ["Congestión (nuevo tiempo)", "Cerrar tramo"], horizontal=True)
    minutos = st.number_input("Nuevo tiempo (min)", 1.0, 300.0,
                              value=G0.edges[ARCOS[tramo]]["peso"] * 2, step=1.0,
                              disabled=accion == "Cerrar tramo")
    if st.button("Agregar incidente", type="primary", width="stretch"):
        st.session_state.incidentes[ARCOS[tramo]] = None if accion == "Cerrar tramo" else minutos
    if st.session_state.incidentes and st.button("Quitar todos", width="stretch"):
        st.session_state.incidentes = {}
        st.rerun()

    for (u, v), m in list(st.session_state.incidentes.items()):
        texto, quitar = st.columns([4, 1])
        texto.write(f"{u} → {v}: " + ("**cerrado**" if m is None
                                      else f"{G0[u][v]['peso']:g} → **{m:g} min**"))
        if quitar.button("✕", key=f"quitar_{u}_{v}"):
            del st.session_state.incidentes[(u, v)]
            st.rerun()

p = s.Parametros(pedidos_por_hora=tasa, vehiculos=vehiculos, horas_recepcion=horas,
                 semilla=int(semilla), tiempo_entrega=descarga, umbral=umbral)

# ---------------------------------------------------------------- red vigente
G = G0
aplicados = []
for (u, v), m in st.session_state.incidentes.items():
    G = r.aplicar_incidente(G, u, v, m)
    aplicados.append(f"{u} → {v}: cerrado" if m is None
                     else f"{u} → {v}: {G0[u][v]['peso']:g} → {m:g} min")

# ---------------------------------------------------------------- encabezado
st.title("Logística del Valle: rutas y flota")
st.write(f"**{escenario}** · {tasa:g} pedidos/h durante {horas:g} h · {vehiculos} vehículos · "
         f"semilla {int(semilla)} · puntual si se entrega en ≤ {umbral:g} min")
if aplicados:
    st.info("Incidentes aplicados: " + " · ".join(aplicados))

try:
    pedidos, resultados, avisos = s.comparar(p, G)
except ValueError as error:
    st.error(f"{error} Revisa los tramos cerrados.")
    st.stop()
for aviso in avisos:
    st.warning(aviso)

tab_sim, tab_rutas, tab_red = st.tabs(["Simulación", "Rutas", "Red vial"])

# ---------------------------------------------------------------- simulación
with tab_sim:
    if pedidos.empty:
        st.warning("Con estos parámetros no llegó ningún pedido. Sube la tasa o las horas de recepción.")
        st.stop()

    st.subheader(f"{len(pedidos)} pedidos (los mismos para ambas políticas)")
    act, rec = resultados["Actual"]["metricas"], resultados["Recomendada"]["metricas"]
    indicadores = [
        ("Entregas puntuales", "entregas puntuales", "{:.0f}", "normal"),
        ("Puntualidad", "puntualidad (%)", "{:.0f} %", "normal"),
        ("Espera promedio", "espera promedio (min)", "{:.0f} min", "inverse"),
        ("Solicitud → entrega", "solicitud→entrega promedio (min)", "{:.0f} min", "inverse"),
        ("Utilización de la flota", "utilización (%)", "{:.0f} %", "off"),
        ("Tiempo adicional", "tiempo adicional (min)", "{:.0f} min", "inverse"),
    ]
    for titulo_politica, m, base in [("Rutas actuales", act, None), ("Rutas recomendadas", rec, act)]:
        st.markdown(f"**{titulo_politica}**")
        columnas = st.columns(len(indicadores))
        for col, (titulo, clave, formato, modo) in zip(columnas, indicadores):
            delta = None if base is None else formato.format(m[clave] - base[clave])
            col.metric(titulo, formato.format(m[clave]), delta=delta, delta_color=modo)

    st.caption("Tiempo adicional: minutos después del cierre de recepción hasta entregar el último pedido. "
               "Utilización: tiempo ocupado de los vehículos / (vehículos × duración total de la operación).")

    mostrar(gr.estado_en_el_tiempo(resultados, p))
    mostrar(gr.distribucion_tiempos(resultados, p))

    politica_gantt = st.radio("Actividad por vehículo", s.POLITICAS, horizontal=True)
    mostrar(gr.gantt(resultados[politica_gantt]["registros"], p,
                     titulo=f"Actividad de la flota — política {politica_gantt}"))

    with st.expander("Tabla de métricas"):
        st.dataframe(s.tabla_metricas(resultados).style.format("{:,.1f}"), width="stretch")
    with st.expander("Detalle por pedido"):
        detalle = pd.concat({pol: res["registros"] for pol, res in resultados.items()},
                            names=["política", "fila"]).reset_index(level=0)
        st.dataframe(detalle.round(1), width="stretch", hide_index=True)
        st.download_button("Descargar CSV", detalle.to_csv(index=False).encode("utf-8"),
                           file_name=f"simulacion_semilla_{int(semilla)}.csv", mime="text/csv")

# ---------------------------------------------------------------- rutas
with tab_rutas:
    st.markdown(
        "La política **recomendada** vuelve a ejecutar Dijkstra sobre la red vigente cada vez que cambian los "
        "incidentes, así que siempre usa la mejor ruta disponible. La política **actual** conserva las rutas de las "
        "hojas de despacho con los tiempos vigentes; si un tramo cerrado forma parte de ellas, ese viaje se reemplaza "
        "por la ruta de menor tiempo.")

    originales = r.rutas_optimas(G0)
    filas = []
    for politica in s.POLITICAS:
        for d, rr in resultados[politica]["rutas"].items():
            for tramo in ["ida", "regreso"]:
                camino, minutos = rr[tramo]
                fila = {"política": politica, "destino": d, "tramo": tramo,
                        "minutos": minutos, "ruta": " → ".join(camino),
                        "cambio por incidentes": "—"}
                if politica == "Recomendada":
                    antes = originales[d][tramo]
                    if antes[0] != camino:
                        fila["cambio por incidentes"] = f"ruta nueva (antes {antes[1]:g} min)"
                    elif antes[1] != minutos:
                        fila["cambio por incidentes"] = f"misma ruta (antes {antes[1]:g} min)"
                filas.append(fila)
    st.dataframe(pd.DataFrame(filas), width="stretch", hide_index=True,
                 height=35 * (len(filas) + 1) + 3)

    destino = st.selectbox("Ver rutas del destino", g.DESTINOS)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(22, 7.5))
    for ax, tramo, titulo in [(ax1, "ida", f"IDA  {g.BODEGA} → {destino}"),
                              (ax2, "regreso", f"REGRESO  {destino} → {g.BODEGA}")]:
        rec_camino, rec_min = resultados["Recomendada"]["rutas"][destino][tramo]
        act_camino, act_min = resultados["Actual"]["rutas"][destino][tramo]
        g.dibujar_rutas(G, [
            (rec_camino, gr.COLOR_POLITICA["Recomendada"], f"Recomendada: {rec_min:g} min", "solid"),
            (act_camino, gr.COLOR_POLITICA["Actual"], f"Actual: {act_min:g} min", "dashed"),
        ], ax=ax, titulo=titulo)
    fig.tight_layout()
    mostrar(fig)

# ---------------------------------------------------------------- red
with tab_red:
    st.caption("Red vigente, con los incidentes aplicados. Los tramos cerrados no aparecen.")
    fig, ax = plt.subplots(figsize=(18, 11))
    g.dibujar_red(G, ax=ax)
    fig.tight_layout()
    mostrar(fig)
