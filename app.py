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
    
    # 1. Limpeza automática de nomes de colunas
    df.columns = df.columns.str.strip()
    
    # 2. Mapeamento de colunas para garantir que o código encontre o que precisa
    # Se o nome na planilha for diferente, ajuste o valor à direita
    mapa = {
        'DATA EMISSAO': 'Data Emissao',
        'PEDIDO': 'Pedido',
        'SOLICITACAO': 'Solicitação',
        'CENTRO DE CUSTO': 'Centro de Custo',
        'FORNECEDOR': 'Fornecedor',
        'DESCRICAO': 'Descricao',
        'CRITICIDADE': 'Criticidade'
    }
    df.rename(columns={c: mapa.get(c.upper(), c) for c in df.columns}, inplace=True)
    
    # 3. Tratamentos
    df['SLA'] = pd.to_numeric(df['SLA'], errors='coerce').fillna(0)
    df['DT EMISSAO'] = pd.to_datetime(df['Data Emissao'], errors='coerce')
    df['IS_ABERTA'] = df['Pedido'].isna() | (df['Pedido'].astype(str).str.upper() == 'NAN') | (df['Pedido'] == 0)
    
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
    return df

df_full = carregar_dados()

# --- FILTROS ---
st.sidebar.header("Filtros de Visão")
anos_disp = sorted(df_full['ANO'].dropna().unique())
ano_sel = st.sidebar.multiselect("Ano:", anos_disp, default=anos_disp)
mes_sel = st.sidebar.multiselect("Mês:", ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'], 
                                 default=['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'])
cc_sel = st.sidebar.multiselect("Centro de Custo:", sorted(df_full['Centro de Custo'].dropna().unique().tolist()))

df_f = df_full.copy()
if ano_sel: df_f = df_f[df_f['ANO'].isin(ano_sel)]
if mes_sel: df_f = df_f[df_f['MES_NOME'].isin(mes_sel)]
if cc_sel: df_f = df_f[df_f['Centro de Custo'].isin(cc_sel)]

df_sc_unicas = df_f.drop_duplicates(subset=['Solicitação'])

# --- DASHBOARD ---
st.title("📊 Dashboard Executivo de Compras")

col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Distribuição de Status")
    status_counts = df_sc_unicas['CATEGORIA_COR'].value_counts()
    fig_p = go.Figure(data=[go.Pie(labels=status_counts.index, values=status_counts.values, 
                                   marker=dict(colors=[CORES_STATUS.get(x, '#ccc') for x in status_counts.index]),
                                   textinfo='percent+label', hole=0.3)])
    st.plotly_chart(fig_p, use_container_width=True)
    cols_s = st.columns(len(status_counts))
    for i, (status, qtd) in enumerate(status_counts.items()): cols_s[i].metric(status, qtd)

with col_r:
    st.subheader("Volume por Criticidade")
    crit_counts = df_sc_unicas.groupby('Criticidade')['Solicitação'].nunique()
    fig_c = px.bar(crit_counts.reset_index(), x='Criticidade', y='Solicitação', text_auto=True)
    st.plotly_chart(fig_c, use_container_width=True)
    cols_c = st.columns(len(crit_counts))
    for i, (crit, qtd) in enumerate(crit_counts.items()): cols_c[i].metric(str(crit), qtd)

st.divider()

col_bl, col_br = st.columns(2)

with col_bl:
    st.subheader("⚠️ Top 10 Solicitações em Aberto (SLA)")
    df_top10 = df_full[df_full['IS_ABERTA']].sort_values('SLA', ascending=False).drop_duplicates(subset=['Solicitação']).head(10)
    st.dataframe(df_top10[['Solicitação', 'Descricao', 'SLA', 'Centro de Custo', 'Fornecedor']], use_container_width=True)

with col_br:
    st.subheader("🏆 Fornecedor Principal (Volume)")
    df_ped = df_f[df_f['Pedido'].notna()].drop_duplicates(subset=['Pedido'])
    if not df_ped.empty and 'Fornecedor' in df_ped.columns:
        top_f = df_ped['Fornecedor'].value_counts().head(1)
        st.metric(f"Fornecedor: {top_f.index[0]}", f"{top_f.values[0]} pedidos")
    else:
        st.write("Dados de fornecedor indisponíveis.")
    
    st.subheader("🛒 Top 10 Itens Mais Comprados")
    top_i = df_f['Descricao'].value_counts().head(10).reset_index()
    top_i.columns = ['Item/Descrição', 'Qtd Comprada']
    st.dataframe(top_i, use_container_width=True)
