import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

# Configuração da página
st.set_page_config(page_title="Dashboard de Compras", layout="wide")

SHEET_ID = "1e7pQ512ge5XMnXxsRODEO7V48KgWo6FpKeITFqBSg1o"
SHEET_NAME = "Solicitações"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

CORES_STATUS = {
    'FINALIZADO': '#28a745', 'ATENÇÃO': '#ffc107',
    'FORA DO PRAZO': '#dc3545', 'NO PRAZO': '#007bff'
}

@st.cache_data(ttl=600)
def carregar_dados():
    response = requests.get(URL)
    response.raise_for_status()
    df = pd.read_csv(io.StringIO(response.text))
    
    df['STATUS_CLEAN'] = df['STATUS'].astype(str).str.strip().str.upper()
    df['SLA'] = pd.to_numeric(df['SLA'], errors='coerce').fillna(0)
    df['DT EMISSAO'] = pd.to_datetime(df['DT Emissao'], errors='coerce')
    df['IS_ABERTA'] = df['Nº Pedido (PC)'].isna()
    
    def categorizar(row):
        if not row['IS_ABERTA']: return 'FINALIZADO'
        sla = row['SLA']
        if sla == 0: return 'ATENÇÃO'
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

# --- FILTROS ---
st.sidebar.header("Filtros Dinâmicos")
anos_disp = sorted(df_full['ANO'].dropna().unique())
ano_sel = st.sidebar.multiselect("Ano:", anos_disp, default=anos_disp)
mes_sel = st.sidebar.multiselect("Mês:", ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'], 
                                 default=['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'])
cc_sel = st.sidebar.multiselect("Centro de Custo:", sorted(df_full['C Custo'].dropna().unique().tolist()))
status_sel = st.sidebar.multiselect("Status:", list(CORES_STATUS.keys()))

df_f = df_full.copy()
if ano_sel: df_f = df_f[df_f['ANO'].isin(ano_sel)]
if mes_sel: df_f = df_f[df_f['MES_NOME'].isin(mes_sel)]
if cc_sel: df_f = df_f[df_f['C Custo'].isin(cc_sel)]
if status_sel: df_f = df_f[df_f['CATEGORIA_COR'].isin(status_sel)]

df_sc_unicas = df_f.drop_duplicates(subset=['Nº Solicitação (SC)'])

# --- DASHBOARD ---
st.title("📊 Dashboard Executivo de Compras")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Pedidos Emitidos", df_sc_unicas['Nº Pedido (PC)'].nunique())
col2.metric("Sol. Fechadas", df_sc_unicas[~df_sc_unicas['IS_ABERTA']].shape[0])
col3.metric("Sol. Abertas", df_sc_unicas[df_sc_unicas['IS_ABERTA']].shape[0])
col4.metric("SLA Médio (Dias)", round(df_sc_unicas['SLA'].mean(), 1))

st.divider()

# Gráficos
c_l, c_r = st.columns(2)
with c_l:
    st.subheader("Distribuição de Status")
    status_counts = df_sc_unicas['CATEGORIA_COR'].value_counts()
    fig_p = go.Figure(data=[go.Pie(labels=status_counts.index, values=status_counts.values, 
                                   marker=dict(colors=[CORES_STATUS.get(x, '#ccc') for x in status_counts.index]),
                                   textinfo='percent+label', hole=0.3)])
    st.plotly_chart(fig_p, use_container_width=True)
    
    # NOVAS MÉTRICAS DE QUANTIDADE ABAIXO DO GRÁFICO
    st.write("### Quantidade por Status")
    cols_status = st.columns(len(status_counts))
    for i, (status, qtd) in enumerate(status_counts.items()):
        cols_status[i].metric(status, qtd)

with c_r:
    st.subheader("Volume por Criticidade")
    fig_c = px.bar(df_sc_unicas.groupby('Criticidade')['Nº Solicitação (SC)'].nunique().reset_index(), 
                   x='Criticidade', y='Nº Solicitação (SC)', text_auto=True)
    st.plotly_chart(fig_c, use_container_width=True)

# Top 10 ABERTAS
st.divider()
st.subheader("⚠️ Top 10 Solicitações em Aberto (Maiores SLAs)")
df_top10 = df_sc_unicas[df_sc_unicas['IS_ABERTA']].sort_values(by='SLA', ascending=False).head(10)
st.dataframe(df_top10[['Nº Solicitação (SC)', 'Descricao', 'SLA', 'C Custo', 'Comprador']], use_container_width=True)
