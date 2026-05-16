# src/tab_geo.py (versão modificada - Etapa 1)
from __future__ import annotations

import gc
import os

import folium
import geopandas as gpd
import pandas as pd
import requests
import streamlit as st
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

from src.analysis import STATUS_LABELS as _STATUS_LABELS

# Constantes de cor por status (inclui nível 0)
_COR_STATUS: dict[int, str] = {
    0: "#17a2b8",   # Sem Atraso — azul info
    1: "#28a745",   # Normal — verde
    2: "#ffc107",   # Atenção — amarelo
    3: "#dc3545",   # Crítico — vermelho
    4: "#6f1d1b",   # Emergência — bordô
}


# GeoJSON das fronteiras de Sergipe (municípios) — fonte: tbrugz/geodata-br (CC0)
SERGIPE_GEOJSON_URL: str = (
    "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-28-mun.json"
)
SERGIPE_GEOJSON_LOCAL: str = "data/geo/sergipe_municipios.geojson"

# Centro aproximado de Sergipe para o mapa
SERGIPE_CENTER: tuple[float, float] = (-10.5741, -37.3857)
SERGIPE_ZOOM: int = 8
# Caminho base dos arquivos geográficos por ano (novo padrão)
# Formato: data/data_map/locais_criticos_YYYY.csv


