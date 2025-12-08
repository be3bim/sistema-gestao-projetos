import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Gestão de Projetos BIM/Engenharia",
    page_icon="🏗️",
    layout="wide"
)

# --- TÍTULO E ESTILO ---
st.title("🏗️ Sistema de Controle de Projetos & BIM")
st.markdown("---")

# --- CONEXÃO COM GOOGLE SHEETS ---
# A conexão busca as credenciais no arquivo .streamlit/secrets.toml
conn = st.connection("gsheets", type=GSheetsConnection)

# Função para carregar dados com tratamento de cache
def load_data(worksheet_name):
    try:
        # Tenta ler a aba específica. Se não existir, retorna DataFrame vazio
        return conn.read(worksheet=worksheet_name, ttl=5)
    except:
        return pd.DataFrame()

# Função para salvar dados (limpa a aba e reescreve - modo simplificado)
def save_data(df, worksheet_name):
    conn.update(worksheet=worksheet_name, data=df)
    st.cache_data.clear() # Limpa cache para atualizar visualização

# --- CARREGAR DADOS INICIAIS ---
# Precisamos garantir que as colunas existam, mesmo se a planilha estiver vazia
df_projetos = load_data("Projetos")
df_tarefas = load_data("Tarefas")

# Estrutura base caso a planilha esteja virgem
cols_projetos = ["ID_Projeto", "Cliente", "Origem", "Tipo", "Area_m2", "Proposta_Aceita_R$", 
                 "Servicos", "Link_Proposta", "Data_Cadastro", "Status_Geral"]
if df_projetos.empty:
    df_projetos = pd.DataFrame(columns=cols_projetos)

cols_tarefas = ["ID_Projeto", "Fase", "Disciplina", "Descricao", "Responsavel", 
                "Data_Inicio", "Data_Deadline", "Prioridade", "Status", "Link_Tarefa"]
if df_tarefas.empty:
    df_tarefas = pd.DataFrame(columns=cols_tarefas)


# --- NAVEGAÇÃO (SIDEBAR) ---
st.sidebar.header("Navegação")
aba_selecionada = st.sidebar.radio("Ir para:", ["Dashboard", "Cadastro de Projetos", "Controle de Tarefas"])

