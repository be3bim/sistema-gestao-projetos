import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import pytz
from fpdf import FPDF
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Engenharia 360º - Gestão Completa",
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

# --- CLASSE PARA GERAR PDF ---
class PDFRelatorio(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Relatório de Status do Projeto', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def gerar_pdf_status(projeto_dados, tarefas_proj, financeiro_proj):
    pdf = PDFRelatorio()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Dados do Projeto
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Cliente: {projeto_dados['Cliente']}", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Tipo: {projeto_dados['Tipo']} | Cidade: {projeto_dados['Cidade']}", ln=True)
    pdf.cell(0, 10, f"Status Atual: {projeto_dados['Status_Geral']}", ln=True)
    pdf.ln(5)
    
    # Tarefas Recentes/Pendentes
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Status das Atividades:", ln=True)
    pdf.set_font("Arial", size=10)
    
    if not tarefas_proj.empty:
        for _, row in tarefas_proj.iterrows():
            status_icon = "[OK]" if row['Status'] == 'Concluído' else "[ ]"
            pdf.cell(0, 8, f"{status_icon} {row['Descricao']} ({row['Fase']}) - {row['Status']}", ln=True)
    else:
        pdf.cell(0, 8, "Nenhuma tarefa registrada.", ln=True)
    
    pdf.ln(5)
    # Resumo Financeiro (Opcional mostrar ao cliente, aqui deixarei oculto ou genérico)
    # Exemplo: Percentual Concluído
    total_tarefas = len(tarefas_proj)
    concluidas = len(tarefas_proj[tarefas_proj['Status'] == 'Concluído'])
    porc = (concluidas/total_tarefas)*100 if total_tarefas > 0 else 0
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Progresso Geral Estimado: {porc:.1f}%", ln=True)
    
    return pdf.output(dest='S').encode('latin-1')

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
df_financeiro = load_data("Financeiro")

# 1. Garantir Colunas PROJETOS (Incluindo novos campos de GED)
cols_proj = ["ID_Projeto", "Cliente", "Origem", "Tipo", "Area_m2", "Proposta_Aceita_R$", 
             "Servicos", "Link_Proposta", "Data_Cadastro", "Status_Geral", "Cidade", 
             "Historico_Log", "Link_Pasta_Executivo", "Link_Pasta_Renders"] # <--- NOVOS
if df_projetos.empty: 
    df_projetos = pd.DataFrame(columns=cols_proj)
else:
    for col in cols_proj:
        if col not in df_projetos.columns: df_projetos[col] = ""

# 2. Garantir Colunas TAREFAS (Incluindo Timesheet)
cols_task = ["ID_Projeto", "Fase", "Disciplina", "Descricao", "Responsavel", 
             "Data_Inicio", "Data_Deadline", "Prioridade", "Status", 
             "Link_Tarefa", "Historico_Log", "Data_Conclusao", "Horas_Gastas"] # <--- NOVO
if df_tarefas.empty: df_tarefas = pd.DataFrame(columns=cols_task)
else:
    for col in cols_task:
        if col not in df_tarefas.columns: df_tarefas[col] = ""

# 3. Garantir Colunas FINANCEIRO (NOVO)
cols_fin = ["ID_Lancamento", "ID_Projeto", "Descricao", "Valor", "Vencimento", "Status", "Data_Pagamento"]
if df_financeiro.empty: df_financeiro = pd.DataFrame(columns=cols_fin)

# --- TRATAMENTO DE DADOS ---
if not df_projetos.empty:
    df_projetos["Proposta_Aceita_R$"] = pd.to_numeric(df_projetos["Proposta_Aceita_R$"], errors="coerce").fillna(0.0)
    df_projetos["Area_m2"] = pd.to_numeric(df_projetos["Area_m2"], errors="coerce").fillna(0.0)

if not df_financeiro.empty:
    df_financeiro["Valor"] = pd.to_numeric(df_financeiro["Valor"], errors="coerce").fillna(0.0)
    df_financeiro["Vencimento"] = pd.to_datetime(df_financeiro["Vencimento"], errors="coerce")

# --- SIDEBAR ---
st.sidebar.title("🏗️ Engenharia 360º")
aba = st.sidebar.radio("Navegação", ["Dashboard", "Cadastro Projetos", "Controle de Tarefas", "Financeiro"])

