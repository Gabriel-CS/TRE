# app_streamlit.py
import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from src.analysis import (
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
        "completas":   "data/output/urnas_completas_2022_1t.zip",
    },
    "2018": {
        "consolidado": "data/output/2018_1t_SE_urnas_consolidado.zip",
        "completas":   "data/output/urnas_completas_2018_1t.zip",
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

# ==============================================================================
# NOVA SEÇÃO: VISÃO POR NÍVEL DE CRITICIDADE 
# ==============================================================================
# 1. Definição do Caminho e Carregamento (Sempre dinâmico por ano)
caminho_csv = f"data/datasets/{ano_selecionado}/urnas_completas_{ano_selecionado}_1t.csv"

if os.path.exists(caminho_csv):
    df_visão = pd.read_csv(caminho_csv, sep=';', encoding='utf-8')
    df_visão.columns = df_visão.columns.str.strip()

    # --- CONDICIONAL 1: VISÃO GERAL (Todas as Críticas) ---
    if status_filter is None or status_filter == "Todas":
        st.markdown("---")
        st.markdown("<div class='section-header'><h2>Visão por Nível de Criticidade</h2></div>", unsafe_allow_html=True)
        
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            st.markdown("<h4 style='text-align: center; color: #1a3a5c;'>Média de Timeout de Biometria</h4>", unsafe_allow_html=True)
            m_timeout = df_visão.groupby('STATUS')['TIMEOUT_BIOMETRIA'].mean()
            m_tempo = df_visão.groupby('STATUS')['TPBSEC'].mean()
            fig_timeout = go.Figure(go.Bar(x=m_timeout.values, y=[f"Nível {s}" for s in m_timeout.index], orientation='h', marker_color=OKABE_ITO, text=[f"{v:.1f} ocorr. (~{int(t)//60}m{int(t)%60}s)" for v, t in zip(m_timeout.values, m_tempo.values)], textposition='outside'))
            fig_timeout = apply_base_layout(fig_timeout, height=350)
            fig_timeout.update_layout(yaxis=dict(tickfont=dict(color='black', size=13)))
            st.plotly_chart(fig_timeout, use_container_width=True)

        with col_v2:
            st.markdown("<h4 style='text-align: center; color: #1a3a5c;'>Média de Inatividade do Eleitor</h4>", unsafe_allow_html=True)
            m_inat = df_visão.groupby('STATUS')['INATIVIDADE'].mean()
            m_t_inat = df_visão.groupby('STATUS')['TTPISEC'].mean()
            fig_inat = go.Figure(go.Bar(x=m_inat.values, y=[f"Nível {s}" for s in m_inat.index], orientation='h', marker_color=OKABE_ITO, text=[f"{v:.1f} ocorr. (~{int(t)//60}m{int(t)%60}s)" for v, t in zip(m_inat.values, m_t_inat.values)], textposition='outside'))
            fig_inat = apply_base_layout(fig_inat, height=350)
            fig_inat.update_layout(yaxis=dict(tickfont=dict(color='black', size=13)))
            st.plotly_chart(fig_inat, use_container_width=True)

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("<h4 style='text-align: center; color: #1a3a5c;'>Distribuição de PCDs por Status</h4>", unsafe_allow_html=True)
            pcd_sum = df_visão.groupby('STATUS')['QTD_PCD'].sum()
            fig_pcd = go.Figure(go.Pie(labels=[f"Nível {s}" for s in pcd_sum.index], values=pcd_sum.values, hole=0.45, marker=dict(colors=OKABE_ITO)))
            st.plotly_chart(apply_base_layout(fig_pcd, height=350), use_container_width=True)

        with col_p2:
            st.markdown("<h4 style='text-align: center; color: #1a3a5c;'>Média de Teclas Indevidas</h4>", unsafe_allow_html=True)
            m_teclas = df_visão.groupby('STATUS')['TECLA_INDEVIDA'].mean()
            fig_teclas = go.Figure(go.Bar(x=m_teclas.values, y=[f"Nível {s}" for s in m_teclas.index], orientation='h', marker_color=OKABE_ITO, text=[f"{v:.2f}" for v in m_teclas.values], textposition='outside'))
            fig_teclas = apply_base_layout(fig_teclas, height=350)
            fig_teclas.update_layout(yaxis=dict(tickfont=dict(color='black', size=13)))
            st.plotly_chart(fig_teclas, use_container_width=True)

    # --- CONDICIONAL 2: DETALHAMENTO POR NÍVEL (0, 1, 2 e 3) ---
    elif status_filter in [0, 1, 2, 3]:
        st.markdown("---")
        titulo_nivel = f"Diagnóstico: Detalhamento Nível {status_filter}" if status_filter > 0 else "Visão Geral: Urnas Não Críticas (Nível 0)"
        st.markdown(f"<div class='section-header'><h2>{titulo_nivel}</h2></div>", unsafe_allow_html=True)
        
        df_nivel = df_visão[df_visão['STATUS'] == status_filter]
        
        # 1. KPIs de Impacto
        # 1. KPIs de Impacto (Ocorrências + Tempo Total Acumulado em Min/Seg)
        st.markdown(f"#### 🚨 Impacto Operacional: Nível {status_filter} vs Média do Estado")
        col_k1, col_k2, col_k3 = st.columns(3)

        def get_metrics(col_ocorr, col_tempo=None):
            m_est = df_visão[col_ocorr].mean()
            m_niv = df_nivel[col_ocorr].mean()
            delta = ((m_niv/m_est)-1)*100 if m_est > 0 else 0
            
            tempo_str = ""
            if col_tempo and col_tempo in df_nivel.columns:
                # AQUI ESTAVA O ERRO: Troquei .sum() por .mean()
                media_segundos = df_nivel[col_tempo].mean() 
                
                # Calculando os minutos e segundos médios
                minutos = int(media_segundos // 60)
                segundos = int(media_segundos % 60)
                tempo_str = f"Tempo total: ~{minutos}m {segundos}s"
            
            return m_niv, delta, tempo_str

        # Cartão 1: Inatividade
        v, d, t = get_metrics('INATIVIDADE', 'TTPISEC')
        with col_k1:
            st.metric("Inatividade", f"{v:.1f} ocorr.", f"{d:+.1f}% vs Estado", delta_color="inverse")
            st.caption(f"⏱️ {t}")

        # Cartão 2: Timeout Biometria
        v, d, t = get_metrics('TIMEOUT_BIOMETRIA', 'TPBSEC')
        with col_k2:
            st.metric("Timeout Bio", f"{v:.1f} ocorr.", f"{d:+.1f}% vs Estado", delta_color="inverse")
            st.caption(f"⏱️ {t}")

        # Cartão 3: Teclas Indevidas
        v, d, _ = get_metrics('TECLA_INDEVIDA')
        with col_k3:
            st.metric("Teclas Indevidas", f"{v:.2f} ocorr.", f"{d:+.1f}% vs Estado", delta_color="inverse")
            st.caption("⌨️ Erros de digitação")
            
        st.write("<br>", unsafe_allow_html=True)
        # 2. Perfil Demográfico (Idade e Escolaridade)
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.markdown("<h4 style='text-align: center; color: #1a3a5c;'>Perfil por Faixa Etária</h4>", unsafe_allow_html=True)
            cols_idade = [c for c in df_nivel.columns if 'IDADE_' in c and 'Inválido' not in c]
            df_i = df_nivel[cols_idade].sum().reset_index()
            
            fig_i = go.Figure(go.Bar(x=df_i[0], y=[c.replace('IDADE_', '').strip() for c in df_i['index']], orientation='h', marker_color='#1b5e20'))
            fig_i = apply_base_layout(fig_i, height=400)
            # AQUI: Adicionada a cor preta e tamanho na fonte do eixo Y
            fig_i.update_layout(yaxis=dict(tickfont=dict(color='black', size=13), categoryorder='total ascending'))
            st.plotly_chart(fig_i, use_container_width=True)

        with col_d2:
            st.markdown("<h4 style='text-align: center; color: #1a3a5c;'>Perfil por Escolaridade</h4>", unsafe_allow_html=True)
            cols_esc = [c for c in df_nivel.columns if 'ESC_' in c]
            df_e = df_nivel[cols_esc].sum().reset_index()
            
            fig_e = go.Figure(go.Bar(x=df_e[0], y=[c.replace('ESC_', '').title() for c in df_e['index']], orientation='h', marker_color='#0d47a1'))
            fig_e = apply_base_layout(fig_e, height=400)
            # AQUI: Adicionada a cor preta e tamanho na fonte do eixo Y
            fig_e.update_layout(yaxis=dict(tickfont=dict(color='black', size=13), categoryorder='total ascending'))
            st.plotly_chart(fig_e, use_container_width=True)

        # 3. Donut PCD vs Não PCD
        st.markdown("<br>", unsafe_allow_html=True)
        _, col_pcd_single, _ = st.columns([1, 2, 1])
        with col_pcd_single:
            st.markdown(f"<h4 style='text-align: center; color: #1a3a5c;'>Proporção de Eleitores PCD</h4>", unsafe_allow_html=True)
            total_votos = df_nivel[[c for c in df_nivel.columns if 'IDADE_' in c]].sum().sum()
            qtd_pcd = df_nivel['QTD_PCD'].sum()
            qtd_nao_pcd = total_votos - qtd_pcd
            
            fig_pcd_bin = go.Figure(go.Pie(labels=['PCD', 'Não PCD'], values=[qtd_pcd, qtd_nao_pcd], hole=0.45, marker=dict(colors=['#d62728', '#bcbd22']), textinfo='percent+value'))
            st.plotly_chart(apply_base_layout(fig_pcd_bin, height=400), use_container_width=True)
        # --- CONDICIONAL 3: ESTUDO DE CASO - URNAS SUPERCRÍTICAS (NÍVEL 4) ---
    # --- CONDICIONAL 3: ESTUDO DE CASO - URNAS SUPERCRÍTICAS (NÍVEL 4) ---
    elif status_filter == 4:
        st.markdown("---")
        st.markdown("<div class='section-header'><h2>🚨 Estudo de Caso: Urnas Supercríticas (Nível 4)</h2></div>", unsafe_allow_html=True)
        
        df_n4 = df_visão[df_visão['STATUS'] == 4]
        
        if df_n4.empty:
            st.success("🎉 Ótima notícia! Não há urnas classificadas como Supercríticas (Nível 4) neste cenário.")
        else:
            # 1. ORDENAÇÃO: Da urna com MAIOR atraso para a com menor atraso
            if 'ATRASO_FILA_MINUTOS' in df_n4.columns:
                df_n4 = df_n4.sort_values(by='ATRASO_FILA_MINUTOS', ascending=False)
                
            st.warning(f"Atenção: Foram encontradas **{len(df_n4)}** urnas Supercríticas. Selecione uma abaixo para investigação detalhada.")
            
            # 2. Criando o Menu com o tempo de atraso já visível!
            opcoes_urna = []
            for index, row in df_n4.iterrows():
                # Puxa o atraso pra mostrar direto no menu
                atraso_str = f" | Atraso: {row.get('ATRASO_FILA_MINUTOS', 0):.0f} min"
                nome_formatado = f"{row['NM_MUNICIPIO']} (Z: {row['NR_ZONA']} - S: {row['NR_SECAO']}){atraso_str}"
                opcoes_urna.append((index, nome_formatado))
                
            urna_selecionada_idx = st.selectbox(
                "Selecione a Urna (Ordenado do maior para o menor atraso):",
                options=[op[0] for op in opcoes_urna],
                format_func=lambda x: next(op[1] for op in opcoes_urna if op[0] == x)
            )
            
            urna = df_n4.loc[urna_selecionada_idx]
            
            # Cabeçalho do Prontuário
            st.markdown(f"""
            <div style="background-color: #f8d7da; padding: 15px; border-radius: 8px; border-left: 5px solid #dc3545; margin-bottom: 20px;">
                <h3 style="color: #721c24; margin-top: 0;">📍 Prontuário da Urna: {urna['NM_MUNICIPIO']} (Z: {urna['NR_ZONA']} | S: {urna['NR_SECAO']})</h3>
                <p style="color: #721c24; margin-bottom: 0;"><strong>Atraso Fila:</strong> {urna.get('ATRASO_FILA_MINUTOS', 'N/A')} minutos</p>
            </div>
            """, unsafe_allow_html=True)
            
            # --- GRADE 2x2 DE GRÁFICOS ---
            col_linha1_1, col_linha1_2 = st.columns(2)
            
            # [1,0] Gráfico 1: Ocorrências Operacionais
            with col_linha1_1:
                st.markdown("<h5 style='text-align: center; color: #1a3a5c;'>Ocorrências Operacionais</h5>", unsafe_allow_html=True)
                metricas = ['TIMEOUT_BIOMETRIA', 'INATIVIDADE', 'TECLA_INDEVIDA']
                labels = ['Timeout Biometria', 'Inatividade', 'Tecla Indevida']
                valores = [urna[m] for m in metricas]
                
                textos_barras = []
                for m, v in zip(metricas, valores):
                    if m == 'TIMEOUT_BIOMETRIA':
                        t = urna['TPBSEC']
                        textos_barras.append(f"{int(v)} ocorr.<br>(~{int(t)//60}m{int(t)%60}s)")
                    elif m == 'INATIVIDADE':
                        t = urna['TTPISEC']
                        textos_barras.append(f"{int(v)} ocorr.<br>(~{int(t)//60}m{int(t)%60}s)")
                    else:
                        textos_barras.append(f"{int(v)} ocorr.")

                fig_op = go.Figure(go.Bar(
                    x=labels, y=valores, 
                    marker_color=['#ff7f0e', '#1f77b4', '#d62728'], 
                    text=textos_barras, textposition='outside'
                ))
                fig_op = apply_base_layout(fig_op, height=350)
                fig_op.update_layout(yaxis=dict(title="Quantidade", tickfont=dict(color='black', size=13)), xaxis=dict(tickfont=dict(color='black', size=13)))
                st.plotly_chart(fig_op, use_container_width=True)

            # [0,1] Gráfico 2: Faixa Etária (AGORA COM PORCENTAGEM)
            with col_linha1_2:
                st.markdown("<h5 style='text-align: center; color: #1a3a5c;'>Faixa Etária</h5>", unsafe_allow_html=True)
                cols_idade = [c for c in df_n4.columns if c.startswith('IDADE_') and 'Inválido' not in c]
                valores_idade = urna[cols_idade].values
                labels_idade = [c.replace('IDADE_', '').strip() for c in cols_idade]
                
                # Cálculo da Porcentagem
                total_idade = valores_idade.sum()
                textos_idade = [f"{int(v)} ({(v/total_idade*100):.1f}%)" if total_idade > 0 else "0" for v in valores_idade]
                
                fig_i_n4 = go.Figure(go.Bar(
                    x=valores_idade, y=labels_idade, orientation='h', marker_color='#2ca02c', 
                    text=textos_idade, textposition='outside'
                ))
                fig_i_n4 = apply_base_layout(fig_i_n4, height=350)
                fig_i_n4.update_layout(yaxis=dict(categoryorder='total ascending', tickfont=dict(color='black', size=13)))
                st.plotly_chart(fig_i_n4, use_container_width=True)

            st.write("<br>", unsafe_allow_html=True) 
            col_linha2_1, col_linha2_2 = st.columns(2)

            # [1,0] Gráfico 3: Escolaridade (AGORA COM PORCENTAGEM)
            with col_linha2_1:
                st.markdown("<h5 style='text-align: center; color: #1a3a5c;'>Escolaridade</h5>", unsafe_allow_html=True)
                cols_esc = [c for c in df_n4.columns if c.startswith('ESC_')]
                valores_esc = urna[cols_esc].values
                labels_esc = [c.replace('ESC_', '').title() for c in cols_esc]
                
                # Cálculo da Porcentagem
                total_esc = valores_esc.sum()
                textos_esc = [f"{int(v)} ({(v/total_esc*100):.1f}%)" if total_esc > 0 else "0" for v in valores_esc]
                
                fig_e_n4 = go.Figure(go.Bar(
                    x=valores_esc, y=labels_esc, orientation='h', marker_color='#9467bd', 
                    text=textos_esc, textposition='outside'
                ))
                fig_e_n4 = apply_base_layout(fig_e_n4, height=350)
                fig_e_n4.update_layout(yaxis=dict(categoryorder='total ascending', tickfont=dict(color='black', size=13)))
                st.plotly_chart(fig_e_n4, use_container_width=True)

            # [1,1] Gráfico 4: PCD
            with col_linha2_2:
                st.markdown("<h5 style='text-align: center; color: #1a3a5c;'>Proporção PCD</h5>", unsafe_allow_html=True)
                total_eleitores = valores_idade.sum()
                pcd = urna.get('QTD_PCD', 0)
                nao_pcd = total_eleitores - pcd
                
                fig_pcd_n4 = go.Figure(go.Pie(
                    labels=['PCD', 'Não PCD'], values=[pcd, nao_pcd], hole=0.45, 
                    marker=dict(colors=['#d62728', '#7f7f7f']), 
                    textinfo='percent+value'
                ))
                st.plotly_chart(apply_base_layout(fig_pcd_n4, height=350), use_container_width=True)
else:
    st.error(f"Arquivo não encontrado: {caminho_csv}")
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
