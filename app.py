import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

# Configuração da página
st.set_page_config(page_title="Dashboard Executivo", layout="wide")

# ... (Mantenha aqui as mesmas funções de carregamento de dados e filtros do código anterior) ...

# --- DASHBOARD (Layout em Quadrantes) ---
st.title("📊 Dashboard Executivo de Compras")

# Linha 1: Quadrante Superior Esquerdo e Superior Direito
col_top_l, col_top_r = st.columns(2)

with col_top_l:
    st.subheader("Quadrante 1: Distribuição de Status")
    status_counts = df_sc_unicas['CATEGORIA_COR'].value_counts()
    fig_p = go.Figure(data=[go.Pie(labels=status_counts.index, values=status_counts.values, 
                                   marker=dict(colors=[CORES_STATUS.get(x, '#ccc') for x in status_counts.index]),
                                   textinfo='percent+label', hole=0.3)])
    st.plotly_chart(fig_p, use_container_width=True)
    # Informações específicas do quadrante 1
    cols_s = st.columns(len(status_counts))
    for i, (status, qtd) in enumerate(status_counts.items()):
        cols_s[i].metric(status, qtd)

with col_top_r:
    st.subheader("Quadrante 2: Volume por Criticidade")
    crit_counts = df_sc_unicas.groupby('Criticidade')['Nº Solicitação (SC)'].nunique()
    fig_c = px.bar(crit_counts.reset_index(), x='Criticidade', y='Nº Solicitação (SC)', text_auto=True)
    st.plotly_chart(fig_c, use_container_width=True)
    # Informações específicas do quadrante 2
    cols_c = st.columns(len(crit_counts))
    for i, (crit, qtd) in enumerate(crit_counts.items()):
        cols_c[i].metric(str(crit), qtd)

st.divider()

# Linha 2: Quadrante Inferior Esquerdo e Inferior Direito
col_bot_l, col_bot_r = st.columns(2)

with col_bot_l:
    st.subheader("Quadrante 3: KPIs de Performance")
    # Métricas agregadas como um bloco de informações
    kpi_col1, kpi_col2 = st.columns(2)
    kpi_col1.metric("Pedidos Emitidos", df_sc_unicas['Nº Pedido (PC)'].nunique())
    kpi_col2.metric("Sol. Fechadas", df_sc_unicas[~df_sc_unicas['IS_ABERTA']].shape[0])
    kpi_col1.metric("Sol. Abertas", df_sc_unicas[df_sc_unicas['IS_ABERTA']].shape[0])
    kpi_col2.metric("SLA Médio", round(df_sc_unicas[df_sc_unicas['IS_ABERTA']]['SLA'].mean(), 1))

with col_bot_r:
    st.subheader("Quadrante 4: Top 10 Abertas (Maior SLA)")
    # Tabela global sem filtros de data
    df_top10 = df_full[df_full['IS_ABERTA']].sort_values('SLA', ascending=False).drop_duplicates(subset=['Nº Solicitação (SC)']).head(10)
    st.dataframe(df_top10[['Nº Solicitação (SC)', 'Descricao', 'SLA', 'C Custo', 'Comprador']], use_container_width=True)