# ==============================================================================
# ABA 1: DASHBOARD (COM CALENDÁRIO E FINANCEIRO)
# ==============================================================================
if aba == "Dashboard":
    st.header("📊 Centro de Comando")
    
    if df_projetos.empty:
        st.warning("Sem dados.")
    else:
        # --- BLOCO 1: KPI GERAL ---
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Projetos Ativos", len(df_projetos[df_projetos["Status_Geral"] == "Ativo"]))
        
        # Lucratividade Simplificada (Soma dos Projetos / Soma das Horas Totais)
        df_tarefas["Horas_Gastas"] = pd.to_numeric(df_tarefas["Horas_Gastas"], errors="coerce").fillna(0.0)
        total_horas = df_tarefas["Horas_Gastas"].sum()
        total_faturado = df_projetos["Proposta_Aceita_R$"].sum()
        valor_hora_medio = (total_faturado / total_horas) if total_horas > 0 else 0
        
        k2.metric("Horas Totais Gastas", f"{total_horas:.1f} h")
        k3.metric("Valor Hora Médio (Real)", f"R$ {valor_hora_medio:.2f}/h")
        
        # Financeiro Rápido
        recebido = df_financeiro[df_financeiro["Status"] == "Pago"]["Valor"].sum()
        a_receber = df_financeiro[df_financeiro["Status"] == "Pendente"]["Valor"].sum()
        k4.metric("A Receber (Caixa)", format_currency_br(a_receber), delta=format_currency_br(recebido))

        st.markdown("---")

        # --- BLOCO 2: CALENDÁRIO (GANTT) ---
        st.subheader("📅 Cronograma de Entregas")
        if not df_tarefas.empty:
            tasks_cal = df_tarefas[df_tarefas["Status"] != "Concluído"].copy()
            tasks_cal["Data_Deadline"] = pd.to_datetime(tasks_cal["Data_Deadline"])
            tasks_cal["Data_Inicio"] = pd.to_datetime(tasks_cal["Data_Inicio"])
            
            # Tratamento para Gantt: Se não tiver data inicio, assume 3 dias antes do prazo
            mask_sem_inicio = pd.isna(tasks_cal["Data_Inicio"])
            tasks_cal.loc[mask_sem_inicio, "Data_Inicio"] = tasks_cal.loc[mask_sem_inicio, "Data_Deadline"] - timedelta(days=3)
            
            # Merge com nome do projeto
            tasks_cal = pd.merge(tasks_cal, df_projetos[["ID_Projeto", "Cliente"]], on="ID_Projeto", how="left")
            
            if not tasks_cal.empty:
                fig_gantt = px.timeline(tasks_cal, x_start="Data_Inicio", x_end="Data_Deadline", 
                                        y="Cliente", color="Responsavel", hover_data=["Descricao", "Fase"],
                                        title="Linha do Tempo de Produção")
                fig_gantt.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_gantt, use_container_width=True)
            else:
                st.info("Sem tarefas com datas para exibir no calendário.")

        # --- BLOCO 3: PDF RAPIDO ---
        st.markdown("---")
        st.subheader("📄 Relatórios de Cliente")
        
        col_sel_p, col_btn_p = st.columns([3, 1])
        proj_pdf = col_sel_p.selectbox("Selecione o Projeto para Gerar Relatório", df_projetos["Cliente"].unique())
        
        if col_btn_p.button("Gerar PDF"):
            # Filtrar dados
            dados_proj = df_projetos[df_projetos["Cliente"] == proj_pdf].iloc[0]
            id_p = dados_proj["ID_Projeto"]
            tasks_p = df_tarefas[df_tarefas["ID_Projeto"] == id_p]
            fin_p = df_financeiro[df_financeiro["ID_Projeto"] == id_p]
            
            # Gerar binário
            pdf_bytes = gerar_pdf_status(dados_proj, tasks_p, fin_p)
            
            col_btn_p.download_button(label="📥 Baixar PDF", 
                                      data=pdf_bytes, 
                                      file_name=f"Relatorio_{proj_pdf}.pdf", 
                                      mime='application/pdf')

