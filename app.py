# app_streamlit.py
import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from analysis import (
    UrnasCriticasAnalysis,
    URN_MODELS,
    OKABE_ITO,
    MODEL_COLOR,
    GRUPOS_ETARIOS,
)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DE DADOS — adicione novos anos aqui
# ═══════════════════════════════════════════════════════════════════════════════
DATA_CONFIG = {
    "2022": {
        "consolidado": "data/output/2022_1t_SE_urnas_consolidado.zip",
        "completas":   "data/data_aux_zip/urnas_completas_2022_1t.zip",
    },
    "2018": {
        "consolidado": "data/output/2018_1t_SE_urnas_consolidado.zip",
        "completas":   "data/data_aux_zip/urnas_completas_2018_1t.zip",
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DA PÁGINA
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Urnas Críticas · Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS DE GRÁFICOS (retornam figuras para st.plotly_chart)
# ═══════════════════════════════════════════════════════════════════════════════
_LAYOUT_BASE = dict(
    paper_bgcolor="white",
    plot_bgcolor="white",
    font=dict(family="Inter, Segoe UI, sans-serif", color="#444", size=12),
    margin=dict(t=50, b=40, l=50, r=20),
    xaxis=dict(showgrid=False, linecolor="#CCCCCC"),
    yaxis=dict(gridcolor="#EEEEEE", linecolor="#CCCCCC"),
    legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="#CCCCCC", borderwidth=1),
    showlegend=False,
)

def apply_base_layout(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(**_LAYOUT_BASE)
    fig.update_layout(height=height)
    return fig

def bar_chart(x, y, text=None, title="", yfmt=None, yrange=None, height=360) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=x,
        y=y,
        marker_color=OKABE_ITO[:len(x)],
        text=text or [f"{v:.1%}" if isinstance(v, float) and v < 1 else str(v) for v in y],
        textposition="outside",
        textfont=dict(size=11, color="#222"),
        width=0.55,
    ))
    fig.update_layout(title=title, showlegend=False)
    if yfmt:
        fig.update_layout(yaxis_tickformat=yfmt)
    if yrange:
        fig.update_layout(yaxis_range=yrange)
    return apply_base_layout(fig, height)

def stacked_bar(df_pct, labels, colors, title="", height=420) -> go.Figure:
    fig = go.Figure()
    for i, col in enumerate(labels):
        if col not in df_pct.columns:
            continue
        vals = df_pct[col].values
        fig.add_trace(go.Bar(
            name=col,
            x=URN_MODELS,
            y=vals,
            marker_color=colors[i % len(colors)],
            text=[f"{v*100:.1f}%" if v > 0.04 else "" for v in vals],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(size=9, color="white"),
        ))
    fig.update_layout(
        barmode="stack",
        title=title,
        legend=dict(orientation="h", yanchor="bottom", y=-0.30, xanchor="center", x=0.5),
        margin=dict(t=50, b=80, l=50, r=20),
        showlegend=True,
    )
    fig.update_layout(yaxis=dict(tickformat=".0%", range=[0, 1.0], gridcolor="#EEEEEE", linecolor="#CCCCCC"))
    return apply_base_layout(fig, height)

# ═══════════════════════════════════════════════════════════════════════════════
# CACHE PARA CARREGAMENTO DOS DADOS
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def load_analysis(consolidado_path, completas_path, status_filter):
    return UrnasCriticasAnalysis(
        path_consolidado=consolidado_path,
        path_urnas_completas=completas_path,
        status_filter=status_filter,
    )

