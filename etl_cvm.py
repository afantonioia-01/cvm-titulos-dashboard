"""
================================================================================
ETL_CVM.PY - PIPELINE DE EXTRAÇÃO E PROCESSAMENTO DOS 12 MESES DA CVM
================================================================================
Baixa ou lê do disco os arquivos mensais do CDA (cda_fi_AAAAMM.zip), Bloco 1
(Títulos Públicos), arquivos de PL e a base cadastral da CVM (Resolução 175).
Salva em formato colunar Parquet otimizado para deploy no Streamlit Cloud.
"""

import os
import io
import re
import zipfile
import requests
import numpy as np
import pandas as pd
from datetime import datetime

PASTA_DADOS = "./dados_cvm"
os.makedirs(PASTA_DADOS, exist_ok=True)

def limpar_cnpj(serie: pd.Series) -> pd.Series:
    """Padroniza CNPJ em 14 dígitos com zeros à esquerda."""
    return serie.astype(str).str.replace(r'\D', '', regex=True).str.zfill(14)

def padronizar_data(serie: pd.Series) -> pd.Series:
    """Padroniza datas para string YYYY-MM-DD."""
    return pd.to_datetime(serie, errors="coerce").dt.strftime('%Y-%m-%d')

def classificar_operacao(row):
    tp = str(row.get('TP_APLIC', '')).upper()
    return 'Compromissada' if 'COMPROMISSAD' in tp else 'Definitiva'

def classificar_conglomerado(row_ou_nome):
    """
    Identifica o conglomerado bancário auditando Gestor, Administrador e Razão Social.
    Reconhece subsidiárias e seguradoras como Brasilprev (BB), Kinea (Itaú), BRAM (Bradesco), etc.
    """
    if isinstance(row_ou_nome, dict) or isinstance(row_ou_nome, pd.Series):
        texto = f"{row_ou_nome.get('Gestor', '')} {row_ou_nome.get('Administrador', '')} {row_ou_nome.get('Denominacao_Social', '')} {row_ou_nome.get('DENOM_SOCIAL', '')}"
    else:
        texto = str(row_ou_nome)
    
    n = texto.upper()
    
    # Banco do Brasil & Brasilprev
    if any(b in n for b in ['BANCO DO BRASIL', 'BB GESTAO', 'BB GESTÃO', 'BB DTVM', 'BB ', 'BRASILPREV', 'BB-']):
        return 'Banco do Brasil'
    # Itaú Unibanco & Kinea
    if any(b in n for b in ['ITAU', 'ITAÚ', 'ITAUVEST', 'KINEA', 'UNIBANCO', 'INTRAG']):
        return 'Itaú Unibanco'
    # Bradesco & BRAM
    if any(b in n for b in ['BRADESCO', 'BRAM', 'BEM DTVM', 'BRADESCO ASSET', 'BRADESCO SEGUROS']):
        return 'Bradesco'
    # Santander
    if any(b in n for b in ['SANTANDER', 'SANVAL']):
        return 'Santander'
    # Caixa Econômica Federal
    if any(b in n for b in ['CAIXA ECONOMICA', 'CAIXA ECONÔMICA', 'CAIXA DTVM', 'CEF']):
        return 'Caixa Econômica'
    # BTG Pactual
    if any(b in n for b in ['BTG', 'BTG PACTUAL']):
        return 'BTG Pactual'
    # Safra
    if any(b in n for b in ['SAFRA', 'J. SAFRA']):
        return 'Safra'
        
    return 'Independentes'

