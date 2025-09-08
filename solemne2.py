import requests
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
def clear_filters_tab2():
    st.session_state["region_tab2"] = "(Todas)"
    st.session_state["comuna_tab2"] = "(Todas)"
    st.session_state["tipo_sis_tab2"] = "(Todos)"

API_BASE = "https://datos.gob.cl/api/3/action/datastore_search"
RESOURCE_ID = "2c44d782-3365-44e3-aefb-2c8b8363a1bc"

st.set_page_config(page_title="Establecimientos de Salud en Chile", layout="wide", page_icon="🏥")
st.title("Establecimientos de Salud en Chile: Público vs Privado")
st.markdown("""Este dashboard interactivo permite hacer una comparativa entre los establecimientos de salud públicos y privados en Chile.""")
st.caption("Fuente: datos.gob.cl")

@st.cache_data(show_spinner=False)
def fetch_data(limit: int = 10000):
    """Descarga registros desde la API"""
    params = {"resource_id": RESOURCE_ID, "limit": limit}
    r = requests.get(API_BASE, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    result = data["result"]
    df = pd.DataFrame(result["records"])
    return df

df = fetch_data()

# LIMPIEZA Y AGRUPACIÓN DE DATOS
# Agrupamos "Publico" y "Público" en "Público" (para arreglar inconsistencias de la fuente de datos)
df["TipoSistemaSaludGlosa"] = df["TipoSistemaSaludGlosa"].replace({"Publico": "Público", "Privado": "Privado"})

# Estandarizamos nombres de regiones y sistema de salud
df["RegionGlosa"] = df["RegionGlosa"].str.strip().str.title()

# Filtramos solo público y privado para el análisis principal
df_analisis = df[df["TipoSistemaSaludGlosa"].isin(["Público", "Privado"])].copy()

# Creamos columna agrupada para el gráfico
df_analisis["SistemaSaludAgrupado"] = df_analisis["TipoSistemaSaludGlosa"]

# Limpieza de la columna NivelAtencionEstabglosa
df_analisis = df_analisis[
    ~df_analisis["NivelAtencionEstabglosa"].isin(["No Aplica", "Pendiente"])
].copy()

# Limpieza de la columna TieneServicioUrgencia
df_analisis["TieneServicioUrgencia"] = df_analisis["TieneServicioUrgencia"].replace({
    "NO": "No",
    "No": "No",
    "SI": "Sí"
})
df_analisis = df_analisis[df_analisis["TieneServicioUrgencia"] != "No Aplica"].copy()

# SUMMARY HEADERS
total = len(df_analisis)
publico = (df_analisis["TipoSistemaSaludGlosa"] == "Público").sum()
privado = (df_analisis["TipoSistemaSaludGlosa"] == "Privado").sum()

pct_publico = publico / total * 100 if total > 0 else 0
pct_privado = privado / total * 100 if total > 0 else 0

st.subheader("Número de Establecimientos")
col1, col2, col3 = st.columns(3)
col1.metric("Total Establecimientos (Público y Privado)", f"{total:,}")
col2.metric("Sistema Público", f"{publico:,} ({pct_publico:.1f}%)")
col3.metric("Sistema Privado", f"{privado:,} ({pct_privado:.1f}%)")

# SELECCIÓN DE VISTAS
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Mapa de Establecimientos",
    "Distribución Geográfica",
    "Histórico de Apertura",
    "Nivel de Atención",
    "Servicios de Urgencia",
    "Tipo de Establecimiento"
])

with tab1:
    st.subheader("Mapa de Establecimientos por Sistema de Salud")

    # Filtros del mapa
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        region2 = st.selectbox(
            "Región",
            ["(Todas)"] + sorted(df_analisis["RegionGlosa"].dropna().unique().tolist()),
            key="region_tab2"
        )
    with col2:
        if region2 != "(Todas)":
            comunas_disponibles = sorted(
                df_analisis[df_analisis["RegionGlosa"] == region2]["ComunaGlosa"].dropna().unique().tolist()
            )
        else:
            comunas_disponibles = sorted(
                df_analisis["ComunaGlosa"].dropna().unique().tolist()
            )
        comuna2 = st.selectbox(
            "Comuna",
            ["(Todas)"] + comunas_disponibles,
            key="comuna_tab2"
        )
    with col3:
        tipo_sis2 = st.selectbox(
            "Sistema de Salud",
            ["(Todos)"] + sorted(df_analisis["TipoSistemaSaludGlosa"].dropna().unique().tolist()),
            key="tipo_sis_tab2"
        )
    with col4:
        st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
        st.button("Eliminar filtros", key="clear_filters_tab2", on_click=clear_filters_tab2)

    df_tab2 = df_analisis.copy()
    if region2 != "(Todas)":
        df_tab2 = df_tab2[df_tab2["RegionGlosa"] == region2]
    if tipo_sis2 != "(Todos)":
        df_tab2 = df_tab2[df_tab2["TipoSistemaSaludGlosa"] == tipo_sis2]
    if comuna2 != "(Todas)":
        df_tab2 = df_tab2[df_tab2["ComunaGlosa"] == comuna2]

    if "Latitud" in df_tab2.columns and "Longitud" in df_tab2.columns:
        df_map = df_tab2.dropna(subset=["Latitud", "Longitud"]).copy()
        df_map["Latitud"] = pd.to_numeric(df_map["Latitud"], errors="coerce")
        df_map["Longitud"] = pd.to_numeric(df_map["Longitud"], errors="coerce")
        df_map = df_map.dropna(subset=["Latitud", "Longitud"])
        st.map(df_map.rename(columns={"Latitud": "latitude", "Longitud": "longitude"}))
    else:
        st.info("Este dataset no incluye columnas de Latitud/Longitud.")

