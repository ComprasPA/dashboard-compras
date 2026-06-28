import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração de Layout
st.set_page_config(page_title="Dashboard de Compras", layout="wide")

# Configuração da Planilha Google (Modo Leitura CSV)
SHEET_ID = "1e7pQ512ge5XMnXxsRODEO7V48KgWo6FpKeITFqBSg1o"
SHEET_NAME = "Solicitações"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

# Carregamento e Tratamento dos Dados
@st.cache_data(ttl=600)
def carregar_dados():
    df = pd.read_csv(URL)
    # Tratamento básico de colunas
    df['STATUS_CLEAN'] = df['STATUS'].astype(str).str.strip().str.upper()
    df['SLA'] = pd.to_numeric(df['SLA'], errors='coerce')
    df['DT EMISSAO'] = pd.to_datetime(df['DT EMISSAO'], errors='coerce')
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

df = carregar_dados()

# Sidebar de Navegação
st.sidebar.title("Navegação")
secao = st.sidebar.radio("Seções do Dashboard:", ["Visão Geral", "Curva ABC", "Gestão de Pendências"])

# --- SEÇÃO 1: VISÃO GERAL ---
if secao == "Visão Geral":
    st.title("📊 Dashboard de Compras - Visão Geral")
    
    # KPIs Rápidos
    col1, col2, col3 = st.columns(3)
    col1.metric("Pendentes", df[df['STATUS_CLEAN'] == 'PENDENTE'].shape[0])
    col2.metric("Fora do Prazo", df[df['CATEGORIA_PRAZO'] == 'Fora do Prazo'].shape[0])
    col3.metric("Finalizados", df[df['STATUS_CLEAN'] == 'FINALIZADO'].shape[0])
    
    st.divider()
    
    # Gráfico Mensal
    df_mes = df.groupby(['MES', 'CATEGORIA_PRAZO']).size().reset_index(name='Qtd')
    fig_mes = px.bar(df_mes, x='MES', y='Qtd', color='CATEGORIA_PRAZO', 
                     title="Volume de Solicitações por Status Mensal", barmode='group')
    st.plotly_chart(fig_mes, use_container_width=True)

# --- SEÇÃO 2: CURVA ABC ---
elif secao == "Curva ABC":
    st.title("📦 Curva ABC de Centros de Custo")
    
    # Cálculo ABC
    df_abc = df.groupby('C Custo')['Nº Solicitação (SC)'].nunique().sort_values(ascending=False).reset_index()
    df_abc['PARTICIPACAO'] = df_abc['Nº Solicitação (SC)'] / df_abc['Nº Solicitação (SC)'].sum()
    df_abc['ACUMULADO'] = df_abc['PARTICIPACAO'].cumsum()
    
    fig_abc = px.bar(df_abc.head(10), x='C Custo', y='Nº Solicitação (SC)', 
                     title="Top 10 Centros de Custo por Volume", text_auto=True)
    st.plotly_chart(fig_abc, use_container_width=True)
    st.dataframe(df_abc, use_container_width=True)

# --- SEÇÃO 3: GESTÃO DE PENDÊNCIAS ---
elif secao == "Pendências":
    st.title("⚠️ Solicitações Pendentes (Prioridade Alta)")
    
    pendentes = df[df['STATUS_CLEAN'] == 'PENDENTE'].sort_values(by='SLA', ascending=False)
    
    # Tabela com formatação condicional simples
    st.dataframe(pendentes[['Nº Solicitação (SC)', 'Descricao', 'SLA', 'C Custo', 'Comprador']], 
                 use_container_width=True)

    if st.button("Atualizar Dados"):
        st.rerun()
