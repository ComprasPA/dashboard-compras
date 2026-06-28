import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard de Compras", layout="wide")

@st.cache_data
def carregar_dados():
    # Substitua pelo nome exato do arquivo que você vai subir
    df = pd.read_excel('Solicitacoes.xlsx', sheet_name='Solicitações')
    df['Status_Clean'] = df['Status'].astype(str).str.strip().str.upper()
    df['SLA'] = pd.to_numeric(df['SLA'], errors='coerce')
    return df

df = carregar_dados()

# Sidebar
st.sidebar.title("Navegação")
secao = st.sidebar.radio("Seções:", ["Visão Geral", "Curva ABC", "Pendências"])

if secao == "Visão Geral":
    st.title("📊 Visão Geral - Performance")
    
    # Lógica de Categorização
    df['Categoria'] = pd.cut(df['SLA'], bins=[-1, 10, 15, 1000], labels=['No Prazo', 'Atenção', 'Fora do Prazo'])
    
    col1, col2, col3 = st.columns(3)
    col1.metric("No Prazo", df[df['Categoria'] == 'No Prazo'].shape[0])
    col2.metric("Atenção", df[df['Categoria'] == 'Atenção'].shape[0])
    col3.metric("Fora do Prazo", df[df['Categoria'] == 'Fora do Prazo'].shape[0])

elif secao == "Curva ABC":
    st.title("📦 Curva ABC - Centros de Custo")
    # Lógica ABC
    df_abc = df.groupby('C Custo')['Nº Solicitação (SC)'].nunique().sort_values(ascending=False).reset_index()
    fig = px.bar(df_abc.head(10), x='C Custo', y='Nº Solicitação (SC)', title="Top 10 Centros de Custo")
    st.plotly_chart(fig, use_container_width=True)

elif secao == "Pendências":
    st.title("⚠️ Gestão de Pendências")
    pendentes = df[df['Status_Clean'] == 'PENDENTE'].sort_values(by='SLA', ascending=False)
    st.dataframe(pendentes, use_container_width=True)
