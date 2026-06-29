import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# Configuração da página
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
    df['MES'] = df['DT EMISSAO'].dt.month_name()
    
    # Categorização de Prazo
    def categorizar(sla):
        if pd.isna(sla): return 'Sem SLA'
        if sla < 10: return 'No Prazo'
        if sla <= 15: return 'Atenção'
        return 'Fora do Prazo'
    
    df['CATEGORIA_PRAZO'] = df['SLA'].apply(categorizar)
    df.loc[df['STATUS_CLEAN'] == 'FINALIZADO', 'CATEGORIA_PRAZO'] = 'Finalizado'
    
    # Dataset com SCs únicas para KPIs
    df_unicos = df.drop_duplicates(subset=['Nº Solicitação (SC)'])
    return df, df_unicos

df, df_unicos = carregar_dados()

# Sidebar
st.sidebar.title("Navegação")
secao = st.sidebar.radio("Seções:", ["Visão Geral", "Curva ABC", "Gestão de Pendências"])

# --- VISÃO GERAL ---
if secao == "Visão Geral":
    st.title("📊 Visão Geral - Performance")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pendentes", df_unicos[df_unicos['STATUS_CLEAN'] == 'PENDENTE'].shape[0])
    col2.metric("No Prazo", df_unicos[df_unicos['CATEGORIA_PRAZO'] == 'No Prazo'].shape[0])
    col3.metric("Atenção", df_unicos[df_unicos['CATEGORIA_PRAZO'] == 'Atenção'].shape[0])
    col4.metric("Fora do Prazo", df_unicos[df_unicos['CATEGORIA_PRAZO'] == 'Fora do Prazo'].shape[0])

    df_mes = df_unicos.groupby(['MES', 'CATEGORIA_PRAZO']).size().reset_index(name='Qtd')
    fig = px.bar(df_mes, x='MES', y='Qtd', color='CATEGORIA_PRAZO', title="Volume de SCs por Mês")
    st.plotly_chart(fig, use_container_width=True)

# --- CURVA ABC ---
elif secao == "Curva ABC":
    st.title("📦 Curva ABC - Itens e C.C.")
    
    # ABC Centros de Custo
    st.subheader("Curva ABC - Centros de Custo")
    df_cc = df_unicos.groupby('C Custo')['Nº Solicitação (SC)'].nunique().sort_values(ascending=False).reset_index()
    st.plotly_chart(px.bar(df_cc.head(10), x='C Custo', y='Nº Solicitação (SC)', title="Top 10 Centros de Custo"), use_container_width=True)

    # ABC Itens
    st.subheader("Curva ABC - Itens")
    df_itens = df_unicos.groupby(['Cod. Produto', 'Descricao'])['Nº Solicitação (SC)'].count().sort_values(ascending=False).reset_index()
    st.dataframe(df_itens.head(20), use_container_width=True)

# --- PENDÊNCIAS ---
elif secao == "Gestão de Pendências":
    st.title("⚠️ Solicitações em Aberto")
    pendentes = df_unicos[df_unicos['STATUS_CLEAN'] == 'PENDENTE'].sort_values(by='SLA', ascending=False)
    st.dataframe(pendentes[['Nº Solicitação (SC)', 'Descricao', 'SLA', 'C Custo', 'Comprador']], use_container_width=True)
