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
    st.write(f"**Total de registros encontrados:** {len(df_filtrado)}")
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
        return df.columns[0] # Retorna a primeira coluna por segurança se não achar

    # Mapeamento ultracurto para ignorar erros de acentuação/corte do Excel
    c_pedido = find_col(['PEDIDO'])
    c_emissao = find_col(['EMISSA'])
    c_qtd = find_col(['QUANTIDA', 'QTD'])
    c_ccusto = find_col(['CUSTO'])
    c_desc = find_col(['DESCRICA', 'DESC'])
    c_solic = find_col(['SOLICITA'])
    c_crit = find_col(['CRITICIDAD'])
    c_status = find_col(['STATUS', 'SITUAC'])

    # Conversões Seguras
    df['SLA'] = pd.to_numeric(df['SLA'], errors='coerce').fillna(0)
    df['DT_DT'] = pd.to_datetime(df[c_emissao], errors='coerce', dayfirst=True)
    df['Qtd_Num'] = pd.to_numeric(df[c_qtd], errors='coerce').fillna(0)
    
    # Lógica Blindada: Verifica ativamente se a célula de Pedido está vazia ou cheia de lixo digital
    s_pedido = df[c_pedido].astype(str).str.strip().str.upper()
    df['IS_ABERTA'] = s_pedido.isin(['NAN', 'NONE', 'NULL', '', '0', '-', '<NA>'])

    df['CATEGORIA_COR'] = 'ATENÇÃO'
    df.loc[~df['IS_ABERTA'], 'CATEGORIA_COR'] = 'FINALIZADO'
    df.loc[df['IS_ABERTA'] & (df['SLA'] < 10), 'CATEGORIA_COR'] = 'NO PRAZO'
    df.loc[df['IS_ABERTA'] & (df['SLA'] >= 10) & (df['SLA'] <= 15), 'CATEGORIA_COR'] = 'ATENÇÃO'
    df.loc[df['IS_ABERTA'] & (df['SLA'] > 15), 'CATEGORIA_COR'] = 'FORA DO PRAZO'

    df['ANO'] = df['DT_DT'].dt.year.fillna(0).astype(int)
    
    mapa_meses = {
        'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março',
        'April': 'Abril', 'May': 'Maio', 'June': 'Junho',
        'July': 'Julho', 'August': 'Agosto', 'September': 'Setembro',
        'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'
    }
    df['MES_NOME'] = df['DT_DT'].dt.month_name().map(mapa_meses).fillna('Sem Data')
    
    return df, c_pedido, c_solic, c_ccusto, c_desc, c_crit, c_emissao, c_status

df_full, c_pedido, c_solic, c_ccusto, c_desc, c_crit, c_emissao, c_status = carregar_dados()
colunas_exibir = [col for col in [c_solic, c_status, c_desc, c_ccusto, c_crit, c_emissao, 'SLA'] if col is not None]

# --- FILTROS ---
st.sidebar.title("Filtros")
anos_disp = sorted(df_full[df_full['ANO'] > 0]['ANO'].unique())
ano_sel = st.sidebar.multiselect("Ano:", anos_disp, default=anos_disp)

meses_todos = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro', 'Sem Data']
mes_sel = st.sidebar.multiselect("Mês:", meses_todos, default=meses_todos)
cc_sel = st.sidebar.multiselect("Centro de Custo:", sorted(df_full[c_ccusto].dropna().astype(str).unique().tolist()))

df_f = df_full.copy()
if ano_sel: df_f = df_f[df_f['ANO'].isin(ano_sel)]
if mes_sel: df_f = df_f[df_f['MES_NOME'].isin(mes_sel)]
if cc_sel: df_f = df_f[df_f[c_ccusto].isin(cc_sel)]
df_sc_unicas = df_f.drop_duplicates(subset=[c_solic])

# --- DASHBOARD ---
st.markdown("<h3>Análise Executiva de Compras</h3>", unsafe_allow_html=True)

# Cálculo seguro de pedidos
pedidos_unicos = df_sc_unicas[c_pedido].astype(str).str.strip().str.upper()
v_pedidos = pedidos_unicos[~pedidos_unicos.isin(['NAN', 'NONE', 'NULL', '', '0', '-', '<NA>'])].nunique()

