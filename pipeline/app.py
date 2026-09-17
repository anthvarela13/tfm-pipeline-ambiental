"""
app.py — Dashboard interactivo de Monitorización Ambiental Global
=================================================================
Trabajo Fin de Máster · Perfil Data Engineer
Máster en Big Data, Data Science e Inteligencia Artificial
Universidad Complutense de Madrid · 2026

Ejecutar:
    cd pipeline/
    streamlit run app.py
"""

import os
import sqlite3

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

# sklearn — opcional (sección ML)
try:
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False

# ── Configuración de página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Monitor Ambiental Global",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Estilo CSS mínimo ─────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #f0f4f8;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 8px;
        border-left: 4px solid #00467F;
    }
    .metric-value { font-size: 2rem; font-weight: 700; color: #00467F; }
    .metric-label { font-size: 0.85rem; color: #555; }
    .alert-red   { border-left-color: #d32f2f !important; }
    .alert-green { border-left-color: #388e3c !important; }
</style>
""", unsafe_allow_html=True)

# ── Paleta de colores ─────────────────────────────────────────────────────────
PALETTE = ["#2196F3", "#4CAF50", "#FF5722", "#9C27B0", "#FF9800", "#00BCD4", "#E91E63"]
OMS_LIMIT = 15  # µg/m³ — guía anual OMS 2021

# ── Conexión a la base de datos ───────────────────────────────────────────────
DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "biodiversity_monitor.db"),
)


@st.cache_resource(show_spinner=False)
def _conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def _sql(query, params=()):
    return pd.read_sql_query(query, _conn(), params=params)


@st.cache_data(ttl=300, show_spinner=False)
def load_air():
    return _sql("SELECT * FROM air_quality")


@st.cache_data(ttl=300, show_spinner=False)
def load_weather():
    df = _sql("SELECT * FROM weather")
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_bio():
    return _sql("SELECT * FROM biodiversity")


@st.cache_data(ttl=300, show_spinner=False)
def load_fires():
    return _sql("SELECT * FROM fire_events")


@st.cache_data(ttl=300, show_spinner=False)
def load_runs():
    return _sql("SELECT * FROM pipeline_runs ORDER BY started_at DESC")


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌍 Monitor Ambiental")
    st.markdown("**TFM · Data Engineer**  \nUCM · 2026")
    st.divider()

    section = st.radio(
        "Sección",
        options=[
            "📊 Resumen",
            "💨 Calidad del Aire",
            "🌡️ Clima",
            "🦁 Biodiversidad",
            "🔥 Incendios",
            "🤖 Machine Learning",
            "🗂️ Explorador de Datos",
        ],
        label_visibility="collapsed",
    )
    st.divider()
    if st.button("🔄 Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Estado de la DB
    try:
        _conn()
        st.success("✅ Base de datos conectada")
    except Exception:
        st.error("❌ DB no encontrada — ejecuta el pipeline primero")


# ═══════════════════════════════════════════════════════════════════════════════
#  SECCIÓN 1 — RESUMEN
# ═══════════════════════════════════════════════════════════════════════════════
if section == "📊 Resumen":
    st.title("📊 Resumen Ejecutivo")
    st.caption("Pipeline ETL de Monitorización Ambiental · Datos en tiempo real desde 4 fuentes públicas")

    # KPIs
    df_air   = load_air()
    df_fire  = load_fires()
    df_bio   = load_bio()
    df_wx    = load_weather()

    pm25     = df_air[df_air["parameter"] == "pm25"]
    avg_pm   = pm25.groupby("location")["value"].mean()
    n_over   = (avg_pm > OMS_LIMIT).sum()
    n_cities = df_air["location"].nunique()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Ciudades monitoreadas", n_cities)
    with c2:
        st.metric("Registros de calidad del aire", f"{len(df_air):,}")
    with c3:
        st.metric(f"Ciudades sobre límite OMS ({OMS_LIMIT} µg/m³)", f"{n_over} de {n_cities}",
                  delta=f"{n_over} en alerta", delta_color="inverse")
    with c4:
        st.metric("Focos de incendio (7 días)", f"{len(df_fire):,}")

    st.divider()

    col_a, col_b = st.columns([3, 2])

    # Mini-gráfico PM2.5
    with col_a:
        st.subheader("PM2.5 por ciudad vs. límite OMS")
        if not pm25.empty:
            df_pm = pm25.groupby("location")["value"].mean().sort_values(ascending=False).reset_index()
            fig, ax = plt.subplots(figsize=(7, 3.5))
            colors = ["#d32f2f" if v > OMS_LIMIT else "#1976D2" for v in df_pm["value"]]
            ax.barh(df_pm["location"], df_pm["value"], color=colors, alpha=0.85, height=0.6)
            ax.axvline(OMS_LIMIT, color="#FF5722", lw=1.8, ls="--", label=f"OMS {OMS_LIMIT} µg/m³")
            for _, row in df_pm.iterrows():
                ax.text(row["value"] + 0.3, df_pm[df_pm["location"] == row["location"]].index[0],
                        f'{row["value"]:.1f}', va="center", fontsize=8.5)
            ax.set_xlabel("PM2.5 promedio (µg/m³)")
            ax.legend(frameon=False, fontsize=8)
            ax.spines[["top", "right"]].set_visible(False)
            ax.set_xlim(0, df_pm["value"].max() * 1.2)
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)
            plt.close()
        else:
            st.info("Sin datos de calidad del aire. Ejecuta el pipeline primero.")

    # Pipeline runs
    with col_b:
        st.subheader("Últimas ejecuciones del pipeline")
        try:
            df_runs = load_runs()
            if not df_runs.empty:
                for _, row in df_runs.head(5).iterrows():
                    status_icon = "✅" if row.get("status") == "ok" else "❌"
                    st.markdown(
                        f"{status_icon} `{str(row.get('started_at',''))[:16]}` — "
                        f"**{row.get('records_loaded', '?')}** registros cargados"
                    )
            else:
                st.info("No hay ejecuciones registradas.")
        except Exception:
            st.info("Tabla pipeline_runs no disponible.")

    # Tabla resumen por fuente
    st.divider()
    st.subheader("Resumen de datos por fuente")
    resumen = pd.DataFrame({
        "Fuente": ["OpenAQ", "Open-Meteo", "GBIF", "NASA FIRMS"],
        "Tabla": ["air_quality", "weather", "biodiversity", "fire_events"],
        "Registros": [len(df_air), len(df_wx), len(df_bio), len(df_fire)],
        "Ciudades / Cobertura": [
            str(df_air["location"].nunique()),
            str(df_wx["location"].nunique()),
            str(df_bio["location_ref"].nunique()) if "location_ref" in df_bio.columns else "—",
            "Global",
        ],
    })
    st.dataframe(resumen, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SECCIÓN 2 — CALIDAD DEL AIRE
# ═══════════════════════════════════════════════════════════════════════════════
elif section == "💨 Calidad del Aire":
    st.title("💨 Calidad del Aire")

    df_air = load_air()
    if df_air.empty:
        st.warning("Sin datos. Ejecuta el pipeline primero.")
        st.stop()

    # Filtros
    c1, c2 = st.columns(2)
    with c1:
        ciudades = st.multiselect("Ciudades", sorted(df_air["location"].unique()),
                                  default=sorted(df_air["location"].unique()))
    with c2:
        params = st.multiselect("Parámetro", sorted(df_air["parameter"].dropna().unique()),
                                default=["pm25"])

    df_f = df_air[df_air["location"].isin(ciudades) & df_air["parameter"].isin(params)]

    # Gráfico PM2.5
    pm25 = df_air[df_air["parameter"] == "pm25"]
    if not pm25.empty:
        df_pm = pm25.groupby("location")["value"].mean().sort_values(ascending=False).reset_index()
        fig, ax = plt.subplots(figsize=(9, 4))
        colors = ["#d32f2f" if v > OMS_LIMIT else "#1976D2" for v in df_pm["value"]]
        bars = ax.barh(df_pm["location"], df_pm["value"], color=colors, alpha=0.85, height=0.6)
        ax.axvline(OMS_LIMIT, color="#FF5722", lw=1.8, ls="--",
                   label=f"Límite OMS 2021 ({OMS_LIMIT} µg/m³)")
        for bar, val in zip(bars, df_pm["value"]):
            ax.text(bar.get_width() + 0.4, bar.get_y() + bar.get_height() / 2,
                    f"{val:.1f}", va="center", fontsize=9)
        ax.set_xlabel("PM2.5 promedio (µg/m³)")
        ax.set_title("Concentración de PM2.5 por ciudad", fontweight="bold")
        ax.legend(frameon=False)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_xlim(0, df_pm["value"].max() * 1.2)
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close()

    # Resumen por contaminante
    st.subheader("Promedio por contaminante y ciudad")
    if not df_f.empty:
        tabla = df_f.groupby(["location", "parameter"])["value"].mean().unstack().round(2)
        st.dataframe(tabla, use_container_width=True)
    else:
        st.info("Selecciona al menos una ciudad y un parámetro.")

    # Datos crudos
    with st.expander("Ver datos crudos"):
        st.dataframe(df_f[["location", "parameter", "value", "unit", "datetime_utc"]],
                     use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SECCIÓN 3 — CLIMA
# ═══════════════════════════════════════════════════════════════════════════════
elif section == "🌡️ Clima":
    st.title("🌡️ Variables Climáticas")

    df_wx = load_weather()
    if df_wx.empty:
        st.warning("Sin datos. Ejecuta el pipeline primero.")
        st.stop()

    ciudades = st.multiselect("Ciudades", sorted(df_wx["location"].unique()),
                              default=sorted(df_wx["location"].unique()))
    df_f = df_wx[df_wx["location"].isin(ciudades)]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Temperatura
    ax = axes[0]
    for i, city in enumerate(ciudades):
        d = df_f[df_f["location"] == city].sort_values("date")
        ax.plot(d["date"], d["temperature_2m"], marker="o", markersize=3,
                lw=1.8, color=PALETTE[i % len(PALETTE)], label=city)
    ax.set_title("Temperatura máxima diaria (°C)", fontweight="bold")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("°C")
    ax.legend(fontsize=8, frameon=False, ncol=2)
    ax.tick_params(axis="x", rotation=30)
    ax.spines[["top", "right"]].set_visible(False)

    # Precipitación acumulada
    ax2 = axes[1]
    if "precipitation" in df_f.columns:
        precip = df_f.groupby("location")["precipitation"].sum().sort_values()
        ax2.barh(precip.index, precip.values, color=PALETTE[:len(precip)], alpha=0.85, height=0.6)
        for i, (city, val) in enumerate(precip.items()):
            ax2.text(val + 0.5, i, f"{val:.0f} mm", va="center", fontsize=9)
        ax2.set_title("Precipitación acumulada (período)", fontweight="bold")
        ax2.set_xlabel("mm")
        ax2.set_xlim(0, precip.max() * 1.2)
    ax2.spines[["top", "right"]].set_visible(False)

    plt.suptitle("Variables Climáticas — Período de Monitoreo", fontsize=13,
                 fontweight="bold", y=1.01)
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close()

    with st.expander("Ver datos crudos"):
        cols = ["location", "date", "temperature_2m", "precipitation",
                "windspeed_10m", "weathercode"]
        st.dataframe(df_f[[c for c in cols if c in df_f.columns]], use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SECCIÓN 4 — BIODIVERSIDAD
# ═══════════════════════════════════════════════════════════════════════════════
elif section == "🦁 Biodiversidad":
    st.title("🦁 Biodiversidad")

    df_bio = load_bio()
    if df_bio.empty:
        st.warning("Sin datos. Ejecuta el pipeline primero.")
        st.stop()

    loc_col = "location_ref" if "location_ref" in df_bio.columns else "location"

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Top clases taxonómicas
    ax = axes[0]
    top_cls = df_bio["class"].value_counts().head(10)
    ax.barh(top_cls.index[::-1], top_cls.values[::-1],
            color=PALETTE[:len(top_cls)], alpha=0.85, height=0.65)
    for i, val in enumerate(top_cls.values[::-1]):
        ax.text(val + 1, i, str(val), va="center", fontsize=9)
    ax.set_title("Observaciones por clase taxonómica (Top 10)", fontweight="bold")
    ax.set_xlabel("Registros")
    ax.set_xlim(0, top_cls.max() * 1.2)
    ax.spines[["top", "right"]].set_visible(False)

    # Distribución por ciudad
    ax2 = axes[1]
    top5_cls = df_bio["class"].value_counts().head(5).index.tolist()
    df_pivot = (
        df_bio[df_bio["class"].isin(top5_cls)]
        .groupby([loc_col, "class"])
        .size()
        .unstack(fill_value=0)
    )
    df_pivot.plot(kind="bar", ax=ax2, color=PALETTE[:5], alpha=0.85, width=0.7)
    ax2.set_title("Biodiversidad por ciudad (Top 5 clases)", fontweight="bold")
    ax2.set_xlabel("")
    ax2.set_ylabel("Registros")
    ax2.tick_params(axis="x", rotation=30)
    ax2.legend(fontsize=8, frameon=False)
    ax2.spines[["top", "right"]].set_visible(False)

    plt.suptitle("Análisis de Biodiversidad Global", fontsize=13, fontweight="bold", y=1.01)
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close()

    # Correlación PM2.5 vs especies
    st.subheader("Correlación: PM2.5 vs. Riqueza de Especies")
    df_air = load_air()
    pm25 = df_air[df_air["parameter"] == "pm25"].groupby("location")["value"].mean().reset_index()
    pm25.columns = ["location", "avg_pm25"]
    n_sp = df_bio.groupby(loc_col)["species"].nunique().reset_index()
    n_sp.columns = ["location", "n_especies"]
    df_corr = pm25.merge(n_sp, on="location")

    if len(df_corr) >= 3:
        fig2, ax3 = plt.subplots(figsize=(7, 4.5))
        colors_c = ["#d32f2f" if v > OMS_LIMIT else "#1976D2" for v in df_corr["avg_pm25"]]
        ax3.scatter(df_corr["avg_pm25"], df_corr["n_especies"],
                    c=colors_c, s=120, zorder=5, edgecolors="white", lw=0.8)
        for _, row in df_corr.iterrows():
            ax3.annotate(row["location"], (row["avg_pm25"], row["n_especies"]),
                         textcoords="offset points", xytext=(6, 4), fontsize=9)
        z = np.polyfit(df_corr["avg_pm25"], df_corr["n_especies"], 1)
        x_l = np.linspace(df_corr["avg_pm25"].min(), df_corr["avg_pm25"].max(), 100)
        ax3.plot(x_l, np.poly1d(z)(x_l), "k--", lw=1.2, alpha=0.5)
        ax3.axvline(OMS_LIMIT, color="#FF5722", lw=1.5, ls="--", alpha=0.7)
        r = df_corr["avg_pm25"].corr(df_corr["n_especies"])
        ax3.set_title(f"PM2.5 vs Riqueza de Especies  (r = {r:.3f})", fontweight="bold")
        ax3.set_xlabel("PM2.5 promedio (µg/m³)")
        ax3.set_ylabel("Especies distintas observadas")
        ax3.spines[["top", "right"]].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig2, use_container_width=True)
        plt.close()
        st.caption(f"Correlación de Pearson: **r = {r:.3f}** — tendencia "
                   f"{'negativa ↓ mayor PM2.5 → menos especies' if r < 0 else 'positiva'}.")
    else:
        st.info("Datos insuficientes para calcular la correlación.")

    with st.expander("Ver datos crudos"):
        st.dataframe(df_bio, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SECCIÓN 5 — INCENDIOS
# ═══════════════════════════════════════════════════════════════════════════════
elif section == "🔥 Incendios":
    st.title("🔥 Incendios Activos Globales — NASA FIRMS / MODIS")
    st.caption("Focos de calor detectados por satélite en los últimos 7 días")

    df_fire = load_fires()
    if df_fire.empty:
        st.warning("Sin datos. Ejecuta el pipeline primero.")
        st.stop()

    conf_min = st.slider("Confianza mínima (%)", 0, 100, 50, step=5)
    df_f = df_fire[df_fire["confidence"] >= conf_min]

    st.metric("Focos graficados", f"{len(df_f):,}")

    fig, ax = plt.subplots(figsize=(13, 6))
    ax.set_facecolor("#0d1b2a")
    fig.patch.set_facecolor("#0d1b2a")
    sc = ax.scatter(
        df_f["lon"], df_f["lat"],
        c=df_f["brightness"], cmap="YlOrRd",
        s=0.5, alpha=0.6, vmin=300, vmax=420, rasterized=True,
    )
    ax.axhline(0,    color="#334466", lw=0.5, ls="--")
    ax.axhline(23.5, color="#334466", lw=0.4, ls=":")
    ax.axhline(-23.5, color="#334466", lw=0.4, ls=":")
    cbar = plt.colorbar(sc, ax=ax, pad=0.01, shrink=0.7)
    cbar.set_label("Temperatura de brillo (K)", color="white", fontsize=9)
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.set_xlabel("Longitud", color="white")
    ax.set_ylabel("Latitud", color="white")
    ax.set_title(f"Incendios Activos Globales — {len(df_f):,} focos detectados",
                 color="white", fontweight="bold")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_edgecolor("#334466")
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close()

    with st.expander("Ver datos crudos"):
        st.dataframe(df_f[["lat", "lon", "brightness", "confidence", "daynight"]],
                     use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SECCIÓN 6 — MACHINE LEARNING
# ═══════════════════════════════════════════════════════════════════════════════
elif section == "🤖 Machine Learning":
    st.title("🤖 Clustering de Ciudades por Perfil Ambiental")
    st.markdown(
        "Modelo **K-Means** no supervisado que agrupa las ciudades según su perfil "
        "combinado de calidad del aire, clima y biodiversidad."
    )

    if not SKLEARN_OK:
        st.error("scikit-learn no está instalado. Ejecuta: `pip install scikit-learn`")
        st.stop()

    df_air = load_air()
    df_wx  = load_weather()
    df_bio = load_bio()
    loc_col = "location_ref" if "location_ref" in df_bio.columns else "location"

    if df_air.empty or df_wx.empty or df_bio.empty:
        st.warning("Sin datos suficientes. Ejecuta el pipeline primero.")
        st.stop()

    # Features
    pm  = df_air[df_air["parameter"] == "pm25" ].groupby("location")["value"].mean().rename("pm25")
    no2 = df_air[df_air["parameter"] == "no2"  ].groupby("location")["value"].mean().rename("no2")
    o3  = df_air[df_air["parameter"] == "o3"   ].groupby("location")["value"].mean().rename("o3")
    tmp = df_wx.groupby("location")["temperature_2m"].mean().rename("temp")
    pre = df_wx.groupby("location")["precipitation"].mean().rename("precip")
    wnd = df_wx.groupby("location")["windspeed_10m"].mean().rename("wind")
    spe = df_bio.groupby(loc_col)["species"].nunique().rename("n_species")

    df_feat = pd.concat([pm, no2, o3, tmp, pre, wnd, spe], axis=1).dropna()
    if len(df_feat) < 3:
        st.warning("Se necesitan al menos 3 ciudades con datos completos.")
        st.stop()

    X = StandardScaler().fit_transform(df_feat)

    # K óptimo
    K_max = min(6, len(df_feat))
    K_range = range(2, K_max)
    inertias, sils = [], []
    for k in K_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        lbl = km.fit_predict(X)
        inertias.append(km.inertia_)
        sils.append(silhouette_score(X, lbl))
    K_OPT = int(K_range[np.argmax(sils)])
    SIL_OPT = max(sils)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("K óptimo (silhouette)", K_OPT)
    with col2:
        st.metric("Coeficiente de Silhouette", f"{SIL_OPT:.3f}")

    # Gráfico codo + silhouette
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    ax.plot(list(K_range), inertias, marker="o", color="#1976D2", lw=2)
    ax.set_title("Método del Codo (Inercia)", fontweight="bold")
    ax.set_xlabel("K")
    ax.set_ylabel("Inercia")
    ax.spines[["top", "right"]].set_visible(False)

    ax2 = axes[1]
    ax2.plot(list(K_range), sils, marker="s", color="#388E3C", lw=2)
    ax2.axvline(K_OPT, color="#d32f2f", ls="--", lw=1.5, label=f"K={K_OPT}")
    ax2.set_title("Coeficiente de Silhouette", fontweight="bold")
    ax2.set_xlabel("K")
    ax2.set_ylabel("Silhouette")
    ax2.legend(frameon=False)
    ax2.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close()

    # Modelo final
    km_final = KMeans(n_clusters=K_OPT, random_state=42, n_init=10)
    df_feat["cluster"] = km_final.fit_predict(X)

    # PCA 2D
    pca = PCA(n_components=2, random_state=42)
    X_2d = pca.fit_transform(X)
    var_exp = pca.explained_variance_ratio_ * 100
    CLUSTER_COLORS = ["#1976D2", "#D32F2F", "#388E3C", "#7B1FA2", "#F57C00"]

    fig2, axes2 = plt.subplots(1, 2, figsize=(13, 5))
    ax = axes2[0]
    for ci in range(K_OPT):
        mask = df_feat["cluster"] == ci
        ax.scatter(X_2d[mask, 0], X_2d[mask, 1],
                   color=CLUSTER_COLORS[ci], s=140, zorder=5,
                   edgecolors="white", lw=0.8, label=f"Cluster {ci}")
        for idx in df_feat[mask].index:
            row_idx = df_feat.index.get_loc(idx)
            ax.annotate(idx, (X_2d[row_idx, 0], X_2d[row_idx, 1]),
                        textcoords="offset points", xytext=(6, 4), fontsize=9)
    ax.set_xlabel(f"PC1 ({var_exp[0]:.1f}% varianza)")
    ax.set_ylabel(f"PC2 ({var_exp[1]:.1f}% varianza)")
    ax.set_title("Visualización PCA 2D de los Clusters", fontweight="bold")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)

    # Radar
    variables = ["pm25", "no2", "o3", "temp", "precip", "wind", "n_species"]
    N = len(variables)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist() + [0]
    ax2 = axes2[1]
    ax2 = fig2.add_subplot(1, 2, 2, polar=True)
    for ci in range(K_OPT):
        vals_raw = df_feat[df_feat["cluster"] == ci][variables].mean().values
        vmin = df_feat[variables].min().values
        vmax = df_feat[variables].max().values
        vals_norm = (vals_raw - vmin) / (vmax - vmin + 1e-9)
        vals_plot = np.concatenate([vals_norm, [vals_norm[0]]])
        ax2.plot(angles, vals_plot, color=CLUSTER_COLORS[ci], lw=2, label=f"Cluster {ci}")
        ax2.fill(angles, vals_plot, color=CLUSTER_COLORS[ci], alpha=0.15)
    ax2.set_xticks(angles[:-1])
    ax2.set_xticklabels(["PM2.5", "NO₂", "O₃", "Temp.", "Precip.", "Viento", "Especies"],
                        fontsize=9)
    ax2.set_title("Perfil ambiental por cluster", fontweight="bold", pad=15)
    ax2.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), frameon=False)
    plt.tight_layout()
    st.pyplot(fig2, use_container_width=True)
    plt.close()

    # Tabla de perfiles
    st.subheader("Perfil de clusters")
    profile = df_feat.groupby("cluster")[variables].mean().round(2)
    profile.index = [f"Cluster {i}" for i in profile.index]
    st.dataframe(profile, use_container_width=True)

    st.subheader("Asignación de ciudades")
    city_cluster = df_feat[["cluster"]].copy()
    city_cluster.index.name = "Ciudad"
    city_cluster.columns = ["Cluster"]
    st.dataframe(city_cluster, use_container_width=True)

    # ── predict_cluster ──────────────────────────────────────────────────────
    st.divider()
    st.subheader("🔮 Predicción para nueva ciudad")
    st.caption("Introduce los indicadores ambientales de una nueva ciudad para clasificarla.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        pm25_in  = st.number_input("PM2.5 (µg/m³)", 0.0, 500.0, 25.0, step=1.0)
        no2_in   = st.number_input("NO₂ (µg/m³)",   0.0, 200.0, 15.0, step=1.0)
    with c2:
        o3_in    = st.number_input("O₃ (µg/m³)",    0.0, 200.0, 60.0, step=1.0)
        temp_in  = st.number_input("Temperatura (°C)", -10.0, 50.0, 20.0, step=0.5)
    with c3:
        pre_in   = st.number_input("Precipitación (mm)", 0.0, 200.0, 5.0, step=0.5)
        wnd_in   = st.number_input("Viento máx. (km/h)", 0.0, 100.0, 20.0, step=1.0)
    with c4:
        spe_in   = st.number_input("Nº especies observadas", 0, 200, 70, step=1)
        ciudad_n = st.text_input("Nombre de la ciudad", value="Nueva Ciudad")

    if st.button("🔍 Clasificar", use_container_width=True):
        sc = StandardScaler()
        sc.fit(df_feat[variables])
        new_vec = sc.transform([[pm25_in, no2_in, o3_in, temp_in, pre_in, wnd_in, spe_in]])
        pred_cluster = int(km_final.predict(new_vec)[0])

        # Describir el cluster predicho
        cluster_pm25 = df_feat[df_feat["cluster"] == pred_cluster]["pm25"].mean()
        perfil = "alta contaminación 🔴" if cluster_pm25 > OMS_LIMIT else "perfil limpio 🔵"

        st.success(
            f"**{ciudad_n}** → **Cluster {pred_cluster}** ({perfil})  \n"
            f"Similar a: **{', '.join(df_feat[df_feat['cluster'] == pred_cluster].index.tolist())}**"
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  SECCIÓN 7 — EXPLORADOR DE DATOS
# ═══════════════════════════════════════════════════════════════════════════════
elif section == "🗂️ Explorador de Datos":
    st.title("🗂️ Explorador de Datos")
    st.caption("Consulta y filtra directamente los datos de la base de datos SQLite.")

    tabla = st.selectbox(
        "Tabla",
        ["air_quality", "weather", "biodiversity", "fire_events", "pipeline_runs"],
    )

    try:
        df_raw = _sql(f"SELECT * FROM {tabla}")
    except Exception as e:
        st.error(f"Error al cargar la tabla: {e}")
        st.stop()

    # Filtro dinámico por columna de texto
    text_cols = df_raw.select_dtypes(include="object").columns.tolist()
    if text_cols:
        col_filtro = st.selectbox("Filtrar por columna", ["(ninguno)"] + text_cols)
        if col_filtro != "(ninguno)":
            valores = st.multiselect(
                f"Valores de '{col_filtro}'",
                sorted(df_raw[col_filtro].dropna().unique()),
            )
            if valores:
                df_raw = df_raw[df_raw[col_filtro].isin(valores)]

    st.markdown(f"**{len(df_raw):,}** filas · **{len(df_raw.columns)}** columnas")
    st.dataframe(df_raw, use_container_width=True, height=500)

    # Descarga CSV
    csv = df_raw.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Descargar CSV",
        data=csv,
        file_name=f"{tabla}.csv",
        mime="text/csv",
    )
