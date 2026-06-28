import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# Configuração de Layout
st.set_page_config(page_title="Dashboard de Compras", layout="wide")

# Configuração da Planilha Google
SHEET_ID = "1e7pQ512ge5XMnXxsRODEO7V48KgWo6FpKeITFqBSg1o"
SHEET_NAME = "Solicitações"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

@st.cache_data(ttl=600)
def carregar_dados():
    response = requests.get(URL)
    response.raise_for_status()
    df = pd.read_csv(io.StringIO(response.text))
    
    # Ajuste preciso conforme cabeçalhos enviados
    df['STATUS_CLEAN'] = df['STATUS'].astype(str).str.strip().str.upper()
    df['SLA'] = pd.to_numeric(df['SLA'], errors='coerce')
    df['DT EMISSAO'] = pd.to_datetime(df['DT Emissao'], errors='coerce')
    df['MES'] = df['DT EMISSAO'].dt.month_name()
    
    # Categorização de SLA
    def categorizar(sla):
        if pd.isna(sla): return 'Sem SLA'
        if sla < 10: return 'No Prazo'
        if sla <= 15: return 'Atenção'
        return 'Fora do Prazo'
    
    df['CATEGORIA_PRAZO'] = df['SLA'].apply(categorizar)
    df.loc[df['STATUS_CLEAN'] == 'FINALIZADO', 'CATEGORIA_PRAZO'] = 'Finalizado'
    return df

# Executa carregamento
df = carregar_dados()

# Sidebar de Navegação
st.sidebar.title("Navegação")
secao = st.sidebar.radio("Seções do Dashboard:", ["Visão Geral", "Curva ABC", "Gestão de Pendências"])

# --- VISÃO GERAL ---
if secao == "Visão Geral":
    st.title("📊 Dashboard de Compras - Visão Geral")
    col1, col2, col3 = st.columns(3)
    col1.metric("Pendentes", df[df['STATUS_CLEAN'] == 'PENDENTE'].shape[0])
    col2.metric("Fora do Prazo", df[df['CATEGORIA_PRAZO'] == 'Fora do Prazo'].shape[0])
    col3.metric("Finalizados", df[df['STATUS_CLEAN'] == 'FINALIZADO'].shape[0])
    
    st.divider()
    df_mes = df.groupby(['MES', 'CATEGORIA_PRAZO']).size().reset_index(name='Qtd')
    fig_mes = px.bar(df_mes, x='MES', y='Qtd', color='CATEGORIA_PRAZO', title="Evolução Mensal", barmode='group')
    st.plotly_chart(fig_mes, use_container_width=True)

# --- CURVA ABC ---
elif secao == "Curva ABC":
    st.title("📦 Curva ABC - Centros de Custo")
    df_abc = df.groupby('C Custo')['Nº Solicitação (SC)'].nunique().sort_values(ascending=False).reset_index()
    fig_abc = px.bar(df_abc.head(10), x='C Custo', y='Nº Solicitação (SC)', title="Top 10 Centros de Custo", text_auto=True)
    st.plotly_chart(fig_abc, use_container_width=True)

# --- PENDÊNCIAS ---
elif secao == "Pendências":
    st.title("⚠️ Solicitações em Aberto")
    pendentes = df[df['STATUS_CLEAN'] == 'PENDENTE'].sort_values(by='SLA', ascending=False)
    st.dataframe(pendentes[['Nº Solicitação (SC)', 'Descricao', 'SLA', 'C Custo', 'Comprador']], use_container_width=True)
