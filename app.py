import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Engenharia 360º - Gestão",
    page_icon="🏗️",
    layout="wide"
)

# --- FUNÇÕES UTILITÁRIAS ---
def format_currency_br(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_date_br(date_obj):
    if pd.isnull(date_obj) or str(date_obj) == "NaT": return ""
    try:
        return pd.to_datetime(date_obj).strftime("%d/%m/%Y")
    except:
        return str(date_obj)

def get_now_br():
    fuso_br = pytz.timezone('America/Sao_Paulo')
    return datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")

def get_today_date():
    return datetime.now().date()

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

def gerar_pdf_status(projeto_dados, tarefas_proj):
    pdf = PDFRelatorio()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Cabeçalho
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, f"Cliente: {projeto_dados['Cliente']}", ln=True, fill=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 8, f"Local: {projeto_dados['Cidade']} | Tipo: {projeto_dados['Tipo']}", ln=True)
    pdf.cell(0, 8, f"Status Atual: {projeto_dados['Status_Geral']}", ln=True)
    pdf.ln(5)
    
    # Tarefas
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, "Status das Atividades Recentes:", ln=True)
    pdf.set_font("Arial", size=10)
    
    if not tarefas_proj.empty:
        tarefas_proj = tarefas_proj.sort_values(by="Status")
        for _, row in tarefas_proj.iterrows():
            status_clean = row['Status']
            marcador = "[OK]" if status_clean == 'Concluído' else "[..]"
            pdf.cell(15, 8, marcador, 0, 0)
            pdf.cell(120, 8, f"{row['Descricao']} ({row['Fase']})", 0, 0)
            pdf.cell(0, 8, f"{status_clean}", 0, 1)
    else:
        pdf.cell(0, 8, "Nenhuma tarefa registrada.", ln=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 10, "Documento gerado automaticamente pelo Sistema de Gestão.", ln=True)
    
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

# --- CARREGAMENTO INICIAL E TRATAMENTO ---
df_projetos = load_data("Projetos")
df_tarefas = load_data("Tarefas")
df_financeiro = load_data("Financeiro")

# Garantir Colunas PROJETOS
cols_proj = ["ID_Projeto", "Cliente", "Origem", "Tipo", "Area_m2", "Proposta_Aceita_R$", 
             "Servicos", "Link_Proposta", "Data_Cadastro", "Status_Geral", "Cidade", 
             "Historico_Log", "Link_Pasta_Executivo", "Link_Pasta_Renders"]
if df_projetos.empty: df_projetos = pd.DataFrame(columns=cols_proj)
else:
    for col in cols_proj:
        if col not in df_projetos.columns: df_projetos[col] = ""
    df_projetos["Proposta_Aceita_R$"] = pd.to_numeric(df_projetos["Proposta_Aceita_R$"], errors="coerce").fillna(0.0)
    df_projetos["Area_m2"] = pd.to_numeric(df_projetos["Area_m2"], errors="coerce").fillna(0.0)

# Garantir Colunas TAREFAS
cols_task = ["ID_Projeto", "Fase", "Disciplina", "Descricao", "Responsavel", 
             "Data_Inicio", "Data_Deadline", "Prioridade", "Status", 
             "Link_Tarefa", "Historico_Log", "Data_Conclusao", "Horas_Gastas"]
if df_tarefas.empty: df_tarefas = pd.DataFrame(columns=cols_task)
else:
    for col in cols_task:
        if col not in df_tarefas.columns: df_tarefas[col] = ""
    df_tarefas["Data_Deadline"] = pd.to_datetime(df_tarefas["Data_Deadline"], errors="coerce")
    df_tarefas["Data_Inicio"] = pd.to_datetime(df_tarefas["Data_Inicio"], errors="coerce")
    df_tarefas["Horas_Gastas"] = pd.to_numeric(df_tarefas["Horas_Gastas"], errors="coerce").fillna(0.0)

