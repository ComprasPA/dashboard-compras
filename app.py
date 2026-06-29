import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

# Configuração da página
st.set_page_config(page_title="Dashboard de Compras", layout="wide")

# Configuração da planilha
SHEET_ID = "1e7pQ512ge5XMnXxsRODEO7V48KgWo6FpKeITFqBSg1o"
SHEET_NAME = "Solicitações"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

# Mapeamento de cores
CORES_STATUS = {
    'FINALIZADO': '#28a745', 'ATENÇÃO': '#ffc107',
    'FORA DO PRAZO': '#dc3545', 'NO PRAZO': '#007bff'
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
    
    def categorizar(row):
        status = row['STATUS_CLEAN']
        sla = row['SLA']
        if status == 'FINALIZADO': return 'FINALIZADO'
        if pd.isna(sla): return 'ATENÇÃO'
        if sla < 10: return 'NO PRAZO'
        if sla <= 15: return 'ATENÇÃO'
        return 'FORA DO PRAZO'
    
    df['CATEGORIA_COR'] = df.apply(categorizar, axis=1)
    df['MES_NOME'] = df['DT EMISSAO'].dt.month_name().map({
        'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março', 'April': 'Abril',
        'May': 'Maio', 'June': 'Junho', 'July': 'Julho', 'August': 'Agosto',
        'September': 'Setembro', 'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'
    })
    df['ANO'] = df['DT EMISSAO'].dt.year
    return df

df_full = carregar_dados()

# --- BARRA LATERAL ---
st.sidebar.header("Filtros Dinâmicos")
ano_sel = st.sidebar.multiselect("Ano:", sorted(df_full['ANO'].dropna().unique()), default=sorted(df_full['ANO'].dropna().unique()))
mes_sel = st.sidebar.multiselect("Mês:", ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'], default=['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'])
cc_sel = st.sidebar.multiselect("Centro de Custo:", sorted(df_full['C Custo'].dropna().unique().tolist()))
status_sel = st.sidebar.multiselect("Status:", list(CORES_STATUS.keys()))

# Aplicação dos Filtros
df_filtrado = df_full.copy()
if ano_sel: df_filtrado = df_filtrado[df_filtrado['ANO'].isin(ano_sel)]
if mes_sel: df_filtrado = df_filtrado[df_filtrado['MES_NOME'].isin(mes_sel)]
if cc_sel: df_filtrado = df_filtrado[df_filtrado['C Custo'].isin(cc_sel)]
if status_sel: df_filtrado = df_filtrado[df_filtrado['CATEGORIA_COR'].isin(status_sel)]

df_unicos = df_filtrado.drop_duplicates(subset=['Nº Solicitação (SC)'])

# --- DASHBOARD ---
st.title("📊 Dashboard Executivo de Compras")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Pedidos Emitidos", df_unicos[df_unicos['Nº Pedido (PC)'].notna()]['Nº Pedido (PC)'].nunique())
col2.metric("Sol. Fechadas", df_unicos[df_unicos['STATUS_CLEAN'] == 'FINALIZADO'].shape[0])
col3.metric("Sol. Abertas", df_unicos[~df_unicos['STATUS_CLEAN'].str.contains('FINALIZADO', na=False)].shape[0])
col4.metric("SLA Médio (Dias)", round(df_unicos['SLA'].mean(), 1))

st.divider()

c_left, c_right = st.columns(2)
with c_left:
    st.subheader("Distribuição de Status")
    status_counts = df_unicos['CATEGORIA_COR'].value_counts()
    fig_pizza = go.Figure(data=[go.Pie(labels=status_counts.index, values=status_counts.values, 
                                       marker=dict(colors=[CORES_STATUS.get(x, '#ccc') for x in status_counts.index]),
                                       textinfo='percent+label', hole=0.3)])
    st.plotly_chart(fig_pizza, use_container_width=True)

with c_right:
    st.subheader("Volume por Criticidade")
    fig_crit = px.bar(df_unicos.groupby('Criticidade')['Nº Solicitação (SC)'].nunique().reset_index(), 
                      x='Criticidade', y='Nº Solicitação (SC)', text_auto=True)
    st.plotly_chart(fig_crit, use_container_width=True)

# Top 10 SLA ABERTAS (Corrigido para evitar duplicidade)
st.divider()
st.subheader("⚠️ Top 10 Solicitações em Aberto (Maiores SLAs)")

# Agrupa por SC pegando o SLA máximo para garantir exclusividade e valor real
df_top10 = df_unicos[~df_unicos['STATUS_CLEAN'].str.contains('FINALIZADO', na=False)].copy()
df_top10 = df_top10.groupby(['Nº Solicitação (SC)', 'Descricao', 'C Custo', 'Comprador'])['SLA'].max().reset_index()
df_top10 = df_top10.sort_values(by='SLA', ascending=False).head(10)

st.dataframe(df_top10, use_container_width=True)
