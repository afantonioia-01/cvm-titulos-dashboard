# 🏛️ Terminal CVM - Análise de Fundos e Títulos Públicos (12M)

Dashboard analítico de nível institucional desenvolvido em **Python** e **Streamlit**, desenhado para auditar **12 meses** de arquivos de carteiras de fundos de investimento da **CVM (Comissão de Valores Mobiliários)** com foco prioritário em **Títulos Públicos Federais (Bloco 1 do CDA)**, **Renda Fixa**, **Operações Definitivas vs. Compromissadas**, **Curvas de Duration** e **Engenharia Reversa de Tesourarias Bancárias**.

---

## 🚀 Funcionalidades Principais

1. **🏛️ Raio-X por Fundo**:
   - Patrimônio Líquido, Total em Títulos Públicos e representatividade percentual sobre o PL.
   - Segregação de **Compras Definitivas** (risco real de mercado/marcação a mercado) vs. **Compromissadas** (liquidez/caixa).
   - Composição de indexadores: LFT (Tesouro Selic), NTN-B (Tesouro IPCA+), LTN (Prefixados) e NTN-F.
   - Curva de vencimento e duration.
   - Tabela analítica ativo por ativo com Código SELIC e ISIN.

2. **🎯 Consulta Inversa (por Título Público)**:
   - Rastreamento dos maiores fundos detentores de qualquer título federal.
   - Volume financeiro total e quantidade de títulos custodiados pela indústria.
   - Gráfico Top 10 e ranking completo com % da carteira.

3. **⚖️ Comparador Temporal (Mês A vs. Mês B)**:
   - Auditoria instantânea de rebalanceamento entre duas competências.
   - Classificação em: **Novo Aporte**, **Liquidado Totalmente**, **Aumentou** ou **Reduziu**.
   - Variação física de títulos ($Delta$ Quantidade) e variação financeira ($Delta$ Volume).

4. **🏦 Engenharia Reversa de Tesourarias Bancárias**:
   - Auditoria dos conglomerados (Itaú Unibanco, Bradesco, Banco do Brasil, Santander, Caixa, BTG Pactual, Safra).
   - Títulos públicos utilizados como lastro de captação de caixa via compromissadas.

5. **📄 Exportação de Relatórios em PDF**:
   - Geração dinâmica de relatórios executivos em PDF com sumário executivo, KPIs de patrimônio e tabela de composição auditada pronta para envio a comitês ou clientes.

---

## 🛠️ Passo a Passo para Deploy no Streamlit Community Cloud (Gratuito)

### Passo 1: Criar o Repositório no GitHub
1. Acesse o seu [GitHub](https://github.com) e crie um novo repositório público (ex: `cvm-titulos-dashboard`).
2. Clone o repositório no seu computador ou faça upload dos arquivos gerados neste projeto:
   - `app.py`
   - `etl_cvm.py`
   - `pdf_export.py`
   - `requirements.txt`
   - `.streamlit/config.toml`
   - `README.md`
   - `.gitignore`

### Passo 2: Executar o ETL e Gerar o Arquivo Parquet
Coloque seus arquivos do CDA (`cda_fi_AAAAMM.zip`) na pasta `dados_cvm/` e rode:
```bash
python etl_cvm.py
```
Isso gerará o arquivo colunar ultra-rápido `carteira_consolidada.parquet`.

### Passo 3: Deploy no Streamlit Cloud
1. Acesse [share.streamlit.io](https://share.streamlit.io) e faça login com sua conta do GitHub.
2. Clique em **"New App"**.
3. Selecione o seu repositório: `seu-usuario/cvm-titulos-dashboard`.
4. Defina o arquivo principal como: `app.py`.
5. Clique em **"Deploy!"**.
6. Em cerca de 1 a 2 minutos o seu painel estará publicado na nuvem com link público e seguro (HTTPS) pronto para uso.

---

## 💻 Como Rodar Localmente

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/cvm-titulos-dashboard.git
cd cvm-titulos-dashboard

# 2. Crie um ambiente virtual
python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Inicie o dashboard
streamlit run app.py
```

---

## 📜 Fundamentos Regulatórios da CVM
- **Resolução CVM 175**: Nova estrutura normativa que unifica a indústria em classes e subclasses de cotas.
- **Sigilo Legal de 90 dias**: Informações individualizadas de ativos podem possuir confidencialidade transitória solicitada pelos administradores para evitar *front-running*.
- **Definitivas vs. Compromissadas**: No Bloco 1 do CDA, operações definitivas representam a carteira proprietária onde o fundo corre risco de taxa, enquanto compromissadas são operações de financiamento lastreadas em títulos públicos (posições doadoras de caixa).
