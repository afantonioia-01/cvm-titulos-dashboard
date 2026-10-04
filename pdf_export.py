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
