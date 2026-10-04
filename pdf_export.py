"""
================================================================================
PDF_EXPORT.PY - GERADOR DE RELATÓRIOS EXECUTIVOS EM PDF
================================================================================
Utiliza a biblioteca fpdf2 (compatível com Streamlit Community Cloud)
para compilar relatórios elegantes de fundos e auditoria de títulos.
"""

from fpdf import FPDF
import pandas as pd
import datetime

class CvmReportPDF(FPDF):
    def header(self):
        # Cabeçalho corporativo
        self.set_fill_color(30, 41, 59) # Slate 800
        self.rect(0, 0, 210, 22, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Helvetica', 'B', 11)
        self.set_xy(12, 6)
        self.cell(0, 10, 'TERMINAL CVM | AUDITORIA DE RENDA FIXA E TÍTULOS PÚBLICOS', 0, 0, 'L')
        self.set_font('Helvetica', '', 8)
        self.set_xy(140, 6)
        self.cell(58, 10, f'Emitido em: {datetime.date.today().strftime("%d/%m/%Y")}', 0, 0, 'R')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}} | Relatório de Governança e Transparência CVM Resolução 175', 0, 0, 'C')

def gerar_relatorio_pdf_fundo(df_fundo: pd.DataFrame, competencia: str) -> bytes:
    """Gera PDF com raio-x cadastral e carteira de títulos públicos."""
    pdf = CvmReportPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    if df_fundo.empty:
        pdf.set_font('Helvetica', '', 12)
        pdf.cell(0, 10, 'Nenhum dado disponível para o fundo nesta competência.', 0, 1)
        return bytes(pdf.output())

    nome = df_fundo["Denominacao_Social"].iloc[0]
    cnpj = df_fundo["CNPJ_CLEAN"].iloc[0]
    pl = df_fundo["VL_PATRIM_LIQ"].iloc[0]
    tot_titulos = df_fundo["VL_MERC_POS_FINAL"].sum()
    pct = (tot_titulos / pl * 100) if pl > 0 else 0
    conglom = df_fundo["CONGLOMERADO"].iloc[0] if "CONGLOMERADO" in df_fundo.columns else "N/D"

    # Título do Fundo
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(15, 23, 42)
    pdf.multi_cell(0, 7, nome)
    pdf.ln(2)

    # Metadados Cadastrais
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 5, f'CNPJ: {cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}  |  Competência: {competencia}  |  Conglomerado: {conglom}', 0, 1)
    pdf.ln(5)

    # Box de Resumo Executivo (KPIs)
    pdf.set_fill_color(241, 245, 249)
    pdf.set_draw_color(203, 213, 225)
    pdf.rect(10, pdf.get_y(), 190, 20, 'DF')
    y_box = pdf.get_y() + 4

    pdf.set_xy(15, y_box)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.cell(55, 4, 'PATRIMÔNIO LÍQUIDO', 0, 1)
    pdf.set_x(15)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(55, 6, f'R$ {pl:,.2f}', 0, 0)

    pdf.set_xy(75, y_box)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(55, 4, 'TOTAL EM TÍTULOS PÚBLICOS', 0, 1)
    pdf.set_x(75)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(55, 6, f'R$ {tot_titulos:,.2f}', 0, 0)

    pdf.set_xy(135, y_box)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(55, 4, 'REPRESENTATIVIDADE NO PL', 0, 1)
    pdf.set_x(135)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(2, 132, 199)
    pdf.cell(55, 6, f'{pct:.2f}%', 0, 0)

    pdf.ln(22)

    # Tabela de Posições
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, 'DETALHAMENTO ATIVO A ATIVO (CARTEIRA CVM):', 0, 1)

    # Header da tabela
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.cell(20, 7, 'Tipo', 1, 0, 'C', 1)
    pdf.cell(22, 7, 'SELIC', 1, 0, 'C', 1)
    pdf.cell(32, 7, 'ISIN', 1, 0, 'C', 1)
    pdf.cell(24, 7, 'Vencimento', 1, 0, 'C', 1)
    pdf.cell(28, 7, 'Operação', 1, 0, 'C', 1)
    pdf.cell(38, 7, 'Volume (R$)', 1, 0, 'R', 1)
    pdf.cell(26, 7, '% do PL', 1, 1, 'R', 1)

    pdf.set_text_color(51, 65, 85)
    pdf.set_font('Helvetica', '', 8)

    for idx, row in df_fundo.iterrows():
        bg = 248 if idx % 2 == 0 else 255
        pdf.set_fill_color(bg, bg, bg)
        
        pdf.cell(20, 6, str(row.get('TP_TITPUB', '')), 1, 0, 'C', 1)
        pdf.cell(22, 6, str(row.get('CD_SELIC', '')), 1, 0, 'C', 1)
        pdf.cell(32, 6, str(row.get('CD_ISIN', '')), 1, 0, 'C', 1)
        venc = str(row.get('DT_VENC', ''))[:10]
        pdf.cell(24, 6, venc, 1, 0, 'C', 1)
        pdf.cell(28, 6, str(row.get('TIPO_OPERACAO', 'Definitiva')), 1, 0, 'C', 1)
        vl = float(row.get('VL_MERC_POS_FINAL', 0))
        pdf.cell(38, 6, f'R$ {vl:,.2f}', 1, 0, 'R', 1)
        pr = float(row.get('PR_SOBRE_PL', 0))
        pdf.cell(26, 6, f'{pr:.2f}%', 1, 1, 'R', 1)

    pdf.ln(8)
    pdf.set_font('Helvetica', 'I', 7)
    pdf.set_text_color(148, 163, 184)
    pdf.multi_cell(0, 4, 'Fonte de dados: CVM - Dados Abertos (Composição e Diversificação das Aplicações - CDA Bloco 1). As posições definitivas refletem a titularidade com risco de taxa e mercado; as operações compromissadas refletem alocação temporária de caixa com garantia colateral.')

    return bytes(pdf.output())

