import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

st.set_page_config(page_title="Dashboard de Compras", layout="wide")

# Configuração da planilha
SHEET_ID = "1e7pQ512ge5XMnXxsRODEO7V48KgWo6FpKeITFqBSg1o"
SHEET_NAME = "Solicitações"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

@st.cache_data(ttl=600)
def carregar_dados():
    response = requests.get(URL)
    response.raise_for_status()
    df = pd.read_csv(io.StringIO(response.text))
    
    # Tratamentos básicos
    df['STATUS_CLEAN'] = df['STATUS'].astype(str).str.strip().str.upper()
    df['SLA'] = pd.to_numeric(df['SLA'], errors='coerce')
    df['DT EMISSAO'] = pd.to_datetime(df['DT Emissao'], errors='coerce')
    
    # Criar colunas de mês e ano para filtragem
    df['MES_NUM'] = df['DT EMISSAO'].dt.month
    df['ANO'] = df['DT EMISSAO'].dt.year
    df['MES_NOME'] = df['DT EMISSAO'].dt.month_name()
    return df

df_full = carregar_dados()

# --- FILTRO POR MÊS NA BARRA LATERAL ---
st.sidebar.title("Filtros")
ano_selecionado = st.sidebar.selectbox("Selecione o Ano:", sorted(df_full['ANO'].dropna().unique()))
mes_selecionado = st.sidebar.selectbox("Selecione o Mês:", sorted(df_full['MES_NOME'].unique()))

# Filtragem dos dados
df_filtrado = df_full[(df_full['ANO'] == ano_selecionado) & (df_full['MES_NOME'] == mes_selecionado)]
df_unicos = df_filtrado.drop_duplicates(subset=['Nº Solicitação (SC)'])

# --- VISÃO GERAL ---
st.title(f"📊 Dashboard de Compras - {mes_selecionado}/{ano_selecionado}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Pendentes", df_unicos[df_unicos['STATUS_CLEAN'] == 'PENDENTE'].shape[0])
col2.metric("No Prazo", df_unicos[df_unicos['SLA'] < 10].shape[0])
col3.metric("Atenção", df_unicos[(df_unicos['SLA'] >= 10) & (df_unicos['SLA'] <= 15)].shape[0])
col4.metric("Fora do Prazo", df_unicos[df_unicos['SLA'] > 15].shape[0])

st.divider()

# Gráfico de Status do Mês selecionado
df_status = df_unicos['STATUS_CLEAN'].value_counts().reset_index()
fig = px.pie(df_status, values='count', names='STATUS_CLEAN', title=f"Status das Solicitações em {mes_selecionado}")
st.plotly_chart(fig, use_container_width=True)

# Curva ABC rápida do mês
st.subheader("📦 Curva ABC de Centros de Custo (Mês Selecionado)")
df_cc = df_unicos.groupby('C Custo')['Nº Solicitação (SC)'].nunique().sort_values(ascending=False).head(10).reset_index()
st.bar_chart(df_cc.set_index('C Custo'))
