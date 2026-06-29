import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# Configuração da página para estilo Dashboard
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
    
    # Padronização e Tratamento
    df['STATUS_CLEAN'] = df['STATUS'].astype(str).str.strip().str.upper()
    df['SLA'] = pd.to_numeric(df['SLA'], errors='coerce')
    df['DT EMISSAO'] = pd.to_datetime(df['DT Emissao'], errors='coerce')
    df['MES_NOME'] = df['DT EMISSAO'].dt.month_name()
    
    meses_pt = {'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março', 'April': 'Abril',
                'May': 'Maio', 'June': 'Junho', 'July': 'Julho', 'August': 'Agosto',
                'September': 'Setembro', 'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'}
    df['MES_NOME'] = df['MES_NOME'].map(meses_pt)
    df['ANO'] = df['DT EMISSAO'].dt.year
    return df

df_full = carregar_dados()

# --- SIDEBAR: Filtros Power BI Style ---
st.sidebar.header("Filtros")
ano_sel = st.sidebar.selectbox("Ano:", sorted(df_full['ANO'].dropna().unique()))
mes_sel = st.sidebar.selectbox("Mês:", ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'])

df_filtrado = df_full[(df_full['ANO'] == ano_sel) & (df_full['MES_NOME'] == mes_sel)]
df_unicos = df_filtrado.drop_duplicates(subset=['Nº Solicitação (SC)'])

# --- ÁREA PRINCIPAL ---
st.title(f"📊 Dashboard de Compras - {mes_sel}/{ano_sel}")

# Métricas (Cards)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Pedidos Emitidos", df_unicos[df_unicos['Nº Pedido (PC)'].notna()]['Nº Pedido (PC)'].nunique())
c2.metric("Sol. Fechadas", df_unicos[df_unicos['STATUS_CLEAN'] == 'FINALIZADO'].shape[0])
c3.metric("Sol. Abertas", df_unicos[df_unicos['STATUS_CLEAN'].str.contains('PENDENTE', na=False)].shape[0])
c4.metric("SLA Médio (Dias)", round(df_unicos['SLA'].mean(), 1))

st.divider()

# Gráfico estilo BI (Interativo)
col_l, col_r = st.columns(2)

with col_l:
    # Gráfico de Pizza Interativo (com hover e zoom)
    fig = px.pie(df_unicos, names='STATUS_CLEAN', title="Distribuição de Status (Clique para filtrar)", 
                 hole=0.3, color_discrete_sequence=px.colors.sequential.RdBu)
    fig.update_traces(textinfo='percent+label', pull=[0.05]*10)
    st.plotly_chart(fig, use_container_width=True)

with col_r:
    # Gráfico de barras horizontal para Curva ABC
    fig_abc = px.bar(df_unicos.groupby('C Custo')['Nº Solicitação (SC)'].nunique().sort_values(ascending=True).tail(10).reset_index(),
                     x='Nº Solicitação (SC)', y='C Custo', orientation='h', title="Top 10 Centros de Custo")
    st.plotly_chart(fig_abc, use_container_width=True)

# Pendências com busca dinâmica
st.subheader("⚠️ Solicitações em Aberto")
df_pendentes = df_unicos[df_unicos['STATUS_CLEAN'].str.contains('PENDENTE', na=False)]
if not df_pendentes.empty:
    st.dataframe(df_pendentes[['Nº Solicitação (SC)', 'Descricao', 'SLA', 'C Custo', 'Comprador']], use_container_width=True)
else:
    st.info("Nenhuma solicitação pendente encontrada para este período.")
