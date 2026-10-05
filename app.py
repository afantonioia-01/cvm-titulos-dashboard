"""
================================================================================
TERMINAL DE FUNDOS & TÍTULOS PÚBLICOS CVM - STREAMLIT COMMUNITY CLOUD
================================================================================
Dashboard para Análise de 12 Meses de Carteiras de Fundos de Investimento (CDA)
com Foco em Títulos Públicos Federais (Bloco 1), Operações Definitivas vs.
Compromissadas, Consulta Inversa por Título, Comparador Temporal e Exportação em PDF.
"""

import os
import io
import re
import datetime
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from pdf_export import gerar_relatorio_pdf_fundo, gerar_relatorio_pdf_titulo, gerar_relatorio_pdf_conglomerado

# ------------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="CVM Títulos Públicos & Fundos | Terminal 12M",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS personalizada para replicar o design moderno e profissional de terminais de mercado
st.markdown("""
<style>
    /* Estilização Geral e Fontes */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }
    
    /* Cards de Indicadores Personalizados */
    .metric-card-box {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        margin-bottom: 8px;
    }
    .metric-label-clean {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #64748b;
        font-weight: 600;
    }
    .metric-val-clean {
        font-size: 20px;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        margin-top: 3px;
        color: #0f172a;
    }
    .metric-sub-clean {
        font-size: 11px;
        color: #0284c7;
        margin-top: 2px;
        font-weight: 500;
    }

    /* Mini Tiles para os 12 Meses */
    .tile-month {
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 8px 4px;
        text-align: center;
        transition: all 0.2s;
    }
    .tile-month-active {
        background: #f0f9ff;
        border: 2px solid #0284c7;
        box-shadow: 0 2px 4px rgba(2, 132, 199, 0.15);
    }
    .tile-date {
        font-size: 10px;
        color: #64748b;
        font-weight: 600;
    }
    .tile-val {
        font-size: 12px;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        color: #0f172a;
        margin-top: 2px;
    }

    /* Badges de Status de Rebalanceamento */
    .badge-status {
        display: inline-block;
        padding: 2px 6px;
        font-size: 10px;
        font-weight: 700;
        border-radius: 4px;
    }
    .badge-novo { background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; }
    .badge-liq { background: #ffe4e6; color: #be123c; border: 1px solid #fecdd3; }
    .badge-aum { background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }
    .badge-red { background: #fef3c7; color: #b45309; border: 1px solid #fde68a; }

    /* Barra Superior das Abas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        border-bottom: 1px solid #e2e8f0;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        border-radius: 6px 6px 0 0;
        font-weight: 600;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 2. CARREGAMENTO DOS DADOS COM CACHING OTIMIZADO
# ------------------------------------------------------------------------------
@st.cache_data(show_spinner="Carregando e indexando histórico de 12 meses da CVM...")
def carregar_dados():
    caminho_parquet = "carteira_consolidada.parquet"
    if os.path.exists(caminho_parquet):
        df = pd.read_parquet(caminho_parquet)
    else:
        from etl_cvm import gerar_base_demonstracao
        df = gerar_base_demonstracao()
        
    if "DT_COMPTC" in df.columns:
        df["DT_COMPTC"] = df["DT_COMPTC"].astype(str)
    if "CNPJ_CLEAN" in df.columns:
        df["CNPJ_CLEAN"] = df["CNPJ_CLEAN"].astype(str).str.zfill(14)
        
    return df

df_all = carregar_dados()

# ------------------------------------------------------------------------------
# 3. BARRA LATERAL COM FILTROS DINÂMICOS
# ------------------------------------------------------------------------------
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Brasao_do_Brasil.svg/150px-Brasao_do_Brasil.svg.png", width=65)
st.sidebar.title("Terminal CVM 12M")
st.sidebar.caption("Títulos Públicos Federais & Carteiras")

meses_disponiveis = sorted(df_all["DT_COMPTC"].unique())
mes_default = meses_disponiveis[-1] if len(meses_disponiveis) > 0 else "2026-07"

st.sidebar.markdown("### 🎛️ Filtros Globais")
comp_selecionada = st.sidebar.selectbox("Competência Principal (Mês):", meses_disponiveis, index=len(meses_disponiveis)-1)

filtro_operacao = st.sidebar.radio(
    "Tipo de Operação:",
    ["Todas", "Apenas Definitivas (Risco de Mercado)", "Apenas Compromissadas (Caixa/Colateral)"],
    index=1
)

tipos_titulos_disp = ["Todos"] + sorted(df_all["TP_TITPUB"].dropna().unique().tolist())
filtro_tipo_tit = st.sidebar.selectbox("Tipo de Título Público:", tipos_titulos_disp)

conglomerados_disp = ["Todos"] + sorted(df_all["CONGLOMERADO"].dropna().unique().tolist())
filtro_conglomerado = st.sidebar.selectbox("Conglomerado Financeiro:", conglomerados_disp)

# Aplicação dos Filtros na Base Ativa
df_filtrado = df_all[df_all["DT_COMPTC"] == comp_selecionada].copy()

if filtro_operacao == "Apenas Definitivas (Risco de Mercado)":
    df_filtrado = df_filtrado[df_filtrado["TIPO_OPERACAO"] == "Definitiva"]
elif filtro_operacao == "Apenas Compromissadas (Caixa/Colateral)":
    df_filtrado = df_filtrado[df_filtrado["TIPO_OPERACAO"] == "Compromissada"]

if filtro_tipo_tit != "Todos":
    df_filtrado = df_filtrado[df_filtrado["TP_TITPUB"] == filtro_tipo_tit]

if filtro_conglomerado != "Todos":
    df_filtrado = df_filtrado[df_filtrado["CONGLOMERADO"] == filtro_conglomerado]

# ------------------------------------------------------------------------------
# 4. ABAS PRINCIPAIS DO DASHBOARD
# ------------------------------------------------------------------------------
tab1, tab_cong, tab2, tab3, tab4, tab5 = st.tabs([
    "🏛️ Raio-X por Fundo",
    "🏢 Visão por Conglomerado",
    "🎯 Consulta Inversa (por Título)",
    "⚖️ Comparador Temporal (Mês A vs B)",
    "🏦 Tesourarias & Bancos",
    "📄 Exportação de Relatórios PDF"
])

# ==============================================================================
# ABA 1: RAIO-X DO FUNDO
# ==============================================================================
with tab1:
    st.subheader("Análise Detalhada de Carteira do Fundo")
    
    todos_fundos = df_all[["CNPJ_CLEAN", "Denominacao_Social"]].drop_duplicates().sort_values("Denominacao_Social")
    opcoes_fundo = {f"{r['Denominacao_Social']} ({r['CNPJ_CLEAN']})": r['CNPJ_CLEAN'] for _, r in todos_fundos.iterrows()}
    
    fundo_nome_sel = st.selectbox("Pesquisar ou Selecionar Fundo:", list(opcoes_fundo.keys()), index=0)
    cnpj_sel = opcoes_fundo[fundo_nome_sel]
    
    dados_fundo_mes = df_all[(df_all["CNPJ_CLEAN"] == cnpj_sel) & (df_all["DT_COMPTC"] == comp_selecionada)].copy()
    
    if dados_fundo_mes.empty:
        st.warning(f"O fundo selecionado não reportou posições de títulos na competência {comp_selecionada}.")
    else:
        pl_fundo = dados_fundo_mes["VL_PATRIM_LIQ"].iloc[0]
        tot_titulos = dados_fundo_mes["VL_MERC_POS_FINAL"].sum()
        pct_tit_pl = (tot_titulos / pl_fundo * 100) if pl_fundo > 0 else 0
        
        tot_def = dados_fundo_mes[dados_fundo_mes["TIPO_OPERACAO"] == "Definitiva"]["VL_MERC_POS_FINAL"].sum()
        tot_comp = dados_fundo_mes[dados_fundo_mes["TIPO_OPERACAO"] == "Compromissada"]["VL_MERC_POS_FINAL"].sum()
        
        # Cards de Indicadores
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"""
        <div class="metric-card-box">
            <div class="metric-label-clean">Patrimônio Líquido (PL)</div>
            <div class="metric-val-clean">R$ {pl_fundo:,.2f}</div>
            <div class="metric-sub-clean">Competência {comp_selecionada}</div>
        </div>
        """, unsafe_allow_html=True)

        c2.markdown(f"""
        <div class="metric-card-box">
            <div class="metric-label-clean">Total em Títulos Públicos</div>
            <div class="metric-val-clean" style="color: #0284c7;">R$ {tot_titulos:,.2f}</div>
            <div class="metric-sub-clean">{pct_tit_pl:.2f}% do PL total</div>
        </div>
        """, unsafe_allow_html=True)

        c3.markdown(f"""
        <div class="metric-card-box">
            <div class="metric-label-clean">Compras Definitivas (Risco)</div>
            <div class="metric-val-clean" style="color: #16a34a;">R$ {tot_def:,.2f}</div>
            <div class="metric-sub-clean">{(tot_def/pl_fundo*100) if pl_fundo>0 else 0:.1f}% com risco de taxa</div>
        </div>
        """, unsafe_allow_html=True)

        c4.markdown(f"""
        <div class="metric-card-box">
            <div class="metric-label-clean">Compromissadas (Caixa)</div>
            <div class="metric-val-clean" style="color: #d97706;">R$ {tot_comp:,.2f}</div>
            <div class="metric-sub-clean">{(tot_comp/pl_fundo*100) if pl_fundo>0 else 0:.1f}% com garantia colateral</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("##### Alocação por Tipo de Título")
            por_tipo = dados_fundo_mes.groupby("TP_TITPUB")["VL_MERC_POS_FINAL"].sum().reset_index()
            fig_pie = px.pie(
                por_tipo,
                names="TP_TITPUB",
                values="VL_MERC_POS_FINAL",
                hole=0.45,
                color_discrete_sequence=["#0284c7", "#10b981", "#f59e0b", "#8b5cf6", "#64748b"]
            )
            fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=280)
            st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
            
        with col_g2:
            st.markdown("##### Curva de Vencimentos (Duration)")
            if "ANO_VENC" not in dados_fundo_mes.columns and "DT_VENC" in dados_fundo_mes.columns:
                dados_fundo_mes["ANO_VENC"] = pd.to_datetime(dados_fundo_mes["DT_VENC"], errors="coerce").dt.year.fillna(9999).astype(int).astype(str)
            
            por_venc = dados_fundo_mes.groupby("ANO_VENC")["VL_MERC_POS_FINAL"].sum().reset_index()
            por_venc["VL_MILHOES"] = por_venc["VL_MERC_POS_FINAL"] / 1e6
            fig_bar = px.bar(
                por_venc,
                x="ANO_VENC",
                y="VL_MILHOES",
                labels={"ANO_VENC": "Ano de Vencimento", "VL_MILHOES": "R$ Milhões"},
                color_discrete_sequence=["#0284c7"]
            )
            fig_bar.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=280)
            st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})
            
        st.markdown("##### Posições Detalhadas em Carteira (Ativo por Ativo)")
        cols_tab = ["TP_TITPUB", "CD_SELIC", "CD_ISIN", "DT_VENC", "TIPO_OPERACAO", "QT_POS_FINAL", "VL_MERC_POS_FINAL", "PR_SOBRE_PL"]
        df_tab = dados_fundo_mes[[c for c in cols_tab if c in dados_fundo_mes.columns]].copy()
        
        df_tab_view = df_tab.copy()
        df_tab_view["QT_POS_FINAL"] = df_tab_view["QT_POS_FINAL"].apply(lambda v: f"{v:,.0f}")
        df_tab_view["VL_MERC_POS_FINAL"] = df_tab_view["VL_MERC_POS_FINAL"].apply(lambda v: f"R$ {v:,.2f}")
        df_tab_view["PR_SOBRE_PL"] = df_tab_view["PR_SOBRE_PL"].apply(lambda v: f"{v:.2f}%")
        st.dataframe(df_tab_view, use_container_width=True)

