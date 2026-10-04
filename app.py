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
from pdf_export import gerar_relatorio_pdf_fundo, gerar_relatorio_pdf_titulo

# ------------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="CVM Títulos Públicos & Fundos | Terminal 12M",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS personalizada para tipografia refinada e cards
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        padding: 16px 20px;
        color: white;
        margin-bottom: 12px;
    }
    .metric-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94a3b8;
        font-weight: 600;
    }
    .metric-value {
        font-size: 22px;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        margin-top: 4px;
        color: #f8fafc;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 2. CARREGAMENTO DOS DADOS COM CACHING OTIMIZADO
# ------------------------------------------------------------------------------
@st.cache_data(show_spinner="Carregando e indexando histórico de 12 meses da CVM...")
def carregar_dados():
    caminho_parquet = "dados_cvm/carteira_consolidada.parquet"
    if os.path.exists(caminho_parquet):
        df = pd.read_parquet(caminho_parquet)
    else:
        # Fallback para script de demonstração ou geração local
        from etl_cvm import gerar_base_demonstracao
        df = gerar_base_demonstracao()
        
    # Assegura tipos e formatações
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
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏛️ Raio-X por Fundo",
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
    
    # Campo de busca com auto-completar
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
        
        # Posições por tipo de operação
        tot_def = dados_fundo_mes[dados_fundo_mes["TIPO_OPERACAO"] == "Definitiva"]["VL_MERC_POS_FINAL"].sum()
        tot_comp = dados_fundo_mes[dados_fundo_mes["TIPO_OPERACAO"] == "Compromissada"]["VL_MERC_POS_FINAL"].sum()
        
        # Cards de Indicadores
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Patrimônio Líquido (PL)", f"R$ {pl_fundo:,.2f}")
        c2.metric("Total Títulos Públicos", f"R$ {tot_titulos:,.2f}")
        c3.metric("Definitivas (Risco Real)", f"R$ {tot_def:,.2f}", f"{(tot_def/pl_fundo*100):.1f}% do PL")
        c4.metric("Compromissadas (Caixa)", f"R$ {tot_comp:,.2f}", f"{(tot_comp/pl_fundo*100):.1f}% do PL")
        
        st.markdown("---")
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("##### Alocação por Tipo de Título")
            por_tipo = dados_fundo_mes.groupby("TP_TITPUB")["VL_MERC_POS_FINAL"].sum().reset_index()
            fig_pie = px.pie(
                por_tipo,
                names="TP_TITPUB",
                values="VL_MERC_POS_FINAL",
                hole=0.45,
                color_discrete_sequence=["#1e3a8a", "#0284c7", "#059669", "#d97706", "#7c3aed"]
            )
            fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=280)
            st.plotly_chart(fig_pie, use_container_width=True)
            
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
            st.plotly_chart(fig_bar, use_container_width=True)
            
        st.markdown("##### Posições Detalhadas em Carteira (Ativo por Ativo)")
        cols_tab = ["TP_TITPUB", "CD_SELIC", "CD_ISIN", "DT_VENC", "TIPO_OPERACAO", "QT_POS_FINAL", "VL_MERC_POS_FINAL", "PR_SOBRE_PL"]
        df_tab = dados_fundo_mes[[c for c in cols_tab if c in dados_fundo_mes.columns]].copy()
        
        # Formatações amigáveis
        df_tab_view = df_tab.copy()
        df_tab_view["QT_POS_FINAL"] = df_tab_view["QT_POS_FINAL"].apply(lambda v: f"{v:,.0f}")
        df_tab_view["VL_MERC_POS_FINAL"] = df_tab_view["VL_MERC_POS_FINAL"].apply(lambda v: f"R$ {v:,.2f}")
        df_tab_view["PR_SOBRE_PL"] = df_tab_view["PR_SOBRE_PL"].apply(lambda v: f"{v:.2f}%")
        st.dataframe(df_tab_view, use_container_width=True)

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
        k1.metric("Volume Total Custodiado", f"R$ {tot_fin:,.2f}", f"R$ {tot_fin/1e9:.2f} Bi")
        k2.metric("Quantidade Total de Títulos", f"{tot_qtd:,.0f} unidades")
        k3.metric("Total de Fundos Detentores", f"{tot_fundos:,} fundos")
        
        st.markdown("---")
        
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
        fig_top.update_layout(yaxis=dict(autorange="reversed"), height=380)
        st.plotly_chart(fig_top, use_container_width=True)
        
        st.markdown("##### Ranking Completo de Detentores")
        cols_det = ["Denominacao_Social", "CNPJ_CLEAN", "QT_POS_FINAL", "VL_MERC_POS_FINAL", "PR_SOBRE_PL", "VL_PATRIM_LIQ"]
        df_det = dados_papel[[c for c in cols_det if c in dados_papel.columns]].sort_values("VL_MERC_POS_FINAL", ascending=False)
        st.dataframe(df_det, use_container_width=True)

