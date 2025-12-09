import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz # Para pegar o fuso horário do Brasil

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Gestão de Projetos - Engenharia",
    page_icon="🏗️",
    layout="wide"
)

# --- FUNÇÕES UTILITÁRIAS ---

# Formatação de Moeda Brasil
def format_currency_br(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Formatação de Data Brasil
def format_date_br(date_obj):
    if pd.isnull(date_obj): return ""
    # Se já for string, tenta converter, senão retorna
    try:
        return pd.to_datetime(date_obj).strftime("%d/%m/%Y")
    except:
        return str(date_obj)

# Data e Hora atual Brasil
def get_now_br():
    fuso_br = pytz.timezone('America/Sao_Paulo')
    return datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(worksheet_name):
    try:
        return conn.read(worksheet=worksheet_name, ttl=0) # ttl=0 para não cachear e ver atualização na hora
    except:
        return pd.DataFrame()

def save_data(df, worksheet_name):
    conn.update(worksheet=worksheet_name, data=df)
    st.cache_data.clear()

# --- CARREGAMENTO INICIAL ---
df_projetos = load_data("Projetos")
df_tarefas = load_data("Tarefas")

# Garantir colunas essenciais
cols_proj = ["ID_Projeto", "Cliente", "Origem", "Tipo", "Area_m2", "Proposta_Aceita_R$", 
             "Servicos", "Link_Proposta", "Data_Cadastro", "Status_Geral"]
if df_projetos.empty: df_projetos = pd.DataFrame(columns=cols_proj)

# Adicionei 'Historico_Log' nas colunas
cols_task = ["ID_Projeto", "Fase", "Disciplina", "Descricao", "Responsavel", 
             "Data_Inicio", "Data_Deadline", "Prioridade", "Status", "Link_Tarefa", "Historico_Log"]
if df_tarefas.empty: df_tarefas = pd.DataFrame(columns=cols_task)
else:
    # Se a coluna de histórico não existir no dataframe carregado, cria ela
    if "Historico_Log" not in df_tarefas.columns:
        df_tarefas["Historico_Log"] = ""


# --- SIDEBAR ---
st.sidebar.title("🏗️ Gestão Integrada")
aba = st.sidebar.radio("Menu", ["Dashboard", "Cadastro Projetos", "Controle de Tarefas"])

# ==============================================================================
# ABA 1: CADASTRO PROJETOS
# ==============================================================================
if aba == "Cadastro Projetos":
    st.header("📂 Projetos e Clientes")
    
    with st.expander("➕ Novo Projeto (Clique para abrir)", expanded=False):
        with st.form("form_projeto", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                cliente = st.text_input("Nome do Cliente")
                # Mudança: Origem agora é texto livre para colocar o nome do escritório
                origem = st.text_input("Origem (Ex: Escritório XYZ, Indicação Fulano)")
                tipo = st.selectbox("Tipo", ["Residencial Unifamiliar", "Residencial Multifamiliar", "Comercial", "Reforma", "Industrial"])
                area = st.number_input("Área (m²)", min_value=0.0, step=1.0)
            with c2:
                valor = st.number_input("Valor Proposta (R$)", min_value=0.0, step=100.0, format="%.2f")
                servicos = st.multiselect("Serviços", ["Modelagem BIM", "Compatibilização", "Pranchas", "Render", "Orçamento"])
                link = st.text_input("Link Proposta (Drive)")
                
            submitted = st.form_submit_button("Salvar Projeto")
            
            if submitted and cliente:
                novo = pd.DataFrame([{
                    "ID_Projeto": len(df_projetos) + 1,
                    "Cliente": cliente,
                    "Origem": origem,
                    "Tipo": tipo,
                    "Area_m2": area,
                    "Proposta_Aceita_R$": valor,
                    "Servicos": ", ".join(servicos),
                    "Link_Proposta": link,
                    "Data_Cadastro": datetime.now().strftime("%Y-%m-%d"),
                    "Status_Geral": "Ativo"
                }])
                save_data(pd.concat([df_projetos, novo], ignore_index=True), "Projetos")
                st.success("Projeto salvo!")
                st.rerun()

    st.divider()
    st.subheader("📋 Gerenciar Projetos Existentes")
    
    if not df_projetos.empty:
        # --- CORREÇÃO DO ERRO DE TIPOS ---
        # 1. Força a coluna de valor a ser número (transforma erro em 0.0)
        df_projetos["Proposta_Aceita_R$"] = pd.to_numeric(df_projetos["Proposta_Aceita_R$"], errors="coerce").fillna(0.0)
        
        # 2. Força a coluna de data a ser data real
        df_projetos["Data_Cadastro"] = pd.to_datetime(df_projetos["Data_Cadastro"], errors="coerce")
        # ---------------------------------

        st.write("Edite o Status Geral diretamente na tabela abaixo:")
        
        # Configuração da coluna de Status como Dropdown
        df_editor = st.data_editor(
            df_projetos,
            column_config={
                "Status_Geral": st.column_config.SelectboxColumn(
                    "Status Geral",
                    help="Status do contrato",
                    width="medium",
                    options=["Ativo", "Concluído", "Cancelado", "Suspenso"],
                    required=True,
                ),
                "Proposta_Aceita_R$": st.column_config.NumberColumn(
                    "Valor (R$)",
                    format="R$ %.2f"
                ),
                "Data_Cadastro": st.column_config.DateColumn(
                    "Data",
                    format="DD/MM/YYYY"
                )
            },
            hide_index=True,
            num_rows="dynamic"
        )
        
        # Botão para salvar alterações feitas na tabela
        if st.button("Salvar Alterações de Status/Dados"):
            # Antes de salvar, garantimos que a data volte para string pro Google Sheets não bugar
            df_editor["Data_Cadastro"] = df_editor["Data_Cadastro"].astype(str)
            save_data(df_editor, "Projetos")
            st.success("Dados atualizados com sucesso!")


# ==============================================================================
# ABA 2: CONTROLE DE TAREFAS
# ==============================================================================
elif aba == "Controle de Tarefas":
    st.header("✅ Quadro de Atividades")
    
    lista_projetos = df_projetos["Cliente"].unique().tolist()
    
    # Cadastro escondido no Expander
    with st.expander("➕ Cadastrar Nova Tarefa", expanded=False):
        with st.form("task_form", clear_on_submit=True):
            proj = st.selectbox("Projeto", lista_projetos)
            c1, c2, c3 = st.columns(3)
            fase = c1.selectbox("Fase", ["Modelagem", "Compatibilização", "Pranchas"])
            # Responsáveis Fixos
            resp = c2.selectbox("Responsável", ["GABRIEL", "MILENNA"])
            prio = c3.selectbox("Prioridade", ["Alta", "Média", "Baixa"])
            
            desc = st.text_input("Descrição da Atividade")
            # Datas com formato BR no input
            d_ini = st.date_input("Início", format="DD/MM/YYYY")
            d_fim = st.date_input("Prazo Final", format="DD/MM/YYYY")
            
            if st.form_submit_button("Adicionar Tarefa"):
                id_p = df_projetos[df_projetos["Cliente"] == proj]["ID_Projeto"].values[0]
                nova = pd.DataFrame([{
                    "ID_Projeto": id_p,
                    "Fase": fase,
                    "Disciplina": "Geral",
                    "Descricao": desc,
                    "Responsavel": resp,
                    "Data_Inicio": str(d_ini),
                    "Data_Deadline": str(d_fim),
                    "Prioridade": prio,
                    "Status": "A Fazer",
                    "Link_Tarefa": "",
                    "Historico_Log": f"Criado em {get_now_br()}"
                }])
                save_data(pd.concat([df_tarefas, nova], ignore_index=True), "Tarefas")
                st.success("Tarefa criada!")
                st.rerun()

    st.divider()

    # --- VISUALIZAÇÃO POR CAIXAS DE PRIORIDADE ---
    
    if df_tarefas.empty:
        st.info("Nenhuma tarefa cadastrada.")
    else:
        # Merge para pegar nome do cliente
        df_full = pd.merge(df_tarefas, df_projetos[["ID_Projeto", "Cliente"]], on="ID_Projeto", how="left")
        
        # Filtros globais
        responsaveis_filtro = st.multiselect("Filtrar Responsável", ["GABRIEL", "MILENNA"], default=["GABRIEL", "MILENNA"])
        df_full = df_full[df_full["Responsavel"].isin(responsaveis_filtro)]

        # Loop para criar as 3 caixas: Alta, Média, Baixa
        ordem_prioridade = ["Alta", "Média", "Baixa"]
        cores = {"Alta": "🔴", "Média": "🟡", "Baixa": "🟢"}

        for prioridade_atual in ordem_prioridade:
            # Filtra tarefas dessa prioridade específica
            subset = df_full[df_full["Prioridade"] == prioridade_atual]
            subset = subset[subset["Status"] != "Concluído"] # Oculta concluídos das caixas principais

            if not subset.empty:
                st.markdown(f"### {cores[prioridade_atual]} Prioridade {prioridade_atual}")
                
                for idx, row in subset.iterrows():
                    # Caixa visual da tarefa
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([3, 2, 2, 3])
                        
                        # Coluna 1: Info Principal
                        c1.markdown(f"**{row['Cliente']}**")
                        c1.caption(f"{row['Fase']} | {row['Descricao']}")
                        
                        # Coluna 2: Prazos
                        data_fmt = format_date_br(row['Data_Deadline'])
                        c2.text(f"📅 {data_fmt}")
                        c2.text(f"👤 {row['Responsavel']}")
                        
                        # Coluna 3: Editar Prioridade
                        nova_prio = c3.selectbox("Prioridade", ["Alta", "Média", "Baixa"], 
                                                 index=["Alta", "Média", "Baixa"].index(row['Prioridade']),
                                                 key=f"prio_{idx}", label_visibility="collapsed")
                        
                        # Coluna 4: Editar Status
                        novo_status = c4.selectbox("Status", ["A Fazer", "Em Andamento", "Revisão", "Concluído"],
                                                   index=["A Fazer", "Em Andamento", "Revisão", "Concluído"].index(row['Status']) if row['Status'] in ["A Fazer", "Em Andamento", "Revisão", "Concluído"] else 0,
                                                   key=f"stat_{idx}", label_visibility="collapsed")

                        # --- LÓGICA DE ATUALIZAÇÃO E HISTÓRICO ---
                        mudou = False
                        log_msg = ""

                        # Verifica se mudou Prioridade
                        if nova_prio != row['Prioridade']:
                            df_tarefas.at[idx, "Prioridade"] = nova_prio
                            log_msg += f"[{get_now_br()}] Prio alterada: {row['Prioridade']} -> {nova_prio}. "
                            mudou = True
                        
                        # Verifica se mudou Status
                        if novo_status != row['Status']:
                            df_tarefas.at[idx, "Status"] = novo_status
                            log_msg += f"[{get_now_br()}] Status alterado: {row['Status']} -> {novo_status}. "
                            mudou = True

                        if mudou:
                            # Adiciona ao histórico existente
                            hist_atual = str(df_tarefas.at[idx, "Historico_Log"]) if pd.notna(df_tarefas.at[idx, "Historico_Log"]) else ""
                            df_tarefas.at[idx, "Historico_Log"] = hist_atual + " | " + log_msg
                            
                            save_data(df_tarefas, "Tarefas")
                            st.toast(f"Tarefa atualizada!", icon="💾")
                            st.rerun()
                        
                        # Mostrar histórico num expander pequeno
                        with st.expander("Ver Histórico de Alterações"):
                            st.caption(str(row.get("Historico_Log", "Sem histórico")))

# ==============================================================================
# ABA 3: DASHBOARD
# ==============================================================================
elif aba == "Dashboard":
    st.header("📊 Indicadores de Desempenho")
    
    if not df_projetos.empty:
        # Converter colunas numéricas
        df_projetos["Proposta_Aceita_R$"] = pd.to_numeric(df_projetos["Proposta_Aceita_R$"], errors='coerce').fillna(0)
        df_projetos["Area_m2"] = pd.to_numeric(df_projetos["Area_m2"], errors='coerce').fillna(0)
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Contratado", format_currency_br(df_projetos["Proposta_Aceita_R$"].sum()))
        kpi2.metric("Área Total Projetada", f"{df_projetos['Area_m2'].sum():,.0f} m²".replace(",", "."))
        kpi3.metric("Projetos Ativos", len(df_projetos[df_projetos["Status_Geral"] == "Ativo"]))

        c1, c2 = st.columns(2)
        
        # Gráfico Origem (Agora que é texto livre, mostramos os Top 5)
        origem_counts = df_projetos["Origem"].value_counts().head(7).reset_index()
        origem_counts.columns = ["Origem", "Qtd"]
        fig_orig = px.bar(origem_counts, x="Qtd", y="Origem", orientation='h', title="Top Origens de Clientes")
        c1.plotly_chart(fig_orig, use_container_width=True)
        
        # Gráfico Tipo
        fig_tipo = px.pie(df_projetos, names="Tipo", title="Distribuição por Tipo de Obra")
        c2.plotly_chart(fig_tipo, use_container_width=True)
