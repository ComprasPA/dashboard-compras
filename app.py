import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

st.set_page_config(page_title="Dashboard Executivo", layout="wide")

SHEET_ID = "1e7pQ512ge5XMnXxsRODEO7V48KgWo6FpKeITFqBSg1o"
SHEET_NAME = "Solicitações"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

CORES_STATUS = {'FINALIZADO': '#28a745', 'ATENÇÃO': '#ffc107', 'FORA DO PRAZO': '#dc3545', 'NO PRAZO': '#007bff'}

@st.cache_data(ttl=600)
def carregar_dados():
    response = requests.get(URL)
    response.raise_for_status()
    df = pd.read_csv(io.StringIO(response.text))
    
    # 1. Limpeza rigorosa: remove espaços e coloca em maiúsculo para busca fácil
    df.columns = df.columns.str.strip()
    
    # Dicionário de equivalência para encontrar as colunas independentemente do nome exato
    def get_col(lista_possiveis):
        for col in df.columns:
            if any(p in col.upper() for p in lista_possiveis):
                return col
        return None

    # Mapeamento dinâmico
    c_emissao = get_col(['DATA', 'EMISSAO'])
    c_pedido = get_col(['Nº PEDIDO', 'PEDIDO (PC)'])
    c_solic = get_col(['Nº SOLICITAÇÃO', 'SOLICITAÇÃO (SC)'])
    c_ccusto = get_col(['C CUSTO', 'CENTRO DE CUSTO'])
    c_forn = get_col(['FORNECEDOR'])
    c_desc = get_col(['DESCRICAO', 'DESCRIÇÃO'])
    c_crit = get_col(['CRITICIDADE'])

    df['SLA'] = pd.to_numeric(df['SLA'], errors='coerce').fillna(0)
    df['DT EMISSAO'] = pd.to_datetime(df[c_emissao], errors='coerce')
    df['IS_ABERTA'] = df[c_pedido].isna() | (df[c_pedido].astype(str).str.lower() == 'nan')
    
    # Lógica de Categorização
    df['CATEGORIA_COR'] = 'ATENÇÃO'
    df.loc[~df['IS_ABERTA'], 'CATEGORIA_COR'] = 'FINALIZADO'
    df.loc[df['IS_ABERTA'] & (df['SLA'] < 10), 'CATEGORIA_COR'] = 'NO PRAZO'
    df.loc[df['IS_ABERTA'] & (df['SLA'] >= 10) & (df['SLA'] <= 15), 'CATEGORIA_COR'] = 'ATENÇÃO'
    df.loc[df['IS_ABERTA'] & (df['SLA'] > 15), 'CATEGORIA_COR'] = 'FORA DO PRAZO'
    
    df['ANO'] = df['DT EMISSAO'].dt.year
    df['MES_NOME'] = df['DT EMISSAO'].dt.month_name().map({
        'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março', 'April': 'Abril',
        'May': 'Maio', 'June': 'Junho', 'July': 'Julho', 'August': 'Agosto',
        'September': 'Setembro', 'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'
    })
    return df, c_solic, c_ccusto, c_pedido, c_forn, c_desc, c_crit

df_full, c_solic, c_ccusto, c_pedido, c_forn, c_desc, c_crit = carregar_dados()

# --- FILTROS ---
st.sidebar.header("Filtros de Visão")
anos_disp = sorted(df_full['ANO'].dropna().unique())
ano_sel = st.sidebar.multiselect("Ano:", anos_disp, default=anos_disp)
mes_sel = st.sidebar.multiselect("Mês:", ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'], default=['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'])
cc_sel = st.sidebar.multiselect("Centro de Custo:", sorted(df_full[c_ccusto].dropna().unique().tolist()))

df_f = df_full.copy()
if ano_sel: df_f = df_f[df_f['ANO'].isin(ano_sel)]
if mes_sel: df_f = df_f[df_f['MES_NOME'].isin(mes_sel)]
if cc_sel: df_f = df_f[df_f[c_ccusto].isin(cc_sel)]

df_sc_unicas = df_f.drop_duplicates(subset=[c_solic])

# --- DASHBOARD ---
st.title("📊 Dashboard Executivo de Compras")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Pedidos Emitidos", df_sc_unicas[c_pedido].nunique())
col2.metric("Sol. Fechadas", df_sc_unicas[~df_sc_unicas['IS_ABERTA']].shape[0])
col3.metric("Sol. Abertas", df_sc_unicas[df_sc_unicas['IS_ABERTA']].shape[0])
col4.metric("SLA Médio (Abertas)", round(df_sc_unicas[df_sc_unicas['IS_ABERTA']]['SLA'].mean(), 1))

st.divider()

col_l, col_r = st.columns(2)
with col_l:
    st.subheader("Distribuição de Status")
    status_counts = df_sc_unicas['CATEGORIA_COR'].value_counts()
    fig_p = go.Figure(data=[go.Pie(labels=status_counts.index, values=status_counts.values, marker=dict(colors=[CORES_STATUS.get(x, '#ccc') for x in status_counts.index]), textinfo='percent+label', hole=0.3)])
    st.plotly_chart(fig_p, use_container_width=True)

with col_r:
    st.subheader("Volume por Criticidade")
    crit_counts = df_sc_unicas.groupby(c_crit)[c_solic].nunique()
    fig_c = px.bar(crit_counts.reset_index(), x=c_crit, y=c_solic, text_auto=True)
    st.plotly_chart(fig_c, use_container_width=True)

st.divider()
st.subheader("⚠️ Top 10 Solicitações em Aberto")
st.dataframe(df_full[df_full['IS_ABERTA']].sort_values('SLA', ascending=False).drop_duplicates(subset=[c_solic]).head(10)[[c_solic, c_desc, 'SLA', c_ccusto, c_forn]], use_container_width=True)

# --- RANKINGS ---
col_rank1, col_rank2 = st.columns(2)
with col_rank1:
    st.subheader("🏆 Top 10 Fornecedores")
    df_ped = df_f[df_f[c_pedido].notna()].drop_duplicates(subset=[c_pedido])
    top_f = df_ped[c_forn].value_counts().head(10).reset_index()
    st.dataframe(top_f, use_container_width=True)
with col_rank2:
    st.subheader("🛒 Top 10 Itens Mais Comprados")
    st.dataframe(df_f[c_desc].value_counts().head(10).reset_index(), use_container_width=True)