@st.cache_data(show_spinner=False, ttl=3600)
def _carregar_geojson_sergipe() -> dict | None:
    """Carrega o GeoJSON das fronteiras de Sergipe (local ou remoto)."""
    # Tenta arquivo local primeiro
    if os.path.exists(SERGIPE_GEOJSON_LOCAL):
        try:
            import json
            with open(SERGIPE_GEOJSON_LOCAL, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Fallback: download do repositório público
    try:
        resp = requests.get(SERGIPE_GEOJSON_URL, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None

@st.cache_data(show_spinner=False, ttl=900)
def carregar_dados_geograficos(ano: str, status_filter: int | None) -> tuple[gpd.GeoDataFrame | None, str | None]:
    """
    Carrega dados geográficos particionados por ano e status.
    Retorna (GeoDataFrame, None) ou (None, mensagem_erro).
    """
    # Define o sufixo do arquivo baseado no filtro
    if status_filter is None or status_filter == "Todas":
        suffix = "all"
    else:
        suffix = f"n{status_filter}"
    
    particionado_path = f"data/geo/{ano}_geo_{suffix}.csv.zip"
    
    # Tenta carregar arquivo particionado primeiro
    if os.path.exists(particionado_path):
        try:
            df = pd.read_csv(particionado_path, compression="zip")
        except Exception as e:
            return None, f"Erro ao ler arquivo particionado: {str(e)}"
    else:
        # Fallback: carrega arquivo completo do ano e filtra
        geo_raw_path = f"data/data_map/locais_criticos_{ano}.csv"
        try:
            df = pd.read_csv(geo_raw_path)
        except FileNotFoundError:
            return None, f"Arquivo não encontrado: `{geo_raw_path}`"
        except Exception as e:
            return None, f"Erro na leitura: {str(e)}"

        # Filtra por status (se necessário)
        if status_filter is None:
            mask = df["STATUS"] > 0
        else:
            mask = df["STATUS"] == status_filter
        df = df[mask].copy()

    
    # Validação das colunas obrigatórias
    cols_obrigatorias = ["NR_LATITUDE", "NR_LONGITUDE", "STATUS", "NM_LOCAL_VOTACAO", "NM_MUNICIPIO"]
    faltantes = [c for c in cols_obrigatorias if c not in df.columns]
    if faltantes:
        return None, f"Colunas ausentes: {', '.join(faltantes)}"
    
    # Conversão e limpeza de coordenadas
    df["NR_LATITUDE"] = pd.to_numeric(df["NR_LATITUDE"], errors="coerce")
    df["NR_LONGITUDE"] = pd.to_numeric(df["NR_LONGITUDE"], errors="coerce")
    df["STATUS"] = pd.to_numeric(df["STATUS"], errors="coerce")
    
    df_valid = df.dropna(subset=["NR_LATITUDE", "NR_LONGITUDE", "STATUS"])
    df_valid = df_valid[
        (df_valid["NR_LATITUDE"] != -1) &
        (df_valid["NR_LONGITUDE"] != -1) &
        (df_valid["NR_LATITUDE"].between(-90, 90)) &
        (df_valid["NR_LONGITUDE"].between(-180, 180))
    ].copy()
    
    if df_valid.empty:
        return None, "Nenhum registro possui coordenadas geográficas válidas."
    
    gdf = gpd.GeoDataFrame(
        df_valid,
        geometry=gpd.points_from_xy(df_valid.NR_LONGITUDE, df_valid.NR_LATITUDE),
        crs="EPSG:4326",
    )
    return gdf, None

def render_tab_geo(ano: str, status_filter: int | None) -> None:
    """Renderiza o conteúdo completo da aba 'Visão Geográfica'."""
    st.markdown(f"""
        <div class="section-header"><h2>Distribuição Geoespacial dos Locais Críticos <span style="color: #adb5bd; font-weight: 400;">· {ano}</span></h2></div>
    """, unsafe_allow_html=True)
    
    # Carrega dados específicos do ano e status
    gdf_geo, erro_geo = carregar_dados_geograficos(ano, status_filter)
    
    if erro_geo:
        st.warning(f"Dados geográficos indisponíveis: {erro_geo}")
        st.info(
            "Para habilitar o mapa, certifique-se de que os arquivos particionados existam "
            "em `data/geo/` ou os arquivos `data/data_map/locais_criticos_2018.csv` e "
            "`data/data_map/locais_criticos_2022.csv` estejam presentes com as colunas "
            "NR_LATITUDE, NR_LONGITUDE, STATUS, NM_LOCAL_VOTACAO e NM_MUNICIPIO."
        )
        return

    # ── Melhoria 3 — Card de seleção de município ────────────────────────────
    # Os municípios exibidos já refletem o nível de criticidade selecionado
    # globalmente (status_filter), pois gdf_geo vem pré-filtrado.
    municipios_disponiveis = sorted(gdf_geo["NM_MUNICIPIO"].dropna().unique())

    col_mun, col_status_sub = st.columns([1, 1])
    with col_mun:
        selected_munis = st.multiselect(
            "🏙️ Municípios",
            municipios_disponiveis,
            default=[],
            placeholder="Selecione um ou mais municípios...",
            key="_geo_muni_main",
            help="Filtra o mapa exibindo apenas os municípios selecionados. Deixe vazio para mostrar todos."
        )
    with col_status_sub:
        status_disponiveis = sorted(gdf_geo["STATUS"].dropna().unique())
        status_display = [f"{int(s)} — {_STATUS_LABELS.get(s, 'Desconhecido')}" for s in status_disponiveis]
        selected_status_display = st.multiselect(
            "Status (sub-filtro)",
            status_display,
            default=status_display,
            key="_geo_status_sub_main"
        )
        selected_status = [int(s.split(" — ")[0]) for s in selected_status_display]

    # Aplica sub-filtros
    mask = pd.Series(True, index=gdf_geo.index)
    if selected_status:
        mask &= gdf_geo["STATUS"].isin(selected_status)
    if selected_munis:
        mask &= gdf_geo["NM_MUNICIPIO"].isin(selected_munis)

    gdf_map = gdf_geo[mask]

    if gdf_map.empty:
        st.info("Nenhum ponto corresponde aos filtros selecionados.")
        return
        
    # Renderiza mapa (mesmo código de antes, mas usando gdf_map)
    
    # Centro sempre em Sergipe (independente dos dados carregados)
    m = folium.Map(
        location=SERGIPE_CENTER,
        zoom_start=SERGIPE_ZOOM,
        tiles="CartoDB positron",
        attr="CartoDB",
    )
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap", attr="OSM").add_to(m)

    # ── Camada de fronteiras de Sergipe ─────────────────────────────────────
    geojson_se = _carregar_geojson_sergipe()
    if geojson_se:
        folium.GeoJson(
            geojson_se,
            name="Fronteiras de Sergipe",
            style_function=lambda feature: {
                "fillColor": "#1a1a2e",
                "color": "#1a1a2e",
                "weight": 2,
                "fillOpacity": 0.08,
                "opacity": 0.6,
            },
            highlight_function=lambda feature: {
                "fillOpacity": 0.15,
                "weight": 3,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["name"],
                aliases=["Município:"],
                style="font-family: Inter, sans-serif; font-size: 0.8rem;",
            ),
        ).add_to(m)

    cluster = MarkerCluster(name="Locais Agrupados", overlay=True, control=False).add_to(m)
    
    for _, row in gdf_map.iterrows():
        status = int(row["STATUS"])
        cor = _COR_STATUS.get(status, "#6c757d")
        label = _STATUS_LABELS.get(status, f"Status {status}")
        
        zona_val = int(row["NR_ZONA"]) if "NR_ZONA" in row.index and pd.notna(row["NR_ZONA"]) else "—"
        secao_val = int(row["NR_SECAO"]) if "NR_SECAO" in row.index and pd.notna(row["NR_SECAO"]) else "—"
        
        # ── Melhoria 4: Informações adicionais no popup ──────────────────────────
        modelo_val = str(row["modelo"]) if "modelo" in row.index and pd.notna(row["modelo"]) else "—"

        atraso_html = ""
        if "ATRASO_FILA_MINUTOS" in row.index and pd.notna(row["ATRASO_FILA_MINUTOS"]):
            atraso_min = float(row["ATRASO_FILA_MINUTOS"])
            atraso_html = f'<div style="font-size: 0.85rem; color: #495057; margin-bottom: 0.3rem;"><b>⏱ Atraso Fila:</b> {atraso_min:.1f} min</div>'

        popup_html = f"""
            <div style="font-family: 'Inter', sans-serif; min-width: 260px;">
                <h4 style="margin: 0 0 0.5rem 0; color: #1a1a2e; font-size: 1rem;">{row['NM_LOCAL_VOTACAO']}</h4>
                <div style="font-size: 0.85rem; color: #495057; margin-bottom: 0.2rem;">
                    <b>Município:</b> {row['NM_MUNICIPIO']}
                </div>
                <div style="display: flex; gap: 1rem; font-size: 0.85rem; color: #495057; margin-bottom: 0.2rem;">
                    <span><b>Zona:</b> {zona_val}</span>
                    <span><b>Seção:</b> {secao_val}</span>
                </div>
                <div style="display: flex; gap: 1rem; font-size: 0.85rem; color: #495057; margin-bottom: 0.2rem;">
                    <span><b>Modelo Urna:</b> {modelo_val}</span>
                </div>
                {atraso_html}
                <div style="margin-top: 0.5rem;">
                    <span style="background: {cor}20; color: {cor}; padding: 0.25rem 0.7rem;
                                 border-radius: 4px; font-size: 0.75rem; font-weight: 600;">
                        {label}
                    </span>
                </div>
            </div>
        """
        
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=6 + (status * 1.5),
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=row["NM_LOCAL_VOTACAO"],
            color=cor,
            fill=True,
            fillColor=cor,
            fillOpacity=0.75,
            weight=2,
        ).add_to(cluster)
    
    folium.LayerControl(collapsed=True).add_to(m)
    
    st.markdown('<div class="folium-map">', unsafe_allow_html=True)
    st_folium(m, width="100%", height=550, returned_objects=[])
    st.markdown("</div>", unsafe_allow_html=True)
    
    del gdf_map, cluster, m
    gc.collect()