import streamlit as st
import pandas as pd
import plotly.graph_objects as go # Usando graph_objects para 3D real
import requests
import io

st.set_page_config(page_title="Dashboard de Compras", layout="wide")

SHEET_ID = "1e7pQ512ge5XMnXxsRODEO7V48KgWo6FpKeITFqBSg1o"
SHEET_NAME = "Solicitações"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

@st.cache_data(ttl=600)
def carregar_dados():
    response = requests.get(URL)
    response.raise_for_status()
    df = pd.read_csv(io.StringIO(response.text))
    
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

# Filtros
st.sidebar.title("Configurações")
ano_sel = st.sidebar.selectbox("Ano:", sorted(df_full['ANO'].dropna().unique()))
mes_sel = st.sidebar.selectbox("Mês:", ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'])

df_filtrado = df_full[(df_full['ANO'] == ano_sel) & (df_full['MES_NOME'] == mes_sel)]
df_unicos = df_filtrado.drop_duplicates(subset=['Nº Solicitação (SC)'])

st.title(f"📊 Dashboard de Compras - {mes_sel}/{ano_sel}")

# Lógica de Pendentes (DEBUG: Se não achar, mostra o que tem)
df_pendentes = df_unicos[df_unicos['STATUS_CLEAN'].str.contains('PENDENTE', na=False)]
if df_pendentes.empty:
    st.warning(f"Nenhum status 'PENDENTE' encontrado. Status disponíveis no mês: {df_unicos['STATUS_CLEAN'].unique()}")

# Métricas
col1, col2, col3, col4 = st.columns(4)
col1.metric("Pedidos Emitidos", df_unicos[df_unicos['Nº Pedido (PC)'].notna()]['Nº Pedido (PC)'].nunique())
col2.metric("Sol. Fechadas", df_unicos[df_unicos['STATUS_CLEAN'] == 'FINALIZADO'].shape[0])
col3.metric("Sol. Abertas", df_pendentes.shape[0])
col4.metric("SLA Médio (Dias)", round(df_unicos['SLA'].mean(), 1))

# Gráfico Pizza 3D com Percentuais
st.subheader("Distribuição de Status")
status_counts = df_unicos['STATUS_CLEAN'].value_counts()
fig = go.Figure(data=[go.Pie(labels=status_counts.index, values=status_counts.values, 
                             hole=.0, pull=[0.1, 0, 0], textinfo='percent+label')])
fig.update_layout(scene=dict(aspectmode='cube'), title_text="Proporção de Status")
st.plotly_chart(fig, use_container_width=True)

# Pendências
st.divider()
st.subheader("⚠️ Solicitações em Aberto (Prioridade Alta)")
st.dataframe(df_pendentes[['Nº Solicitação (SC)', 'Descricao', 'SLA', 'C Custo', 'Comprador']], use_container_width=True)