# ==============================================================================
# ABA 3: COMPARADOR TEMPORAL (MÊS A vs MÊS B)
# ==============================================================================
with tab3:
    st.subheader("Comparador Histórico de Rebalanceamento")
    
    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    with col_f1:
        fundo_comp_sel = st.selectbox("Fundo para Comparação:", list(opcoes_fundo.keys()), key="comp_fundo")
        cnpj_comp = opcoes_fundo[fundo_comp_sel]
    with col_f2:
        mes_a = st.selectbox("Mês Base (A):", meses_disponiveis, index=max(0, len(meses_disponiveis)-2))
    with col_f3:
        mes_b = st.selectbox("Mês de Comparação (B):", meses_disponiveis, index=len(meses_disponiveis)-1)
        
    if mes_a == mes_b:
        st.warning("Selecione dois meses distintos para verificar movimentações.")
    else:
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
        
        # Resumo de Movimentações
        s_novos = (diff["STATUS"] == "NOVO APORTE").sum()
        s_liq = (diff["STATUS"] == "LIQUIDADO").sum()
        s_aum = (diff["STATUS"] == "AUMENTOU").sum()
        s_red = (diff["STATUS"] == "REDUZIU").sum()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Novos Aportes", f"{s_novos} papéis")
        m2.metric("Liquidações Totais", f"{s_liq} papéis")
        m3.metric("Aumentos de Posição", f"{s_aum} papéis")
        m4.metric("Reduções de Posição", f"{s_red} papéis")
        
        st.markdown("---")
        st.markdown("##### Auditoria de Variação de Ativos")
        st.dataframe(diff.sort_values("DELTA_VL", ascending=False), use_container_width=True)

# ==============================================================================
# ABA 4: TESOURARIAS & BANCOS
# ==============================================================================
with tab4:
    st.subheader("Engenharia Reversa: Tesourarias & Lastro de Compromissadas")
    st.caption("Mapeamento de papéis utilizados pelas mesas bancárias como garantia em operações de caixa de seus fundos.")
    
    bancos_lista = ["Itaú Unibanco", "Bradesco", "Banco do Brasil", "Santander", "Caixa Econômica", "BTG Pactual", "Safra"]
    banco_sel = st.selectbox("Selecione o Conglomerado Bancário:", bancos_lista)
    
    df_banco = df_all[(df_all["CONGLOMERADO"] == banco_sel) & (df_all["TIPO_OPERACAO"] == "Compromissada")].copy()
    
    if df_banco.empty:
        st.info("Nenhuma operação compromissada identificada para este conglomerado nos 12 meses.")
    else:
        # Evolução do lastro ao longo dos 12 meses
        evolucao = df_banco.groupby(["DT_COMPTC", "TP_TITPUB"])["VL_MERC_POS_FINAL"].sum().reset_index()
        evolucao["VL_BILHOES"] = evolucao["VL_MERC_POS_FINAL"] / 1e9
        
        fig_banco = px.bar(
            evolucao,
            x="DT_COMPTC",
            y="VL_BILHOES",
            color="TP_TITPUB",
            title=f"Evolução do Volume Lastreado em Compromissadas - {banco_sel} (R$ Bi)",
            labels={"DT_COMPTC": "Competência", "VL_BILHOES": "R$ Bilhões", "TP_TITPUB": "Tipo de Título"}
        )
        st.plotly_chart(fig_banco, use_container_width=True)

# ==============================================================================
# ABA 5: EXPORTAÇÃO EM PDF
# ==============================================================================
with tab5:
    st.subheader("📄 Central de Exportação de Relatórios Executivos em PDF")
    st.markdown("Gere relatórios institucionais completos com sumário executivo, KPIs de patrimônio e tabela de composição auditada.")
    
    tipo_relatorio = st.radio("Escolha o Modelo de Relatório:", ["Relatório Cadastral & Carteira de Fundo", "Auditoria de Detentores por Título Público"])
    
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