v_fechadas = df_sc_unicas[~df_sc_unicas['IS_ABERTA']].shape[0]
v_abertas = df_sc_unicas[df_sc_unicas['IS_ABERTA']].shape[0]
v_sla = round(df_sc_unicas[df_sc_unicas['IS_ABERTA']]['SLA'].mean(), 1) if v_abertas > 0 else 0

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

# --- QUADRANTE SUPERIOR ---
col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    st.markdown("#### ⚠️ Top 10 Solicitações em Aberto (Global)")
    df_abertas_global = df_full[df_full['IS_ABERTA']].copy()
    if not df_abertas_global.empty:
        df_abertas_global['SLA'] = pd.to_numeric(df_abertas_global['SLA'], errors='coerce').fillna(0)
        df_top10_abertas = df_abertas_global.sort_values(by='SLA', ascending=False).drop_duplicates(subset=[c_solic]).head(10)
        df_top10_abertas['Solicitação_Str'] = df_top10_abertas[c_solic].astype(str)
        
        fig_top_solic = px.bar(df_top10_abertas, x='SLA', y='Solicitação_Str', text='SLA', orientation='h', hover_data=[c_desc], color_discrete_sequence=['#e91e63'])
        fig_top_solic.update_traces(textposition='inside', textfont_size=18, hovertemplate="<b>Solicitação:</b> %{y}<br><b>SLA:</b> %{x} dias<br><b>Item:</b> %{customdata[0]}<extra></extra>")
        fig_top_solic.update_layout(**dark_layout)
        fig_top_solic.update_xaxes(visible=False)
        fig_top_solic.update_yaxes(autorange="reversed", type='category', title="", tickfont=dict(size=14))
        
        evento_solic = st.plotly_chart(fig_top_solic, use_container_width=True, on_select="rerun", config={'displayModeBar': False}, key=f"solic_{st.session_state.solic_key}")
        if evento_solic and len(evento_solic.selection.get("points", [])) > 0:
            id_clicado = str(evento_solic.selection["points"][0]["y"]).strip()
            df_detalhe = df_full[df_full[c_solic].astype(str).str.strip() == id_clicado]
            st.session_state.df_modal = df_detalhe.drop_duplicates(subset=[c_solic])[colunas_exibir]
            st.session_state.abrir_modal = True
            st.session_state.solic_key += 1
            st.rerun()

with col_graf2:
    st.markdown("#### 🛒 Top 10 Itens Mais Comprados (Frequência)")
    df_itens = df_f.copy()
    if not df_itens.empty:
        desc_lower = df_itens[c_desc].astype(str).str.lower()
        termos_excluidos = ['oleo comb diesel comum a granel', 'gasolina', 'serviço', 'servico', 'serv']
        filtro_exclusao = ~desc_lower.str.contains('|'.join(termos_excluidos), na=False)
        
        top_itens = df_itens[filtro_exclusao][c_desc].value_counts().reset_index().head(10)
        top_itens.columns = ['Item/Descrição', 'Vezes Solicitado']
        
        fig_top_itens = px.bar(top_itens, x='Vezes Solicitado', y='Item/Descrição', text_auto=True, orientation='h', color_discrete_sequence=['#00c853'])
        fig_top_itens.update_layout(**dark_layout)
        fig_top_itens.update_traces(textfont_size=18)
        fig_top_itens.update_xaxes(visible=False)
        fig_top_itens.update_yaxes(autorange="reversed", title="", tickfont=dict(size=14))
        
        evento_item = st.plotly_chart(fig_top_itens, use_container_width=True, on_select="rerun", config={'displayModeBar': False}, key=f"item_{st.session_state.item_key}")
        if evento_item and len(evento_item.selection.get("points", [])) > 0:
            nome_item_clicado = str(evento_item.selection["points"][0]["y"]).strip()
            df_detalhe = df_f[df_f[c_desc].astype(str).str.strip() == nome_item_clicado]
            st.session_state.df_modal = df_detalhe.drop_duplicates(subset=[c_solic])[colunas_exibir]
            st.session_state.abrir_modal = True
            st.session_state.item_key += 1
            st.rerun()

