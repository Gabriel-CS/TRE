# app.py
import gc
import os

import pandas as pd
import streamlit as st

from src.analysis import (
    GRUPOS_ETARIOS,
    MODEL_COLOR,
    OKABE_ITO,
    STATUS_LABELS,
    URN_MODELS,
    UrnasCriticasAnalysis,
)
from src.tab_criticidade import render_tab_criticidade
from src.tab_geo import render_tab_geo
from src.tab_modelo import render_tab_modelo

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DE DADOS  (v2 — sem datasets gigantes, apenas CSVs particionados)
# ═══════════════════════════════════════════════════════════════════════════════

def _nivel_key(status_filter):
    """Converte status_filter (None ou int) para a chave string/int do dict."""
    return "todas as criticas" if status_filter is None else status_filter


DATA_CONFIG: dict[str, dict] = {
    "2022": {
        "niveis": {
            "todas as criticas": "data/output/nivel_criticidade/df_criticas_all_2022.csv",
            0:    "data/output/nivel_criticidade/df_critica_n0_2022.csv",
            1:    "data/output/nivel_criticidade/df_critica_n1_2022.csv",
            2:    "data/output/nivel_criticidade/df_critica_n2_2022.csv",
            3:    "data/output/nivel_criticidade/df_critica_n3_2022.csv",
            4:    "data/output/nivel_criticidade/df_critica_n4_2022.csv",
        },
        "modelos_urnas": {
            "todas as criticas": "data/output/modelos_urnas/df_completas_all_2022.zip",
            0:    "data/output/modelos_urnas/df_completas_n0_2022.zip",
            1:    "data/output/modelos_urnas/df_completas_n1_2022.zip",
            2:    "data/output/modelos_urnas/df_completas_n2_2022.zip",
            3:    "data/output/modelos_urnas/df_completas_n3_2022.zip",
            4:    "data/output/modelos_urnas/df_completas_n4_2022.zip",
        },
    },
    "2018": {
        "niveis": {
            "todas as criticas": "data/output/nivel_criticidade/df_criticas_all_2018.csv",
            0:    "data/output/nivel_criticidade/df_critica_n0_2018.csv",
            1:    "data/output/nivel_criticidade/df_critica_n1_2018.csv",
            2:    "data/output/nivel_criticidade/df_critica_n2_2018.csv",
            3:    "data/output/nivel_criticidade/df_critica_n3_2018.csv",
            4:    "data/output/nivel_criticidade/df_critica_n4_2018.csv",
        },
        "modelos_urnas": {
            "todas as criticas": "data/output/modelos_urnas/df_completas_all_2018.zip",
            0:    "data/output/modelos_urnas/df_completas_n0_2018.zip",
            1:    "data/output/modelos_urnas/df_completas_n1_2018.zip",
            2:    "data/output/modelos_urnas/df_completas_n2_2018.zip",
            3:    "data/output/modelos_urnas/df_completas_n3_2018.zip",
            4:    "data/output/modelos_urnas/df_completas_n4_2018.zip",
        },
    },
}