# ==============================================================================
# ABA 2: CADASTRO PROJETOS (COM GED)
# ==============================================================================
elif aba == "Cadastro Projetos":
    st.header("📂 Projetos e Documentação (GED)")
    
    if not df_projetos.empty and "Origem" in df_projetos.columns:
        lista_origens = sorted(df_projetos["Origem"].dropna().unique().tolist())
    else:
        lista_origens = []

    with st.expander("➕ Novo Projeto", expanded=False):
        with st.form("form_projeto", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                cliente = st.text_input("Nome do Cliente")
                cidade = st.text_input("Cidade da Obra")
                origem = st.text_input("Origem (Ex: Instagram, Indicação)")
                tipo = st.selectbox("Tipo", ["Residencial Unifamiliar", "Residencial Multifamiliar", "Comercial", "Reforma", "Industrial"])
                area = st.number_input("Área (m²)", min_value=0.0)
            with c2:
                valor = st.number_input("Valor Proposta (R$)", min_value=0.0, step=100.0)
                servicos = st.multiselect("Serviços", ["Modelagem BIM", "Compatibilização", "Pranchas"])
                st.markdown("**Links Rápidos (GED):**")
                link_prop = st.text_input("Link Proposta")
                link_exec = st.text_input("Link Pasta Executivo")
                link_render = st.text_input("Link Pasta Renders")
                
            if st.form_submit_button("Salvar Projeto"):
                if cliente:
                    novo = pd.DataFrame([{
                        "ID_Projeto": len(df_projetos) + 1,
                        "Cliente": cliente, "Origem": origem, "Tipo": tipo, "Area_m2": area,
                        "Proposta_Aceita_R$": valor, "Servicos": ", ".join(servicos),
                        "Link_Proposta": link_prop, "Link_Pasta_Executivo": link_exec, 
                        "Link_Pasta_Renders": link_render, "Data_Cadastro": datetime.now().strftime("%Y-%m-%d"),
                        "Status_Geral": "Ativo", "Cidade": cidade, "Historico_Log": f"Criado em {get_now_br()}"
                    }])
                    save_data(pd.concat([df_projetos, novo], ignore_index=True), "Projetos")
                    st.success("Salvo!")
                    st.rerun()

    # --- GED VISUAL ---
    st.subheader("🗂️ Acesso Rápido aos Arquivos")
    if not df_projetos.empty:
        for idx, row in df_projetos[df_projetos["Status_Geral"]=="Ativo"].iterrows():
            with st.container(border=True):
                c_info, c_links = st.columns([2, 3])
                c_info.markdown(f"**{row['Cliente']}** ({row['Cidade']})")
                c_info.caption(f"Fase: {row['Status_Geral']}")
                
                # Botões de Link
                if row["Link_Proposta"]: c_links.link_button("📄 Proposta", row["Link_Proposta"])
                if row["Link_Pasta_Executivo"]: c_links.link_button("🏗️ Executivo", row["Link_Pasta_Executivo"])
                if row["Link_Pasta_Renders"]: c_links.link_button("🖼️ Renders", row["Link_Pasta_Renders"])

# ==============================================================================
# ABA 3: CONTROLE DE TAREFAS (COM TIMESHEET)
# ==============================================================================
elif aba == "Controle de Tarefas":
    st.header("✅ Atividades e Timesheet")
    
    lista_projetos = df_projetos["Cliente"].unique().tolist()
    
    with st.expander("➕ Nova Tarefa"):
        with st.form("task_form", clear_on_submit=True):
            proj = st.selectbox("Projeto", lista_projetos)
            c1, c2, c3 = st.columns(3)
            fase = c1.selectbox("Fase", ["Modelagem", "Compatibilização", "Pranchas"])
            resp = c2.selectbox("Responsável", ["GABRIEL", "MILENNA"])
            prio = c3.selectbox("Prioridade", ["Alta", "Média", "Baixa"])
            
            desc = st.text_input("Descrição")
            d_ini = st.date_input("Início")
            d_fim = st.date_input("Prazo")
            link_t = st.text_input("Link Específico")

            if st.form_submit_button("Criar"):
                id_p = df_projetos[df_projetos["Cliente"] == proj]["ID_Projeto"].values[0]
                nova = pd.DataFrame([{
                    "ID_Projeto": id_p, "Fase": fase, "Descricao": desc, "Responsavel": resp,
                    "Data_Inicio": str(d_ini), "Data_Deadline": str(d_fim), "Prioridade": prio,
                    "Status": "A Fazer", "Link_Tarefa": link_t, 
                    "Historico_Log": f"Criado em {get_now_br()}", "Data_Conclusao": "", "Horas_Gastas": 0.0
                }])
                save_data(pd.concat([df_tarefas, nova], ignore_index=True), "Tarefas")
                st.success("Criado!")
                st.rerun()

    st.divider()

    # --- LISTA COM TIMESHEET ---
    if not df_tarefas.empty:
        df_full = pd.merge(df_tarefas, df_projetos[["ID_Projeto", "Cliente"]], on="ID_Projeto", how="left")
        
        resp_f = st.multiselect("Responsável", ["GABRIEL", "MILENNA"], default=["GABRIEL", "MILENNA"])
        df_full = df_full[df_full["Responsavel"].isin(resp_f)]

        for prio in ["Alta", "Média", "Baixa"]:
            subset = df_full[(df_full["Prioridade"] == prio) & (df_full["Status"] != "Concluído")]
            if not subset.empty:
                st.markdown(f"### {prio}")
                for idx, row in subset.iterrows():
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                        c1.markdown(f"**{row['Cliente']}**")
                        c1.text(f"{row['Descricao']}")
                        c2.text(f"De: {format_date_br(row['Data_Inicio'])}")
                        c2.text(f"Até: {format_date_br(row['Data_Deadline'])}")
                        
                        # Edição de Status e Horas
                        novo_status = c3.selectbox("Status", ["A Fazer", "Em Andamento", "Revisão", "Concluído"], 
                                                   index=["A Fazer", "Em Andamento", "Revisão", "Concluído"].index(row['Status']), key=f"s_{idx}")
                        
                        # Campo de Timesheet
                        horas = c4.number_input("Horas Gastas", value=float(row.get("Horas_Gastas", 0.0)), step=0.5, key=f"h_{idx}")
                        
                        if c4.button("💾", key=f"b_{idx}"):
                            # Salvar alterações
                            df_tarefas.at[idx, "Status"] = novo_status
                            df_tarefas.at[idx, "Horas_Gastas"] = horas
                            
                            log = ""
                            if novo_status == "Concluído" and row['Status'] != "Concluído":
                                df_tarefas.at[idx, "Data_Conclusao"] = get_now_br()
                                log = f" | Concluído em {get_now_br()}"
                            
                            current_hist = str(df_tarefas.at[idx, "Historico_Log"])
                            df_tarefas.at[idx, "Historico_Log"] = current_hist + log
                            
                            save_data(df_tarefas, "Tarefas")
                            st.success("Atualizado!")
                            st.rerun()

# ==============================================================================
# ABA 4: FINANCEIRO (NOVO)
# ==============================================================================
elif aba == "Financeiro":
    st.header("💰 Controle Financeiro de Projetos")
    
    lista_projetos = df_projetos["Cliente"].unique().tolist()
    
    with st.expander("➕ Lançar Novo Recebimento / Parcela"):
        with st.form("fin_form", clear_on_submit=True):
            proj_fin = st.selectbox("Projeto", lista_projetos)
            desc_fin = st.text_input("Descrição (Ex: Entrada, Parcela 2, Final)")
            valor_fin = st.number_input("Valor (R$)", min_value=0.0, step=100.0)
            venc_fin = st.date_input("Data Vencimento")
            status_fin = st.selectbox("Status", ["Pendente", "Pago"])
            
            if st.form_submit_button("Lançar"):
                id_p = df_projetos[df_projetos["Cliente"] == proj_fin]["ID_Projeto"].values[0]
                data_pg = str(venc_fin) if status_fin == "Pago" else ""
                
                novo_fin = pd.DataFrame([{
                    "ID_Lancamento": len(df_financeiro) + 1,
                    "ID_Projeto": id_p,
                    "Descricao": desc_fin,
                    "Valor": valor_fin,
                    "Vencimento": str(venc_fin),
                    "Status": status_fin,
                    "Data_Pagamento": data_pg
                }])
                save_data(pd.concat([df_financeiro, novo_fin], ignore_index=True), "Financeiro")
                st.success("Lançamento financeiro registrado!")
                st.rerun()
    
    st.divider()
    
    # Tabela Financeira Editável
    if not df_financeiro.empty:
        # Merge para ver nome do cliente
        df_fin_view = pd.merge(df_financeiro, df_projetos[["ID_Projeto", "Cliente"]], on="ID_Projeto", how="left")
        
        # Filtros
        filtro_status = st.multiselect("Filtrar Status", ["Pendente", "Pago"], default=["Pendente"])
        df_fin_view = df_fin_view[df_fin_view["Status"].isin(filtro_status)]
        
        st.subheader("Extrato de Lançamentos")
        for idx, row in df_fin_view.iterrows():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                c1.markdown(f"**{row['Cliente']}**")
                c1.caption(row['Descricao'])
                c2.markdown(f"**{format_currency_br(row['Valor'])}**")
                c2.text(f"Venc: {format_date_br(row['Vencimento'])}")
                
                # Botão para dar baixa
                if row['Status'] == 'Pendente':
                    c3.warning("Pendente")
                    if c4.button("Dar Baixa (Receber)", key=f"baixa_{idx}"):
                        # Encontrar índice original no dataframe principal
                        real_idx = df_financeiro[df_financeiro["ID_Lancamento"] == row["ID_Lancamento"]].index[0]
                        df_financeiro.at[real_idx, "Status"] = "Pago"
                        df_financeiro.at[real_idx, "Data_Pagamento"] = str(datetime.now().date())
                        save_data(df_financeiro, "Financeiro")
                        st.balloons()
                        st.rerun()
                else:
                    c3.success(f"Pago em {format_date_br(row['Data_Pagamento'])}")