with tab2:
    st.subheader("Distribución por Región y Sistema de Salud")
    if "RegionGlosa" in df_analisis.columns and "SistemaSaludAgrupado" in df_analisis.columns:
        region_sistema = (
            df_analisis.groupby(["RegionGlosa", "SistemaSaludAgrupado"])
            .size()
            .unstack(fill_value=0)
            .loc[lambda x: x.sum(axis=1).sort_values(ascending=False).index]
        )

        top5 = region_sistema.head(5)[["Público", "Privado"]]
        top5["Total"] = top5["Público"] + top5["Privado"]

        col_graf, col_tabla = st.columns([2, 1])
        with col_graf:
            fig, ax = plt.subplots(figsize=(10, 7))
            region_sistema.plot(kind="barh", stacked=True, ax=ax, color=["#264653", "#fc8d62"])
            ax.set_xlabel("Cantidad")
            ax.set_ylabel("Región")
            ax.legend(title="Sistema de Salud")
            plt.tight_layout()
            st.pyplot(fig)

        with col_tabla:
            st.markdown("#### Top 5 Regiones con Más Establecimientos")
            tabla_top5 = top5[["Público", "Privado", "Total"]].sort_values("Total", ascending=False).copy()
            tabla_top5.index.name = "Región"
            st.dataframe(tabla_top5)
    else:
        st.info("No hay datos suficientes para mostrar este gráfico.")

