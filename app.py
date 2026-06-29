import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

# Configuração da Página
st.set_page_config(page_title="Dashboard Executivo", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS (ESTILO DARK E CARDS NEON) ---
st.markdown("""
<style>
    /* Fundo da tela principal */
    .stApp {
        background-color: #13152a;
    }
    
    /* Estilo base dos Cards */
    .metric-card {
        padding: 20px;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 8px rgba(0,0,0,0.4);
        margin-bottom: 20px;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Cores dos Cards iguais à imagem */
    .card-blue { background: linear-gradient(135deg, #0f62fe 0%, #0033a0 100%); }
    .card-green { background: linear-gradient(135deg, #00c853 0%, #009624 100%); }
    .card-pink { background: linear-gradient(135deg, #e91e63 0%, #ad1457 100%); }
    .card-purple { background: linear-gradient(135deg, #7c4dff 0%, #4527a0 100%); }
    
    /* Textos dos Cards */
    .metric-title { font-size: 16px; font-weight: 500; margin-bottom: 10px; opacity: 0.9; }
    .metric-value { font-size: 36px; font-weight: bold; margin: 0; }
    
    /* Ajustes gerais de texto para branco */
    h1, h2, h3, h4, p, label { color: #ffffff !important; }
    
    /* Fundo dos painéis e sidebar */
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
st.sidebar.title("Filtros")
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

# --- DASHBOARD HEADER ---
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

dark_layout = dict(
    paper_bgcolor='rgba(0,0,0,0)', 
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(color='#ffffff'),
    margin=dict(t=30, b=30, l=30, r=30)
)

with c_l:
    st.markdown("#### Distribuição de Status")
    status_counts = df_sc_unicas['CATEGORIA_COR'].value_counts()
    
    col_nums, col_pizza = st.columns([1, 2])
    
    with col_nums:
        st.write("<br>", unsafe_allow_html=True)
        if len(status_counts) > 0:
            for status, qtd in status_counts.items(): 
                st.metric(status, qtd)
                
    with col_pizza:
        fig_p = go.Figure(data=[go.Pie(
            labels=status_counts.index, 
            values=status_counts.values, 
            marker=dict(colors=[CORES_STATUS.get(x, '#888') for x in status_counts.index]), 
            textinfo='percent', 
            textfont=dict(color='white', size=14),
            hole=0.4
        )])
        
        fig_p.update_layout(**dark_layout)
        fig_p.update_layout(showlegend=True) 
        st.plotly_chart(fig_p, use_container_width=True)

with c_r:
    st.markdown("#### Volume por Criticidade")
    crit_counts = df_sc_unicas.groupby(c_crit)[c_solic].nunique().reset_index()
    fig_c = px.bar(crit_counts, y=c_crit, x=c_solic, text_auto=True, orientation='h', color_discrete_sequence=['#0f62fe'])
    
    fig_c.update_layout(**dark_layout)
    fig_c.update_traces(textfont_size=32) 
    fig_c.update_xaxes(visible=False) 
    fig_c.update_yaxes(title="", tickfont=dict(size=24)) 
    
    st.plotly_chart(fig_c, use_container_width=True)

st.markdown("<hr style='border-color: #2b2b40;'>", unsafe_allow_html=True)

# --- GRÁFICOS QUADRANTE SUPERIOR ---
col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    st.markdown("#### ⚠️ Top 10 Solicitações em Aberto (Global)")
    df_abertas_global = df_full[df_full['IS_ABERTA']].copy()
    df_abertas_global['SLA'] = pd.to_numeric(df_abertas_global['SLA'], errors='coerce').fillna(0)
    df_top10_abertas = df_abertas_global.sort_values(by='SLA', ascending=False).drop_duplicates(subset=[c_solic]).head(10)
    
    df_top10_abertas['Solicitação_Str'] = df_top10_abertas[c_solic].astype(str)
    
    fig_top_solic = px.bar(
        df_top10_abertas, 
        x='SLA', 
        y='Solicitação_Str', 
        text='SLA', 
        orientation='h', 
        hover_data=[c_desc],
        color_discrete_sequence=['#e91e63']
    )
    
    # Reduzido para 18
    fig_top_solic.update_traces(
        textposition='inside', 
        textfont_size=18,
        hovertemplate="<b>Solicitação:</b> %{y}<br><b>SLA:</b> %{x} dias<br><b>Item:</b> %{customdata[0]}<extra></extra>"
    )
    fig_top_solic.update_layout(**dark_layout)
    fig_top_solic.update_xaxes(visible=False)
    # Eixo reduzido para 14
    fig_top_solic.update_yaxes(autorange="reversed", type='category', title="", tickfont=dict(size=14))
    
    st.plotly_chart(fig_top_solic, use_container_width=True)

with col_graf2:
    st.markdown("#### 🛒 Top 10 Itens Mais Comprados (Frequência)")
    df_itens = df_f.copy()
    desc_lower = df_itens[c_desc].astype(str).str.lower()
    
    termos_excluidos = ['oleo comb diesel comum a granel', 'gasolina', 'serviço', 'servico', 'serv']
    filtro_exclusao = ~desc_lower.str.contains('|'.join(termos_excluidos), na=False)
    
    top_itens = df_itens[filtro_exclusao][c_desc].value_counts().reset_index().head(10)
    top_itens.columns = ['Item/Descrição', 'Vezes Solicitado']
    
    fig_top_itens = px.bar(top_itens, x='Vezes Solicitado', y='Item/Descrição', text_auto=True, orientation='h', color_discrete_sequence=['#00c853'])
    fig_top_itens.update_layout(**dark_layout)
    
    # Reduzido para 18
    fig_top_itens.update_traces(textfont_size=18)
    fig_top_itens.update_xaxes(visible=False)
    # Eixo reduzido para 14
    fig_top_itens.update_yaxes(autorange="reversed", title="", tickfont=dict(size=14))
    
    st.plotly_chart(fig_top_itens, use_container_width=True)

st.markdown("<hr style='border-color: #2b2b40;'>", unsafe_allow_html=True)

# --- GRÁFICO INFERIOR ---
st.markdown("#### 🏢 Top 10 Centros de Custo (Sol. Abertas por Criticidade)")

df_cc_abertas = df_f[df_f['IS_ABERTA']].drop_duplicates(subset=[c_solic]).copy()

if not df_cc_abertas.empty:
    top_cc = df_cc_abertas.groupby([c_ccusto, c_crit])[c_solic].nunique().unstack(fill_value=0)
    top_cc['Total Geral'] = top_cc.sum(axis=1)
    top_cc = top_cc.sort_values(by='Total Geral', ascending=False).head(10).reset_index()
    
    cols_crit = [col for col in top_cc.columns if col not in [c_ccusto, 'Total Geral']]
    
    fig_top_cc = px.bar(
        top_cc, 
        y=c_ccusto, 
        x=cols_crit, 
        orientation='h', 
        text_auto=True,
        color_discrete_sequence=['#0f62fe', '#ffb300', '#e91e63']
    )
    
    fig_top_cc.update_layout(**dark_layout, barmode='stack')
    # Reduzido para 18
    fig_top_cc.update_traces(textfont_size=18, textposition="inside")
    fig_top_cc.update_xaxes(visible=False)
    # Eixo reduzido para 14
    fig_top_cc.update_yaxes(autorange="reversed", type='category', title="", tickfont=dict(size=14))
    
    st.plotly_chart(fig_top_cc, use_container_width=True)
else:
    st.write("Sem registros abertos para os filtros aplicados.")
