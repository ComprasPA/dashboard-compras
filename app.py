import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

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
    
    # TRATAMENTO ROBUSTO DOS DADOS
    df['STATUS_CLEAN'] = df['STATUS'].astype(str).str.strip().str.upper()
    # Garantir que SLA seja tratado como número real
    df['SLA'] = pd.to_numeric(df['SLA'], errors='coerce').fillna(0)
    df['DT EMISSAO'] = pd.to_datetime(df['DT Emissao'], errors='coerce')
    
    # ABERTA = SEM NÚMERO DE PEDIDO (PC)
    df['IS_ABERTA'] = df['Nº Pedido (PC)'].isna() | (df['Nº Pedido (PC)'].astype(str).str.strip() == '')
    
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

# --- BARRA LATERAL ---
st.sidebar.header("Filtros Dinâmicos")
anos_disp = sorted(df_full['ANO'].dropna().unique())
ano_sel = st.sidebar.multiselect("Ano:", anos_disp, default=anos_disp)
cc_sel = st.sidebar.multiselect("Centro de Custo:", sorted(df_full['C Custo'].dropna().unique().tolist()))

df_f = df_full.copy()
if ano_sel: df_f = df_f[df_f['ANO'].isin(ano_sel)]
if cc_sel: df_f = df_f[df_f['C Custo'].isin(cc_sel)]

# --- DASHBOARD ---
st.title("📊 Dashboard Executivo de Compras")

# Métricas (Considerando apenas o que é único por SC)
df_sc_unicas = df_f.drop_duplicates(subset=['Nº Solicitação (SC)'])
col1, col2, col3, col4 = st.columns(4)
col1.metric("Pedidos Emitidos", df_sc_unicas['Nº Pedido (PC)'].dropna().nunique())
col2.metric("Sol. Fechadas", df_sc_unicas[~df_sc_unicas['IS_ABERTA']].shape[0])
col3.metric("Sol. Abertas", df_sc_unicas[df_sc_unicas['IS_ABERTA']].shape[0])
col4.metric("SLA Médio (Abertas)", round(df_sc_unicas[df_sc_unicas['IS_ABERTA']]['SLA'].mean(), 1))

st.divider()

# Top 10 ABERTAS (Lógica Corrigida: Agrupando por SC para pegar o valor real máximo)
st.subheader("⚠️ Top 10 Solicitações em Aberto (Maiores SLAs)")

# Filtra apenas abertas, agrupa por SC, pega o SLA máximo e ordena
df_top10 = df_f[df_f['IS_ABERTA']].groupby(['Nº Solicitação (SC)', 'Descricao', 'C Custo', 'Comprador'])['SLA'].max().reset_index()
df_top10 = df_top10.sort_values(by='SLA', ascending=False).head(10)

# Exibe
if not df_top10.empty:
    st.dataframe(df_top10, use_container_width=True)
else:
    st.info("Nenhuma solicitação em aberto encontrada.")