def gerar_relatorio_pdf_titulo(df_titulo: pd.DataFrame, titulo_id: str, competencia: str) -> bytes:
    """Gera PDF com a lista dos maiores fundos detentores de um papel específico."""
    pdf = CvmReportPDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 7, f'AUDITORIA DE DETENTORES: {titulo_id}', 0, 1)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 5, f'Competência: {competencia}  |  Total de Fundos Detentores: {len(df_titulo)}', 0, 1)
    pdf.ln(6)

    # Header da tabela
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.cell(85, 7, 'Fundo de Investimento', 1, 0, 'L', 1)
    pdf.cell(32, 7, 'CNPJ', 1, 0, 'C', 1)
    pdf.cell(25, 7, 'Qtd Títulos', 1, 0, 'R', 1)
    pdf.cell(30, 7, 'Volume (R$)', 1, 0, 'R', 1)
    pdf.cell(18, 7, '% do PL', 1, 1, 'R', 1)

    pdf.set_text_color(51, 65, 85)
    pdf.set_font('Helvetica', '', 8)

    top30 = df_titulo.sort_values('VL_MERC_POS_FINAL', ascending=False).head(30)
    for idx, row in top30.reset_index(drop=True).iterrows():
        bg = 248 if idx % 2 == 0 else 255
        pdf.set_fill_color(bg, bg, bg)
        nome = str(row.get('Denominacao_Social', ''))[:40]
        pdf.cell(85, 6, nome, 1, 0, 'L', 1)
        cnpj = str(row.get('CNPJ_CLEAN', ''))
        pdf.cell(32, 6, cnpj, 1, 0, 'C', 1)
        qtd = float(row.get('QT_POS_FINAL', 0))
        pdf.cell(25, 6, f'{qtd:,.0f}', 1, 0, 'R', 1)
        vl = float(row.get('VL_MERC_POS_FINAL', 0))
        pdf.cell(30, 6, f'R$ {vl:,.2f}', 1, 0, 'R', 1)
        pr = float(row.get('PR_SOBRE_PL', 0))
        pdf.cell(18, 6, f'{pr:.2f}%', 1, 1, 'R', 1)

    return bytes(pdf.output())

