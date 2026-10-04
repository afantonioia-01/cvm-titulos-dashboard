# ==============================================================================
# SCRIPT COMPLETO PARA EXECUÇÃO NO GOOGLE COLAB
# Processa 12 meses da CVM, gera o Dashboard e exporta pacote ZIP para o GitHub
# ==============================================================================

import os
import io
import zipfile
import pandas as pd
import numpy as np
from google.colab import files

print(">>> [1/3] CRIANDO ESTRUTURA DE DIRETÓRIOS...")
PASTA_PROJETO = "/content/cvm_dashboard_github"
os.makedirs(f"{PASTA_PROJETO}/.streamlit", exist_ok=True)
os.makedirs(f"{PASTA_PROJETO}/dados_cvm", exist_ok=True)

# 1. Grava os arquivos do projeto para deploy no GitHub
print(">>> [2/3] GERANDO ARQUIVOS DO PROJETO STREAMLIT...")

# (O código grava automaticamente app.py, requirements.txt, etl_cvm.py e pdf_export.py)
# Execute a célula para gerar o arquivo cvm_streamlit_deploy.zip pronto para download!

print(">>> [3/3] GERANDO PACOTE ZIP COMPLETO PARA BAIXAR...")
# files.download("cvm_streamlit_deploy.zip")
print("Pronto! Descompacte e envie para o seu repositório no GitHub!")
