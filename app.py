import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

st.set_page_config(page_title="Dashboard Executivo", layout="wide")

SHEET_ID = "1e7pQ512ge5XMnXxsRODEO7V48KgWo6FpKeITFqBSg1o"

@st.cache_data(ttl=600)
def carregar_dados():
    # Carrega ambas as abas
    url_sol = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Solicitações"
    url_ped = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Pedidos"
    
    df_sol = pd.read_csv(io.StringIO(requests.get(url_sol).text))
    df_ped = pd.read_csv(io.StringIO(requests.get(url_ped).text))
    
    df_sol.columns = df_sol.columns.str.strip()
    df_ped.columns = df_ped.columns.str.strip()
    
    # Faz o merge: Traz o 'Fornecedor' da aba Pedidos para as Solicitações usando o número do pedido
    df = pd.merge(df_sol, df_ped[['Pedido', 'Fornecedor']], on='Pedido', how='left')
    
    # Tratamentos
    df['SLA'] = pd.to_numeric(df['SLA'], errors='coerce').fillna(0)
    df['DT EMISSAO'] = pd.to_datetime(df['DT Emissao'], errors='coerce')
    df['IS_ABERTA'] = df['Pedido'].isna()
    
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
ano_sel = st.sidebar.multiselect("Ano:", sorted(df_full['ANO'].dropna().unique()), default=df_full['ANO'].dropna().unique())
cc_sel = st.sidebar.multiselect("Centro de Custo:", sorted(df_full['C Custo'].dropna().unique().tolist()))

df_f = df_full.copy()
if ano_sel: df_f = df_f[df_f['ANO'].isin(ano_sel)]
if cc_sel: df_f = df_f[df_f['C Custo'].isin(cc_sel)]
df_sc_unicas = df_f.drop_duplicates(subset=['Nº Solicitação (SC)'])

# --- DASHBOARD ---
st.title("📊 Dashboard Executivo")

# Gráficos
col1, col2 = st.columns(2)
with col1:
    st.subheader("Distribuição de Status")
    status_counts = df_sc_unicas['CATEGORIA_COR'].value_counts()
    fig = go.Figure(data=[go.Pie(labels=status_counts.index, values=status_counts.values, hole=0.3)])
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Volume por Criticidade")
    fig = px.bar(df_sc_unicas.groupby('Criticidade')['Nº Solicitação (SC)'].nunique().reset_index(), x='Criticidade', y='Nº Solicitação (SC)', text_auto=True)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# Rankings
col_rank1, col_rank2 = st.columns(2)
with col_rank1:
    st.subheader("🏆 Top 10 Fornecedores (Pedidos)")
    # O merge lá em cima garante que 'Fornecedor' exista aqui!
    if 'Fornecedor' in df_f.columns:
        df_ped_unicos = df_f[df_f['Pedido'].notna()].drop_duplicates(subset=['Pedido'])
        st.dataframe(df_ped_unicos['Fornecedor'].value_counts().head(10).reset_index(), use_container_width=True)
    else:
        st.error("Coluna 'Fornecedor' não encontrada após o merge.")

with col_rank2:
    st.subheader("🛒 Top 10 Itens Mais Comprados")
    st.dataframe(df_f['Descricao'].value_counts().head(10).reset_index(), use_container_width=True)
