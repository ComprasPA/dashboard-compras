import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

# Configuração da Página
st.set_page_config(page_title="Dashboard Executivo", layout="wide", initial_sidebar_state="expanded")

# --- INICIALIZAÇÃO DE CHAVES ---
if "pizza_key" not in st.session_state: st.session_state.pizza_key = 0
if "solic_key" not in st.session_state: st.session_state.solic_key = 0
if "item_key" not in st.session_state: st.session_state.item_key = 0
if "cc_key" not in st.session_state: st.session_state.cc_key = 0

@st.dialog("📋 Detalhes das Solicitações", width="large")
def abrir_modal(df_filtrado):
    st.write(f"**Total de registros encontrados:** {len(df_filtrado)}")
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

# --- CSS E URL ---
st.markdown("""<style>.stApp { background-color: #13152a; } h1,h2,h3,h4,p,label{color:white!important;}</style>""", unsafe_allow_html=True)
SHEET_ID = "1e7pQ512ge5XMnXxsRODEO7V48KgWo6FpKeITFqBSg1o"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Solicitações"

@st.cache_data(ttl=600)
def carregar_dados():
    df = pd.read_csv(io.StringIO(requests.get(URL).text))
    df.columns = df.columns.str.strip()
    # Mapeamento para garantir consistência
    cols = {c: c.upper() for c in df.columns}
    df = df.rename(columns=cols)
    
    # Identificar colunas chaves
    c_pedido = next((c for c in df.columns if 'PEDIDO' in c), df.columns[0])
    c_emissao = next((c for c in df.columns if 'EMISSA' in c), df.columns[1])
    c_solic = next((c for c in df.columns if 'SOLICITA' in c), df.columns[0])
    c_ccusto = next((c for c in df.columns if 'CUSTO' in c), df.columns[2])
    c_desc = next((c for c in df.columns if 'DESC' in c), df.columns[3])
    c_crit = next((c for c in df.columns if 'CRITIC' in c), df.columns[4])
    
    df['SLA'] = pd.to_numeric(df['SLA'], errors='coerce').fillna(0)
    df['IS_ABERTA'] = df[c_pedido].isna() | (df[c_pedido].astype(str).lower() == 'nan')
    return df, c_pedido, c_solic, c_ccusto, c_desc, c_crit, c_emissao

df_full, c_pedido, c_solic, c_ccusto, c_desc, c_crit, c_emissao = carregar_dados()

# --- FILTROS ---
st.sidebar.title("Filtros")
cc_sel = st.sidebar.multiselect("Centro de Custo:", sorted(df_full[c_ccusto].dropna().unique()))
df_f = df_full[df_full[c_ccusto].isin(cc_sel)] if cc_sel else df_full.copy()

# --- DASHBOARD ---
st.markdown("<h3>Análise Executiva de Compras</h3>", unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
col1.metric("Pedidos Emitidos", df_f[c_pedido].nunique())
col2.metric("Sol. Abertas", df_f[df_f['IS_ABERTA']].shape[0])
col3.metric("SLA Médio (Dias)", round(df_f[df_f['IS_ABERTA']]['SLA'].mean(), 1))

# --- GRÁFICOS INFERIORES ---
c_l, c_r = st.columns(2)
with c_l:
    st.markdown("#### ⚠️ Top 10 Solicitações em Aberto")
    top_abertas = df_f[df_f['IS_ABERTA']].sort_values('SLA', ascending=False).head(10)
    fig1 = px.bar(top_abertas, x='SLA', y=c_solic.astype(str), orientation='h', color_discrete_sequence=['#e91e63'])
    fig1.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
    st.plotly_chart(fig1, use_container_width=True)

with c_r:
    st.markdown("#### 🛒 Top 10 Itens Mais Comprados")
    top_itens = df_f[c_desc].value_counts().head(10).reset_index()
    fig2 = px.bar(top_itens, x='count', y=c_desc, orientation='h', color_discrete_sequence=['#00c853'])
    fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
    st.plotly_chart(fig2, use_container_width=True)

# --- GERENCIADOR DE MODAL ---
if st.session_state.get("abrir_modal", False):
    abrir_modal(st.session_state.df_modal)
    st.session_state.abrir_modal = False
