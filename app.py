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
    
    # Tratamentos de Colunas
    df['STATUS_CLEAN'] = df['STATUS'].astype(str).str.strip().str.upper()
    df['SLA'] = pd.to_numeric(df['SLA'], errors='coerce')
    df['DT EMISSAO'] = pd.to_datetime(df['DT Emissao'], errors='coerce')
    df['MES_NOME'] = df['DT EMISSAO'].dt.month_name()
    
    # Mapeamento para meses em Português
    meses_pt = {
        'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março', 'April': 'Abril',
        'May': 'Maio', 'June': 'Junho', 'July': 'Julho', 'August': 'Agosto',
        'September': 'Setembro', 'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'
    }
    df['MES_NOME'] = df['MES_NOME'].map(meses_pt)
    df['ANO'] = df['DT EMISSAO'].dt.year
    return df

df_full = carregar_dados()

# --- BARRA LATERAL ---
st.sidebar.title("Configurações")
ano_sel = st.sidebar.selectbox("Ano:", sorted(df_full['ANO'].dropna().unique()))
mes_sel = st.sidebar.selectbox("Mês:", ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'])

df_filtrado = df_full[(df_full['ANO'] == ano_sel) & (df_full['MES_NOME'] == mes_sel)]
df_unicos = df_filtrado.drop_duplicates(subset=['Nº Solicitação (SC)'])

# --- VISÃO GERAL ---
st.title(f"📊 Dashboard de Compras - {mes_sel}/{ano_sel}")

num_pedidos = df_unicos[df_unicos['Nº Pedido (PC)'].notna()]['Nº Pedido (PC)'].nunique()
sol_fechadas = df_unicos[df_unicos['STATUS_CLEAN'] == 'FINALIZADO'].shape[0]
sol_abertas = df_unicos[df_unicos['STATUS_CLEAN'] == 'PENDENTE'].shape[0]
sla_medio = round(df_unicos['SLA'].mean(), 1) if not df_unicos['SLA'].isna().all() else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Pedidos Emitidos", num_pedidos)
c2.metric("Sol. Fechadas", sol_fechadas)
c3.metric("Sol. Abertas", sol_abertas)
c4.metric("SLA Médio (Dias)", sla_medio)

st.divider()

# Gráfico de Status
fig = px.pie(df_unicos, names='STATUS_CLEAN', title="Distribuição de Status das Solicitações")
st.plotly_chart(fig, use_container_width=True)

# --- TABS ---
tab1, tab2 = st.tabs(["📦 Curva ABC (Centros de Custo)", "⚠️ Gestão de Pendências"])

with tab1:
    st.subheader("Top 10 Centros de Custo")
    df_cc = df_unicos.groupby('C Custo')['Nº Solicitação (SC)'].nunique().sort_values(ascending=False).head(10)
    st.bar_chart(df_cc)

with tab2:
    st.subheader("Solicitações em Aberto (Maiores SLAs)")
    pendentes = df_unicos[df_unicos['STATUS_CLEAN'] == 'PENDENTE'].sort_values(by='SLA', ascending=False)
    # Renomeando colunas para exibição amigável
    display_df = pendentes.rename(columns={'Nº Solicitação (SC)': 'Número SC', 'Descricao': 'Descrição', 'C Custo': 'Centro de Custo'})
    st.dataframe(display_df[['Número SC', 'Descrição', 'SLA', 'Centro de Custo', 'Comprador']], use_container_width=True)