def gerar_relatorio_pdf_conglomerado(df_conglom: pd.DataFrame, nome_conglom: str, competencia: str) -> bytes:
    """Gera PDF executivo consolidado do conglomerado com AuM, ranking de fundos e títulos."""
    pdf = CvmReportPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    if df_conglom.empty:
        pdf.set_font('Helvetica', '', 12)
        pdf.cell(0, 10, f'Nenhum dado disponível para {nome_conglom} nesta competência.', 0, 1)
        return bytes(pdf.output())

    # Métricas consolidadas
    fundos_df = df_conglom[['CNPJ_CLEAN', 'Denominacao_Social', 'VL_PATRIM_LIQ']].drop_duplicates('CNPJ_CLEAN')
    pl_total = fundos_df['VL_PATRIM_LIQ'].sum()
    tot_titulos = df_conglom['VL_MERC_POS_FINAL'].sum()
    tot_def = df_conglom[df_conglom['TIPO_OPERACAO'] == 'Definitiva']['VL_MERC_POS_FINAL'].sum()
    tot_comp = df_conglom[df_conglom['TIPO_OPERACAO'] == 'Compromissada']['VL_MERC_POS_FINAL'].sum()

    # Cabeçalho
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, f'CONSOLIDADO DO GRUPO: {nome_conglom.upper()}', 0, 1)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 5, f'Competência: {competencia}  |  Total de Fundos: {len(fundos_df)}  |  Posições Ativas: {len(df_conglom):,}', 0, 1)
    pdf.ln(4)

    # Box de KPIs
    pdf.set_fill_color(241, 245, 249)
    pdf.set_draw_color(203, 213, 225)
    pdf.rect(10, pdf.get_y(), 190, 20, 'DF')
    y_box = pdf.get_y() + 4

    pdf.set_xy(12, y_box)
    pdf.set_font('Helvetica', 'B', 7)
    pdf.cell(45, 4, 'AuM CONSOLIDADO (PL)', 0, 1)
    pdf.set_x(12)
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(45, 6, f'R$ {pl_total:,.2f}', 0, 0)

    pdf.set_xy(58, y_box)
    pdf.set_font('Helvetica', 'B', 7)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(45, 4, 'TOTAL EM TÍTULOS', 0, 1)
    pdf.set_x(58)
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(45, 6, f'R$ {tot_titulos:,.2f}', 0, 0)

    pdf.set_xy(105, y_box)
    pdf.set_font('Helvetica', 'B', 7)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(45, 4, 'DEFINITIVAS (RISCO)', 0, 1)
    pdf.set_x(105)
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.set_text_color(22, 163, 74)
    pdf.cell(45, 6, f'R$ {tot_def:,.2f}', 0, 0)

    pdf.set_xy(152, y_box)
    pdf.set_font('Helvetica', 'B', 7)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(45, 4, 'COMPROMISSADAS (CAIXA)', 0, 1)
    pdf.set_x(152)
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.set_text_color(217, 119, 6)
    pdf.cell(45, 6, f'R$ {tot_comp:,.2f}', 0, 0)

    pdf.ln(22)

    # Tabela 1: Top Fundos do Conglomerado
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 7, 'TOP FUNDOS DO CONGLOMERADO POR PATRIMÔNIO LÍQUIDO:', 0, 1)

    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 7.5)
    pdf.cell(80, 6, 'Fundo de Investimento', 1, 0, 'L', 1)
    pdf.cell(32, 6, 'CNPJ', 1, 0, 'C', 1)
    pdf.cell(38, 6, 'Patrimônio Líquido', 1, 0, 'R', 1)
    pdf.cell(40, 6, 'Total em Títulos', 1, 1, 'R', 1)

    pdf.set_text_color(51, 65, 85)
    pdf.set_font('Helvetica', '', 7.5)

    resumo_f = []
    for _, f_row in fundos_df.iterrows():
        c_cnpj = f_row['CNPJ_CLEAN']
        c_nome = str(f_row['Denominacao_Social'])[:42]
        c_pl = f_row['VL_PATRIM_LIQ']
        f_tit = df_conglom[df_conglom['CNPJ_CLEAN'] == c_cnpj]['VL_MERC_POS_FINAL'].sum()
        resumo_f.append({'nome': c_nome, 'cnpj': c_cnpj, 'pl': c_pl, 'tit': f_tit})

    top_f = pd.DataFrame(resumo_f).sort_values('pl', ascending=False).head(12)
    for idx, row in top_f.reset_index(drop=True).iterrows():
        bg = 248 if idx % 2 == 0 else 255
        pdf.set_fill_color(bg, bg, bg)
        pdf.cell(80, 5.5, row['nome'], 1, 0, 'L', 1)
        pdf.cell(32, 5.5, str(row['cnpj']), 1, 0, 'C', 1)
        pdf.cell(38, 5.5, f"R$ {row['pl']:,.2f}", 1, 0, 'R', 1)
        pdf.cell(40, 5.5, f"R$ {row['tit']:,.2f}", 1, 1, 'R', 1)

    pdf.ln(5)

    # Tabela 2: Principais Títulos Públicos Detidos
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 7, 'PRINCIPAIS TÍTULOS PÚBLICOS CUSTODIADOS PELO CONGLOMERADO:', 0, 1)

    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 7.5)
    pdf.cell(20, 6, 'Tipo', 1, 0, 'C', 1)
    pdf.cell(25, 6, 'SELIC', 1, 0, 'C', 1)
    pdf.cell(35, 6, 'ISIN', 1, 0, 'C', 1)
    pdf.cell(25, 6, 'Vencimento', 1, 0, 'C', 1)
    pdf.cell(35, 6, 'Quantidade', 1, 0, 'R', 1)
    pdf.cell(50, 6, 'Volume Consolidado (R$)', 1, 1, 'R', 1)

    pdf.set_text_color(51, 65, 85)
    pdf.set_font('Helvetica', '', 7.5)

    titulos_top = df_conglom.groupby(['TP_TITPUB', 'CD_SELIC', 'CD_ISIN', 'DT_VENC']).agg(
        QT_TOT=('QT_POS_FINAL', 'sum'),
        VL_TOT=('VL_MERC_POS_FINAL', 'sum')
    ).reset_index().sort_values('VL_TOT', ascending=False).head(12)

    for idx, row in titulos_top.reset_index(drop=True).iterrows():
        bg = 248 if idx % 2 == 0 else 255
        pdf.set_fill_color(bg, bg, bg)
        pdf.cell(20, 5.5, str(row['TP_TITPUB']), 1, 0, 'C', 1)
        pdf.cell(25, 5.5, str(row['CD_SELIC']), 1, 0, 'C', 1)
        pdf.cell(35, 5.5, str(row['CD_ISIN']), 1, 0, 'C', 1)
        dt_v = str(row['DT_VENC'])[:10]
        pdf.cell(25, 5.5, dt_v, 1, 0, 'C', 1)
        pdf.cell(35, 5.5, f"{float(row['QT_TOT']):,.0f}", 1, 0, 'R', 1)
        pdf.cell(50, 5.5, f"R$ {float(row['VL_TOT']):,.2f}", 1, 1, 'R', 1)

    return bytes(pdf.output())