# Garantir Colunas FINANCEIRO
cols_fin = ["ID_Lancamento", "ID_Projeto", "Descricao", "Valor", "Vencimento", "Status", "Data_Pagamento"]
if df_financeiro.empty: df_financeiro = pd.DataFrame(columns=cols_fin)
else:
    df_financeiro["Valor"] = pd.to_numeric(df_financeiro["Valor"], errors="coerce").fillna(0.0)
    df_financeiro["Vencimento"] = pd.to_datetime(df_financeiro["Vencimento"], errors="coerce")


# --- MENU LATERAL ---
st.sidebar.title("🏗️ Engenharia 360º")
aba = st.sidebar.radio("Menu Principal", 
    ["Dash Operacional", "Dash Financeiro", "Cadastro Projetos", "Controle de Tarefas", "Controle Financeiro"]
)

# ==============================================================================
# ABA 1: DASHBOARD OPERACIONAL
# ==============================================================================
if aba == "Dash Operacional":
    st.header("⚙️ Dashboard Operacional")
    st.markdown("---")

    if df_projetos.empty:
        st.warning("Cadastre projetos para iniciar.")
    else:
        hoje = pd.to_datetime(get_today_date())
        pendentes = df_tarefas[df_tarefas["Status"] != "Concluído"].copy()
        
        atrasadas = pendentes[pendentes["Data_Deadline"] < hoje]
        urgentes = pendentes[(pendentes["Data_Deadline"] >= hoje) & (pendentes["Data_Deadline"] <= hoje + timedelta(days=1))]
        proj_ativos = df_projetos[df_projetos["Status_Geral"] == "Ativo"]

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Projetos em Andamento", len(proj_ativos))
        k2.metric("Tarefas Atrasadas", len(atrasadas), delta=-len(atrasadas), delta_color="inverse")
        k3.metric("Urgentes (48h)", len(urgentes), delta="Atenção" if len(urgentes) > 0 else "Ok", delta_color="inverse")
        k4.metric("Total Pendências", len(pendentes))

        g1, g2 = st.columns([2, 1])
        
        with g1:
            st.subheader("📅 Cronograma (Gantt)")
            if not pendentes.empty:
                tasks_gantt = pendentes.copy()
                mask_sem_ini = pd.isna(tasks_gantt["Data_Inicio"])
                tasks_gantt.loc[mask_sem_ini, "Data_Inicio"] = tasks_gantt.loc[mask_sem_ini, "Data_Deadline"] - timedelta(days=5)
                tasks_gantt = pd.merge(tasks_gantt, df_projetos[["ID_Projeto", "Cliente"]], on="ID_Projeto", how="left")
                tasks_gantt = tasks_gantt.dropna(subset=["Data_Inicio", "Data_Deadline"])
                
                if not tasks_gantt.empty:
                    fig_gantt = px.timeline(tasks_gantt, x_start="Data_Inicio", x_end="Data_Deadline", 
                                            y="Cliente", color="Responsavel", hover_data=["Descricao", "Status"],
                                            color_discrete_map={"GABRIEL": "#3366CC", "MILENNA": "#DC3912"})
                    fig_gantt.update_yaxes(autorange="reversed")
                    st.plotly_chart(fig_gantt, use_container_width=True)
                else:
                    st.info("Datas insuficientes para gerar gráfico.")
            else:
                st.info("Nenhuma tarefa pendente.")

        with g2:
            st.subheader("👥 Carga de Trabalho")
            if not pendentes.empty:
                contagem_resp = pendentes["Responsavel"].value_counts().reset_index()
                contagem_resp.columns = ["Responsavel", "Tarefas"]
                fig_carga = px.bar(contagem_resp, x="Responsavel", y="Tarefas", text_auto=True, color="Responsavel")
                st.plotly_chart(fig_carga, use_container_width=True)

        st.markdown("---")
        c_pdf1, c_pdf2 = st.columns([3, 1])
        c_pdf1.subheader("📄 Gerador de Relatório")
        if not proj_ativos.empty:
            proj_sel_pdf = c_pdf1.selectbox("Selecione o Projeto:", proj_ativos["Cliente"].unique())
            if c_pdf2.button("Gerar Relatório PDF"):
                dados_p = df_projetos[df_projetos["Cliente"] == proj_sel_pdf].iloc[0]
                tasks_p = df_tarefas[df_tarefas["ID_Projeto"] == dados_p["ID_Projeto"]]
                pdf_bytes = gerar_pdf_status(dados_p, tasks_p)
                c_pdf2.download_button("📥 Baixar Arquivo", data=pdf_bytes, file_name=f"Status_{proj_sel_pdf}.pdf", mime='application/pdf')