st.markdown("<hr style='border-color: #2b2b40;'>", unsafe_allow_html=True)

# --- GRÁFICO INFERIOR ---
st.markdown("#### 🏢 Top 10 Centros de Custo (Sol. Abertas por Criticidade)")
df_cc_abertas = df_f[df_f['IS_ABERTA']].copy()
if not df_cc_abertas.empty:
    df_unicas_cc = df_cc_abertas.drop_duplicates(subset=[c_solic])
    totais_cc = df_unicas_cc.groupby(c_ccusto)[c_solic].nunique().reset_index(name='Total')
    top_10_cc_nomes = totais_cc.sort_values(by='Total', ascending=False).head(10)[c_ccusto].tolist()
    df_top10_cc = df_cc_abertas[df_cc_abertas[c_ccusto].isin(top_10_cc_nomes)]
    df_plot_cc = df_top10_cc.groupby([c_ccusto, c_crit])[c_solic].nunique().reset_index(name='Quantidade')
    
    mapa_cores_crit = {}
    for crit in df_plot_cc[c_crit].unique():
        crit_str = str(crit).lower().strip()
        if 'direta' in crit_str: mapa_cores_crit[crit] = '#00c853'      
        elif 'emerg' in crit_str: mapa_cores_crit[crit] = '#e91e63'   
        elif 'rotin' in crit_str: mapa_cores_crit[crit] = '#0f62fe'      
        else: mapa_cores_crit[crit] = '#ffb300'      
        
    todas_crits = df_plot_cc[c_crit].unique().tolist()
    ordem_desejada = []
    ordem_desejada.extend([c for c in todas_crits if 'direta' in str(c).lower()])
    ordem_desejada.extend([c for c in todas_crits if 'corre' in str(c).lower() or 'process' in str(c).lower()])
    ordem_desejada.extend([c for c in todas_crits if 'emerg' in str(c).lower()])
    ordem_desejada.extend([c for c in todas_crits if 'rotin' in str(c).lower()])
    
    for c in todas_crits:
        if c not in ordem_desejada: ordem_desejada.append(c)
    
    fig_top_cc = px.bar(df_plot_cc, y=c_ccusto, x='Quantidade', color=c_crit, orientation='h', text_auto=True, custom_data=[c_crit], color_discrete_map=mapa_cores_crit, category_orders={c_crit: ordem_desejada})
    fig_top_cc.update_layout(**dark_layout, barmode='stack')
    fig_top_cc.update_traces(textfont_size=18, textposition="inside")
    fig_top_cc.update_xaxes(visible=False)
    fig_top_cc.update_yaxes(type='category', categoryorder='array', categoryarray=top_10_cc_nomes[::-1], title="", tickfont=dict(size=14))
    
    evento_cc = st.plotly_chart(fig_top_cc, use_container_width=True, on_select="rerun", config={'displayModeBar': False}, key=f"cc_{st.session_state.cc_key}")
    if evento_cc and len(evento_cc.selection.get("points", [])) > 0:
        ponto_selecionado = evento_cc.selection["points"][0]
        cc_clicado = str(ponto_selecionado["y"]).strip()
        crit_clicada = str(ponto_selecionado["customdata"][0]).strip()
        df_detalhe = df_f[(df_f[c_ccusto].astype(str).str.strip() == cc_clicado) & (df_f[c_crit].astype(str).str.strip() == crit_clicada) & (df_f['IS_ABERTA'])]
        st.session_state.df_modal = df_detalhe.drop_duplicates(subset=[c_solic])[colunas_exibir]
        st.session_state.abrir_modal = True
        st.session_state.cc_key += 1
        st.rerun()
else:
    st.write("Sem registros abertos.")

# --- GERENCIADOR DE MODAL CENTRALIZADO (DESMARCAÇÃO AUTOMÁTICA) ---
if st.session_state.get("abrir_modal", False):
    abrir_modal(st.session_state.df_modal)
    st.session_state.abrir_modal = False
