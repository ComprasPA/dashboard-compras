
import streamlit as st
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Dashboard de Compras", layout="wide")

# Função para carregar dados
@st.cache_data
def carregar_dados():
    # Ajuste o caminho conforme o nome do seu arquivo na pasta data/
    df = pd.read_excel('data/FOLLOW UP - COMPRAS 2026.xlsx', sheet_name='Solicitações')
    return df

# Sidebar para navegação
st.sidebar.title("Navegação")
pagina = st.sidebar.radio("Escolha a seção:", ["Visão Geral", "Curva ABC", "Gestão de Pendências"])

df = carregar_dados()

# Lógica de navegação
if pagina == "Visão Geral":
    st.title("📊 Visão Geral do Setor")
    st.write("Bem-vindo ao novo Dashboard de Compras.")
    # Aqui inseriremos os indicadores de No Prazo, Fora do Prazo, etc.

elif pagina == "Curva ABC":
    st.title("📦 Análise Curva ABC")
    st.write("Visualização de impacto por C.C. e Itens.")

elif pagina == "Gestão de Pendências":
    st.title("⚠️ Solicitações em Aberto")
    # Aqui filtraremos as pendentes por maior SLA