# ==============================================================================
# ABA CONGLOMERADO: VISÃO CONSOLIDADA DE CONGLOMERADO
# ==============================================================================
with tab_cong:
    st.subheader("🏢 Visão Consolidada por Conglomerado Financeiro")
    st.caption("Análise agregada de todos os fundos sob gestão do grupo: AuM consolidado, divisão definitivas vs compromissadas, ranking de fundos e títulos.")
    
    lista_conglom_tab = ["Itaú Unibanco", "Banco do Brasil", "Bradesco", "BTG Pactual", "Santander", "Caixa Econômica", "Safra", "Independentes"]
    conglom_escolhido = st.selectbox("Selecione o Conglomerado Financeiro:", lista_conglom_tab, index=0, key="sel_conglom_tab")
    
    # Filtrar dados do conglomerado na competência ativa
    df_cg_mes = df_all[(df_all["CONGLOMERADO"] == conglom_escolhido) & (df_all["DT_COMPTC"] == comp_selecionada)].copy()
    
    if df_cg_mes.empty:
        st.info(f"Nenhuma posição registrada para o conglomerado {conglom_escolhido} na competência {comp_selecionada}.")
    else:
        # Fundos únicos e AuM consolidado
        fundos_cg = df_cg_mes[["CNPJ_CLEAN", "Denominacao_Social", "VL_PATRIM_LIQ"]].drop_duplicates("CNPJ_CLEAN")
        pl_consolidado = fundos_cg["VL_PATRIM_LIQ"].sum()
        
        tot_titulos_cg = df_cg_mes["VL_MERC_POS_FINAL"].sum()
        tot_def_cg = df_cg_mes[df_cg_mes["TIPO_OPERACAO"] == "Definitiva"]["VL_MERC_POS_FINAL"].sum()
        tot_comp_cg = df_cg_mes[df_cg_mes["TIPO_OPERACAO"] == "Compromissada"]["VL_MERC_POS_FINAL"].sum()
        
        pct_tit_pl_cg = (tot_titulos_cg / pl_consolidado * 100) if pl_consolidado > 0 else 0
        pct_def_cg = (tot_def_cg / pl_consolidado * 100) if pl_consolidado > 0 else 0
        pct_comp_cg = (tot_comp_cg / pl_consolidado * 100) if pl_consolidado > 0 else 0
        
        # 5 Cards de Indicadores
        cg1, cg2, cg3, cg4, cg5 = st.columns(5)
        cg1.markdown(f"""
        <div class="metric-card-box">
            <div class="metric-label-clean">AuM Consolidado (PL)</div>
            <div class="metric-val-clean">R$ {pl_consolidado:,.2f}</div>
            <div class="metric-sub-clean">R$ {pl_consolidado/1e9:.2f} Bi sob gestão</div>
        </div>
        """, unsafe_allow_html=True)
        
        cg2.markdown(f"""
        <div class="metric-card-box">
            <div class="metric-label-clean">Total Títulos Públicos</div>
            <div class="metric-val-clean" style="color: #0284c7;">R$ {tot_titulos_cg:,.2f}</div>
            <div class="metric-sub-clean">{pct_tit_pl_cg:.1f}% do PL consolidado</div>
        </div>
        """, unsafe_allow_html=True)
        
        cg3.markdown(f"""
        <div class="metric-card-box">
            <div class="metric-label-clean" style="color: #16a34a;">Definitivas (Risco)</div>
            <div class="metric-val-clean">R$ {tot_def_cg:,.2f}</div>
            <div class="metric-sub-clean">{pct_def_cg:.1f}% carteira proprietária</div>
        </div>
        """, unsafe_allow_html=True)
        
        cg4.markdown(f"""
        <div class="metric-card-box">
            <div class="metric-label-clean" style="color: #d97706;">Compromissadas (Caixa)</div>
            <div class="metric-val-clean">R$ {tot_comp_cg:,.2f}</div>
            <div class="metric-sub-clean">{pct_comp_cg:.1f}% em colateral/liquidez</div>
        </div>
        """, unsafe_allow_html=True)
        
        cg5.markdown(f"""
        <div class="metric-card-box">
            <div class="metric-label-clean">Grade de Fundos</div>
            <div class="metric-val-clean">{len(fundos_cg)} fundos</div>
            <div class="metric-sub-clean">{len(df_cg_mes):,} posições ativas</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Benchmark Oficial ANBIMA (Ago/2026) e Reconciliação
        anbima_bench = {
            "Banco do Brasil": {"tot": 1969.2, "rf": 1387.4, "prev": 467.2, "obs": "95% do patrimônio do BB é Renda Fixa e Previdência conservadora alocado no Bloco 1 (LFT/NTN-B), gerando aderência quase 1:1 com a ANBIMA."},
            "Itaú Unibanco": {"tot": 1381.7, "rf": 759.7, "prev": 302.9, "obs": "Na ANBIMA, R$ 1,06 Trilhão são Renda Fixa e Previdência (exatamente o volume do Bloco 1). Os demais ~R$ 330 Bi a 480 Bi são Ações, Multimercados em Bolsa, FIP e FIDC que não compram títulos públicos no SELIC."},
            "Bradesco": {"tot": 1044.6, "rf": 537.2, "prev": 357.1, "obs": "Na ANBIMA, R$ 894 Bi estão em Renda Fixa e Previdência (cobertos no Bloco 1). O restante está em FIDC, Ações e Multimercados em Bolsa."},
            "BTG Pactual": {"tot": 743.4, "rf": 214.4, "prev": 40.1, "obs": "No BTG, R$ 254 Bi são Renda Fixa e Previdência. Mais de R$ 480 Bi são FIP (R$ 104 Bi), FIDC (R$ 86 Bi), Ações (R$ 84 Bi) e Multimercados em bolsa."},
            "Caixa Econômica": {"tot": 638.5, "rf": 401.7, "prev": 213.3, "obs": "96% da Caixa é Renda Fixa (R$ 401 Bi) e Previdência (R$ 213 Bi). Com a classificação unificada da Caixa Asset, o volume é capturado em sua totalidade."},
            "Santander": {"tot": 432.4, "rf": 268.8, "prev": 119.8, "obs": "R$ 388 Bi do Santander estão em Renda Fixa e Previdência, com alta cobertura no Bloco 1."},
            "Safra": {"tot": 206.3, "rf": 128.9, "prev": 28.2, "obs": "R$ 157 Bi do Safra estão em Renda Fixa e Previdência."}
        }
        
        if conglom_escolhido in anbima_bench:
            b_info = anbima_bench[conglom_escolhido]
            st.markdown(f"""
            <div style="background: #0f172a; color: #f8fafc; border-radius: 8px; padding: 14px 16px; margin-top: 10px; margin-bottom: 12px; border: 1px solid #1e293b;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                    <div>
                        <span style="background: rgba(2, 132, 199, 0.2); color: #38bdf8; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase;">Reconciliação Oficial ANBIMA</span>
                        <div style="font-size: 13px; font-weight: 700; color: #ffffff; margin-top: 4px;">Ranking de Gestores ANBIMA vs. CDA Bloco 1 CVM (Títulos Públicos)</div>
                    </div>
                    <div style="display: flex; gap: 16px; font-family: 'JetBrains Mono', monospace; font-size: 12px;">
                        <div>
                            <span style="color: #94a3b8; font-size: 10px; display: block;">AuM Total ANBIMA:</span>
                            <strong style="color: #38bdf8;">R$ {b_info['tot']:.1f} Bi</strong>
                        </div>
                        <div>
                            <span style="color: #94a3b8; font-size: 10px; display: block;">Renda Fixa + Prev ANBIMA:</span>
                            <strong style="color: #4ade80;">R$ {(b_info['rf'] + b_info['prev']):.1f} Bi</strong>
                        </div>
                    </div>
                </div>
                <div style="margin-top: 8px; font-size: 11px; color: #cbd5e1; line-height: 1.4; border-top: 1px solid #1e293b; padding-top: 6px;">
                    💡 <strong>Fundamento Metodológico:</strong> {b_info['obs']}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        # Gráficos da Visão Consolidada
        col_cgg1, col_cgg2 = st.columns(2)
        with col_cgg1:
            st.markdown("##### 🥧 Alocação Consolidada por Tipo de Título")
            por_tipo_cg = df_cg_mes.groupby("TP_TITPUB")["VL_MERC_POS_FINAL"].sum().reset_index()
            fig_pie_cg = px.pie(
                por_tipo_cg,
                names="TP_TITPUB",
                values="VL_MERC_POS_FINAL",
                hole=0.45,
                color_discrete_sequence=["#0284c7", "#10b981", "#f59e0b", "#8b5cf6", "#64748b"]
            )
            fig_pie_cg.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=280)
            st.plotly_chart(fig_pie_cg, use_container_width=True, config={'displayModeBar': False})
            
        with col_cgg2:
            st.markdown("##### 📊 Curva de Vencimentos Consolidada (Duration)")
            if "ANO_VENC" not in df_cg_mes.columns and "DT_VENC" in df_cg_mes.columns:
                df_cg_mes["ANO_VENC"] = pd.to_datetime(df_cg_mes["DT_VENC"], errors="coerce").dt.year.fillna(9999).astype(int).astype(str)
            
            por_venc_cg = df_cg_mes.groupby("ANO_VENC")["VL_MERC_POS_FINAL"].sum().reset_index()
            por_venc_cg["VL_BILHOES"] = por_venc_cg["VL_MERC_POS_FINAL"] / 1e9
            fig_bar_cg = px.bar(
                por_venc_cg,
                x="ANO_VENC",
                y="VL_BILHOES",
                labels={"ANO_VENC": "Ano de Vencimento", "VL_BILHOES": "R$ Bilhões"},
                color_discrete_sequence=["#4f46e5"]
            )
            fig_bar_cg.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=280)
            st.plotly_chart(fig_bar_cg, use_container_width=True, config={'displayModeBar': False})
            
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        # Tabela 1: Ranking dos Fundos do Conglomerado
        st.markdown(f"##### 🏛️ Grade de Fundos do {conglom_escolhido} ({len(fundos_cg)} fundos)")
        st.caption("Abertura individual do Patrimônio Líquido, Total de Títulos Públicos, Definitivas e Compromissadas")
        
        filtro_txt_cg = st.text_input("Filtrar fundos por nome ou CNPJ:", "", key="busca_fundo_cg")
        
        resumo_fundos = []
        for _, f_row in fundos_cg.iterrows():
            c_cnpj = str(f_row["CNPJ_CLEAN"])
            c_nome = f_row["Denominacao_Social"]
            c_pl = f_row["VL_PATRIM_LIQ"]
            
            f_pos = df_cg_mes[df_cg_mes["CNPJ_CLEAN"] == c_cnpj]
            f_tit = f_pos["VL_MERC_POS_FINAL"].sum()
            f_def = f_pos[f_pos["TIPO_OPERACAO"] == "Definitiva"]["VL_MERC_POS_FINAL"].sum()
            f_comp = f_pos[f_pos["TIPO_OPERACAO"] == "Compromissada"]["VL_MERC_POS_FINAL"].sum()
            f_pct = (f_tit / c_pl * 100) if c_pl > 0 else 0
            
            cnpj_fmt = f"{c_cnpj[:2]}.{c_cnpj[2:5]}.{c_cnpj[5:8]}/{c_cnpj[8:12]}-{c_cnpj[12:]}" if len(c_cnpj)==14 else c_cnpj
            resumo_fundos.append({
                "Denominacao_Social": c_nome,
                "CNPJ": cnpj_fmt,
                "VL_PATRIM_LIQ": c_pl,
                "TOTAL_TITULOS": f_tit,
                "DEFINITIVAS": f_def,
                "COMPROMISSADAS": f_comp,
                "PCT_PL": f_pct
            })
            
        df_rf = pd.DataFrame(resumo_fundos).sort_values("VL_PATRIM_LIQ", ascending=False)
        
        if filtro_txt_cg:
            df_rf = df_rf[df_rf["Denominacao_Social"].str.contains(filtro_txt_cg, case=False, na=False) | df_rf["CNPJ"].str.contains(filtro_txt_cg, case=False, na=False)]
            
        df_rf_view = df_rf.copy()
        df_rf_view["VL_PATRIM_LIQ"] = df_rf_view["VL_PATRIM_LIQ"].apply(lambda v: f"R$ {v:,.2f}")
        df_rf_view["TOTAL_TITULOS"] = df_rf_view["TOTAL_TITULOS"].apply(lambda v: f"R$ {v:,.2f}")
        df_rf_view["DEFINITIVAS"] = df_rf_view["DEFINITIVAS"].apply(lambda v: f"R$ {v:,.2f}")
        df_rf_view["COMPROMISSADAS"] = df_rf_view["COMPROMISSADAS"].apply(lambda v: f"R$ {v:,.2f}")
        df_rf_view["PCT_PL"] = df_rf_view["PCT_PL"].apply(lambda v: f"{v:.2f}%")
        
        df_rf_view.rename(columns={
            "Denominacao_Social": "Fundo de Investimento",
            "VL_PATRIM_LIQ": "Patrimônio Líquido",
            "TOTAL_TITULOS": "Total Títulos",
            "DEFINITIVAS": "Definitivas (Risco)",
            "COMPROMISSADAS": "Compromissadas (Caixa)",
            "PCT_PL": "% no PL"
        }, inplace=True)
        st.dataframe(df_rf_view, use_container_width=True)
        
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        
        # Tabela 2: Principais Títulos Públicos Detidos pelo Conglomerado
        st.markdown(f"##### 🎯 Principais Títulos Públicos Custodiados pelo {conglom_escolhido}")
        st.caption("Consolidação dos papéis mais representativos no portfólio de todos os fundos do conglomerado")
        
        titulos_cg = df_cg_mes.groupby(["TP_TITPUB", "CD_SELIC", "CD_ISIN", "DT_VENC"]).agg(
            QT_TOTAL=("QT_POS_FINAL", "sum"),
            VL_TOTAL=("VL_MERC_POS_FINAL", "sum"),
            QTD_FUNDOS=("CNPJ_CLEAN", "nunique")
        ).reset_index().sort_values("VL_TOTAL", ascending=False)
        
        titulos_cg_view = titulos_cg.copy()
        titulos_cg_view["QT_TOTAL"] = titulos_cg_view["QT_TOTAL"].apply(lambda v: f"{v:,.0f}")
        titulos_cg_view["VL_TOTAL"] = titulos_cg_view["VL_TOTAL"].apply(lambda v: f"R$ {v:,.2f}")
        titulos_cg_view.rename(columns={
            "TP_TITPUB": "Tipo",
            "CD_SELIC": "Código SELIC",
            "CD_ISIN": "ISIN",
            "DT_VENC": "Vencimento",
            "QT_TOTAL": "Quantidade Total",
            "VL_TOTAL": "Volume Consolidado (R$)",
            "QTD_FUNDOS": "Qtd de Fundos Detentores"
        }, inplace=True)
        st.dataframe(titulos_cg_view, use_container_width=True)