def processar_arquivos_cvm(pasta_origem: str = PASTA_DADOS) -> pd.DataFrame:
    """
    Processa todos os arquivos .zip e .csv presentes na pasta e consolida
    uma tabela tratada e enriquecida pronta para o Streamlit.
    """
    print(f"Iniciando varredura em: {pasta_origem}")
    lista_titulos = []
    lista_pls = []
    df_cad = pd.DataFrame()

    arquivos = sorted(os.listdir(pasta_origem))
    for arq in arquivos:
        caminho = os.path.join(pasta_origem, arq)
        
        # 1. Base Cadastral
        if arq.endswith(".csv") and ("cadastral" in arq.lower() or "cad" in arq.lower()):
            print(f"-> Lendo Cadastro: {arq}")
            df_cad = pd.read_csv(caminho, sep=";", encoding="ISO-8859-1", low_memory=False)
            col_c = "CNPJ_Fundo" if "CNPJ_Fundo" in df_cad.columns else "CNPJ_FUNDO"
            col_n = "Denominacao_Social" if "Denominacao_Social" in df_cad.columns else "DENOM_SOCIAL"
            df_cad["CNPJ_CLEAN"] = limpar_cnpj(df_cad[col_c])
            df_cad["Denominacao_Social"] = df_cad[col_n].astype(str)
            df_cad = df_cad[["CNPJ_CLEAN", "Denominacao_Social", "Situacao", "Gestor", "Administrador"]].drop_duplicates("CNPJ_CLEAN")

        # 2. Arquivos Mensais do CDA
        elif arq.endswith(".zip"):
            print(f"-> Lendo CDA mensal: {arq}")
            with zipfile.ZipFile(caminho) as z:
                nomes_internos = z.namelist()
                
                # Bloco 1 (Títulos Públicos do SELIC)
                blc1_files = [f for f in nomes_internos if "BLC_1" in f]
                if blc1_files:
                    with z.open(blc1_files[0]) as f:
                        d = pd.read_csv(f, sep=";", encoding="ISO-8859-1", decimal=",", low_memory=False)
                        col_cnpj = "CNPJ_FUNDO_CLASSE" if "CNPJ_FUNDO_CLASSE" in d.columns else "CNPJ_FUNDO"
                        d["CNPJ_CLEAN"] = limpar_cnpj(d[col_cnpj])
                        d["DT_COMPTC"] = padronizar_data(d["DT_COMPTC"])
                        d["VL_MERC_POS_FINAL"] = pd.to_numeric(d["VL_MERC_POS_FINAL"], errors="coerce").fillna(0.0)
                        d["QT_POS_FINAL"] = pd.to_numeric(d["QT_POS_FINAL"], errors="coerce").fillna(0.0)
                        if "DT_VENC" in d.columns:
                            d["DT_VENC"] = pd.to_datetime(d["DT_VENC"], errors="coerce").dt.strftime('%Y-%m-%d')
                        lista_titulos.append(d)

                # Patrimônio Líquido
                pl_files = [f for f in nomes_internos if "_PL_" in f]
                if pl_files:
                    with z.open(pl_files[0]) as f:
                        dp = pd.read_csv(f, sep=";", encoding="ISO-8859-1", decimal=",", low_memory=False)
                        col_cp = "CNPJ_FUNDO_CLASSE" if "CNPJ_FUNDO_CLASSE" in dp.columns else "CNPJ_FUNDO"
                        dp["CNPJ_CLEAN"] = limpar_cnpj(dp[col_cp])
                        dp["DT_COMPTC"] = padronizar_data(dp["DT_COMPTC"])
                        dp["VL_PATRIM_LIQ"] = pd.to_numeric(dp["VL_PATRIM_LIQ"], errors="coerce").fillna(0.0)
                        lista_pls.append(dp[["CNPJ_CLEAN", "DT_COMPTC", "VL_PATRIM_LIQ"]])

    if not lista_titulos:
        print("Aviso: Nenhum arquivo ZIP localizado. Gerando base de dados demonstrativa de 12 meses...")
        return gerar_base_demonstracao()

    df_tit = pd.concat(lista_titulos, ignore_index=True)
    df_pls_all = pd.concat(lista_pls, ignore_index=True).drop_duplicates(["CNPJ_CLEAN", "DT_COMPTC"]) if lista_pls else pd.DataFrame()

    df_consolidado = df_tit.merge(df_pls_all, on=["CNPJ_CLEAN", "DT_COMPTC"], how="left")
    df_consolidado["VL_PATRIM_LIQ"] = df_consolidado["VL_PATRIM_LIQ"].fillna(0.0)
    df_consolidado["PR_SOBRE_PL"] = np.where(
        df_consolidado["VL_PATRIM_LIQ"] > 0,
        (df_consolidado["VL_MERC_POS_FINAL"] / df_consolidado["VL_PATRIM_LIQ"]) * 100,
        0.0
    )

    df_consolidado["TIPO_OPERACAO"] = df_consolidado.apply(classificar_operacao, axis=1)

    if not df_cad.empty:
        df_consolidado = df_consolidado.merge(df_cad, on="CNPJ_CLEAN", how="left")
    else:
        df_consolidado["Denominacao_Social"] = df_consolidado["DENOM_SOCIAL"]

    df_consolidado["CONGLOMERADO"] = df_consolidado.apply(classificar_conglomerado, axis=1)

    df_consolidado["ID_PAPEL"] = (
        df_consolidado["TP_TITPUB"].astype(str) + " (" +
        df_consolidado["CD_ISIN"].astype(str) + " - Venc: " +
        df_consolidado["DT_VENC"].astype(str) + ")"
    )

    saida_parquet = os.path.join(pasta_origem, "carteira_consolidada.parquet")
    df_consolidado.to_parquet(saida_parquet, index=False, compression="snappy")
    print(f"Base consolidada salva com sucesso: {saida_parquet} ({len(df_consolidado):,} registros)")
    return df_consolidado

