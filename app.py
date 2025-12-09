import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Gestão de Projetos - Engenharia",
    page_icon="🏗️",
    layout="wide"
)

# --- FUNÇÕES UTILITÁRIAS ---
def format_currency_br(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_date_br(date_obj):
    if pd.isnull(date_obj): return ""
    try:
        return pd.to_datetime(date_obj).strftime("%d/%m/%Y")
    except:
        return str(date_obj)

def get_now_br():
    fuso_br = pytz.timezone('America/Sao_Paulo')
    return datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")

# --- CONEXÃO ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(worksheet_name):
    try:
        return conn.read(worksheet=worksheet_name, ttl=0)
    except:
        return pd.DataFrame()

def save_data(df, worksheet_name):
    conn.update(worksheet=worksheet_name, data=df)
    st.cache_data.clear()

# --- CARREGAMENTO INICIAL ---
df_projetos = load_data("Projetos")
df_tarefas = load_data("Tarefas")

# Garantir colunas Projetos (Adicionado 'Cidade')
cols_proj = ["ID_Projeto", "Cliente", "Origem", "Tipo", "Area_m2", "Proposta_Aceita_R$", 
             "Servicos", "Link_Proposta", "Data_Cadastro", "Status_Geral", "Cidade"]
if df_projetos.empty: 
    df_projetos = pd.DataFrame(columns=cols_proj)
else:
    if "Cidade" not in df_projetos.columns:
        df_projetos["Cidade"] = ""

# Garantir colunas Tarefas
cols_task = ["ID_Projeto", "Fase", "Disciplina", "Descricao", "Responsavel", 
             "Data_Inicio", "Data_Deadline", "Prioridade", "Status", "Link_Tarefa", "Historico_Log"]
if df_tarefas.empty: df_tarefas = pd.DataFrame(columns=cols_task)
else:
    if "Historico_Log" not in df_tarefas.columns: df_tarefas["Historico_Log"] = ""

# Tratamento de Tipos para Gráficos
if not df_projetos.empty:
    df_projetos["Proposta_Aceita_R$"] = pd.to_numeric(df_projetos["Proposta_Aceita_R$"], errors="coerce").fillna(0.0)
    df_projetos["Area_m2"] = pd.to_numeric(df_projetos["Area_m2"], errors="coerce").fillna(0.0)

# --- MENU LATERAL ---
st.sidebar.title("🏗️ Gestão Integrada")
aba = st.sidebar.radio("Navegação", ["Dashboard", "Cadastro Projetos", "Controle de Tarefas"])

# ==============================================================================
# ABA 1: DASHBOARD (REMODELADO)
# ==============================================================================
if aba == "Dashboard":
    st.header("📊 Visão Geral do Escritório")
    
    if df_projetos.empty:
        st.warning("Cadastre projetos para visualizar o Dashboard.")
    else:
        # ================= SEÇÃO: PROJETOS =================
        st.markdown("### 🏢 PROJETOS")
        st.markdown("---")
        
        # Filtros
        ativos = df_projetos[df_projetos["Status_Geral"] == "Ativo"]
        concluidos = df_projetos[df_projetos["Status_Geral"] == "Concluído"]
        parados = df_projetos[df_projetos["Status_Geral"].isin(["Suspenso", "Cancelado", "Parado"])]
        
        c1, c2, c3, c4 = st.columns(4)
        
        # 1. Ativos
        c1.metric("Projetos Ativos", len(ativos))
        with c1.expander("Ver Lista (Ativos)"):
            if not ativos.empty:
                st.dataframe(ativos[["Cliente", "Tipo"]], hide_index=True)
            else:
                st.write("Nenhum.")

        # 2. Concluídos
        c2.metric("Concluídos", len(concluidos))
        with c2.expander("Ver Lista (Concluídos)"):
            if not concluidos.empty:
                st.dataframe(concluidos[["Cliente", "Data_Cadastro"]], hide_index=True)
            else:
                st.write("Nenhum.")

        # 3. Parados
        c3.metric("Parados/Suspensos", len(parados))
        with c3.expander("Ver Lista (Parados)"):
            if not parados.empty:
                st.dataframe(parados[["Cliente", "Status_Geral"]], hide_index=True)
            else:
                st.write("Nenhum.")
                
        # 4. Total
        c4.metric("Total Geral", len(df_projetos))

        # ================= SEÇÃO: TAREFAS =================
        st.markdown("### ✅ TAREFAS")
        st.markdown("---")
        
        if not df_tarefas.empty:
            # Preparação de Dados
            df_tarefas["Data_Deadline"] = pd.to_datetime(df_tarefas["Data_Deadline"], errors="coerce")
            hoje = pd.to_datetime(datetime.now().date())
            
            # Filtro Atrasadas (Não concluídas e data menor que hoje)
            atrasadas = df_tarefas[
                (df_tarefas["Status"] != "Concluído") & 
                (df_tarefas["Data_Deadline"] < hoje)
            ].copy()
            
            # Merge com nome do projeto
            atrasadas = pd.merge(atrasadas, df_projetos[["ID_Projeto", "Cliente"]], on="ID_Projeto", how="left")
            
            t1, t2 = st.columns([1, 3])
            
            t1.metric("Total de Tarefas", len(df_tarefas))
            t1.metric("⚠️ Atrasadas", len(atrasadas), delta=-len(atrasadas), delta_color="inverse")
            
            with t2:
                st.caption("📅 Carga de Trabalho (Tarefas por Data de Entrega)")
                # Gráfico de Linha do Tempo
                pendentes = df_tarefas[df_tarefas["Status"] != "Concluído"].copy()
                if not pendentes.empty:
                    pendentes["Data_Str"] = pendentes["Data_Deadline"].dt.strftime("%d/%m/%Y")
                    contagem_data = pendentes.groupby("Data_Deadline").size().reset_index(name="Quantidade")
                    
                    fig_timeline = px.bar(contagem_data, x="Data_Deadline", y="Quantidade", 
                                          title="Tarefas a Entregar por Dia", text_auto=True)
                    fig_timeline.update_layout(xaxis_title="Data de Entrega", yaxis_title="Qtd Tarefas")
                    st.plotly_chart(fig_timeline, use_container_width=True)
            
            # Lista Interativa de Atrasadas
            st.subheader("🔥 Lista de Tarefas Atrasadas (Clique para ver detalhes)")
            if not atrasadas.empty:
                # Dataframe selecionável
                event = st.dataframe(
                    atrasadas[["Cliente", "Descricao", "Responsavel", "Data_Deadline"]],
                    hide_index=True,
                    on_select="rerun", # Permite clicar na linha
                    selection_mode="single-row",
                    use_container_width=True
                )
                
                # Se alguém clicou em uma linha
                if len(event.selection.rows) > 0:
                    idx_selecionado = event.selection.rows[0]
                    tarefa_detalhe = atrasadas.iloc[idx_selecionado]
                    
                    with st.container(border=True):
                        st.markdown(f"**Detalhes da Tarefa: {tarefa_detalhe['Descricao']}**")
                        c_d1, c_d2, c_d3 = st.columns(3)
                        c_d1.write(f"**Projeto:** {tarefa_detalhe['Cliente']}")
                        c_d2.write(f"**Responsável:** {tarefa_detalhe['Responsavel']}")
                        c_d3.write(f"**Fase:** {tarefa_detalhe['Fase']}")
                        st.warning(f"Era para ter entregue em: {format_date_br(tarefa_detalhe['Data_Deadline'])}")
                        st.info(f"Link/Info: {tarefa_detalhe['Link_Tarefa'] or 'Sem link'}")
            else:
                st.success("Nenhuma tarefa atrasada! 🎉")

        # ================= SEÇÃO: INDICADORES =================
        st.markdown("### 📈 INDICADORES ESTRATÉGICOS")
        st.markdown("---")
        
        ind1, ind2 = st.columns(2)
        
        # Gráfico Origem
        with ind1:
            fig_origem = px.pie(df_projetos, names="Origem", title="Origem dos Clientes", hole=0.4)
            st.plotly_chart(fig_origem, use_container_width=True)
            
        # Gráfico Tipo de Obra
        with ind2:
            fig_tipo = px.pie(df_projetos, names="Tipo", title="Distribuição por Tipo de Obra")
            st.plotly_chart(fig_tipo, use_container_width=True)
            
        # Métricas Financeiras e Área
        st.markdown("#### 💰 Totais Acumulados")
        m1, m2 = st.columns(2)
        m1.info(f"**Total Contratado:** {format_currency_br(df_projetos['Proposta_Aceita_R$'].sum())}")
        m2.info(f"**Área Total Projetada:** {df_projetos['Area_m2'].sum():,.0f} m²".replace(",", "."))
        
        # Gráficos de Barra (Serviço e Cidade)
        g1, g2 = st.columns(2)
        
        with g1:
            st.markdown("**Projetos por Tipo de Serviço**")
            # Lógica para separar serviços (Ex: "BIM, Render" vira 1 BIM e 1 Render)
            servicos_split = df_projetos["Servicos"].str.split(", ", expand=True).stack()
            if not servicos_split.empty:
                contagem_serv = servicos_split.value_counts().reset_index()
                contagem_serv.columns = ["Servico", "Qtd"]
                fig_serv = px.bar(contagem_serv, x="Qtd", y="Servico", orientation='h', text_auto=True)
                st.plotly_chart(fig_serv, use_container_width=True)
        
        with g2:
            st.markdown("**Projetos por Cidade**")
            if "Cidade" in df_projetos.columns:
                contagem_cid = df_projetos["Cidade"].value_counts().reset_index()
                contagem_cid.columns = ["Cidade", "Qtd"]
                fig_cid = px.bar(contagem_cid, x="Cidade", y="Qtd", text_auto=True)
                st.plotly_chart(fig_cid, use_container_width=True)


# ==============================================================================
# ABA 2: CADASTRO PROJETOS (ATUALIZADO)
# ==============================================================================
# ==============================================================================
# ABA 2: CADASTRO PROJETOS (ATUALIZADO COM LISTA INTELIGENTE)
# ==============================================================================
elif aba == "Cadastro Projetos":
    st.header("📂 Cadastro de Novos Projetos")
    
    with st.expander("➕ Novo Projeto (Clique para abrir)", expanded=True):
        with st.form("form_projeto", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                cliente = st.text_input("Nome do Cliente")
                cidade = st.text_input("Cidade da Obra")
                
                # --- LÓGICA DE ORIGEM DINÂMICA ---
                # 1. Pega o que já existe no banco de dados (sem repetir e remove vazios)
                if not df_projetos.empty and "Origem" in df_projetos.columns:
                    # dropna() tira vazios, unique() tira repetidos, sorted() organiza A-Z
                    historico_origens = sorted(df_projetos["Origem"].dropna().unique().tolist())
                else:
                    historico_origens = []

                # 2. Adiciona opção de criar nova no topo ou fim
                opcoes_origem = ["➕ Cadastrar Nova Origem..."] + historico_origens
                
                sel_origem = st.selectbox("Origem do Cliente", opcoes_origem)
                
                # 3. Se escolheu cadastrar nova, mostra o campo de texto. Se não, usa a seleção.
                if sel_origem == "➕ Cadastrar Nova Origem...":
                    origem = st.text_input("Digite a Nova Origem:")
                else:
                    origem = sel_origem
                # ----------------------------------
                
                tipo = st.selectbox("Tipo", ["Residencial Unifamiliar", "Residencial Multifamiliar", "Comercial", "Reforma", "Industrial"])
                area = st.number_input("Área (m²)", min_value=0.0, step=1.0)
            with c2:
                valor = st.number_input("Valor Proposta (R$)", min_value=0.0, step=100.0, format="%.2f")
                servicos = st.multiselect("Serviços", ["Modelagem BIM", "Compatibilização", "Pranchas", "Render", "Orçamento", "Consultoria"])
                link = st.text_input("Link Proposta (Drive)")
                
            submitted = st.form_submit_button("Salvar Projeto")
            
            if submitted and cliente:
                # Verifica se a origem foi preenchida corretamente
                if not origem:
                    st.error("Por favor, preencha a Origem do cliente.")
                else:
                    novo = pd.DataFrame([{
                        "ID_Projeto": len(df_projetos) + 1,
                        "Cliente": cliente,
                        "Origem": origem, # Aqui entra o valor novo ou o selecionado
                        "Tipo": tipo,
                        "Area_m2": area,
                        "Proposta_Aceita_R$": valor,
                        "Servicos": ", ".join(servicos),
                        "Link_Proposta": link,
                        "Data_Cadastro": datetime.now().strftime("%Y-%m-%d"),
                        "Status_Geral": "Ativo",
                        "Cidade": cidade
                    }])
                    
                    df_final = pd.concat([df_projetos, novo], ignore_index=True)
                    save_data(df_final, "Projetos")
                    st.success(f"Projeto de {cliente} salvo! A origem '{origem}' foi gravada.")
                    st.rerun()


# ==============================================================================
# ABA 3: CONTROLE DE TAREFAS (MANUTENÇÃO DO ANTERIOR)
# ==============================================================================
elif aba == "Controle de Tarefas":
    st.header("✅ Quadro de Atividades")
    
    lista_projetos = df_projetos["Cliente"].unique().tolist()
    
    with st.expander("➕ Cadastrar Nova Tarefa"):
        with st.form("task_form", clear_on_submit=True):
            proj = st.selectbox("Projeto", lista_projetos)
            c1, c2, c3 = st.columns(3)
            fase = c1.selectbox("Fase", ["Modelagem", "Compatibilização", "Pranchas", "Render"])
            resp = c2.selectbox("Responsável", ["GABRIEL", "MILENNA"])
            prio = c3.selectbox("Prioridade", ["Alta", "Média", "Baixa"])
            
            desc = st.text_input("Descrição da Atividade")
            d_ini = st.date_input("Início", format="DD/MM/YYYY")
            d_fim = st.date_input("Prazo Final", format="DD/MM/YYYY")
            link_t = st.text_input("Link Arquivos")

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
                    "Link_Tarefa": link_t,
                    "Historico_Log": f"Criado em {get_now_br()}"
                }])
                save_data(pd.concat([df_tarefas, nova], ignore_index=True), "Tarefas")
                st.success("Tarefa criada!")
                st.rerun()

    st.divider()

    if df_tarefas.empty:
        st.info("Nenhuma tarefa.")
    else:
        df_full = pd.merge(df_tarefas, df_projetos[["ID_Projeto", "Cliente"]], on="ID_Projeto", how="left")
        
        responsaveis_filtro = st.multiselect("Filtrar Responsável", ["GABRIEL", "MILENNA"], default=["GABRIEL", "MILENNA"])
        df_full = df_full[df_full["Responsavel"].isin(responsaveis_filtro)]

        ordem_prioridade = ["Alta", "Média", "Baixa"]
        cores = {"Alta": "🔴", "Média": "🟡", "Baixa": "🟢"}

        for prioridade_atual in ordem_prioridade:
            subset = df_full[df_full["Prioridade"] == prioridade_atual]
            subset = subset[subset["Status"] != "Concluído"]

            if not subset.empty:
                st.markdown(f"### {cores[prioridade_atual]} Prioridade {prioridade_atual}")
                for idx, row in subset.iterrows():
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([3, 2, 2, 3])
                        c1.markdown(f"**{row['Cliente']}**")
                        c1.caption(f"{row['Fase']} | {row['Descricao']}")
                        c2.text(f"📅 {format_date_br(row['Data_Deadline'])}")
                        c2.text(f"👤 {row['Responsavel']}")
                        
                        nova_prio = c3.selectbox("Prioridade", ["Alta", "Média", "Baixa"], 
                                                 index=["Alta", "Média", "Baixa"].index(row['Prioridade']),
                                                 key=f"prio_{idx}", label_visibility="collapsed")
                        
                        opcoes_status = ["A Fazer", "Em Andamento", "Revisão", "Concluído"]
                        idx_status = opcoes_status.index(row['Status']) if row['Status'] in opcoes_status else 0
                        novo_status = c4.selectbox("Status", opcoes_status, index=idx_status, key=f"stat_{idx}", label_visibility="collapsed")

                        mudou = False
                        log_msg = ""
                        
                        # Detecta mudanças
                        if nova_prio != row['Prioridade']:
                            df_tarefas.at[idx, "Prioridade"] = nova_prio
                            log_msg += f"[{get_now_br()}] Prio: {row['Prioridade']}->{nova_prio}. "
                            mudou = True
                        if novo_status != row['Status']:
                            df_tarefas.at[idx, "Status"] = novo_status
                            log_msg += f"[{get_now_br()}] Status: {row['Status']}->{novo_status}. "
                            mudou = True

                        if mudou:
                            hist_atual = str(df_tarefas.at[idx, "Historico_Log"]) if pd.notna(df_tarefas.at[idx, "Historico_Log"]) else ""
                            df_tarefas.at[idx, "Historico_Log"] = hist_atual + " | " + log_msg
                            save_data(df_tarefas, "Tarefas")
                            st.rerun()