# ==============================================================================
# ABA 2: CONSULTA INVERSA (POR TÍTULO PÚBLICO)
# ==============================================================================
with tab2:
    st.subheader("Auditoria de Detentores por Título Público")
    
    papeis_disp = sorted(df_all["ID_PAPEL"].dropna().unique().tolist())
    papel_sel = st.selectbox("Selecione o Papel para Auditar:", papeis_disp)
    
    somente_def = st.checkbox("Excluir operações compromissadas (Apenas compras definitivas / carteira real)", value=True)
    
    dados_papel = df_all[(df_all["ID_PAPEL"] == papel_sel) & (df_all["DT_COMPTC"] == comp_selecionada)].copy()
    if somente_def:
        dados_papel = dados_papel[dados_papel["TIPO_OPERACAO"] == "Definitiva"]
        
    if dados_papel.empty:
        st.info("Nenhuma posição localizada para este papel com os filtros atuais.")
    else:
        tot_qtd = dados_papel["QT_POS_FINAL"].sum()
        tot_fin = dados_papel["VL_MERC_POS_FINAL"].sum()
        tot_fundos = dados_papel["CNPJ_CLEAN"].nunique()
        
        k1, k2, k3 = st.columns(3)
        k1.markdown(f"""
        <div class="metric-card-box">
            <div class="metric-label-clean">Volume Total Custodiado</div>
            <div class="metric-val-clean">R$ {tot_fin:,.2f}</div>
            <div class="metric-sub-clean">R$ {tot_fin/1e9:.2f} Bilhões na indústria</div>
        </div>
        """, unsafe_allow_html=True)

        k2.markdown(f"""
        <div class="metric-card-box">
            <div class="metric-label-clean">Quantidade de Títulos</div>
            <div class="metric-val-clean" style="color: #0284c7;">{tot_qtd:,.0f}</div>
            <div class="metric-sub-clean">Unidades físicas no SELIC</div>
        </div>
        """, unsafe_allow_html=True)

        k3.markdown(f"""
        <div class="metric-card-box">
            <div class="metric-label-clean">Fundos Detentores</div>
            <div class="metric-val-clean" style="color: #10b981;">{tot_fundos:,} fundos</div>
            <div class="metric-sub-clean">Com posições ativas registradas</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        # Gráfico Top 10 Detentores
        top10 = dados_papel.sort_values("VL_MERC_POS_FINAL", ascending=False).head(10).copy()
        top10["NOME_CURTO"] = top10["Denominacao_Social"].astype(str).str.slice(0, 35) + "..."
        
        fig_top = px.bar(
            top10,
            x="VL_MERC_POS_FINAL",
            y="NOME_CURTO",
            orientation="h",
            labels={"VL_MERC_POS_FINAL": "Valor Alocado (R$)", "NOME_CURTO": "Fundo"},
            title="Top 10 Maiores Detentores do Papel na Indústria",
            color_discrete_sequence=["#0f766e"]
        )
        fig_top.update_layout(yaxis=dict(autorange="reversed"), height=360, margin=dict(t=30, b=10, l=10, r=10))
        st.plotly_chart(fig_top, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown("##### Ranking Completo de Detentores")
        cols_det = ["Denominacao_Social", "CNPJ_CLEAN", "QT_POS_FINAL", "VL_MERC_POS_FINAL", "PR_SOBRE_PL", "VL_PATRIM_LIQ"]
        df_det = dados_papel[[c for c in cols_det if c in dados_papel.columns]].sort_values("VL_MERC_POS_FINAL", ascending=False)
        
        df_det_fmt = df_det.copy()
        df_det_fmt["QT_POS_FINAL"] = df_det_fmt["QT_POS_FINAL"].apply(lambda v: f"{v:,.0f}")
        df_det_fmt["VL_MERC_POS_FINAL"] = df_det_fmt["VL_MERC_POS_FINAL"].apply(lambda v: f"R$ {v:,.2f}")
        df_det_fmt["PR_SOBRE_PL"] = df_det_fmt["PR_SOBRE_PL"].apply(lambda v: f"{v:.2f}%")
        df_det_fmt["VL_PATRIM_LIQ"] = df_det_fmt["VL_PATRIM_LIQ"].apply(lambda v: f"R$ {v:,.2f}")
        st.dataframe(df_det_fmt, use_container_width=True)

# ==============================================================================
# ABA 3: COMPARADOR TEMPORAL (MÊS A vs MÊS B & VISÃO INVERSA POR TÍTULO)
# ==============================================================================
with tab3:
    st.subheader("Comparador Histórico de Rebalanceamento & Fluxo")
    
    modo_comp = st.radio(
        "Modo de Análise:",
        ["🏛️ Rebalanceamento por Fundo", "🎯 Fluxo Institucional por Título (Visão Inversa & Estratégia 12M)"],
        horizontal=True
    )
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        mes_a = st.selectbox("Mês Base (A):", meses_disponiveis, index=max(0, len(meses_disponiveis)-2), key="c_mes_a")
    with col_m2:
        mes_b = st.selectbox("Mês de Comparação (B):", meses_disponiveis, index=len(meses_disponiveis)-1, key="c_mes_b")
        
    if mes_a == mes_b:
        st.warning("Selecione dois meses distintos para verificar as movimentações.")
    else:
        # -------------------------------------------------------------
        # MODO 1: REBALANCEAMENTO POR FUNDO
        # -------------------------------------------------------------
        if modo_comp == "🏛️ Rebalanceamento por Fundo":
            fundo_comp_sel = st.selectbox("Fundo para Comparação:", list(opcoes_fundo.keys()), key="comp_fundo")
            cnpj_comp = opcoes_fundo[fundo_comp_sel]
            
            df_a = df_all[(df_all["CNPJ_CLEAN"] == cnpj_comp) & (df_all["DT_COMPTC"] == mes_a) & (df_all["TIPO_OPERACAO"] == "Definitiva")]
            df_b = df_all[(df_all["CNPJ_CLEAN"] == cnpj_comp) & (df_all["DT_COMPTC"] == mes_b) & (df_all["TIPO_OPERACAO"] == "Definitiva")]
            
            grp_a = df_a.groupby("ID_PAPEL").agg(QT_A=("QT_POS_FINAL", "sum"), VL_A=("VL_MERC_POS_FINAL", "sum"), PR_A=("PR_SOBRE_PL", "sum")).reset_index()
            grp_b = df_b.groupby("ID_PAPEL").agg(QT_B=("QT_POS_FINAL", "sum"), VL_B=("VL_MERC_POS_FINAL", "sum"), PR_B=("PR_SOBRE_PL", "sum")).reset_index()
            
            diff = pd.merge(grp_a, grp_b, on="ID_PAPEL", how="outer").fillna(0.0)
            diff["DELTA_QT"] = diff["QT_B"] - diff["QT_A"]
            diff["DELTA_VL"] = diff["VL_B"] - diff["VL_A"]
            diff["DELTA_PR"] = diff["PR_B"] - diff["PR_A"]
            
            def classificar_mov(r):
                if r["QT_A"] == 0 and r["QT_B"] > 0: return "NOVO APORTE"
                if r["QT_A"] > 0 and r["QT_B"] == 0: return "LIQUIDADO"
                if r["DELTA_QT"] > 0: return "AUMENTOU"
                if r["DELTA_QT"] < 0: return "REDUZIU"
                return "INALTERADO"
                
            diff["STATUS"] = diff.apply(classificar_mov, axis=1)
            
            s_novos = (diff["STATUS"] == "NOVO APORTE").sum()
            s_liq = (diff["STATUS"] == "LIQUIDADO").sum()
            s_aum = (diff["STATUS"] == "AUMENTOU").sum()
            s_red = (diff["STATUS"] == "REDUZIU").sum()
            
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f"""
            <div class="metric-card-box">
                <div class="metric-label-clean" style="color: #16a34a;">Novos Aportes</div>
                <div class="metric-val-clean">{s_novos} papéis</div>
                <div class="metric-sub-clean">Entradas inéditas na carteira</div>
            </div>
            """, unsafe_allow_html=True)

            m2.markdown(f"""
            <div class="metric-card-box">
                <div class="metric-label-clean" style="color: #dc2626;">Liquidações Totais</div>
                <div class="metric-val-clean">{s_liq} papéis</div>
                <div class="metric-sub-clean">Posições zeradas ou vencidas</div>
            </div>
            """, unsafe_allow_html=True)

            m3.markdown(f"""
            <div class="metric-card-box">
                <div class="metric-label-clean" style="color: #0284c7;">Aumentos de Posição</div>
                <div class="metric-val-clean">{s_aum} papéis</div>
                <div class="metric-sub-clean">Aporte físico adicional (+Qtd)</div>
            </div>
            """, unsafe_allow_html=True)

            m4.markdown(f"""
            <div class="metric-card-box">
                <div class="metric-label-clean" style="color: #d97706;">Reduções de Posição</div>
                <div class="metric-val-clean">{s_red} papéis</div>
                <div class="metric-sub-clean">Venda física parcial (-Qtd)</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            st.markdown("##### Auditoria de Variação de Ativos em Carteira")
            
            diff_fmt = diff.sort_values("DELTA_VL", ascending=False).copy()
            diff_fmt["QT_A"] = diff_fmt["QT_A"].apply(lambda v: f"{v:,.0f}")
            diff_fmt["QT_B"] = diff_fmt["QT_B"].apply(lambda v: f"{v:,.0f}")
            diff_fmt["DELTA_QT"] = diff_fmt["DELTA_QT"].apply(lambda v: f"{'+' if v>0 else ''}{v:,.0f}")
            diff_fmt["VL_A"] = diff_fmt["VL_A"].apply(lambda v: f"R$ {v:,.2f}")
            diff_fmt["VL_B"] = diff_fmt["VL_B"].apply(lambda v: f"R$ {v:,.2f}")
            diff_fmt["DELTA_VL"] = diff_fmt["DELTA_VL"].apply(lambda v: f"{'+' if v>0 else ''}R$ {v:,.2f}")
            diff_fmt["PR_A"] = diff_fmt["PR_A"].apply(lambda v: f"{v:.2f}%")
            diff_fmt["PR_B"] = diff_fmt["PR_B"].apply(lambda v: f"{v:.2f}%")
            diff_fmt["DELTA_PR"] = diff_fmt["DELTA_PR"].apply(lambda v: f"{'+' if v>0 else ''}{v:.2f}%")
            st.dataframe(diff_fmt, use_container_width=True)

        # -------------------------------------------------------------
        # MODO 2: VISÃO INVERSA POR TÍTULO (QUEM COMPROU / QUEM VENDEU & 12M TREND)
        # -------------------------------------------------------------
        else:
            p_comp_sel = st.selectbox("Selecione o Título Público para Rastrear Fluxo:", papeis_disp, key="comp_papel_sel")
            
            df_tit_a = df_all[(df_all["ID_PAPEL"] == p_comp_sel) & (df_all["DT_COMPTC"] == mes_a) & (df_all["TIPO_OPERACAO"] == "Definitiva")]
            df_tit_b = df_all[(df_all["ID_PAPEL"] == p_comp_sel) & (df_all["DT_COMPTC"] == mes_b) & (df_all["TIPO_OPERACAO"] == "Definitiva")]
            
            grp_ta = df_tit_a.groupby(["CNPJ_CLEAN", "Denominacao_Social", "CONGLOMERADO"]).agg(QT_A=("QT_POS_FINAL", "sum"), VL_A=("VL_MERC_POS_FINAL", "sum"), PR_A=("PR_SOBRE_PL", "sum")).reset_index()
            grp_tb = df_tit_b.groupby(["CNPJ_CLEAN", "Denominacao_Social", "CONGLOMERADO"]).agg(QT_B=("QT_POS_FINAL", "sum"), VL_B=("VL_MERC_POS_FINAL", "sum"), PR_B=("PR_SOBRE_PL", "sum")).reset_index()
            
            diff_tit = pd.merge(grp_ta, grp_tb, on=["CNPJ_CLEAN", "Denominacao_Social", "CONGLOMERADO"], how="outer").fillna(0.0)
            diff_tit["DELTA_QT"] = diff_tit["QT_B"] - diff_tit["QT_A"]
            diff_tit["DELTA_VL"] = diff_tit["VL_B"] - diff_tit["VL_A"]
            diff_tit["DELTA_PR"] = diff_tit["PR_B"] - diff_tit["PR_A"]
            
            def class_flow(r):
                if r["QT_A"] == 0 and r["QT_B"] > 0: return "NOVO ENTRANTE"
                if r["QT_A"] > 0 and r["QT_B"] == 0: return "ZEROU POSIÇÃO"
                if r["DELTA_QT"] > 0: return "COMPRADOR LÍQUIDO"
                if r["DELTA_QT"] < 0: return "VENDEDOR LÍQUIDO"
                return "INALTERADO"
                
            diff_tit["CLASSIFICACAO"] = diff_tit.apply(class_flow, axis=1)
            
            tot_qa = diff_tit["QT_A"].sum()
            tot_qb = diff_tit["QT_B"].sum()
            delta_q_ind = tot_qb - tot_qa
            
            tot_va = diff_tit["VL_A"].sum()
            tot_vb = diff_tit["VL_B"].sum()
            delta_v_ind = tot_vb - tot_va
            
            fds_a = (diff_tit["QT_A"] > 0).sum()
            fds_b = (diff_tit["QT_B"] > 0).sum()
            
            # Cards Macro do Título
            k1, k2, k3 = st.columns(3)
            k1.markdown(f"""
            <div class="metric-card-box">
                <div class="metric-label-clean">Variação Física na Indústria</div>
                <div class="metric-val-clean" style="color: {'#16a34a' if delta_q_ind>=0 else '#dc2626'};">
                    {'+' if delta_q_ind>=0 else ''}{delta_q_ind:,.0f} títulos
                </div>
                <div class="metric-sub-clean">De {tot_qa:,.0f} para {tot_qb:,.0f} unidades</div>
            </div>
            """, unsafe_allow_html=True)

            k2.markdown(f"""
            <div class="metric-card-box">
                <div class="metric-label-clean">Variação Financeira Líquida</div>
                <div class="metric-val-clean" style="color: {'#16a34a' if delta_v_ind>=0 else '#dc2626'};">
                    {'+' if delta_v_ind>=0 else ''}R$ {delta_v_ind:,.2f}
                </div>
                <div class="metric-sub-clean">Saldo: {delta_v_ind/1e9:+.2f} R$ Bi</div>
            </div>
            """, unsafe_allow_html=True)

            k3.markdown(f"""
            <div class="metric-card-box">
                <div class="metric-label-clean">Saldo de Fundos Posicionados</div>
                <div class="metric-val-clean">
                    {fds_b - fds_a:+d} fundos
                </div>
                <div class="metric-sub-clean">De {fds_a} para {fds_b} fundos detentores</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            
            # Evolução Histórica 12 Meses do Papel (Mudança de Estratégia)
            st.markdown("##### 📈 Evolução Histórica da Posição da Indústria no Papel (12 Meses)")
            st.caption("Permite verificar se a indústria está aumentando exposição ao papel (acumulação) ou reduzindo duration.")
            
            hist_papel = df_all[(df_all["ID_PAPEL"] == p_comp_sel) & (df_all["TIPO_OPERACAO"] == "Definitiva")].groupby("DT_COMPTC").agg(
                VOL_BI=("VL_MERC_POS_FINAL", lambda v: v.sum() / 1e9),
                QTD_TOTAL=("QT_POS_FINAL", "sum"),
                FUNDOS=("CNPJ_CLEAN", "nunique")
            ).reset_index()
            
            fig_hist = px.bar(
                hist_papel,
                x="DT_COMPTC",
                y="VOL_BI",
                title="Volume Alocado no Papel ao Longo dos 12 Meses (R$ Bilhões)",
                labels={"DT_COMPTC": "Competência", "VOL_BI": "Volume (R$ Bi)"},
                color_discrete_sequence=["#0284c7"]
            )
            fig_hist.update_layout(height=260, margin=dict(t=30, b=10, l=10, r=10))
            st.plotly_chart(fig_hist, use_container_width=True, config={'displayModeBar': False})
            
            # Compradores vs Vendedores
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                st.markdown("##### 🟢 Top 5 Maiores Compradores Líquidos (+Qtd)")
                top_comp = diff_tit[diff_tit["DELTA_QT"] > 0].sort_values("DELTA_QT", ascending=False).head(5).copy()
                if top_comp.empty:
                    st.info("Nenhum comprador líquido identificado.")
                else:
                    top_comp["NOME_C"] = top_comp["Denominacao_Social"].str.slice(0, 32) + "..."
                    fig_c = px.bar(
                        top_comp,
                        x="DELTA_QT",
                        y="NOME_C",
                        orientation="h",
                        labels={"DELTA_QT": "Títulos Comprados (+)", "NOME_C": "Fundo"},
                        color_discrete_sequence=["#16a34a"]
                    )
                    fig_c.update_layout(yaxis=dict(autorange="reversed"), height=250, margin=dict(t=10, b=10, l=10, r=10))
                    st.plotly_chart(fig_c, use_container_width=True, config={'displayModeBar': False})
                    
            with col_b2:
                st.markdown("##### 🔴 Top 5 Maiores Vendedores Líquidos (-Qtd)")
                top_vend = diff_tit[diff_tit["DELTA_QT"] < 0].sort_values("DELTA_QT", ascending=True).head(5).copy()
                if top_vend.empty:
                    st.info("Nenhum vendedor líquido identificado.")
                else:
                    top_vend["NOME_V"] = top_vend["Denominacao_Social"].str.slice(0, 32) + "..."
                    top_vend["DELTA_ABS"] = top_vend["DELTA_QT"].abs()
                    fig_v = px.bar(
                        top_vend,
                        x="DELTA_ABS",
                        y="NOME_V",
                        orientation="h",
                        labels={"DELTA_ABS": "Títulos Vendidos (-)", "NOME_V": "Fundo"},
                        color_discrete_sequence=["#dc2626"]
                    )
                    fig_v.update_layout(yaxis=dict(autorange="reversed"), height=250, margin=dict(t=10, b=10, l=10, r=10))
                    st.plotly_chart(fig_v, use_container_width=True, config={'displayModeBar': False})
                    
            st.markdown("##### Detalhamento Completo de Movimentação por Fundo no Papel")
            diff_tit_fmt = diff_tit.sort_values("DELTA_QT", ascending=False).copy()
            diff_tit_fmt["QT_A"] = diff_tit_fmt["QT_A"].apply(lambda v: f"{v:,.0f}")
            diff_tit_fmt["QT_B"] = diff_tit_fmt["QT_B"].apply(lambda v: f"{v:,.0f}")
            diff_tit_fmt["DELTA_QT"] = diff_tit_fmt["DELTA_QT"].apply(lambda v: f"{'+' if v>0 else ''}{v:,.0f}")
            diff_tit_fmt["DELTA_VL"] = diff_tit_fmt["DELTA_VL"].apply(lambda v: f"{'+' if v>0 else ''}R$ {v:,.2f}")
            diff_tit_fmt["PR_A"] = diff_tit_fmt["PR_A"].apply(lambda v: f"{v:.2f}%")
            diff_tit_fmt["PR_B"] = diff_tit_fmt["PR_B"].apply(lambda v: f"{v:.2f}%")
            diff_tit_fmt["DELTA_PR"] = diff_tit_fmt["DELTA_PR"].apply(lambda v: f"{'+' if v>0 else ''}{v:.2f}%")
            st.dataframe(diff_tit_fmt, use_container_width=True)

# ==============================================================================
# ABA 4: TESOURARIAS & BANCOS (VISÃO HÍBRIDA: EVOLUÇÃO, CARDS & COLATERAL)
# ==============================================================================
with tab4:
    st.subheader("Engenharia Reversa: Tesourarias & Lastro de Compromissadas")
    st.caption("Mapeamento de papéis utilizados pelas mesas bancárias como garantia em operações de caixa de seus fundos.")
    
    bancos_lista = ["Banco do Brasil", "Itaú Unibanco", "Bradesco", "Santander", "Caixa Econômica", "BTG Pactual", "Safra"]
    banco_sel = st.selectbox("Selecione o Conglomerado Bancário:", bancos_lista)
    
    df_banco = df_all[(df_all["CONGLOMERADO"] == banco_sel) & (df_all["TIPO_OPERACAO"] == "Compromissada")].copy()
    
    if df_banco.empty:
        st.info("Nenhuma operação compromissada identificada para este conglomerado nos 12 meses.")
    else:
        dados_banco_mes = df_banco[df_banco["DT_COMPTC"] == comp_selecionada].copy()
        total_lastro_mes = dados_banco_mes["VL_MERC_POS_FINAL"].sum()
        
        # Header Box Institucional
        st.markdown(f"""
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 700;">Conglomerado Bancário / Mesa de Tesouraria</div>
                    <div style="font-size: 18px; font-weight: 700; color: #0f172a; margin-top: 2px;">{banco_sel}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 11px; color: #64748b;">Volume Lastreado em {comp_selecionada}</div>
                    <div style="font-size: 22px; font-weight: 700; font-family: 'JetBrains Mono'; color: #0f172a;">R$ {total_lastro_mes:,.2f}</div>
                    <div style="font-size: 11px; color: #0284c7; font-weight: 600;">R$ {total_lastro_mes/1e9:.2f} Bilhões de caixa colateralizado</div>
                </div>
            </div>
            <div style="margin-top: 10px; padding-top: 8px; border-top: 1px solid #f1f5f9; font-size: 11px; color: #64748b;">
                🛡️ <strong>Fundamento Institucional:</strong> Em operações compromissadas, os fundos emprestam caixa para as tesourarias bancárias remunerados a CDI/Selic diário, recebendo títulos públicos federais como garantia colateral vinculada no Selic/Cetip.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Evolução Histórica (Tiles dos 12 Meses)
        st.markdown(f"##### Evolução Histórica do Volume em Compromissadas (12 Meses) — {banco_sel}")
        st.caption("Recursos captados pela tesouraria do banco junto à sua grade de fundos (Valores em R$ Bi)")
        
        evolucao_tot = df_banco.groupby("DT_COMPTC")["VL_MERC_POS_FINAL"].sum().reset_index()
        evolucao_tot["VL_BI"] = evolucao_tot["VL_MERC_POS_FINAL"] / 1e9
        
        # Exibe os 12 meses em colunas de cards limpos
        cols_tiles = st.columns(len(meses_disponiveis))
        for idx, m in enumerate(meses_disponiveis):
            val_m = evolucao_tot[evolucao_tot["DT_COMPTC"] == m]
            v_bi = val_m["VL_BI"].iloc[0] if not val_m.empty else 0.0
            is_active = (m == comp_selecionada)
            
            with cols_tiles[idx]:
                st.markdown(f"""
                <div class="tile-month {'tile-month-active' if is_active else ''}">
                    <div class="tile-date">{m.split('-')[1]}/{m.split('-')[0][2:]}</div>
                    <div class="tile-val">{v_bi:.1f}</div>
                    <div style="font-size: 9px; color: #94a3b8;">R$ Bi</div>
                </div>
                """, unsafe_allow_html=True)
                
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        
        # Gráfico Empilhado de Evolução do Volume por Tipo de Papel
        evolucao_tipo = df_banco.groupby(["DT_COMPTC", "TP_TITPUB"])["VL_MERC_POS_FINAL"].sum().reset_index()
        evolucao_tipo["VL_BILHOES"] = evolucao_tipo["VL_MERC_POS_FINAL"] / 1e9
        
        fig_banco = px.bar(
            evolucao_tipo,
            x="DT_COMPTC",
            y="VL_BILHOES",
            color="TP_TITPUB",
            title=f"Composição Mensal de Lastro — {banco_sel} (R$ Bi)",
            labels={"DT_COMPTC": "Competência", "VL_BILHOES": "R$ Bilhões", "TP_TITPUB": "Tipo de Título"},
            color_discrete_sequence=["#0284c7", "#10b981", "#f59e0b", "#8b5cf6"]
        )
        fig_banco.update_layout(height=280, margin=dict(t=30, b=10, l=10, r=10))
        st.plotly_chart(fig_banco, use_container_width=True, config={'displayModeBar': False})
        
        # Grid com 2 colunas: Breakdown por tipo e Tabela de principais papéis
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown(f"##### 🎯 Títulos Utilizados como Lastro ({comp_selecionada})")
            lastro_mes_tipo = dados_banco_mes.groupby("TP_TITPUB")["VL_MERC_POS_FINAL"].sum().reset_index()
            lastro_mes_tipo["PCT"] = (lastro_mes_tipo["VL_MERC_POS_FINAL"] / total_lastro_mes * 100) if total_lastro_mes > 0 else 0
            
            for _, r in lastro_mes_tipo.iterrows():
                st.markdown(f"""
                <div style="margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; font-size: 12px; font-weight: 600;">
                        <span>{r['TP_TITPUB']}</span>
                        <span style="font-family: monospace;">R$ {r['VL_MERC_POS_FINAL']:,.2f} ({r['PCT']:.1f}%)</span>
                    </div>
                    <div style="width: 100%; height: 6px; background: #e2e8f0; border-radius: 4px; overflow: hidden; margin-top: 3px;">
                        <div style="width: {min(100, max(2, r['PCT']))}%; height: 100%; background: #0f172a; border-radius: 4px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            st.caption("A preferência por LFT e LTN decorre da alta liquidez e facilidade de repasse com o Banco Central.")
            
        with col_t2:
            st.markdown(f"##### 📑 Principais Papéis Entregues como Colateral")
            top_papeis = dados_banco_mes.groupby(["TP_TITPUB", "CD_ISIN", "DT_VENC"]).agg(
                VOL=("VL_MERC_POS_FINAL", "sum"),
                FUNDOS=("CNPJ_CLEAN", "nunique")
            ).reset_index().sort_values("VOL", ascending=False).head(6)
            
            top_papeis_fmt = top_papeis.copy()
            top_papeis_fmt["VOL"] = top_papeis_fmt["VOL"].apply(lambda v: f"R$ {v:,.2f}")
            top_papeis_fmt.rename(columns={
                "TP_TITPUB": "Tipo",
                "CD_ISIN": "ISIN",
                "DT_VENC": "Vencimento",
                "FUNDOS": "Qtd Fundos",
                "VOL": "Volume Lastreado"
            }, inplace=True)
            st.dataframe(top_papeis_fmt, use_container_width=True)

# ==============================================================================
# ABA 5: EXPORTAÇÃO EM PDF
# ==============================================================================
with tab5:
    st.subheader("📄 Central de Exportação de Relatórios Executivos em PDF")
    st.markdown("Gere relatórios institucionais completos com sumário executivo, KPIs de patrimônio e tabela de composição auditada.")
    
    tipo_relatorio = st.radio("Escolha o Modelo de Relatório:", ["Relatório Cadastral & Carteira de Fundo", "Visão Consolidada de Conglomerado", "Auditoria de Detentores por Título Público"])
    
    if tipo_relatorio == "Relatório Cadastral & Carteira de Fundo":
        fundo_pdf_sel = st.selectbox("Fundo para Exportar:", list(opcoes_fundo.keys()), key="pdf_fundo")
        cnpj_pdf = opcoes_fundo[fundo_pdf_sel]
        
        dados_pdf = df_all[(df_all["CNPJ_CLEAN"] == cnpj_pdf) & (df_all["DT_COMPTC"] == comp_selecionada)]
        
        if st.button("Gerar Relatório em PDF do Fundo", type="primary"):
            with st.spinner("Gerando PDF executivo..."):
                pdf_bytes = gerar_relatorio_pdf_fundo(dados_pdf, comp_selecionada)
                st.download_button(
                    label="⬇️ Baixar Relatório em PDF",
                    data=pdf_bytes,
                    file_name=f"relatorio_cvm_{cnpj_pdf}_{comp_selecionada}.pdf",
                    mime="application/pdf"
                )
    elif tipo_relatorio == "Visão Consolidada de Conglomerado":
        conglom_pdf_sel = st.selectbox("Conglomerado para Exportar:", lista_conglom_tab, key="pdf_conglom")
        dados_conglom_pdf = df_all[(df_all["CONGLOMERADO"] == conglom_pdf_sel) & (df_all["DT_COMPTC"] == comp_selecionada)]
        
        if st.button("Gerar Relatório em PDF do Conglomerado", type="primary"):
            with st.spinner("Gerando relatório consolidado em PDF..."):
                pdf_bytes = gerar_relatorio_pdf_conglomerado(dados_conglom_pdf, conglom_pdf_sel, comp_selecionada)
                st.download_button(
                    label="⬇️ Baixar Relatório do Conglomerado em PDF",
                    data=pdf_bytes,
                    file_name=f"consolidado_{conglom_pdf_sel.lower().replace(' ', '_')}_{comp_selecionada}.pdf",
                    mime="application/pdf"
                )
    else:
        papel_pdf_sel = st.selectbox("Título Público para Exportar:", papeis_disp, key="pdf_papel")
        dados_papel_pdf = df_all[(df_all["ID_PAPEL"] == papel_pdf_sel) & (df_all["DT_COMPTC"] == comp_selecionada)]
        
        if st.button("Gerar Auditoria em PDF do Título", type="primary"):
            with st.spinner("Compilando auditoria em PDF..."):
                pdf_bytes = gerar_relatorio_pdf_titulo(dados_papel_pdf, papel_pdf_sel, comp_selecionada)
                st.download_button(
                    label="⬇️ Baixar Auditoria em PDF",
                    data=pdf_bytes,
                    file_name=f"auditoria_titulo_{comp_selecionada}.pdf",
                    mime="application/pdf"
                )
