import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# Configuração da página
st.set_page_config(page_title="Dashboard de Compras", layout="wide")

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
    df['MES_NOME'] = df['DT EMISSAO'].dt.month_name()
    
    meses_pt = {
        'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março', 'April': 'Abril',
        'May': 'Maio', 'June': 'Junho', 'July': 'Julho', 'August': 'Agosto',
        'September': 'Setembro', 'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'
    }
    df['MES_NOME'] = df['MES_NOME'].map(meses_pt)
    df['ANO'] = df['DT EMISSAO'].dt.year
    return df

df_full = carregar_dados()

# Filtros
st.sidebar.title("Configurações")
ano_sel = st.sidebar.selectbox("Ano:", sorted(df_full['ANO'].dropna().unique()))
mes_sel = st.sidebar.selectbox("Mês:", ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'])

df_filtrado = df_full[(df_full['ANO'] == ano_sel) & (df_full['MES_NOME'] == mes_sel)]
df_unicos = df_filtrado.drop_duplicates(subset=['Nº Solicitação (SC)'])

# Visão Geral
st.title(f"📊 Dashboard de Compras - {mes_sel}/{ano_sel}")

# Lógica robusta para detectar Pendentes (procura por qualquer variação de "PENDENTE")
df_pendentes = df_unicos[df_unicos['STATUS_CLEAN'].str.contains('PENDENTE', na=False)]

num_pedidos = df_unicos[df_unicos['Nº Pedido (PC)'].notna()]['Nº Pedido (PC)'].nunique()
sol_fechadas = df_unicos[df_unicos['STATUS_CLEAN'] == 'FINALIZADO'].shape[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Pedidos Emitidos", num_pedidos)
c2.metric("Sol. Fechadas", sol_fechadas)
c3.metric("Sol. Abertas", df_pendentes.shape[0])
c4.metric("SLA Médio (Dias)", round(df_unicos['SLA'].mean(), 1))

st.divider()

# Gráfico 3D (O Plotly não possui Pie 3D nativo, mas usamos Sunburst para simular efeito 3D volumétrico)
st.subheader("Distribuição de Status (Visualização Volumétrica)")
fig = px.sunburst(df_unicos, path=['STATUS_CLEAN'], title="Proporção de Status")
st.plotly_chart(fig, use_container_width=True)

# Tabs
tab1, tab2 = st.tabs(["📦 Curva ABC", "🚨 Criticidade"])

with tab1:
    st.bar_chart(df_unicos.groupby('C Custo')['Nº Solicitação (SC)'].nunique().sort_values(ascending=False).head(10))

with tab2:
    st.bar_chart(df_unicos.groupby('Criticidade')['Nº Solicitação (SC)'].nunique())

# Gestão de Pendências Corrigida
st.divider()
st.subheader("⚠️ Solicitações em Aberto (Prioridade Alta)")
pendentes_exibicao = df_pendentes.sort_values(by='SLA', ascending=False)
display_df = pendentes_exibicao.rename(columns={'Nº Solicitação (SC)': 'Número SC', 'Descricao': 'Descrição', 'C Custo': 'Centro de Custo'})
st.dataframe(display_df[['Número SC', 'Descrição', 'SLA', 'Centro de Custo', 'Comprador']], use_container_width=True)
