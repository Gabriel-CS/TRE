from __future__ import annotations

import gc

import plotly.express as px
import streamlit as st

from src.analysis import OKABE_ITO, URN_MODELS
from src.charts import (
    apply_base_layout,
    bar_chart,
    bar_chart_horizontal,
    stacked_bar,
)


def render_tab_modelo(analise) -> None:
    """Renderiza o conteúdo completo da aba 'Análise por Modelo de Urna'."""

    _render_distribuicao(analise)
    _render_falhas_biometricas(analise)
    _render_inatividade(analise)
    _render_teclas_indevidas(analise)
    _render_escolaridade(analise)
    _render_faixa_etaria(analise)
    _render_pcd(analise)


# ──────────────────────────────────────────────────────────────────────────────
# Seções individuais
# ──────────────────────────────────────────────────────────────────────────────

def _render_distribuicao(analise) -> None:
    st.markdown("""
        <div class="section-header"><h2>Distribuição de Modelos</h2></div>
        <div class="section-desc">Proporção e quantidade absoluta de seções por modelo de urna.</div>
    """, unsafe_allow_html=True)

    dist = analise.get_model_distribution()
    col1, col2 = st.columns(2)

    with col1:
        fig = bar_chart(
            URN_MODELS, dist["proportions"],
            text=[f"{v*100:.1f}%" for v in dist["proportions"]],
            title="Proporção de Urnas por Modelo", yfmt=".0%", yrange=[0, 1.0],
        )
        st.plotly_chart(fig, use_container_width=True)
        del fig

    with col2:
        fig = bar_chart(
            URN_MODELS, dist["counts"],
            text=[f"{v:,}" for v in dist["counts"]],
            title="Total de Seções por Modelo",
            yrange=[0, max(dist["counts"]) * 1.25 or 1],
        )
        st.plotly_chart(fig, use_container_width=True)
        del fig

    del dist
    gc.collect()