# ==============================================================================
# ABA 2: DASHBOARD FINANCEIRO (Agora com Inteligência Comercial)
# ==============================================================================
elif aba == "Dash Financeiro":
    st.header("💰 Dashboard Financeiro e Comercial")
    st.markdown("---")
    
    if df_financeiro.empty:
        st.warning("Sem dados financeiros.")
    else:
        df_fin_calc = df_financeiro.dropna(subset=["Vencimento"]).copy()
        
        total_previsto = df_financeiro["Valor"].sum()
        recebido = df_financeiro[df_financeiro["Status"] == "Pago"]["Valor"].sum()
        a_receber = df_financeiro[df_financeiro["Status"] == "Pendente"]["Valor"].sum()
        
        hoje = pd.to_datetime(get_today_date())
        atrasados = df_fin_calc[(df_fin_calc["Status"] == "Pendente") & (df_fin_calc["Vencimento"] < hoje)]
        valor_atrasado = atrasados["Valor"].sum()

        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Total em Caixa", format_currency_br(recebido))
        f2.metric("A Receber", format_currency_br(a_receber))
        f3.metric("⚠️ Em Atraso", format_currency_br(valor_atrasado), delta_color="inverse")
        
        # Métrica Extra: Preço Médio do m² (Considerando valor de contrato)
        area_total = df_projetos["Area_m2"].sum()
        contrato_total = df_projetos["Proposta_Aceita_R$"].sum()
        preco_m2 = (contrato_total / area_total) if area_total > 0 else 0
        f4.metric("Preço Médio/m²", format_currency_br(preco_m2))

        st.markdown("---")
        
        # --- ANÁLISE COMERCIAL (USANDO TIPO E CIDADE) ---
        st.subheader("📊 Inteligência Comercial")
        c_tipo, c_cidade = st.columns(2)
        
        with c_tipo:
            # Agrupar Valor de Contrato por Tipo
            if not df_projetos.empty:
                df_tipo = df_projetos.groupby("Tipo")["Proposta_Aceita_R$"].sum().reset_index()
                fig_tipo = px.pie(df_tipo, values="Proposta_Aceita_R$", names="Tipo", title="Faturamento por Tipo de Obra", hole=0.4)
                st.plotly_chart(fig_tipo, use_container_width=True)
                
        with c_cidade:
            # Agrupar Valor de Contrato por Cidade
            if not df_projetos.empty:
                df_cidade = df_projetos.groupby("Cidade")["Proposta_Aceita_R$"].sum().reset_index()
                fig_cidade = px.bar(df_cidade, x="Cidade", y="Proposta_Aceita_R$", title="Faturamento por Cidade", text_auto=True)
                fig_cidade.update_layout(yaxis_title="Valor Contratado (R$)")
                st.plotly_chart(fig_cidade, use_container_width=True)

        st.markdown("---")
        
        # --- FLUXO E ATRASOS ---
        fg1, fg2 = st.columns(2)
        
        with fg1:
            st.subheader("📈 Fluxo de Entradas (Vencimento)")
            if not df_fin_calc.empty:
                df_fin_calc["Mes_Ano"] = df_fin_calc["Vencimento"].dt.strftime("%Y-%m")
                fluxo = df_fin_calc.groupby("Mes_Ano")["Valor"].sum().reset_index()
                fig_fluxo = px.bar(fluxo, x="Mes_Ano", y="Valor", text_auto=True)
                st.plotly_chart(fig_fluxo, use_container_width=True)
            
        with fg2:
            st.subheader("🚨 Contas em Atraso")
            if not atrasados.empty:
                atrasados_view = pd.merge(atrasados, df_projetos[["ID_Projeto", "Cliente"]], on="ID_Projeto", how="left")
                atrasados_view["Vencimento_Fmt"] = atrasados_view["Vencimento"].apply(lambda x: format_date_br(x))
                atrasados_view["Valor_Fmt"] = atrasados_view["Valor"].apply(lambda x: format_currency_br(x))
                st.dataframe(atrasados_view[["Cliente", "Descricao", "Vencimento_Fmt", "Valor_Fmt"]], hide_index=True, use_container_width=True)
            else:
                st.success("Tudo em dia!")

