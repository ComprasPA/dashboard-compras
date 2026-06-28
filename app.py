import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Dashboard de Compras", layout="wide")

# Função de carregamento com cache
@st.cache_data
def carregar_dados():
    df = pd.read_excel('data/FOLLOW UP - COMPRAS 2026.xlsx', sheet_name='Solicitações')
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

# Sidebar
st.sidebar.title("Navegação")
secao = st.sidebar.radio("Seções:", ["Visão Geral", "Curva ABC", "Pendências"])

if secao == "Visão Geral":
    st.title("📊 Performance Mensal")
    
    # Gráfico de barras empilhadas por mês
    df_mes = df.groupby(['MES', 'CATEGORIA_PRAZO']).size().reset_index(name='Qtd')
    fig_mes = px.bar(df_mes, x='MES', y='Qtd', color='CATEGORIA_PRAZO', title="Volume de Solicitações por Status/Mês")
    st.plotly_chart(fig_mes, use_container_width=True)

elif secao == "Curva ABC":
    st.title("📦 Curva ABC - Centros de Custo")
    
    df_abc = df.groupby('C Custo')['Nº Solicitação (SC)'].nunique().sort_values(ascending=False).reset_index()
    df_abc['PARTICIPACAO'] = df_abc['Nº Solicitação (SC)'] / df_abc['Nº Solicitação (SC)'].sum()
    df_abc['ACUMULADO'] = df_abc['PARTICIPACAO'].cumsum()
    
    fig_abc = px.bar(df_abc.head(10), x='C Custo', y='Nº Solicitação (SC)', title="Top 10 Centros de Custo (Volume)")
    st.plotly_chart(fig_abc, use_container_width=True)
    st.dataframe(df_abc.head(10), use_container_width=True)

elif secao == "Pendências":
    st.title("⚠️ Gestão de Pendências")
    # Filtrando pendentes (Ajuste o nome do status se necessário conforme o seu arquivo)
    pendentes = df[df['STATUS_CLEAN'] == 'PENDENTE'].sort_values(by='SLA', ascending=False)
    st.dataframe(pendentes[['Nº Solicitação (SC)', 'Descricao', 'SLA', 'C Custo']], use_container_width=True)