def _render_falhas_biometricas(analise) -> None:
    st.markdown("""
        <div class="section-header"><h2>Falhas Biométricas na Pré-Habilitação</h2></div>
        <div class="section-desc">Proporção de votantes com falha biométrica, entre os que tiveram biometria solicitada.</div>
    """, unsafe_allow_html=True)

    bio = analise.get_bio_failure_rates()
    col_bio1, col_bio2 = st.columns([3, 1])

    with col_bio1:
        fig = bar_chart(
            URN_MODELS, bio["rates"],
            text=[f"{v*100:.1f}%" for v in bio["rates"]],
            title="Falha Biométrica por Modelo", yfmt=".0%", yrange=[0, 1.0],
        )
        st.plotly_chart(fig, use_container_width=True)
        del fig

    with col_bio2:
        st.markdown(
            "<h5 style='text-align: center; color: #1a3a5c; margin-top:0; margin-bottom:8px; "
            "font-size:0.85rem; font-weight:600;'>Resumo por Modelo</h5>",
            unsafe_allow_html=True,
        )
        
        st.markdown(f"""
                <div class='resumo-card'>
                    <div style="display: flex; align-items: center; justify-content: space-between; padding: 0 20px;">
                        <div style="width: 120px;">
                            <span class='resumo-nome'>Modelo</span>
                        </div>
                        <div style="text-align: center; flex: 1;">
                            <div class='resumo-metrica-valor'>Solicitada</div>
                        </div>
                        <div style="text-align: right; width: 100px;">
                            <div class='resumo-metrica-valor'>Falhas</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        for i, m in enumerate(URN_MODELS):
            vm = analise.voters[m]
            bio_m = vm[vm["bio_solicitada"] == True]
            falhas = (bio_m["n_falhas_bio"] > 0).sum()
            cor = OKABE_ITO[i]
            st.markdown(f"""
                <div class='resumo-card'>
                    <div style="display: flex; align-items: center; justify-content: space-between; padding: 0 20px;">
                        <div style="display: flex; align-items: center; gap: 6px; width: 120px;">
                            <span class='resumo-dot' style='background:{cor};'></span>
                            <span class='resumo-nome'>{m}</span>
                        </div>
                        <div style="text-align: center; flex: 1;">
                            <div class='resumo-metrica-valor'>{len(bio_m):,}</div>
                        </div>
                        <div style="text-align: right; width: 130px;">
                            <div class='resumo-metrica-valor'>{falhas:,}</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            del vm, bio_m

    del bio
    gc.collect()


def _render_inatividade(analise) -> None:
    st.markdown("""
        <div class="section-header"><h2>Tempo de Inatividade durante a Seção</h2></div>
        <div class="section-desc">Média e desvio padrão do tempo de inatividade no processo de votação (excluindo zeros).</div>
    """, unsafe_allow_html=True)

    inat = analise.get_inactivity_times()
    fig = bar_chart_horizontal(
        URN_MODELS, inat["means"],
        text=[f"{m:.1f}s (±{s:.1f})" for m, s in zip(inat["means"], inat["stds"])],
        title="Tempo de Inatividade (média ± DP)",
        xrange=[0, max(m + s for m, s in zip(inat["means"], inat["stds"])) * 1.25 or 1],
    )
    st.plotly_chart(fig, use_container_width=True)
    del fig, inat
    gc.collect()


def _render_teclas_indevidas(analise) -> None:
    st.markdown("""
        <div class="section-header"><h2>Proporção de Teclas Indevidas</h2></div>
        <div class="section-desc">Parcela do total de teclas indevidas concentrada por modelo.</div>
    """, unsafe_allow_html=True)

    inv_keys = analise.get_invalid_keys()
    total_kp = analise.df_log["n_teclas_inv"].sum()
    col1, col2 = st.columns([3, 1])

    with col1:
        fig = bar_chart(
            URN_MODELS, inv_keys["proportions"],
            text=[f"{v*100:.1f}%" for v in inv_keys["proportions"]],
            title="Teclas Indevidas por Modelo", yfmt=".0%", yrange=[0, 1.0],
        )
        st.plotly_chart(fig, use_container_width=True)
        del fig

    with col2:
        st.markdown(
            "<h5 style='text-align: center; color: #1a3a5c; margin-top:0; margin-bottom:8px; "
            "font-size:0.85rem; font-weight:600;'>Resumo por Modelo</h5>",
            unsafe_allow_html=True,
        )

        st.markdown(f"""
                <div class='resumo-card'>
                    <div style="display: flex; align-items: center; justify-content: space-between; padding: 0 20px;">
                        <div style="width: 120px;">
                            <span class='resumo-nome'>Modelo</span>
                        </div>
                        <div style="text-align: center; flex: 1;">
                            <div class='resumo-metrica-valor'>Indevidas</div>
                        </div>
                        <div style="text-align: right; width: 100px;">
                            <div class='resumo-metrica-valor'>Total</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        for i, m in enumerate(URN_MODELS):
            vm = analise.voters[m]
            qtd = int(vm[vm["n_teclas_inv"] > 0]["n_teclas_inv"].sum())
            cor = OKABE_ITO[i]

            st.markdown(f"""
                <div class='resumo-card'>
                    <div style="display: flex; align-items: center; justify-content: space-between; padding: 0 20px;">
                        <div style="display: flex; align-items: center; gap: 6px; width: 120px;">
                            <span class='resumo-dot' style='background:{cor};'></span>
                            <span class='resumo-nome'>{m}</span>
                        </div>
                        <div style="text-align: center; flex: 1;">
                            <div class='resumo-metrica-valor'>{qtd:,}</div>
                        </div>
                        <div style="text-align: right; width: 130px;">
                            <div class='resumo-metrica-valor'>{total_kp:,}</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            del vm

    del inv_keys, total_kp
    gc.collect()


def _render_escolaridade(analise) -> None:
    st.markdown("""
        <div class="section-header"><h2>Escolaridade</h2></div>
        <div class="section-desc">Distribuição por grau de escolaridade e proporção de baixa escolaridade.</div>
    """, unsafe_allow_html=True)

    edu = analise.get_education_distribution()
    low_edu = analise.get_low_education()
    col1, col2 = st.columns(2)

    with col1:
        fig = stacked_bar(
            edu["df_proportions"], edu["labels"],
            px.colors.qualitative.Pastel,
            title="Distribuição por Escolaridade",
        )
        st.plotly_chart(fig, use_container_width=True)
        del fig

    with col2:
        fig = bar_chart(
            URN_MODELS, low_edu["proportions"],
            text=[f"{v*100:.1f}%" for v in low_edu["proportions"]],
            title="Baixa Escolaridade por Modelo", yfmt=".0%", yrange=[0, 1.0],
        )
        st.plotly_chart(fig, use_container_width=True)
        del fig

    del edu, low_edu
    gc.collect()


def _render_faixa_etaria(analise) -> None:
    st.markdown("""
        <div class="section-header"><h2>Faixa Etária</h2></div>
        <div class="section-desc">Distribuição etária e proporção de eleitores idosos (≥ 60 anos).</div>
    """, unsafe_allow_html=True)

    age = analise.get_age_distribution()
    elderly = analise.get_elderly_proportion()
    col1, col2 = st.columns(2)

    with col1:
        fig = stacked_bar(
            age["df_proportions"], age["groups"],
            px.colors.qualitative.Safe,
            title="Distribuição por Faixa Etária",
        )
        st.plotly_chart(fig, use_container_width=True)
        del fig

    with col2:
        fig = bar_chart(
            URN_MODELS, elderly["proportions"],
            text=[f"{v*100:.1f}%" for v in elderly["proportions"]],
            title="Eleitores Idosos (≥ 60 anos)", yfmt=".0%", yrange=[0, 1.0],
        )
        st.plotly_chart(fig, use_container_width=True)
        del fig

    del age, elderly
    gc.collect()


def _render_pcd(analise) -> None:
    st.markdown("""
        <div class="section-header"><h2>Eleitores PCD</h2></div>
        <div class="section-desc">Quantidade absoluta, taxa e relação com falhas biométricas.</div>
    """, unsafe_allow_html=True)

    pcd = analise.get_pcd_stats()
    col1, col2 = st.columns(2)

    with col1:
        fig = bar_chart(
            URN_MODELS, pcd["totals"],
            text=[f"{v:,}" for v in pcd["totals"]],
            title="Total de Eleitores PCD",
            yrange=[0, max(pcd["totals"]) * 1.25 or 1],
        )
        st.plotly_chart(fig, use_container_width=True)
        del fig

    with col2:
        fig = bar_chart(
            URN_MODELS, pcd["taxas"],
            text=[f"{v*100:.2f}%" for v in pcd["taxas"]],
            title="Taxa de Eleitores PCD", yfmt=".2%", yrange=[0, 1.0],
        )
        st.plotly_chart(fig, use_container_width=True)
        del fig

    del pcd
    gc.collect()
