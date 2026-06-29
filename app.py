import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

st.set_page_config(page_title="Dashboard Executivo", layout="wide")

SHEET_ID = "1e7pQ512ge5XMnXxsRODEO7V48KgWo6FpKeITFqBSg1o"
URL_SOL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Solicitações"
URL_PED = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Pedidos"

@st.cache_data(ttl=600)
def carregar_dados():
    df_sol = pd.read_csv(io.StringIO(requests.get(URL_SOL).text))
    df_ped = pd.read_csv(io.StringIO(requests.get(URL_PED).text))
    
    # Padronização agressiva para evitar KeyError
    df_sol.columns = df_sol.columns.str.strip().str.upper()
    df_ped.columns = df_ped.columns.str.strip().str.upper()
    
    # Identificar colunas dinamicamente
    col_pedido = next((c for c in df_sol.columns if 'PEDIDO' in c), 'PEDIDO')
    col_emissao = next((c for c in df_ped.columns if 'EMISSAO' in c), 'DATA EMISSAO')
    
    # Cruzamento para trazer dados da aba Pedidos
    df = pd.merge(df_sol, df_ped[['PEDIDO', col_emissao, 'FORNECEDOR']], left_on=col_pedido, right_on='PEDIDO', how='left')
    
    df['SLA'] = pd.to_numeric(df['SLA'], errors='coerce').fillna(0)
    df['DT EMISSAO'] = pd.to_datetime(df[col_emissao], errors='coerce')
    df['IS_ABERTA'] = df['PEDIDO'].isna()
    
    # Categorização
    df['CATEGORIA_COR'] = 'ATENÇÃO'
    df.loc[~df['IS_ABERTA'], 'CATEGORIA_COR'] = 'FINALIZADO'
    df.loc[df['IS_ABERTA'] & (df['SLA'] < 10), 'CATEGORIA_COR'] = 'NO PRAZO'
    df.loc[df['IS_ABERTA'] & (df['SLA'] >= 10) & (df['SLA'] <= 15), 'CATEGORIA_COR'] = 'ATENÇÃO'
    df.loc[df['IS_ABERTA'] & (df['SLA'] > 15), 'CATEGORIA_COR'] = 'FORA DO PRAZO'
    
    df['ANO'] = df['DT EMISSAO'].dt.year
    df['MES_NOME'] = df['DT EMISSAO'].dt.month_name()
    return df

df_full = carregar_dados()

# --- FILTROS ---
st.sidebar.header("Filtros")
anos_disp = sorted(df_full['ANO'].dropna().unique())
ano_sel = st.sidebar.multiselect("Ano:", anos_disp, default=anos_disp)
cc_sel = st.sidebar.multiselect("Centro de Custo:", sorted(df_full['CENTRO DE CUSTO'].dropna().unique().tolist()))

df_f = df_full.copy()
if ano_sel: df_f = df_f[df_f['ANO'].isin(ano_sel)]
if cc_sel: df_f = df_f[df_f['CENTRO DE CUSTO'].isin(cc_sel)]

# --- DASHBOARD ---
st.title("📊 Dashboard Executivo de Compras")

col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Distribuição de Status")
    status_counts = df_f['CATEGORIA_COR'].value_counts()
    fig_p = go.Figure(data=[go.Pie(labels=status_counts.index, values=status_counts.values, hole=0.3)])
    st.plotly_chart(fig_p, use_container_width=True)

with col_r:
    st.subheader("Volume por Criticidade")
    fig_c = px.bar(df_f.groupby('CRITICIDADE')['SOLICITAÇÃO'].nunique().reset_index(), x='CRITICIDADE', y='SOLICITAÇÃO')
    st.plotly_chart(fig_c, use_container_width=True)

st.divider()

col_bl, col_br = st.columns(2)
with col_bl:
    st.subheader("⚠️ Top 10 Solicitações em Aberto")
    st.dataframe(df_f[df_f['IS_ABERTA']].sort_values('SLA', ascending=False).head(10)[['SOLICITAÇÃO', 'DESCRICAO', 'SLA', 'FORNECEDOR']])

with col_br:
    st.subheader("🏆 Fornecedor Principal (Volume)")
    top_f = df_f[df_f['PEDIDO'].notna()]['FORNECEDOR'].value_counts().head(1)
    if not top_f.empty:
        st.metric(f"Fornecedor: {top_f.index[0]}", f"{top_f.values[0]} pedidos")
    
    st.subheader("🛒 Top 10 Itens Mais Comprados")
    st.dataframe(df_f['DESCRICAO'].value_counts().head(10))
