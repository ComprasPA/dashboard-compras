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
    
    df_sol.columns = df_sol.columns.str.strip().str.upper()
    df_ped.columns = df_ped.columns.str.strip().str.upper()
    
    # Busca dinâmica robusta
    def find_col(df, terms):
        for col in df.columns:
            if any(term in col for term in terms): return col
        return None

    # Mapeamento
    col_sol = find_col(df_sol, ['SOLICITAÇÃO', 'SOLICITACAO'])
    col_desc = find_col(df_sol, ['DESCRICAO', 'DESCRIÇÃO'])
    col_cc = find_col(df_sol, ['CENTRO DE CUSTO', 'C CUSTO'])
    col_forn = find_col(df_ped, ['FORNECEDOR'])
    col_ped = find_col(df_sol, ['PEDIDO'])
    col_emiss = find_col(df_ped, ['EMISSAO', 'EMISSÃO'])
    col_crit = find_col(df_sol, ['CRITICIDADE'])

    # Merge
    df = pd.merge(df_sol, df_ped[['PEDIDO', col_emiss, 'FORNECEDOR']], left_on=col_ped, right_on='PEDIDO', how='left')
    
    df['SLA'] = pd.to_numeric(df['SLA'], errors='coerce').fillna(0)
    df['DT EMISSAO'] = pd.to_datetime(df[col_emiss], errors='coerce')
    df['IS_ABERTA'] = df[col_ped].isna()
    
    # Categorização
    df['CATEGORIA_COR'] = 'ATENÇÃO'
    df.loc[~df['IS_ABERTA'], 'CATEGORIA_COR'] = 'FINALIZADO'
    df.loc[df['IS_ABERTA'] & (df['SLA'] < 10), 'CATEGORIA_COR'] = 'NO PRAZO'
    df.loc[df['IS_ABERTA'] & (df['SLA'] >= 10) & (df['SLA'] <= 15), 'CATEGORIA_COR'] = 'ATENÇÃO'
    df.loc[df['IS_ABERTA'] & (df['SLA'] > 15), 'CATEGORIA_COR'] = 'FORA DO PRAZO'
    
    df['ANO'] = df['DT EMISSAO'].dt.year
    df['MES_NOME'] = df['DT EMISSAO'].dt.month_name()
    return df, col_sol, col_desc, col_cc, col_forn, col_ped, col_crit

df_full, c_solic, c_desc, c_cc, c_forn, c_ped, c_crit = carregar_dados()

# --- FILTROS ---
st.sidebar.header("Filtros")
ano_sel = st.sidebar.multiselect("Ano:", sorted(df_full['ANO'].dropna().unique()))
df_f = df_full.copy()
if ano_sel: df_f = df_f[df_f['ANO'].isin(ano_sel)]

# --- DASHBOARD ---
st.title("📊 Dashboard Executivo de Compras")

# --- QUADRANTE 3 (SLA) COM PROTEÇÃO ---
st.divider()
st.subheader("⚠️ Top 10 Solicitações em Aberto (SLA)")

# Lista de colunas seguras para exibir
cols_exibir = [c for c in [c_solic, c_desc, 'SLA', c_cc, c_forn] if c in df_full.columns]

if cols_exibir:
    df_top10 = df_full[df_full['IS_ABERTA']].sort_values('SLA', ascending=False).drop_duplicates(subset=[c_solic]).head(10)
    st.dataframe(df_top10[cols_exibir], use_container_width=True)
else:
    st.warning("Colunas para exibição não encontradas. Verifique a estrutura da planilha.")
    st.write("Colunas encontradas:", df_full.columns.tolist())