# ==============================================================================
# ABA 1: CADASTRO DE PROJETOS
# ==============================================================================
if aba_selecionada == "Cadastro de Projetos":
    st.header("📂 Cadastro de Novos Projetos")
    
    with st.form("form_projeto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            cliente = st.text_input("Nome do Cliente")
            origem = st.selectbox("Origem do Cliente", 
                                  ["Indicação", "Instagram/Redes", "Google/Site", "Parceiro/Arquiteto", "Outro"])
            tipo = st.selectbox("Tipo de Obra", ["Residencial Unifamiliar", "Residencial Multifamiliar", "Comercial", "Reforma", "Galpão/Industrial"])
            area = st.number_input("Área (m²)", min_value=0.0, step=1.0)
        
        with col2:
            valor = st.number_input("Valor Proposta Aceita (R$)", min_value=0.0, step=100.0)
            servicos = st.multiselect("Serviços Contratados", 
                                      ["Modelagem BIM", "Compatibilização", "Montagem de Pranchas", "Renderização", "Orçamentação"])
            link_prop = st.text_input("Link da Proposta/Contrato (Google Drive)")
            status_geral = "Ativo" # Padrão ao criar
            
        submitted = st.form_submit_button("Cadastrar Projeto")
        
        if submitted:
            if cliente and servicos:
                novo_id = len(df_projetos) + 1
                novo_projeto = pd.DataFrame([{
                    "ID_Projeto": novo_id,
                    "Cliente": cliente,
                    "Origem": origem,
                    "Tipo": tipo,
                    "Area_m2": area,
                    "Proposta_Aceita_R$": valor,
                    "Servicos": ", ".join(servicos), # Converte lista para string
                    "Link_Proposta": link_prop,
                    "Data_Cadastro": datetime.now().strftime("%Y-%m-%d"),
                    "Status_Geral": status_geral
                }])
                
                df_projetos_atualizado = pd.concat([df_projetos, novo_projeto], ignore_index=True)
                save_data(df_projetos_atualizado, "Projetos")
                st.success(f"Projeto de {cliente} cadastrado com sucesso!")
            else:
                st.error("Preencha pelo menos o Cliente e os Serviços.")

    st.subheader("📋 Projetos Cadastrados")
    st.dataframe(df_projetos)

# ==============================================================================
# ABA 2: CONTROLE DE TAREFAS
# ==============================================================================
elif aba_selecionada == "Controle de Tarefas":
    st.header("✅ Controle de Produção e Prazos")
    
    # Seleção do Projeto para atribuir tarefa
    lista_projetos = df_projetos["Cliente"].unique().tolist() if not df_projetos.empty else []
    
    with st.expander("➕ Adicionar Nova Tarefa", expanded=True):
        with st.form("form_tarefa", clear_on_submit=True):
            proj_selecionado = st.selectbox("Selecione o Projeto", lista_projetos)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                fase = st.selectbox("Fase do Projeto", ["Modelagem", "Compatibilização", "Montagem de Pranchas"])
                disciplina = st.selectbox("Disciplina", ["Arquitetura", "Estrutural", "Hidrossanitário", "Elétrico", "Coordenação"])
            with c2:
                resp = st.selectbox("Responsável", ["Engenheiro", "Esposa", "Terceirizado"]) # Personalize aqui
                prioridade = st.selectbox("Prioridade", ["Alta", "Média", "Baixa"])
            with c3:
                inicio = st.date_input("Data Início")
                prazo = st.date_input("Prazo de Entrega (Deadline)")
            
            desc = st.text_area("Descrição do que deve ser feito")
            link_t = st.text_input("Link para arquivos de trabalho")
            
            submit_tarefa = st.form_submit_button("Criar Tarefa")
            
            if submit_tarefa and proj_selecionado:
                # Buscar ID do projeto baseado no nome
                id_proj = df_projetos[df_projetos["Cliente"] == proj_selecionado]["ID_Projeto"].values[0]
                
                nova_tarefa = pd.DataFrame([{
                    "ID_Projeto": id_proj,
                    "Fase": fase,
                    "Disciplina": disciplina,
                    "Descricao": desc,
                    "Responsavel": resp,
                    "Data_Inicio": str(inicio),
                    "Data_Deadline": str(prazo),
                    "Prioridade": prioridade,
                    "Status": "A Fazer",
                    "Link_Tarefa": link_t
                }])
                
                df_tarefas_atualizado = pd.concat([df_tarefas, nova_tarefa], ignore_index=True)
                save_data(df_tarefas_atualizado, "Tarefas")
                st.success("Tarefa adicionada!")

    st.divider()
    
    # Visualização e Edição de Status
    st.subheader("Suas Tarefas Pendentes")
    
    if not df_tarefas.empty:
        # Merge para trazer o nome do cliente para a tabela de tarefas
        df_view = pd.merge(df_tarefas, df_projetos[["ID_Projeto", "Cliente"]], on="ID_Projeto", how="left")
        
        # Filtros
        col_f1, col_f2 = st.columns(2)
        filtro_resp = col_f1.multiselect("Filtrar por Responsável", df_view["Responsavel"].unique())
        filtro_status = col_f2.multiselect("Filtrar por Status", df_view["Status"].unique(), default=["A Fazer", "Em Andamento"])
        
        if filtro_resp:
            df_view = df_view[df_view["Responsavel"].isin(filtro_resp)]
        if filtro_status:
            df_view = df_view[df_view["Status"].isin(filtro_status)]
            
        # Exibição Customizada
        for index, row in df_view.iterrows():
            with st.container():
                c_a, c_b, c_c, c_d = st.columns([2, 4, 2, 2])
                c_a.markdown(f"**{row['Cliente']}**")
                c_b.text(f"{row['Fase']} - {row['Descricao']}")
                c_c.warning(f"📅 {row['Data_Deadline']}")
                
                # Botão simples para mudar status (Simulação de atualização)
                # Nota: Em app real complexo, usaríamos st.data_editor
                novo_status = c_d.selectbox("Status", ["A Fazer", "Em Andamento", "Concluído"], 
                                            index=["A Fazer", "Em Andamento", "Concluído"].index(row['Status']), 
                                            key=f"status_{index}")
                
                if novo_status != row['Status']:
                    # Atualiza no dataframe original
                    df_tarefas.at[index, "Status"] = novo_status
                    save_data(df_tarefas, "Tarefas")
                    st.rerun()
                st.divider()
    else:
        st.info("Nenhuma tarefa cadastrada.")

# ==============================================================================
# ABA 3: DASHBOARD ESTATÍSTICO
# ==============================================================================
elif aba_selecionada == "Dashboard":
    st.header("📊 Dashboard Gerencial")
    
    if df_projetos.empty:
        st.warning("Cadastre projetos para ver as estatísticas.")
    else:
        # Conversão de tipos para garantir cálculos
        df_projetos["Area_m2"] = pd.to_numeric(df_projetos["Area_m2"])
        df_projetos["Data_Cadastro"] = pd.to_datetime(df_projetos["Data_Cadastro"])
        df_tarefas["Data_Deadline"] = pd.to_datetime(df_tarefas["Data_Deadline"])

        # --- MÉTRICAS SUPERIORES ---
        col1, col2, col3, col4 = st.columns(4)
        
        qtd_ativos = len(df_projetos[df_projetos["Status_Geral"] == "Ativo"])
        col1.metric("Projetos Ativos", qtd_ativos)
        
        tarefas_atrasadas = len(df_tarefas[(df_tarefas["Status"] != "Concluído") & 
                                           (df_tarefas["Data_Deadline"] < pd.to_datetime("today"))])
        col2.metric("Tarefas Atrasadas", tarefas_atrasadas, delta=-tarefas_atrasadas, delta_color="inverse")
        
        projetos_concluidos = len(df_projetos[df_projetos["Status_Geral"] == "Concluído"]) # Exemplo hipotético
        col3.metric("Projetos Entregues", projetos_concluidos)
        
        total_m2 = df_projetos["Area_m2"].sum()
        col4.metric("Total Projetado (m²)", f"{total_m2:,.0f} m²")

        st.markdown("---")

        # --- GRÁFICOS ---
        c_chart1, c_chart2 = st.columns(2)

        with c_chart1:
            st.subheader("📍 Origem dos Clientes")
            # Gráfico de Rosca (Donut) para Origem
            fig_origem = px.pie(df_projetos, names="Origem", hole=0.4, title="Distribuição por Indicação/Origem")
            st.plotly_chart(fig_origem, use_container_width=True)

        with c_chart2:
            st.subheader("📅 Projetos por Mês")
            # Agrupar por mês
            df_projetos["Mes_Ano"] = df_projetos["Data_Cadastro"].dt.to_period("M").astype(str)
            projetos_por_mes = df_projetos.groupby("Mes_Ano").size().reset_index(name="Quantidade")
            
            fig_mes = px.bar(projetos_por_mes, x="Mes_Ano", y="Quantidade", title="Evolução de Contratações", text_auto=True)
            st.plotly_chart(fig_mes, use_container_width=True)

        # Gráfico Extra: Tarefas por Pessoa
        st.subheader("👥 Carga de Trabalho (Tarefas Pendentes)")
        if not df_tarefas.empty:
            pendentes = df_tarefas[df_tarefas["Status"] != "Concluído"]
            fig_carga = px.bar(pendentes, x="Responsavel", color="Prioridade", title="Tarefas a Fazer por Responsável")
            st.plotly_chart(fig_carga, use_container_width=True)
