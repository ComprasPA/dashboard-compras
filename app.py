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
    # 1. Carrega as duas abas
    url_sol = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Solicitações"
    url_ped = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Pedidos"
    
    df_sol = pd.read_csv(io.StringIO(requests.get(url_sol).text))
    df_ped = pd.read_csv(io.StringIO(requests.get(url_ped).text))
    
    # Padroniza colunas
    df_sol.columns = df_sol.columns.str.strip()
    df_ped.columns = df_ped.columns.str.strip()
    
    # 2. Faz o cruzamento (Merge) na coluna 'Pedido'
    # Isso garante que a 'Data Emissao' (que está em Pedidos) venha para o df principal
    df = pd.merge(df_sol, df_ped[['Pedido', 'Data Emissao', 'Fornecedor']], on='Pedido', how='left')
    
    # Tratamentos
    df['SLA'] = pd.to_numeric(df['SLA'], errors='coerce').fillna(0)
    df['DT EMISSAO'] = pd.to_datetime(df['Data Emissao'], errors='coerce')
    df['IS_ABERTA'] = df['Pedido'].isna() | (df['Pedido'].astype(str).str.upper() == 'NAN')
    
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

# O restante do seu dashboard (filtros e gráficos) permanece exatamente igual ao que enviamos anteriormente.