# ═══════════════════════════════════════════════════════════════════════════════
# INTERFACE DO DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    .kpi-box {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        background: white;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        margin-bottom: 10px;
    }
    .kpi-value {
        font-size: 1.6rem;
        font-weight: bold;
        color: #0072B2;
        margin: 5px 0;
    }
    .kpi-label {
        font-size: 0.8rem;
        color: #666;
    }
    .section-header {
        border-left: 4px solid #0072B2;
        padding-left: 10px;
        margin-bottom: 6px;
    }
    .section-header h2 {
        margin: 0;
        font-size: 1.1rem;
        color: #1a3a5c;
    }
    .section-desc {
        font-size: 0.82rem;
        color: #666;
        margin-bottom: 14px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🗳️ Urnas Críticas — Dashboard")
st.markdown("Análise operacional e sociodemográfica por modelo de urna")

# Filtros
col1, col2 = st.columns(2)
with col1:
    anos_disponiveis = sorted(DATA_CONFIG.keys())
    ano_selecionado = st.selectbox("Ano", anos_disponiveis, index=len(anos_disponiveis)-1)
with col2:
    status_opcoes = {
        "> 0 (Todas as críticas)": None,
        "0 — Não crítica": 0,
        "1 — Crítica leve": 1,
        "2 — Crítica": 2,
        "3 — Crítica alta": 3,
        "4 — Crítica máxima": 4,
    }
    status_label = st.selectbox("Status", list(status_opcoes.keys()))
    status_filter = status_opcoes[status_label]

# Carrega análise
cfg = DATA_CONFIG[ano_selecionado]
if not os.path.exists(cfg["consolidado"]) or not os.path.exists(cfg["completas"]):
    st.error(f"Arquivo(s) não encontrado(s) para o ano {ano_selecionado}. Verifique os caminhos.")
    st.stop()

analise = load_analysis(cfg["consolidado"], cfg["completas"], status_filter)

# ── KPIs ─────────────────────────────────────────────────────────────────────
overview = analise.get_overview()
pct = overview["total_secoes_criticas"] / max(overview["total_secoes"], 1)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown("<div class='kpi-box'>", unsafe_allow_html=True)
    st.markdown("<div class='kpi-label'>Selecionadas</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-value' style='color:#D55E00;'>{overview['total_secoes_criticas']:,}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='kpi-box'>", unsafe_allow_html=True)
    st.markdown("<div class='kpi-label'>Total Seções</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-value'>{overview['total_secoes']:,}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col3:
    st.markdown("<div class='kpi-box'>", unsafe_allow_html=True)
    st.markdown("<div class='kpi-label'>Votantes (log)</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-value' style='color:#009E73;'>{overview['total_votantes']:,}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col4:
    st.markdown("<div class='kpi-box'>", unsafe_allow_html=True)
    st.markdown("<div class='kpi-label'>Modelos</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-value'>{len(overview['modelos_presentes'])}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col5:
    st.markdown("<div class='kpi-box'>", unsafe_allow_html=True)
    st.markdown("<div class='kpi-label'>Taxa Selecionada</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-value'>{pct:.1%}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ── Distribuição de Modelos ──────────────────────────────────────────────────
st.markdown("---")
st.markdown("<div class='section-header'><h2>Distribuição de Modelos</h2></div>", unsafe_allow_html=True)
st.markdown("<div class='section-desc'>Proporção e quantidade absoluta de seções por modelo de urna.</div>", unsafe_allow_html=True)

dist = analise.get_model_distribution()
col1, col2 = st.columns(2)
with col1:
    fig_dist_pct = bar_chart(
        URN_MODELS, dist["proportions"],
        text=[f"{v*100:.1f}%" for v in dist["proportions"]],
        title="Proporção de Urnas por Modelo", yfmt=".0%",
        yrange=[0, max(dist["proportions"]) * 1.25 or 0.1],
    )
    st.plotly_chart(fig_dist_pct, use_container_width=True)

with col2:
    fig_dist_count = bar_chart(
        URN_MODELS, dist["counts"],
        text=[f"{v:,}" for v in dist["counts"]],
        title="Total de Seções por Modelo",
        yrange=[0, max(dist["counts"]) * 1.25 or 1],
    )
    st.plotly_chart(fig_dist_count, use_container_width=True)

# ── Falhas Biométricas ───────────────────────────────────────────────────────
st.markdown("---")
st.markdown("<div class='section-header'><h2>Falhas Biométricas na Pré-Habilitação</h2></div>", unsafe_allow_html=True)
st.markdown("<div class='section-desc'>Proporção de votantes com ≥1 falha biométrica, entre os que tiveram biometria solicitada.</div>", unsafe_allow_html=True)

bio = analise.get_bio_failure_rates()
fig_bio = bar_chart(
    URN_MODELS, bio["rates"],
    text=[f"{v*100:.1f}%" for v in bio["rates"]],
    title="Falha Biométrica por Modelo", yfmt=".0%", yrange=[0, 1.0],
)
st.plotly_chart(fig_bio, use_container_width=True)

# ── Tempo de Fila e Autenticação ─────────────────────────────────────────────
st.markdown("---")
st.markdown("<div class='section-header'><h2>Tempo de Espera em Fila e Duração da Autenticação</h2></div>", unsafe_allow_html=True)
st.markdown("<div class='section-desc'>Média ± desvio padrão (excluindo registros zerados).</div>", unsafe_allow_html=True)

fila = analise.get_queue_times()
auth = analise.get_auth_duration()

col1, col2 = st.columns(2)
with col1:
    fig_fila = bar_chart(
        URN_MODELS, fila["means"],
        text=[f"{v:.1f}s" for v in fila["means"]],
        title="Tempo de Fila (média ± DP)",
        yrange=[0, max([m + s for m, s in zip(fila["means"], fila["stds"])]) * 1.25 or 1],
    )
    st.plotly_chart(fig_fila, use_container_width=True)

with col2:
    fig_auth = bar_chart(
        URN_MODELS, auth["means"],
        text=[f"{v:.1f}s" for v in auth["means"]],
        title="Duração da Autenticação (média ± DP)",
        yrange=[0, max([m + s for m, s in zip(auth["means"], auth["stds"])]) * 1.25 or 1],
    )
    st.plotly_chart(fig_auth, use_container_width=True)

# ── Tempo de Inatividade ─────────────────────────────────────────────────────
st.markdown("---")
st.markdown("<div class='section-header'><h2>Tempo de Inatividade durante a Seção</h2></div>", unsafe_allow_html=True)
st.markdown("<div class='section-desc'>Média ± desvio padrão do tempo de inatividade no processo de votação (excluindo zeros).</div>", unsafe_allow_html=True)

inat = analise.get_inactivity_times()
fig_inat = bar_chart(
    URN_MODELS, inat["means"],
    text=[f"{v:.1f}s" for v in inat["means"]],
    title="Tempo de Inatividade (média ± DP)",
    yrange=[0, max([m + s for m, s in zip(inat["means"], inat["stds"])]) * 1.25 or 1],
)
st.plotly_chart(fig_inat, use_container_width=True)

# ── Teclas Indevidas ─────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("<div class='section-header'><h2>Proporção de Teclas Indevidas</h2></div>", unsafe_allow_html=True)
st.markdown("<div class='section-desc'>Parcela do total de teclas indevidas concentrada por modelo.</div>", unsafe_allow_html=True)

inv_keys = analise.get_invalid_keys()
fig_keys = bar_chart(
    URN_MODELS, inv_keys["proportions"],
    text=[f"{v*100:.1f}%" for v in inv_keys["proportions"]],
    title="Teclas Indevidas por Modelo", yfmt=".0%",
    yrange=[0, max(inv_keys["proportions"]) * 1.25 or 0.1],
)
st.plotly_chart(fig_keys, use_container_width=True)

# ── Escolaridade ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("<div class='section-header'><h2>Escolaridade</h2></div>", unsafe_allow_html=True)
st.markdown("<div class='section-desc'>Distribuição por grau de escolaridade e proporção de baixa escolaridade.</div>", unsafe_allow_html=True)

edu = analise.get_education_distribution()
low_edu = analise.get_low_education()
col1, col2 = st.columns(2)
with col1:
    fig_edu_stacked = stacked_bar(
        edu["df_proportions"],
        edu["labels"],
        px.colors.qualitative.Pastel,
        title="Distribuição por Escolaridade",
    )
    st.plotly_chart(fig_edu_stacked, use_container_width=True)
with col2:
    fig_low_edu = bar_chart(
        URN_MODELS, low_edu["proportions"],
        text=[f"{v*100:.1f}%" for v in low_edu["proportions"]],
        title="Baixa Escolaridade por Modelo", yfmt=".0%",
        yrange=[0, max(low_edu["proportions"]) * 1.25 or 0.1],
    )
    st.plotly_chart(fig_low_edu, use_container_width=True)

# ── Faixa Etária ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("<div class='section-header'><h2>Faixa Etária</h2></div>", unsafe_allow_html=True)
st.markdown("<div class='section-desc'>Distribuição etária e proporção de eleitores idosos (≥ 60 anos).</div>", unsafe_allow_html=True)

age = analise.get_age_distribution()
elderly = analise.get_elderly_proportion()
col1, col2 = st.columns(2)
with col1:
    fig_age_stacked = stacked_bar(
        age["df_proportions"],
        age["groups"],
        px.colors.qualitative.Safe,
        title="Distribuição por Faixa Etária",
    )
    st.plotly_chart(fig_age_stacked, use_container_width=True)
with col2:
    fig_elderly = bar_chart(
        URN_MODELS, elderly["proportions"],
        text=[f"{v*100:.1f}%" for v in elderly["proportions"]],
        title="Eleitores Idosos (≥ 60 anos)", yfmt=".0%",
        yrange=[0, max(elderly["proportions"]) * 1.25 or 0.1],
    )
    st.plotly_chart(fig_elderly, use_container_width=True)

# ── Eleitores PCD ────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("<div class='section-header'><h2>Eleitores PCD</h2></div>", unsafe_allow_html=True)
st.markdown("<div class='section-desc'>Quantidade absoluta, taxa e relação com falhas biométricas.</div>", unsafe_allow_html=True)

pcd = analise.get_pcd_stats()
col1, col2 = st.columns(2)
with col1:
    fig_pcd_count = bar_chart(
        URN_MODELS, pcd["totals"],
        text=[f"{v:,}" for v in pcd["totals"]],
        title="Total de Eleitores PCD",
        yrange=[0, max(pcd["totals"]) * 1.25 or 1],
    )
    st.plotly_chart(fig_pcd_count, use_container_width=True)
with col2:
    fig_pcd_rate = bar_chart(
        URN_MODELS, pcd["taxas"],
        text=[f"{v*100:.2f}%" for v in pcd["taxas"]],
        title="Taxa de Eleitores PCD", yfmt=".2%",
        yrange=[0, max(pcd["taxas"]) * 1.3 or 0.01],
    )
    st.plotly_chart(fig_pcd_rate, use_container_width=True)
#
#fig_scatter = go.Figure(
#    data=[
#        go.Scatter(
#            x=[pcd["taxas"][i] * 100],
#            y=[bio["rates"][i] * 100],
#            mode="markers+text",
#            name=m,
#            marker=dict(size=16, color=OKABE_ITO[i], line=dict(width=1.5, color="white")),
#            text=[m],
#            textposition="top right",
#            textfont=dict(size=10, color=OKABE_ITO[i]),
#        )
#        for i, m in enumerate(URN_MODELS)
#    ],
#    layout=dict(
#        title="Taxa PCD × Falha Biométrica",
#        xaxis=dict(title="Taxa PCD (%)", ticksuffix="%", showgrid=False, linecolor="#CCCCCC"),
#        yaxis=dict(title="Falha biométrica (%)", ticksuffix="%", gridcolor="#EEEEEE", range=[0, 70]),
#        showlegend=False,
#    ),
#)
#fig_scatter = apply_base_layout(fig_scatter, height=400)
#st.plotly_chart(fig_scatter, use_container_width=True)

# ── Tabelas Resumo ───────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("<div class='section-header'><h2>Tabelas Resumo</h2></div>", unsafe_allow_html=True)
st.markdown("<div class='section-desc'>Métricas operacionais consolidadas por modelo.</div>", unsafe_allow_html=True)

op_sum = analise.get_operational_summary()
pcd_sum = analise.get_pcd_summary()

st.subheader("Métricas Operacionais")
st.dataframe(op_sum, use_container_width=True, hide_index=True)

#st.subheader("Eleitores PCD")
#st.dataframe(pcd_sum, use_container_width=True, hide_index=True)

st.subheader("Distribuição de STATUS")
status_counts = overview["status_counts"]
badge_html = ""
for label, count in status_counts.items():
    cor = ""
    if "Não" in label:
        cor = "#009E73"
    elif "leve" in label:
        cor = "#E69F00"
    elif "alta" in label or "máx" in label:
        cor = "#D55E00"
    else:
        cor = "#444"
    badge_html += f'<span style="background:{cor};color:white;padding:5px 10px;border-radius:20px;margin-right:8px;font-size:0.8rem;">{label}: {count:,}</span>'
st.markdown(badge_html, unsafe_allow_html=True)

st.markdown("---")
st.caption("Dashboard desenvolvido com Streamlit · Dados: TSE / Urnas Eletrônicas")