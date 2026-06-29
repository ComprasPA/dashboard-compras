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
    
    # Tratamentos
    df['STATUS_CLEAN'] = df['STATUS'].astype(str).str.strip().str.upper()
    df['SLA'] = pd.to_numeric(df['SLA'], errors='coerce')
    df['DT EMISSAO'] = pd.to_datetime(df['DT Emissao'], errors='coerce')
    return df

df_full = carregar_dados()

# --- FILTRO NA BARRA LATERAL ---
st.sidebar.title("Filtros")
data_min = df_full['DT EMISSAO'].min().date()
data_max = df_full['DT EMISSAO'].max().date()

intervalo = st.sidebar.date_input("Selecione o período:", [data_min, data_max])

# Aplica o filtro se o usuário selecionar duas datas
if len(intervalo) == 2:
    inicio, fim = intervalo
    df_filtrado = df_full[(df_full['DT EMISSAO'].dt.date >= inicio) & (df_full['DT EMISSAO'].dt.date <= fim)]
else:
    df_filtrado = df_full

df_unicos = df_filtrado.drop_duplicates(subset=['Nº Solicitação (SC)'])

# --- VISÃO GERAL (Atualizada com o Filtro) ---
st.title("📊 Dashboard de Compras")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Pendentes", df_unicos[df_unicos['STATUS_CLEAN'] == 'PENDENTE'].shape[0])
col2.metric("No Prazo", df_unicos[df_unicos['SLA'] < 10].shape[0])
col3.metric("Atenção", df_unicos[(df_unicos['SLA'] >= 10) & (df_unicos['SLA'] <= 15)].shape[0])
col4.metric("Fora do Prazo", df_unicos[df_unicos['SLA'] > 15].shape[0])

st.divider()

# Gráfico de Status do Período Selecionado
df_status = df_unicos['STATUS_CLEAN'].value_counts().reset_index()
fig = px.pie(df_status, values='count', names='STATUS_CLEAN', title="Distribuição de Status no Período")
st.plotly_chart(fig, use_container_width=True)