# ==============================================================================
# ABA 3: CADASTRO PROJETOS (VISUAL LIMPO E EDITÁVEL)
# ==============================================================================
elif aba == "Cadastro Projetos":
    st.header("📂 Projetos e Documentação")
    
    if not df_projetos.empty and "Origem" in df_projetos.columns:
        lista_origens = sorted(df_projetos["Origem"].dropna().unique().tolist())
    else:
        lista_origens = []

    # --- FORMULÁRIO (MANTIDO IGUAL) ---
    with st.expander("➕ Novo Projeto", expanded=False):
        with st.form("form_projeto", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                cliente = st.text_input("Nome do Cliente")
                cidade = st.text_input("Cidade da Obra")
                origem = st.text_input("Origem")
                tipo = st.selectbox("Tipo", ["Residencial Unifamiliar", "Residencial Multifamiliar", "Comercial", "Reforma", "Industrial"])
                area = st.number_input("Área (m²)", min_value=0.0)
            with c2:
                valor = st.number_input("Valor Proposta (R$)", min_value=0.0, step=100.0)
                servicos = st.multiselect("Serviços", ["Modelagem BIM", "Compatibilização", "Pranchas"])
                st.markdown("**Links Rápidos (GED):**")
                link_prop = st.text_input("Link Pasta Financeiro/Proposta")
                link_exec = st.text_input("Link Pasta Projetos/Executivo")
                link_render = st.text_input("Link Pasta Renders")
                
            if st.form_submit_button("Salvar Projeto"):
                if cliente:
                    novo = pd.DataFrame([{
                        "ID_Projeto": len(df_projetos) + 1, "Cliente": cliente, "Origem": origem, 
                        "Tipo": tipo, "Area_m2": area, "Proposta_Aceita_R$": valor, 
                        "Servicos": ", ".join(servicos), "Link_Proposta": link_prop, 
                        "Link_Pasta_Executivo": link_exec, "Link_Pasta_Renders": link_render, 
                        "Data_Cadastro": datetime.now().strftime("%Y-%m-%d"),
                        "Status_Geral": "Ativo", "Cidade": cidade, "Historico_Log": f"Criado em {get_now_br()}"
                    }])
                    save_data(pd.concat([df_projetos, novo], ignore_index=True), "Projetos")
                    st.success("Salvo!")
                    st.rerun()

    st.divider()
    st.subheader("Gerenciar Carteira")

    if df_projetos.empty:
        st.info("Nenhum projeto cadastrado.")
    else:
        # Ordenar: Ativos primeiro
        df_view = df_projetos.sort_values(by="Status_Geral", ascending=True)

        for idx, row in df_view.iterrows():
            # Ícone visual do status
            icon_status = "🟢" if row['Status_Geral'] == 'Ativo' else "🏁"
            
            # O EXPANDER É O NOME DO PROJETO
            with st.expander(f"{icon_status} {row['Cliente']} | {row['Cidade']}"):
                
                # Layout interno do Card
                c_dados, c_links, c_edit = st.columns([2, 2, 2])
                
                # Coluna 1: Dados fixos
                with c_dados:
                    st.caption("Detalhes:")
                    st.write(f"**Tipo:** {row['Tipo']}")
                    st.write(f"**Área:** {row['Area_m2']} m²")
                    st.write(f"**Serviços:** {row['Servicos']}")
                
                # Coluna 2: Links (Blindados)
                with c_links:
                    st.caption("Acesso Rápido:")
                    def criar_botao(label, url):
                        s_url = str(url).strip()
                        if s_url and s_url.lower() != "nan":
                            st.link_button(label, s_url)
                    
                    criar_botao("💰 Financeiro", row["Link_Proposta"])
                    criar_botao("📂 Projetos", row["Link_Pasta_Executivo"])
                    criar_botao("🖼️ Renders", row["Link_Pasta_Renders"])

                # Coluna 3: Edição de Status
                with c_edit:
                    st.caption("Controle:")
                    # Seletor de Status
                    opcoes_status = ["Ativo", "Concluído", "Suspenso", "Cancelado"]
                    idx_st = opcoes_status.index(row['Status_Geral']) if row['Status_Geral'] in opcoes_status else 0
                    
                    novo_status = st.selectbox("Situação do Projeto", opcoes_status, index=idx_st, key=f"st_proj_{idx}")
                    
                    # Botão Salvar Específico deste projeto
                    if st.button("Atualizar Status", key=f"btn_up_{idx}"):
                        if novo_status != row['Status_Geral']:
                            df_projetos.at[idx, "Status_Geral"] = novo_status
                            
                            # Log histórico
                            hist = str(df_projetos.at[idx, "Historico_Log"])
                            msg = f" | Status alterado para {novo_status} em {get_now_br()}"
                            df_projetos.at[idx, "Historico_Log"] = hist + msg
                            
                            save_data(df_projetos, "Projetos")
                            st.success("Atualizado!")
                            st.rerun()
# ==============================================================================
# ABA 4: CONTROLE DE TAREFAS (AJUSTE DE LAYOUT STATUS)
# ==============================================================================
elif aba == "Controle de Tarefas":
    st.header("✅ Atividades e Timesheet")
    lista_projetos = df_projetos["Cliente"].unique().tolist()
    
    with st.expander("➕ Nova Tarefa", expanded=False):
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

            if st.form_submit_button("Criar Tarefa"):
                if proj:
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
    if not df_tarefas.empty:
        df_full = pd.merge(df_tarefas, df_projetos[["ID_Projeto", "Cliente"]], on="ID_Projeto", how="left")
        resp_f = st.multiselect("Filtrar Responsável", ["GABRIEL", "MILENNA"], default=["GABRIEL", "MILENNA"])
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
                        c2.text(f"Até: {format_date_br(row['Data_Deadline'])}")
                        
                        # MUDANÇA AQUI: Label dentro do componente para alinhar
                        novo_status = c3.selectbox("Status", ["A Fazer", "Em Andamento", "Revisão", "Concluído"], 
                                                   index=["A Fazer", "Em Andamento", "Revisão", "Concluído"].index(row['Status']), 
                                                   key=f"s_{idx}")
                                                   
                        horas = c4.number_input("Horas Gastas", value=float(row.get("Horas_Gastas", 0.0)), step=0.5, key=f"h_{idx}")
                        
                        if c4.button("💾 Salvar", key=f"b_{idx}"):
                            df_tarefas.at[idx, "Status"] = novo_status
                            df_tarefas.at[idx, "Horas_Gastas"] = horas
                            if novo_status == "Concluído" and row['Status'] != "Concluído":
                                df_tarefas.at[idx, "Data_Conclusao"] = get_now_br()
                            save_data(df_tarefas, "Tarefas")
                            st.rerun()

        st.markdown("---")
        with st.expander("✅ Histórico de Entregas"):
            concluidas = df_full[df_full["Status"] == "Concluído"]
            if not concluidas.empty:
                for idx, row in concluidas.iterrows():
                    with st.container(border=True):
                        col_a, col_b = st.columns([5, 1])
                        col_a.markdown(f"~~**{row['Cliente']}** - {row['Descricao']}~~ (Entregue: {row.get('Data_Conclusao', '-')})")
                        if col_b.button("Reabrir", key=f"re_{idx}"):
                            df_tarefas.at[idx, "Status"] = "Em Andamento"
                            df_tarefas.at[idx, "Data_Conclusao"] = ""
                            save_data(df_tarefas, "Tarefas")
                            st.rerun()
# ==============================================================================
# ABA 5: CONTROLE FINANCEIRO (TITULO LIMPO)
# ==============================================================================
elif aba == "Controle Financeiro":
    st.header("💰 Lançamentos e Baixas")
    
    lista_projetos = df_projetos["Cliente"].unique().tolist()
    
    with st.expander("➕ Novo Lançamento", expanded=True):
        with st.form("fin_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            proj_fin = c1.selectbox("Projeto", lista_projetos)
            desc_fin = c2.text_input("Descrição (Ex: Entrada 30%)")
            valor_fin = c3.number_input("Valor (R$)", min_value=0.0, step=100.0)
            
            c4, c5 = st.columns(2)
            venc_fin = c4.date_input("Vencimento")
            status_fin = c5.selectbox("Status Inicial", ["Pendente", "Pago"])
            
            if st.form_submit_button("Registrar Lançamento"):
                if proj_fin:
                    id_p = df_projetos[df_projetos["Cliente"] == proj_fin]["ID_Projeto"].values[0]
                    data_pg = str(venc_fin) if status_fin == "Pago" else ""
                    
                    novo_fin = pd.DataFrame([{
                        "ID_Lancamento": len(df_financeiro) + 1, "ID_Projeto": id_p,
                        "Descricao": desc_fin, "Valor": valor_fin,
                        "Vencimento": str(venc_fin), "Status": status_fin, "Data_Pagamento": data_pg
                    }])
                    
                    df_final = pd.concat([df_financeiro, novo_fin], ignore_index=True)
                    df_final["Vencimento"] = pd.to_datetime(df_final["Vencimento"]).dt.strftime("%Y-%m-%d")
                    save_data(df_final, "Financeiro")
                    st.success("Lançamento registrado!")
                    st.rerun()
    
    st.divider()
    
    if not df_financeiro.empty:
        st.subheader("Extrato por Projeto")
        df_view = pd.merge(df_financeiro, df_projetos[["ID_Projeto", "Cliente"]], on="ID_Projeto", how="left")
        projetos_com_fin = df_view["Cliente"].unique()
        
        if len(projetos_com_fin) == 0:
            st.info("Nenhum lançamento encontrado.")
        
        for cliente in projetos_com_fin:
            subset = df_view[df_view["Cliente"] == cliente]
            
            # Verifica se tem alguma pendência para definir a cor do ícone
            tem_pendencia = subset[subset["Status"] == "Pendente"].shape[0] > 0
            icone = "🔴" if tem_pendencia else "✅"
            
            # TÍTULO LIMPO: Apenas ícone e nome do cliente
            with st.expander(f"{icone} {cliente}"):
                
                for idx, row in subset.iterrows():
                    with st.container(border=True):
                        c_desc, c_val, c_btn = st.columns([3, 2, 2])
                        
                        c_desc.markdown(f"**{row['Descricao']}**")
                        data_venc_fmt = format_date_br(row['Vencimento'])
                        
                        if row['Status'] == 'Pendente':
                            c_desc.caption(f"Vence em: {data_venc_fmt}")
                        else:
                            c_desc.caption(f"Pago em: {format_date_br(row['Data_Pagamento'])}")
                        
                        c_val.markdown(f"**{format_currency_br(row['Valor'])}**")
                        
                        if row['Status'] == 'Pendente':
                            if c_btn.button("Receber", key=f"rec_{row['ID_Lancamento']}"):
                                real_idx = df_financeiro[df_financeiro["ID_Lancamento"] == row["ID_Lancamento"]].index[0]
                                df_financeiro.at[real_idx, "Status"] = "Pago"
                                df_financeiro.at[real_idx, "Data_Pagamento"] = str(get_today_date())
                                df_financeiro["Vencimento"] = pd.to_datetime(df_financeiro["Vencimento"]).dt.strftime("%Y-%m-%d")
                                save_data(df_financeiro, "Financeiro")
                                st.balloons()
                                st.rerun()
                        else:
                            c_btn.success("Pago")
    else:
        st.info("Nenhum lançamento financeiro registrado ainda.")