with tab3:
    st.subheader("Histórico de Apertura de Establecimientos por Década y Sistema de Salud")

    if "FechaInicioFuncionamientoEstab" in df_analisis.columns and "SistemaSaludAgrupado" in df_analisis.columns:
        df_analisis["AñoInicio"] = pd.to_datetime(df_analisis["FechaInicioFuncionamientoEstab"], errors="coerce").dt.year
        df_analisis["Década"] = (df_analisis["AñoInicio"] // 10 * 10).astype("Int64")
        df_decada = df_analisis.dropna(subset=["Década"])

        decada_sistema = (
            df_decada.groupby(["Década", "SistemaSaludAgrupado"])
            .size()
            .unstack(fill_value=0)
            .sort_index()
        )

        col_graf1, col_graf2 = st.columns([1, 1])
        with col_graf1:
            st.markdown("#### Apertura de Establecimientos por Década")
            fig, ax = plt.subplots(figsize=(5, 4))
            decada_sistema.plot(kind="bar", ax=ax, color=["#264653", "#fc8d62"])
            ax.set_xlabel("Década de Inicio")
            ax.set_ylabel("Cantidad de Establecimientos")
            ax.legend(title="Sistema de Salud")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            st.pyplot(fig)

        with col_graf2:
            st.markdown("#### Crecimiento Acumulado por Año")
            df_linea = df_analisis.dropna(subset=["AñoInicio"])
            crecimiento = (
                df_linea.groupby(["AñoInicio", "SistemaSaludAgrupado"])
                .size()
                .unstack(fill_value=0)
                .sort_index()
                .cumsum()
            )
            fig_linea, ax_linea = plt.subplots(figsize=(5, 4))
            crecimiento.plot(ax=ax_linea, linewidth=2)
            ax_linea.set_xlabel("Año de Inicio")
            ax_linea.set_ylabel("Establecimientos acumulados")
            ax_linea.legend(title="Sistema de Salud")
            plt.tight_layout()
            st.pyplot(fig_linea)
    else:
        st.info("No hay datos suficientes para mostrar el análisis.")

with tab4:
    st.subheader("Comparativa por Nivel de Atención y Sistema de Salud")

    if "NivelAtencionEstabglosa" in df_analisis.columns and "SistemaSaludAgrupado" in df_analisis.columns:
        nivel_sistema = (
            df_analisis.groupby(["NivelAtencionEstabglosa", "SistemaSaludAgrupado"])
            .size()
            .unstack(fill_value=0)
            .loc[lambda x: x.sum(axis=1).sort_values(ascending=False).index]
        )

        col_graf, col_tabla = st.columns([1, 1])
        with col_graf:
            fig, ax = plt.subplots(figsize=(5, 4))
            nivel_sistema.plot(kind="bar", ax=ax, color=["#264653", "#fc8d62"])
            ax.set_xlabel("Nivel de Atención")
            ax.set_ylabel("Cantidad de Establecimientos")
            ax.legend(title="Sistema de Salud")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            st.pyplot(fig)

        with col_tabla:
            nivel_sistema["Total"] = nivel_sistema.sum(axis=1)
            nivel_sistema["% Público"] = nivel_sistema["Público"] / nivel_sistema["Total"] * 100
            nivel_sistema["% Privado"] = nivel_sistema["Privado"] / nivel_sistema["Total"] * 100
            st.markdown("#### Resumen por Nivel de Atención")
            tabla_nivel = nivel_sistema[["Público", "Privado", "% Público", "% Privado"]].copy()
            tabla_nivel.index.name = "Nivel de Atención"
            st.dataframe(tabla_nivel.style.format({"% Público": "{:.1f}%", "% Privado": "{:.1f}%"}))
    else:
        st.info("No hay datos suficientes para mostrar el análisis.")

with tab5:
    st.subheader("Comparativa de Servicio de Urgencia por Sistema de Salud")

    if "TieneServicioUrgencia" in df_analisis.columns and "SistemaSaludAgrupado" in df_analisis.columns:
        urgencia_sistema = (
            df_analisis.groupby(["TieneServicioUrgencia", "SistemaSaludAgrupado"])
            .size()
            .unstack(fill_value=0)
            .loc[lambda x: x.sum(axis=1).sort_values(ascending=False).index]
        )

        col_graf, col_tabla = st.columns([1, 1])
        with col_graf:
            fig, ax = plt.subplots(figsize=(5, 4))
            urgencia_sistema.plot(kind="bar", ax=ax, color=["#264653", "#fc8d62"])
            ax.set_xlabel("Servicio de Urgencia")
            ax.set_ylabel("Cantidad de Establecimientos")
            ax.legend(title="Sistema de Salud")
            plt.xticks(rotation=0, ha="center")
            plt.tight_layout()
            st.pyplot(fig)

        with col_tabla:
            st.markdown("#### Resumen por Servicio de Urgencia")
            urgencia_sistema = urgencia_sistema.copy()
            urgencia_sistema["Total"] = urgencia_sistema.sum(axis=1)
            urgencia_sistema["% Público"] = urgencia_sistema["Público"] / urgencia_sistema["Total"] * 100
            urgencia_sistema["% Privado"] = urgencia_sistema["Privado"] / urgencia_sistema["Total"] * 100
            tabla_urgencia = urgencia_sistema[["Público", "Privado", "% Público", "% Privado"]].copy()
            tabla_urgencia.index.name = "Servicio de Urgencia"
            st.dataframe(tabla_urgencia.style.format({"% Público": "{:.1f}%", "% Privado": "{:.1f}%"}))
    else:
        st.info("No hay datos suficientes para mostrar el análisis.")

with tab6:
    st.subheader("Top 3 Tipos de Establecimiento Público y Privado")

    if "TipoEstablecimientoGlosa" in df_analisis.columns and "SistemaSaludAgrupado" in df_analisis.columns:
        top_publico = (
            df_analisis[df_analisis["SistemaSaludAgrupado"] == "Público"]
            ["TipoEstablecimientoGlosa"]
            .value_counts()
            .head(3)
        )
        top_privado = (
            df_analisis[df_analisis["SistemaSaludAgrupado"] == "Privado"]
            ["TipoEstablecimientoGlosa"]
            .value_counts()
            .head(3)
        )

        col_pub, col_priv = st.columns(2)
        with col_pub:
            st.markdown("### Público")
            fig_pub, ax_pub = plt.subplots(figsize=(5, 2.5))
            top_publico.sort_values().plot(kind="barh", ax=ax_pub, color="#264653")
            ax_pub.set_xlabel("Cantidad")
            ax_pub.set_ylabel("Tipo de Establecimiento")
            plt.tight_layout()
            st.pyplot(fig_pub)
            tabla_pub = top_publico.rename("Cantidad").to_frame()
            tabla_pub.index.name = "Tipo de Establecimiento"
            st.dataframe(tabla_pub)

        with col_priv:
            st.markdown("### Privado")
            fig_priv, ax_priv = plt.subplots(figsize=(5, 2.5))
            top_privado.sort_values().plot(kind="barh", ax=ax_priv, color="#fc8d62")
            ax_priv.set_xlabel("Cantidad")
            ax_priv.set_ylabel("Tipo de Establecimiento")
            plt.tight_layout()
            st.pyplot(fig_priv)
            tabla_priv = top_privado.rename("Cantidad").to_frame()
            tabla_priv.index.name = "Tipo de Establecimiento"
            st.dataframe(tabla_priv)
    else:
        st.info("No hay datos suficientes para mostrar el análisis.")



