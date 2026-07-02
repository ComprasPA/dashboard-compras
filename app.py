import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

# Configuração da Página
st.set_page_config(page_title="Dashboard Executivo", layout="wide", initial_sidebar_state="expanded")

# --- INICIALIZAÇÃO DE CHAVES DE CONTROLE DE SELEÇÃO ---
if "pizza_key" not in st.session_state: st.session_state.pizza_key = 0
if "solic_key" not in st.session_state: st.session_state.solic_key = 0
if "item_key" not in st.session_state: st.session_state.item_key = 0
if "cc_key" not in st.session_state: st.session_state.cc_key = 0

# --- FUNÇÃO DO POP-UP (MODAL) ---
@st.dialog("📋 Detalhes das Solicitações", width="large")
def abrir_modal(df_filtrado):
    st.write(f"**Total de solicitações únicas encontradas:** {len(df_filtrado)}")
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

# --- CUSTOM CSS (ESTILO DARK E CARDS NEON) ---
st.markdown("""
<style>
    .stApp { background-color: #13152a; }
    .metric-card {
        padding: 20px;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 8px rgba(0,0,0,0.4);
        margin-bottom: 20px;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .card-blue { background: linear-gradient(135deg, #0f62fe 0%, #0033a0 100%); }
    .card-green { background: linear-gradient(135deg, #00c853 0%, #009624 100%); }
    .card-pink { background: linear-gradient(135deg, #e91e63 0%, #ad1457 100%); }
    .card-purple { background: linear-gradient(135deg, #7c4dff 0%, #4527a0 100%); }
    .metric-title { font-size: 16px; font-weight: 500; margin-bottom: 10px; opacity: 0.9; }
    .metric-value { font-size: 36px; font-weight: bold; margin: 0; }
    h1, h2, h3, h4, p, label { color: #ffffff !important; }
    [data-testid="stSidebar"] { background-color: #1b1d36; }
</style>
""", unsafe_allow_html=True)

SHEET_ID = "1e7pQ512ge5XMnXxsRODEO7V48KgWo6FpKeITFqBSg1o"
SHEET_NAME = "Solicitações"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

CORES_STATUS = {'FINALIZADO': '#00c853', 'ATENÇÃO': '#ffb300', 'FORA DO PRAZO': '#e91e63', 'NO PRAZO': '#0f62fe'}

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
    c_status = find_col(['STATUS', 'SITUAÇÃO', 'SITUACAO'])

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
    
    mapa_meses = {
        'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março',
        'April': 'Abril', 'May': 'Maio', 'June': 'Junho',
        'July': 'Julho', 'August': 'Agosto', 'September': 'Setembro',
        'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'
    }
    df['MES_NOME'] = df['DT_DT'].dt.month_name().map(mapa_meses)
    
    return df, c_pedido, c_solic, c_ccusto, c_desc, c_crit, c_emissao, c_status

df_full, c_pedido, c_solic, c_ccusto, c_desc, c_crit, c_emissao, c_status = carregar_dados()
colunas_exibir = [col for col in [c_solic, c_status, c_desc, c_ccusto, c_crit, c_emissao, 'SLA'] if col is not None]

# --- FILTROS ---
st.sidebar.title("Filtros")
anos_disp = sorted(df_full['ANO'].dropna().unique())
ano_sel = st.sidebar.multiselect("Ano:", anos_disp, default=anos_disp)

meses_todos = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
mes_sel = st.sidebar.multiselect("Mês:", meses_todos, default=meses_todos)
cc_sel = st.sidebar.multiselect("Centro de Custo:", sorted(df_full[c_ccusto].dropna().unique().tolist()))

df_f = df_full.copy()
if ano_sel: df_f = df_f[df_f['ANO'].isin(ano_sel)]
if mes_sel: df_f = df_f[df_f['MES_NOME'].isin(mes_sel)]
if cc_sel: df_f = df_f[df_f[c_ccusto].isin(cc_sel)]
df_sc_unicas = df_f.drop_duplicates(subset=[c_solic])

# --- DASHBOARD ---
st.markdown("<h3>Análise Executiva de Compras</h3>", unsafe_allow_html=True)

v_pedidos = df_sc_unicas[c_pedido].nunique()
v_fechadas = df_sc_unicas[~df_sc_unicas['IS_ABERTA']].shape[0]
v_abertas = df_sc_unicas[df_sc_unicas['IS_ABERTA']].shape[0]
v_sla = round(df_sc_unicas[df_sc_unicas['IS_ABERTA']]['SLA'].mean(), 1)

col1, col2, col3, col4 = st.columns(4)
col1.markdown(f'<div class="metric-card card-blue"><div class="metric-title">Pedidos Emitidos</div><div class="metric-value">{v_pedidos}</div></div>', unsafe_allow_html=True)
col2.markdown(f'<div class="metric-card card-green"><div class="metric-title">Sol. Fechadas</div><div class="metric-value">{v_fechadas}</div></div>', unsafe_allow_html=True)
col3.markdown(f'<div class="metric-card card-pink"><div class="metric-title">Sol. Abertas</div><div class="metric-value">{v_abertas}</div></div>', unsafe_allow_html=True)
col4.markdown(f'<div class="metric-card card-purple"><div class="metric-title">SLA Médio (Abertas)</div><div class="metric-value">{v_sla} dias</div></div>', unsafe_allow_html=True)

# --- GRÁFICOS ---
c_l, c_r = st.columns(2)
dark_layout = dict(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff'), margin=dict(t=30, b=30, l=30, r=30))

with c_l:
    st.markdown("#### Distribuição de Status")
    status_counts = df_sc_unicas['CATEGORIA_COR'].value_counts()
    col_nums, col_pizza = st.columns([1, 2])
    with col_nums:
        st.write("<br>", unsafe_allow_html=True)
        if len(status_counts) > 0:
            for status, qtd in status_counts.items(): 
                st.metric(status, qtd)
                if st.button(f"🔍 Detalhes", key=f"btn_{status}"):
                    df_detalhe = df_f[df_f['CATEGORIA_COR'] == status]
                    st.session_state.df_modal = df_detalhe.drop_duplicates(subset=[c_solic])[colunas_exibir]
                    st.session_state.abrir_modal = True
                    st.rerun()
    with col_pizza:
        fig_p = go.Figure(data=[go.Pie(labels=status_counts.index, values=status_counts.values, marker=dict(colors=[CORES_STATUS.get(x, '#888') for x in status_counts.index]), textinfo='percent', textfont=dict(color='white', size=14), hole=0.4)])
        fig_p.update_layout(**dark_layout)
        st.plotly_chart(fig_p, use_container_width=True, config={'displayModeBar': False})

with c_r:
    st.markdown("#### Volume por Criticidade")
    crit_counts = df_sc_unicas.groupby(c_crit)[c_solic].nunique().reset_index()
    fig_c = px.bar(crit_counts, y=c_crit, x=c_solic, text_auto=True, orientation='h', color_discrete_sequence=['#0f62fe'])
    fig_c.update_layout(**dark_layout)
    fig_c.update_traces(textfont_size=21) 
    fig_c.update_xaxes(visible=False) 
    fig_c.update_yaxes(title="", tickfont=dict(size=16)) 
    st.plotly_chart(fig_c, use_container_width=True, config={'displayModeBar': False})

st.markdown("<hr style='border-color: #2b2b40;'>", unsafe_allow_html=True)

# --- GERENCIADOR DE MODAL CENTRALIZADO ---
if st.session_state.get("abrir_modal", False):
    abrir_modal(st.session_state.df_modal)
    st.session_state.abrir_modal = False