# Cores associadas aos níveis de criticidade (para UI / popover)
STATUS_COLORS: dict[int, str] = {
    0: "#17a2b8",   # Sem Atraso
    1: "#28a745",   # Normal
    2: "#ffc107",   # Atenção
    3: "#dc3545",   # Crítico
    4: "#6f1d1b",   # Emergência
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DA PÁGINA
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Urnas Críticas | Dashboard Integrado",
    page_icon=":round_pushpin:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════════════════════════
# TEMA CORPORATIVO MINIMALISTA
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

        .main-header { font-weight: 700; color: #1a1a2e; letter-spacing: -0.02em;
                       margin-bottom: 0.25rem; font-size: 1.6rem; }
        .sub-header  { color: #6c757d; font-size: 1rem; margin-top: -0.25rem; margin-bottom: 1.25rem; }

        .kpi-box { background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
                   border: 1px solid #e9ecef; border-radius: 12px; padding: 1.25rem;
                   text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
                   transition: transform 0.2s ease, box-shadow 0.2s ease; height: 100%; }
        .kpi-box:hover  { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
        .kpi-label      { font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
                          letter-spacing: 0.08em; color: #adb5bd; margin-bottom: 0.5rem; }
        .kpi-value      { font-size: 1.6rem; font-weight: 700; color: #212529; line-height: 1.2; }
        .kpi-accent     { color: #0072B2; }
        .kpi-danger     { color: #D55E00; }
        .kpi-success    { color: #009E73; }

        .section-header { border-left: 4px solid #1a1a2e; padding-left: 12px;
                          margin: 1.5rem 0 0.75rem 0; }
        .section-header h2 { margin: 0; font-size: 1.15rem; font-weight: 600; color: #1a1a2e; }
        .section-desc { font-size: 0.85rem; color: #6c757d; margin-bottom: 1rem; padding-left: 16px; }

        .folium-map { border-radius: 12px; overflow: hidden;
                      box-shadow: 0 4px 16px rgba(0,0,0,0.08); border: 1px solid #e9ecef; }

        .resumo-card { border: 1px solid #e9ecef; border-radius: 8px; padding: 8px 12px;
                       margin-bottom: 6px; background: white; display: flex;
                       align-items: center; justify-content: space-between;
                       gap: 10px; transition: background 0.15s; }
        .resumo-card:hover       { background: #f8f9fa; }
        .resumo-dot              { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
        .resumo-nome             { font-size: 0.8rem; font-weight: 600; color: #1a1a2e; }
        .resumo-metrica-valor    { font-size: 0.82rem; font-weight: 700; color: #333;
                                   font-family: 'SF Mono', Monaco, monospace; }
        .resumo-metrica-label    { font-size: 0.6rem; color: #adb5bd;
                                   text-transform: uppercase; letter-spacing: 0.3px; }

        .alert-box     { padding: 1rem 1.25rem; border-radius: 8px; border-left: 4px solid; margin-bottom: 1rem; }
        .alert-danger  { background: #f8d7da; border-color: #dc3545; color: #721c24; }
        .alert-success { background: #d4edda; border-color: #28a745; color: #155724; }
        .alert-warning { background: #fff3cd; border-color: #ffc107; color: #856404; }

        .status-badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px;
                        font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
                        letter-spacing: 0.05em; }
        .status-1 { background: #d4edda; color: #155724; }
        .status-2 { background: #fff3cd; color: #856404; }
        .status-3 { background: #f8d7da; color: #721c24; }
        .status-4 { background: #f5c6cb; color: #721c24; }

        .footer { margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid #e9ecef;
                  text-align: center; color: #adb5bd; font-size: 0.8rem; }

        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] { padding: 10px 20px; font-weight: 500; font-size: 0.9rem;
                                       border-radius: 8px 8px 0 0; color: #6c757d; }
        .stTabs [aria-selected="true"] { background: #1a1a2e !important; color: white !important; }

        /* ═════════════════════════════════════════════════════════════════
           Melhoria 5 — Botao de informacao estilizado (popover nativo)
           ═════════════════════════════════════════════════════════════════ */
        [data-testid="stPopoverButton"] > button {
            border-radius: 50% !important;
            width: 24px !important; height: 24px !important;
            min-width: 24px !important; min-height: 24px !important;
            padding: 0 !important; margin: 0 !important;
            background: #e9ecef !important; color: #6c757d !important;
            font-size: 12px !important; font-weight: 700 !important;
            border: 1px solid #ced4da !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
            transition: all 0.2s ease !important;
            display: inline-flex !important; align-items: center !important;
            justify-content: center !important; line-height: 1 !important;
        }
        [data-testid="stPopoverButton"] > button:hover {
            background: #1a1a2e !important; color: white !important;
            border-color: #1a1a2e !important;
            box-shadow: 0 2px 6px rgba(26,26,46,0.25) !important;
            transform: scale(1.1);
        }
        [data-testid="stPopoverButton"] {
            padding: 0 !important; margin: 0 !important;
        }
    </style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CACHE DE DADOS — ESTRATÉGIA DE MEMÓRIA (apenas CSVs leves por filtro)
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False, max_entries=2, ttl=300)
def _load_csv_cached(path: str) -> pd.DataFrame:
    """Carrega CSV particionado tentando vírgula e ponto-e-vírgula como separadores."""
    import os

    # Primeiro tenta com vírgula (padrão)
    try:
        df = pd.read_csv(path, sep=",", encoding="utf-8")
        # Se só tiver 1 coluna, provavelmente o separador está errado
        if len(df.columns) <= 1:
            raise ValueError("Possivelmente separador incorreto")
    except Exception:
        # Fallback: tenta com ponto-e-vírgula
        df = pd.read_csv(path, sep=";", encoding="utf-8")

    df.columns = df.columns.str.strip()
    return df


@st.cache_data(show_spinner=False, max_entries=4, ttl=1800)
def _count_rows(path: str) -> int:
    """Conta linhas carregando apenas a primeira coluna — extremamente leve."""
    try:
        df = pd.read_csv(path, sep=",", encoding="utf-8", usecols=[0])
        return len(df)
    except Exception:
        return 0


@st.cache_data(show_spinner=False, max_entries=2, ttl=600)
def _load_estado_means(nivel_all_path: str) -> dict[str, float]:
    """Lê apenas 3 colunas do CSV 'all' para calcular médias estaduais."""
    cols = ["TIMEOUT_BIOMETRIA", "INATIVIDADE", "TECLA_INDEVIDA"]
    try:
        df = pd.read_csv(nivel_all_path, sep=",", encoding="utf-8", usecols=cols)
        return {c: float(df[c].mean()) for c in cols}
    except Exception:
        return {}

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════
col_title, col_info = st.columns([3, 1])
with col_title:
    st.markdown("""
        <div class="main-header">Urnas Críticas · Dashboard Integrado</div>
        <div class="sub-header">Análise operacional, sociodemográfica e geoespacial por modelo de urna</div>
    """, unsafe_allow_html=True)
with col_info:
    st.markdown(f"""
        <div style="text-align: right; color: #adb5bd; font-size: 0.85rem; margin-top: 0.5rem;">
            <div style="font-weight: 600; color: #495057;">Última atualização</div>
            <div>{pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown(
    "<hr style='margin: 0.5rem 0 1.5rem 0; border: none; border-top: 1px solid #e9ecef;'>",
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════════════════════
# FILTROS GLOBAIS
# ═══════════════════════════════════════════════════════════════════════════════
fil_col1, fil_col2, fil_col3 = st.columns([1, 1.6, 1.7])

with fil_col1:
    anos_disponiveis = sorted(DATA_CONFIG.keys())
    ano_selecionado = st.selectbox("Ano eleitoral", anos_disponiveis, index=len(anos_disponiveis) - 1)

with fil_col2:
    # Layout interno: dropdown à esquerda, botão de info à direita
    col_status, col_info_btn = st.columns([4, 1])

    with col_status:
        status_opcoes = {
            "Todas as críticas": None,
            "1 — Normal":             1,
            "2 — Atenção":            2,
            "3 — Crítico":            3,
            "4 — Emergência":         4,
        }

        status_label = st.selectbox(
            "Status operacional", 
            list(status_opcoes.keys()),
        )
        status_filter = status_opcoes[status_label]

    with col_info_btn:
        # Alinha o botão verticalmente com o dropdown
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

        # Botao de informacao estilizado — popover nativo do Streamlit com CSS customizado
        with st.popover("i", use_container_width=False):
            for lvl, label in STATUS_LABELS.items():
                cor = STATUS_COLORS[lvl]
                desc = {
                    0: "Secoes sem atraso significativo na fila. Operacao fluida dentro dos parametros esperados.",
                    1: "Atraso leve e pontual na fila, dentro da margem de tolerancia operacional.",
                    2: "Atraso moderado na fila que causou pequenas interrupcoes no fluxo de votacao.",
                    3: "Atraso consideravel na fila, impactando significativamente o tempo de espera dos eleitores.",
                    4: "Atraso severo e prolongado na fila. Situacao critica que demandou intervencao imediata.",
                }[lvl]
                st.markdown(f"""
                    <div style="border-left:3px solid {cor};background:linear-gradient(90deg,{cor}10 0%,#fff 100%);padding:6px 8px;border-radius:0 6px 6px 0;margin-bottom:6px;">
                        <div style="display:flex;align-items:center;gap:6px;margin-bottom:2px;">
                            <span style="display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;border-radius:50%;background:{cor};color:white;font-size:10px;font-weight:700;">{lvl}</span>
                            <span style="font-size:13px;font-weight:600;color:#1a1a2e;">{label}</span>
                        </div>
                        <div style="font-size:11px;color:#495057;line-height:1.4;padding-left:24px;">{desc}</div>
                    </div>
                """, unsafe_allow_html=True)

if 'last_ano' not in st.session_state:
    st.session_state['last_ano'] = ano_selecionado

if st.session_state['last_ano'] != ano_selecionado:
    # Ano mudou: limpa todos os caches para liberar memória do ano anterior
    st.cache_data.clear()
    st.session_state['last_ano'] = ano_selecionado
    st.rerun()

with fil_col3:
    pass
#═══════════════════════════════════════════════════════════════════════════════
# VALIDAÇÃO DE ARQUIVOS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
cfg = DATA_CONFIG[ano_selecionado]

nivel_path   = cfg["niveis"][_nivel_key(status_filter)]
modelo_path  = cfg["modelos_urnas"][_nivel_key(status_filter)]

for path_check, label in [(nivel_path, "Níveis"), (modelo_path, "Modelos")]:
    if not os.path.exists(path_check):
        st.error(
            f"Arquivo não encontrado ({label}): `{path_check}`  \n"
            "Verifique os caminhos em `DATA_CONFIG`."
        )
        st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
# CARREGAMENTO DE DADOS  (apenas os 2 arquivos do filtro ativo)
# ═══════════════════════════════════════════════════════════════════════════════
with st.spinner("Carregando dados..."):
    # 1. Seções do nível selecionado (demografia + ocorrências agregadas por seção)
    df_secoes = _load_csv_cached(nivel_path)

    # 2. Log de votantes do nível selecionado (métricas operacionais por modelo de urna)
    df_voter_log = _load_csv_cached(modelo_path)

    # 3. Total global de seções
    # NOTA: nível 0 (Sem Atraso) removido do filtro. Se precisar voltar:
    # n0_path      = cfg["niveis"][_nivel_key(0)]
    # total_n0     = _count_rows(n0_path)     if os.path.exists(n0_path)    else 0
    n_all_path   = cfg["niveis"][_nivel_key(None)]
    total_crit   = _count_rows(n_all_path)  if os.path.exists(n_all_path) else 0
    total_secoes_global = total_crit  # + total_n0  (comentado: n0 removido)

    # 4. Médias estaduais para "vs Estado" (apenas quando filtro específico ativo)
    estado_means: dict[str, float] = {}
    if status_filter is not None:
        if os.path.exists(n_all_path):
            estado_means = _load_estado_means(n_all_path)

# Constrói a análise a partir dos DataFrames já em RAM (zero I/O adicional)
analise = UrnasCriticasAnalysis.from_dataframes(
    df_2022=df_voter_log,          # log de votantes filtrado por nível (modelos_urnas)
    df_completas=df_secoes,        # seções filtradas por nível (niveis)
    status_filter=status_filter,
    prefiltered=True,              # df_completas já está filtrado pelo status
    total_secoes_override=total_secoes_global,
)

# ═══════════════════════════════════════════════════════════════════════════════
# KPIs GLOBAIS
# ═══════════════════════════════════════════════════════════════════════════════
overview = analise.get_overview()
pct = overview["total_secoes_criticas"] / max(overview["total_secoes"], 1)

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-label">Selecionadas</div>
            <div class="kpi-value kpi-danger">{overview['total_secoes_criticas']:,}</div>
        </div>
    """, unsafe_allow_html=True)
with k2:
    st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-label">Total Seções</div>
            <div class="kpi-value">{overview['total_secoes']:,}</div>
        </div>
    """, unsafe_allow_html=True)
with k3:
    st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-label">Votantes</div>
            <div class="kpi-value kpi-success">{overview['total_votantes']:,}</div>
        </div>
    """, unsafe_allow_html=True)
with k4:
    st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-label">Modelos</div>
            <div class="kpi-value">{len(overview['modelos_presentes'])}</div>
        </div>
    """, unsafe_allow_html=True)
with k5:
    st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-label">Taxa Selecionada</div>
            <div class="kpi-value kpi-accent">{pct:.1%}</div>
        </div>
    """, unsafe_allow_html=True)

del overview
gc.collect()

st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# ABAS PRINCIPAIS
# ═══════════════════════════════════════════════════════════════════════════════
tab_geo, tab_criticidade, tab_modelo = st.tabs([
    "Visão Geográfica",
    "Análise por Criticidade",
    "Análise por Modelo de Urna",
])

with tab_geo:
    render_tab_geo(ano_selecionado, status_filter)

with tab_criticidade:
    # df_criticas já é o subconjunto correto para o filtro ativo
    render_tab_criticidade(analise.df_criticas, status_filter, estado_means)

with tab_modelo:
    render_tab_modelo(analise)

# ═══════════════════════════════════════════════════════════════════════════════
# CLEANUP FINAL
# ═══════════════════════════════════════════════════════════════════════════════
del analise, df_secoes, df_voter_log
gc.collect()

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
    <div class="footer">
        <div style="font-weight: 600; color: #adb5bd; margin-bottom: 0.25rem;">
            Sistema de Monitoramento Eleitoral Integrado
        </div>
        <div>Dados: TSE / Urnas Eletrônicas | Dashboard desenvolvido com Streamlit</div>
    </div>
""", unsafe_allow_html=True)