def gerar_base_demonstracao() -> pd.DataFrame:
    """Gera base sintética com 12 meses idêntica ao layout CVM para testes imediatos."""
    meses = ['2025-08', '2025-09', '2025-10', '2025-11', '2025-12', '2026-01', '2026-02', '2026-03', '2026-04', '2026-05', '2026-06', '2026-07']
    fundos = [
        {"cnpj": "00017024000153", "nome": "BB TOP RENDA FIXA DI LP FI", "pl": 42000000000, "banco": "Banco do Brasil"},
        {"cnpj": "01597187000115", "nome": "ITAU SOBERANO RF SIMPLES LP FI", "pl": 68000000000, "banco": "Itaú Unibanco"},
        {"cnpj": "02298136000180", "nome": "BRADESCO FIC FI RF REFERENCIADO DI", "pl": 51000000000, "banco": "Bradesco"},
        {"cnpj": "07432896000185", "nome": "BTG PACTUAL TESOURO SELIC SIMPLES FI", "pl": 33000000000, "banco": "BTG Pactual"},
        {"cnpj": "03737206000197", "nome": "KINEA RENDA FIXA ABSOLUTO FIC FIM", "pl": 14000000000, "banco": "Itaú Unibanco"},
        {"cnpj": "03082360000171", "nome": "SANTANDER FIC FI RF CLÁSSICO DI", "pl": 29000000000, "banco": "Santander"}
    ]
    titulos = [
        ("LFT", "210100", "BRSTNCLF1R91", "2026-03-01", 15420.0),
        ("LFT", "210100", "BRSTNCLF1RT8", "2030-12-01", 15510.0),
        ("NTN-B", "760199", "BRSTNCNTB674", "2026-08-15", 4620.0),
        ("NTN-B", "760199", "BRSTNCNTB732", "2035-08-15", 4210.0),
        ("LTN", "100000", "BRSTNCLN1071", "2027-01-01", 810.0),
        ("NTN-F", "210200", "BRSTNCNTF170", "2031-01-01", 980.0)
    ]
    linhas = []
    for m_idx, m in enumerate(meses):
        for f in fundos:
            pl_mes = f["pl"] * (1 + m_idx * 0.008)
            for t_tipo, t_selic, t_isin, t_venc, pu in titulos:
                qtd = int((pl_mes * 0.08) / pu)
                vl = qtd * pu
                is_repo = (t_tipo == "LFT" and "2030" in t_venc)
                op = "Compromissada" if is_repo else "Definitiva"
                linhas.append({
                    "CNPJ_CLEAN": f["cnpj"],
                    "Denominacao_Social": f["nome"],
                    "DT_COMPTC": m,
                    "TP_TITPUB": t_tipo,
                    "CD_SELIC": t_selic,
                    "CD_ISIN": t_isin,
                    "DT_VENC": t_venc,
                    "QT_POS_FINAL": qtd,
                    "VL_MERC_POS_FINAL": vl,
                    "VL_PATRIM_LIQ": pl_mes,
                    "PR_SOBRE_PL": (vl / pl_mes) * 100,
                    "TIPO_OPERACAO": op,
                    "CONGLOMERADO": f["banco"],
                    "ID_PAPEL": f"{t_tipo} ({t_isin} - Venc: {t_venc})"
                })
    return pd.DataFrame(linhas)

if __name__ == "__main__":
    df = processar_arquivos_cvm()
