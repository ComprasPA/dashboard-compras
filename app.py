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

# Mapeamento oficial de cores
CORES_STATUS = {
    'FINALIZADO': '#28a745',  # Verde
    'ATENÇÃO': '#ffc107',     # Amarelo
    'FORA DO PRAZO': '#dc3545',# Vermelho
    'NO PRAZO': '#007bff'     # Azul
}

@st.cache_data(ttl=600)
def carregar_dados():
    response = requests.get(URL)
    response.raise_for_status()
    df = pd.read_csv(io.StringIO(response.text))
    
    # Tratamentos
    df['STATUS_CLEAN'] = df['STATUS'].astype(str).str.strip().str.upper()
    df['SLA'] = pd.to_numeric(df['SLA'], errors='coerce')
    df['DT EMISSAO'] = pd.to_datetime(df['DT Emissao'], errors='coerce')
    
    # Mapeamento de Categorias de Prazo
    def categorizar(row):
        status = row['STATUS_CLEAN']
        sla = row['SLA']
        if status == 'FINALIZADO': return 'FINALIZADO'
        if pd.isna(sla): return 'ATENÇÃO'
        if sla < 10: return 'NO PRAZO'
        if sla <= 15: return 'ATENÇÃO'
        return 'FORA DO PRAZO'
    
    df['CATEGORIA_COR'] = df.apply(categorizar, axis=1)
    
    # Configuração de data
    meses_pt = {'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março', 'April': 'Abril',
                'May': 'Maio', 'June': 'Junho', 'July': 'Julho', 'August': 'Agosto',
                'September': 'Setembro', 'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'}
    df['MES_NOME'] = df['DT EMISSAO'].dt.month_name().map(meses_pt)
    df['ANO'] = df['DT EMISSAO'].dt.year
    return df

df_full = carregar_dados()

# --- BARRA LATERAL ---
st.sidebar.header("Filtros")
ano_sel = st.sidebar.selectbox("Ano:", sorted(df_full['ANO'].dropna().unique()))
mes_sel = st.sidebar.selectbox("Mês:", ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'])

df_filtrado = df_full[(df_full['ANO'] == ano_sel) & (df_full['MES_NOME'] == mes_sel)]
df_unicos = df_filtrado.drop_duplicates(subset=['Nº Solicitação (SC)'])

# --- DASHBOARD ---
st.title(f"📊 Dashboard de Compras - {mes_sel}/{ano_sel}")

# Métricas
col1, col2, col3, col4 = st.columns(4)
col1.metric("Pedidos Emitidos", df_unicos[df_unicos['Nº Pedido (PC)'].notna()]['Nº Pedido (PC)'].nunique())
col2.metric("Sol. Fechadas", df_unicos[df_unicos['STATUS_CLEAN'] == 'FINALIZADO'].shape[0])
col3.metric("SLA Médio (Dias)", round(df_unicos['SLA'].mean(), 1))

st.divider()

# Gráfico de Pizza 3D-like com Cores Fixas
st.subheader("Distribuição de Status")
fig = px.pie(df_unicos, names='CATEGORIA_COR', 
             color='CATEGORIA_COR', 
             color_discrete_map=CORES_STATUS,
             hole=0.3)
fig.update_traces(textinfo='percent+label')
st.plotly_chart(fig, use_container_width=True)

# Pendências
st.subheader("⚠️ Solicitações em Aberto")
pendentes = df_unicos[~df_unicos['STATUS_CLEAN'].str.contains('FINALIZADO', na=False)]
st.dataframe(pendentes[['Nº Solicitação (SC)', 'Descricao', 'SLA', 'C Custo', 'Comprador']], use_container_width=True)
