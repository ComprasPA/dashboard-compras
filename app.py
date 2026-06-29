import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

st.set_page_config(page_title="Dashboard Executivo", layout="wide")

SHEET_ID = "1e7pQ512ge5XMnXxsRODEO7V48KgWo6FpKeITFqBSg1o"
SHEET_NAME = "Solicitações"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

CORES_STATUS = {'FINALIZADO': '#28a745', 'ATENÇÃO': '#ffc107', 'FORA DO PRAZO': '#dc3545', 'NO PRAZO': '#007bff'}

@st.cache_data(ttl=600)
def carregar_dados():
    response = requests.get(URL)
    response.raise_for_status()
    df = pd.read_csv(io.StringIO(response.text))
    df.columns = df.columns.str.strip()
    return df

df_full = carregar_dados()

# --- MAPEAMENTO (AJUSTE AQUI SE O NOME NA PLANILHA FOR DIFERENTE) ---
MAPA = {
    'SLA': 'SLA',
    'DT_EMISSAO': 'DT Emissao',
    'PEDIDO': 'Nº Pedido (PC)',
    'SOLICITACAO': 'Nº Solicitação (SC)',
    'C_CUSTO': 'C Custo',
    'DESCRICAO': 'Descricao',
    'FORNECEDOR': 'Fornecedor',
    'CRITICIDADE': 'Criticidade'
}

# Tratamento
df_full[MAPA['SLA']] = pd.to_numeric(df_full[MAPA['SLA']], errors='coerce').fillna(0)
df_full['DT_DT'] = pd.to_datetime(df_full[MAPA['DT_EMISSAO']], errors='coerce')
df_full['IS_ABERTA'] = df_full[MAPA['PEDIDO']].isna() | (df_full[MAPA['PEDIDO']].astype(str).str.lower() == 'nan')

df_full['CATEGORIA_COR'] = 'ATENÇÃO'
df_full.loc[~df_full['IS_ABERTA'], 'CATEGORIA_COR'] = 'FINALIZADO'
df_full.loc[df_full['IS_ABERTA'] & (df_full[MAPA['SLA']] < 10), 'CATEGORIA_COR'] = 'NO PRAZO'
df_full.loc[df_full['IS_ABERTA'] & (df_full[MAPA['SLA']] >= 10) & (df_full[MAPA['SLA']] <= 15), 'CATEGORIA_COR'] = 'ATENÇÃO'
df_full.loc[df_full['IS_ABERTA'] & (df_full[MAPA['SLA']] > 15), 'CATEGORIA_COR'] = 'FORA DO PRAZO'

df_full['ANO'] = df_full['DT_DT'].dt.year
df_full['MES_NOME'] = df_full['DT_DT'].dt.month_name()

# --- FILTROS ---
st.sidebar.header("Filtros")
ano_sel = st.sidebar.multiselect("Ano:", sorted(df_full['ANO'].dropna().unique()), default=df_full['ANO'].dropna().unique())
cc_sel = st.sidebar.multiselect("Centro de Custo:", sorted(df_full[MAPA['C_CUSTO']].dropna().unique().tolist()))

df_f = df_full.copy()
if ano_sel: df_f = df_f[df_f['ANO'].isin(ano_sel)]
if cc_sel: df_f = df_f[df_f[MAPA['C_CUSTO']].isin(cc_sel)]
df_sc_unicas = df_f.drop_duplicates(subset=[MAPA['SOLICITACAO']])

# --- DASHBOARD ---
st.title("📊 Dashboard Executivo")

# Gráficos
col1, col2 = st.columns(2)
with col1:
    st.subheader("Distribuição de Status")
    status_counts = df_sc_unicas['CATEGORIA_COR'].value_counts()
    fig = go.Figure(data=[go.Pie(labels=status_counts.index, values=status_counts.values, marker=dict(colors=[CORES_STATUS.get(x, '#ccc') for x in status_counts.index]), hole=0.3)])
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Volume por Criticidade")
    fig = px.bar(df_sc_unicas.groupby(MAPA['CRITICIDADE'])[MAPA['SOLICITACAO']].nunique().reset_index(), x=MAPA['CRITICIDADE'], y=MAPA['SOLICITACAO'], text_auto=True)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# Rankings
col_rank1, col_rank2 = st.columns(2)
with col_rank1:
    st.subheader("🏆 Top 10 Fornecedores (Pedidos)")
    # Filtra pedidos únicos e conta o fornecedor
    df_ped = df_f[df_f[MAPA['PEDIDO']].notna()].drop_duplicates(subset=[MAPA['PEDIDO']])
    st.dataframe(df_ped[MAPA['FORNECEDOR']].value_counts().head(10).reset_index(), use_container_width=True)

with col_rank2:
    st.subheader("🛒 Top 10 Itens Mais Comprados")
    st.dataframe(df_f[MAPA['DESCRICAO']].value_counts().head(10).reset_index(), use_container_width=True)
