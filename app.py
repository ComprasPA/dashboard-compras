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
    df.columns = df.columns.str.strip()

    def find_col(keywords):
        for col in df.columns:
            if any(k in col.upper() for k in keywords): return col
        return None

    c_pedido = find_col(['PEDIDO', 'Nº PEDIDO'])
    c_emissao = find_col(['EMISSAO', 'EMISSÃO'])
    c_qtd = find_col(['QTD', 'QUANTIDADE'])
    c_ccusto = find_col(['CUSTO'])
    c_desc = find_col(['DESC'])
    c_solic = find_col(['SOLICITAÇÃO', 'SOLICITACAO'])
    c_crit = find_col(['CRITICIDADE'])

    df['SLA'] = pd.to_numeric(df['SLA'], errors='coerce').fillna(0)
    df['DT_DT'] = pd.to_datetime(df[c_emissao], errors='coerce')
    df['IS_ABERTA'] = df[c_pedido].isna() | (df[c_pedido].astype(str).str.lower() == 'nan')
    df['Qtd_Num'] = pd.to_numeric(df[c_qtd], errors='coerce').fillna(0) if c_qtd else 0

    df['CATEGORIA_COR'] = 'ATENÇÃO'
    df.loc[~df['IS_ABERTA'], 'CATEGORIA_COR'] = 'FINALIZADO'
    df.loc[df['IS_ABERTA'] & (df['SLA'] < 10), 'CATEGORIA_COR'] = 'NO PRAZO'
    df.loc[df['IS_ABERTA'] & (df['SLA'] >= 10) & (df['SLA'] <= 15), 'CATEGORIA_COR'] = 'ATENÇÃO'
    df.loc[df['IS_ABERTA'] & (df['SLA'] > 15), 'CATEGORIA_COR'] = 'FORA DO PRAZO'

    df['ANO'] = df['DT_DT'].dt.year
    df['MES_NOME'] = df['DT_DT'].dt.month_name()
    return df, c_pedido, c_solic, c_ccusto, c_desc, c_crit

df_full, c_pedido, c_solic, c_ccusto, c_desc, c_crit = carregar_dados()

# --- FILTROS ---
st.sidebar.header("Filtros de Visão")
anos_disp = sorted(df_full['ANO'].dropna().unique())
ano_sel = st.sidebar.multiselect("Ano:", anos_disp, default=anos_disp)
meses_todos = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
mes_sel = st.sidebar.multiselect("Mês:", meses_todos, default=meses_todos)
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

c_l, c_r = st.columns(2)
with c_l:
    st.subheader("Distribuição de Status")
    status_counts = df_sc_unicas['CATEGORIA_COR'].value_counts()
    fig_p = go.Figure(data=[go.Pie(labels=status_counts.index, values=status_counts.values, marker=dict(colors=[CORES_STATUS.get(x, '#ccc') for x in status_counts.index]), hole=0.3)])
    st.plotly_chart(fig_p, use_container_width=True)

with c_r:
    st.subheader("Volume por Criticidade")
    fig_c = px.bar(df_sc_unicas.groupby(c_crit)[c_solic].nunique().reset_index(), x=c_crit, y=c_solic, text_auto=True)
    st.plotly_chart(fig_c, use_container_width=True)

st.divider()

# --- TABELAS LADO A LADO ---
col_tabela1, col_tabela2 = st.columns(2)

with col_tabela1:
    st.subheader("⚠️ Top 10 Solicitações em Aberto")
    df_top10_abertas = df_f[df_f['IS_ABERTA']].sort_values('SLA', ascending=False).drop_duplicates(subset=[c_solic]).head(10)
    st.dataframe(df_top10_abertas[[c_solic, c_desc, 'SLA', c_ccusto]], use_container_width=True)

with col_tabela2:
    st.subheader("🛒 Top 10 Itens Mais Comprados (Frequência)")
    
    df_itens = df_f.copy()
    
    # Cria uma coluna temporária em minúsculo para aplicar o filtro sem perder a formatação original
    desc_lower = df_itens[c_desc].astype(str).str.lower()
    
    # Itens a remover
    termos_excluidos = ['oleo comb diesel comum a granel', 'gasolina']
    
    # Aplica o filtro de exclusão
    filtro_exclusao = ~desc_lower.str.contains('|'.join(termos_excluidos), na=False)
    df_itens_filtrado = df_itens[filtro_exclusao]
    
    # Conta a frequência em que o item aparece na planilha
    top_itens = df_itens_filtrado[c_desc].value_counts().reset_index().head(10)
    top_itens.columns = ['Item/Descrição', 'Vezes Solicitado']
    
    st.dataframe(top_itens, use_container_width=True)
