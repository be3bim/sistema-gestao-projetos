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
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, f"Cliente: {projeto_dados['Cliente']}", ln=True, fill=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 8, f"Local: {projeto_dados['Cidade']} | Tipo: {projeto_dados['Tipo']}", ln=True)
    pdf.cell(0, 8, f"Status Atual: {projeto_dados['Status_Geral']}", ln=True)
    pdf.ln(5)
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
df_despesas = load_data("Despesas")

# 1. Colunas PROJETOS
cols_proj = ["ID_Projeto", "Cliente", "Origem", "Tipo", "Area_m2", "Proposta_Aceita_R$", 
             "Servicos", "Link_Proposta", "Link_Pasta_Executivo", "Link_Pasta_Renders", 
             "Data_Cadastro", "Status_Geral", "Cidade", "Historico_Log"]
if df_projetos.empty: df_projetos = pd.DataFrame(columns=cols_proj)
else:
    for col in cols_proj:
        if col not in df_projetos.columns: df_projetos[col] = ""
    df_projetos["Proposta_Aceita_R$"] = pd.to_numeric(df_projetos["Proposta_Aceita_R$"], errors="coerce").fillna(0.0)
    df_projetos["Area_m2"] = pd.to_numeric(df_projetos["Area_m2"], errors="coerce").fillna(0.0)

# 2. Colunas TAREFAS
cols_task = ["ID_Projeto", "Fase", "Disciplina", "Descricao", "Responsavel", 
             "Data_Inicio", "Data_Deadline", "Prioridade", "Status", 
             "Historico_Log", "Data_Conclusao", "Horas_Gastas"]
if df_tarefas.empty: df_tarefas = pd.DataFrame(columns=cols_task)
else:
    for col in cols_task:
        if col not in df_tarefas.columns: df_tarefas[col] = ""
    df_tarefas["Data_Deadline"] = pd.to_datetime(df_tarefas["Data_Deadline"], errors="coerce")
    df_tarefas["Data_Inicio"] = pd.to_datetime(df_tarefas["Data_Inicio"], errors="coerce")
    df_tarefas["Horas_Gastas"] = pd.to_numeric(df_tarefas["Horas_Gastas"], errors="coerce").fillna(0.0)

# 3. Colunas FINANCEIRO
cols_fin = ["ID_Lancamento", "ID_Projeto", "Descricao", "Valor", "Vencimento", "Status", "Data_Pagamento", "Valor_Imposto"]
if df_financeiro.empty: df_financeiro = pd.DataFrame(columns=cols_fin)
else:
    if "Valor_Imposto" not in df_financeiro.columns: df_financeiro["Valor_Imposto"] = 0.0
    df_financeiro["Valor"] = pd.to_numeric(df_financeiro["Valor"], errors="coerce").fillna(0.0)
    df_financeiro["Valor_Imposto"] = pd.to_numeric(df_financeiro["Valor_Imposto"], errors="coerce").fillna(0.0)
    df_financeiro["Vencimento"] = pd.to_datetime(df_financeiro["Vencimento"], errors="coerce")

# 4. Colunas DESPESAS
cols_desp = ["ID_Despesa", "Descricao", "Categoria", "Valor", "Vencimento", "Status", "Data_Pagamento"]
if df_despesas.empty: df_despesas = pd.DataFrame(columns=cols_desp)
else:
    df_despesas["Valor"] = pd.to_numeric(df_despesas["Valor"], errors="coerce").fillna(0.0)
    df_despesas["Vencimento"] = pd.to_datetime(df_despesas["Vencimento"], errors="coerce")


# --- MENU LATERAL ---
st.sidebar.title("🏗️ Engenharia 360º")
aba = st.sidebar.radio("Menu Principal", 
    ["Dash Operacional", "Dash Financeiro", "Cadastro Projetos", "Controle de Tarefas", "Controle Financeiro", "Controle Despesas"]
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
                    st.info("Datas insuficientes.")
            else:
                st.info("Sem tarefas pendentes.")

        with g2:
            st.subheader("👥 Carga de Trabalho")
            if not pendentes.empty:
                contagem_resp = pendentes["Responsavel"].value_counts().reset_index()
                contagem_resp.columns = ["Responsavel", "Tarefas"]
                fig_carga = px.bar(contagem_resp, x="Responsavel", y="Tarefas", text_auto=True, color="Responsavel")
                st.plotly_chart(fig_carga, use_container_width=True)

        st.markdown("---")
        c_pdf1, c_pdf2 = st.columns([3, 1])
        c_pdf1.subheader("📄 Relatório de Status")
        if not proj_ativos.empty:
            proj_sel_pdf = c_pdf1.selectbox("Selecione o Projeto:", proj_ativos["Cliente"].unique())
            if c_pdf2.button("Gerar PDF"):
                dados_p = df_projetos[df_projetos["Cliente"] == proj_sel_pdf].iloc[0]
                tasks_p = df_tarefas[df_tarefas["ID_Projeto"] == dados_p["ID_Projeto"]]
                pdf_bytes = gerar_pdf_status(dados_p, tasks_p)
                c_pdf2.download_button("📥 Baixar PDF", data=pdf_bytes, file_name=f"Status_{proj_sel_pdf}.pdf", mime='application/pdf')

# ==============================================================================
# ABA 2: DASHBOARD FINANCEIRO (COMPLETO V6)
# ==============================================================================
elif aba == "Dash Financeiro":
    ano_atual = datetime.now().year
    st.header(f"💰 Dashboard Financeiro ({ano_atual})")
    st.markdown("---")
    
    if df_financeiro.empty:
        st.warning("Sem dados financeiros.")
    else:
        # --- PREPARAÇÃO DOS DADOS ---
        df_fin_calc = df_financeiro.dropna(subset=["Vencimento"]).copy()
        df_fin_calc["Vencimento"] = pd.to_datetime(df_fin_calc["Vencimento"], errors="coerce")
        df_fin_calc["Data_Pagamento"] = pd.to_datetime(df_fin_calc["Data_Pagamento"], errors="coerce")
        
        # Data Híbrida (Caixa vs Competência)
        df_fin_calc["Data_Considerada"] = df_fin_calc.apply(
            lambda x: x["Data_Pagamento"] if (x["Status"] == "Pago" and pd.notnull(x["Data_Pagamento"])) else x["Vencimento"], 
            axis=1
        )
        df_fin_calc["Data_Considerada"] = pd.to_datetime(df_fin_calc["Data_Considerada"], errors="coerce")
        df_fin_calc["Ano_Ref"] = df_fin_calc["Data_Considerada"].dt.year
        
        # Despesas (Saídas)
        df_desp_calc = df_despesas.dropna(subset=["Vencimento"]).copy()
        df_desp_calc["Vencimento"] = pd.to_datetime(df_desp_calc["Vencimento"], errors="coerce")
        df_desp_calc["Data_Pagamento"] = pd.to_datetime(df_desp_calc["Data_Pagamento"], errors="coerce")
        
        df_desp_calc["Data_Considerada"] = df_desp_calc.apply(
            lambda x: x["Data_Pagamento"] if (x["Status"] == "Pago" and pd.notnull(x["Data_Pagamento"])) else x["Vencimento"], 
            axis=1
        )
        df_desp_calc["Data_Considerada"] = pd.to_datetime(df_desp_calc["Data_Considerada"], errors="coerce")
        df_desp_calc["Ano_Ref"] = df_desp_calc["Data_Considerada"].dt.year

        # --- FILTRO ANO ATUAL ---
        entradas_ano = df_fin_calc[df_fin_calc["Ano_Ref"] == ano_atual]
        saidas_ano = df_desp_calc[df_desp_calc["Ano_Ref"] == ano_atual]
        
        # Totais
        receita_bruta = entradas_ano[entradas_ano["Status"] == "Pago"]["Valor"].sum()
        impostos_pagos = entradas_ano[entradas_ano["Status"] == "Pago"]["Valor_Imposto"].sum()
        custos_fixos_pagos = saidas_ano[saidas_ano["Status"] == "Pago"]["Valor"].sum()
        lucro_liquido = receita_bruta - impostos_pagos - custos_fixos_pagos
        margem_lucro = (lucro_liquido / receita_bruta * 100) if receita_bruta > 0 else 0
        a_receber = entradas_ano[entradas_ano["Status"] == "Pendente"]["Valor"].sum()
        a_pagar = saidas_ano[saidas_ano["Status"] == "Pendente"]["Valor"].sum()

        # --- KPIs ---
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Receita Bruta (Caixa)", format_currency_br(receita_bruta))
        c2.metric("Impostos (15.5%)", format_currency_br(impostos_pagos), delta="- Gov", delta_color="inverse")
        c3.metric("Custos Fixos", format_currency_br(custos_fixos_pagos), delta="- Desp", delta_color="inverse")
        c4.metric("Lucro Líquido Real", format_currency_br(lucro_liquido), delta=f"{margem_lucro:.1f}%")
        c5.metric("Previsão Futura", format_currency_br(a_receber - a_pagar), help="A Receber - A Pagar (Deste ano)")

        st.markdown("---")
        
        # --- GRÁFICOS FLUXO ---
        g1, g2 = st.columns(2)
        with g1:
            st.subheader(f"📊 Composição Financeira")
            dados_fin = pd.DataFrame({
                "Categoria": ["Receita Bruta", "Impostos", "Custos Fixos", "Lucro Líquido"],
                "Valor": [receita_bruta, -impostos_pagos, -custos_fixos_pagos, lucro_liquido]
            })
            fig_fin = px.bar(dados_fin, x="Categoria", y="Valor", text_auto=True, color="Categoria",
                             color_discrete_sequence=["#2E86C1", "#E74C3C", "#E67E22", "#27AE60"])
            st.plotly_chart(fig_fin, use_container_width=True)
            
        with g2:
            st.subheader(f"📈 Fluxo Mensal Real")
            if not entradas_ano.empty:
                entradas_ano["Mes"] = entradas_ano["Data_Considerada"].dt.strftime("%Y-%m")
                fluxo_ent = entradas_ano.groupby("Mes")["Valor"].sum().reset_index()
                fluxo_ent["Tipo"] = "Entrada"
            else:
                fluxo_ent = pd.DataFrame()
            
            if not saidas_ano.empty:
                saidas_ano["Mes"] = saidas_ano["Data_Considerada"].dt.strftime("%Y-%m")
                fluxo_sai = saidas_ano.groupby("Mes")["Valor"].sum().reset_index()
                fluxo_sai["Tipo"] = "Saída"
            else:
                fluxo_sai = pd.DataFrame()
            
            df_fluxo = pd.concat([fluxo_ent, fluxo_sai])
            if not df_fluxo.empty:
                df_fluxo = df_fluxo.sort_values("Mes")
                fig_fluxo = px.bar(df_fluxo, x="Mes", y="Valor", color="Tipo", barmode="group",
                                   color_discrete_map={"Entrada": "#27AE60", "Saída": "#E74C3C"})
                st.plotly_chart(fig_fluxo, use_container_width=True)
            else:
                st.info("Sem movimentações.")

        st.markdown("---")

        # =========================================================
        # SEÇÃO 1: INTELIGÊNCIA COMERCIAL
        # =========================================================
        st.subheader(f"🧠 Inteligência Comercial ({ano_atual})")
        
        df_analise = pd.merge(entradas_ano, df_projetos[["ID_Projeto", "Cliente", "Origem", "Tipo", "Cidade", "Area_m2"]], 
                              on="ID_Projeto", how="left")
        
        if df_analise.empty:
            st.info("Sem dados comerciais.")
        else:
            col_i1, col_i2 = st.columns(2)
            with col_i1:
                st.markdown("**💰 Receita por Origem**")
                if "Origem" in df_analise.columns:
                    df_origem = df_analise.groupby("Origem")["Valor"].sum().reset_index()
                    if not df_origem.empty:
                        fig_origem = px.pie(df_origem, values="Valor", names="Origem", hole=0.4,
                                            color_discrete_sequence=px.colors.qualitative.Pastel)
                        st.plotly_chart(fig_origem, use_container_width=True)

            with col_i2:
                st.markdown("**🏗️ Receita por Tipo**")
                if "Tipo" in df_analise.columns:
                    df_tipo = df_analise.groupby("Tipo")["Valor"].sum().reset_index()
                    if not df_tipo.empty:
                        fig_tipo = px.bar(df_tipo, x="Valor", y="Tipo", orientation='h', text_auto=True)
                        st.plotly_chart(fig_tipo, use_container_width=True)

            # =========================================================
            # SEÇÃO 2: EFICIÊNCIA E HORAS
            # =========================================================
            st.markdown("---")
            st.subheader("⏱️ Eficiência e Lucratividade Real (Horas Gastas)")
            
            horas_por_proj = df_tarefas.groupby("ID_Projeto")["Horas_Gastas"].sum().reset_index()
            proj_financeiro = df_projetos[["ID_Projeto", "Cliente", "Proposta_Aceita_R$"]].copy()
            df_eficiencia = pd.merge(proj_financeiro, horas_por_proj, on="ID_Projeto", how="inner")
            
            df_eficiencia = df_eficiencia[df_eficiencia["Horas_Gastas"] > 0] 
            df_eficiencia["Valor_Hora_Real"] = df_eficiencia["Proposta_Aceita_R$"] / df_eficiencia["Horas_Gastas"]
            
            if not df_eficiencia.empty:
                df_eficiencia = df_eficiencia.sort_values(by="Valor_Hora_Real", ascending=True)
                
                c_efic1, c_efic2 = st.columns([2, 1])
                with c_efic1:
                    st.markdown("**🏆 Ranking: Valor Real da Hora (R$/h)**")
                    fig_hour = px.bar(df_eficiencia, x="Valor_Hora_Real", y="Cliente", orientation='h', text_auto=".2f",
                                      color="Valor_Hora_Real", color_continuous_scale="RdYlGn")
                    fig_hour.update_layout(xaxis_title="Valor por Hora (R$)", yaxis_title="")
                    st.plotly_chart(fig_hour, use_container_width=True)
                    
                with c_efic2:
                    st.markdown("**📉 Horas Totais**")
                    fig_pizza_h = px.pie(df_eficiencia, values="Horas_Gastas", names="Cliente", hole=0.4)
                    st.plotly_chart(fig_pizza_h, use_container_width=True)
            else:
                st.info("Nenhuma hora registrada.")

# ==============================================================================
# ABA 3: CADASTRO PROJETOS
# ==============================================================================
elif aba == "Cadastro Projetos":
    st.header("📂 Projetos e Documentação")
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
        st.info("Nenhum projeto.")
    else:
        df_view = df_projetos.sort_values(by="Status_Geral", ascending=True)
        for idx, row in df_view.iterrows():
            icon_status = "🟢" if row['Status_Geral'] == 'Ativo' else "🏁"
            with st.expander(f"{icon_status} {row['Cliente']} | {row['Cidade']}"):
                c_dados, c_links, c_edit = st.columns([2, 2, 2])
                with c_dados:
                    st.caption("Detalhes:")
                    st.write(f"**Tipo:** {row['Tipo']}")
                    st.write(f"**Área:** {row['Area_m2']} m²")
                with c_links:
                    st.caption("Acesso Rápido:")
                    def criar_botao(label, url):
                        s_url = str(url).strip()
                        if s_url and s_url.lower() != "nan": st.link_button(label, s_url)
                    criar_botao("💰 Financeiro", row["Link_Proposta"])
                    criar_botao("📂 Projetos", row["Link_Pasta_Executivo"])
                    criar_botao("🖼️ Renders", row["Link_Pasta_Renders"])
                with c_edit:
                    st.caption("Controle:")
                    opcoes_status = ["Ativo", "Concluído", "Suspenso", "Cancelado"]
                    idx_st = opcoes_status.index(row['Status_Geral']) if row['Status_Geral'] in opcoes_status else 0
                    novo_status = st.selectbox("Situação", opcoes_status, index=idx_st, key=f"st_proj_{idx}")
                    if st.button("Atualizar", key=f"btn_up_{idx}"):
                        if novo_status != row['Status_Geral']:
                            df_projetos.at[idx, "Status_Geral"] = novo_status
                            save_data(df_projetos, "Projetos")
                            st.success("Atualizado!")
                            st.rerun()

# ==============================================================================
# ABA 4: CONTROLE DE TAREFAS (COM FILTRO DE PROJETOS ATIVOS)
# ==============================================================================
elif aba == "Controle de Tarefas":
    st.header("✅ Atividades e Timesheet")
    
    # MUDANÇA: Filtra apenas projetos com Status "Ativo" para o formulário
    lista_projetos = df_projetos[df_projetos["Status_Geral"] == "Ativo"]["Cliente"].unique().tolist()
    
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
            
            if st.form_submit_button("Criar Tarefa"):
                if proj:
                    id_p = df_projetos[df_projetos["Cliente"] == proj]["ID_Projeto"].values[0]
                    
                    nova = pd.DataFrame([{
                        "ID_Projeto": id_p, "Fase": fase, "Descricao": desc, "Responsavel": resp,
                        "Data_Inicio": str(d_ini), "Data_Deadline": str(d_fim), "Prioridade": prio,
                        "Status": "A Fazer", 
                        "Historico_Log": f"Criado em {get_now_br()}", "Data_Conclusao": "", "Horas_Gastas": 0.0
                    }])
                    
                    df_final = pd.concat([df_tarefas, nova], ignore_index=True)
                    df_final["Data_Inicio"] = pd.to_datetime(df_final["Data_Inicio"], errors='coerce').dt.strftime("%Y-%m-%d")
                    df_final["Data_Deadline"] = pd.to_datetime(df_final["Data_Deadline"], errors='coerce').dt.strftime("%Y-%m-%d")
                    
                    save_data(df_final, "Tarefas")
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
                        c2.text(f"De: {format_date_br(row['Data_Inicio'])}")
                        c2.text(f"Até: {format_date_br(row['Data_Deadline'])}")
                        
                        novo_status = c3.selectbox("Status", ["A Fazer", "Em Andamento", "Revisão", "Concluído"], 
                                                   index=["A Fazer", "Em Andamento", "Revisão", "Concluído"].index(row['Status']), 
                                                   key=f"s_{idx}")
                        horas = c4.number_input("Horas Gastas", value=float(row.get("Horas_Gastas", 0.0)), step=0.5, key=f"h_{idx}")
                        
                        if c4.button("💾 Salvar", key=f"b_{idx}"):
                            df_tarefas.at[idx, "Status"] = novo_status
                            df_tarefas.at[idx, "Horas_Gastas"] = horas
                            if novo_status == "Concluído" and row['Status'] != "Concluído":
                                df_tarefas.at[idx, "Data_Conclusao"] = get_now_br()
                            
                            df_tarefas["Data_Inicio"] = pd.to_datetime(df_tarefas["Data_Inicio"], errors='coerce').dt.strftime("%Y-%m-%d")
                            df_tarefas["Data_Deadline"] = pd.to_datetime(df_tarefas["Data_Deadline"], errors='coerce').dt.strftime("%Y-%m-%d")
                            
                            save_data(df_tarefas, "Tarefas")
                            st.rerun()
        st.markdown("---")
        with st.expander("✅ Histórico de Entregas"):
            concluidas = df_full[df_full["Status"] == "Concluído"]
            if not concluidas.empty:
                for idx, row in concluidas.iterrows():
                    with st.container(border=True):
                        c_a, c_b = st.columns([5, 1])
                        c_a.markdown(f"~~**{row['Cliente']}** - {row['Descricao']}~~ (Entregue: {row.get('Data_Conclusao', '-')})")
                        if c_b.button("Reabrir", key=f"re_{idx}"):
                            df_tarefas.at[idx, "Status"] = "Em Andamento"
                            df_tarefas.at[idx, "Data_Conclusao"] = ""
                            df_tarefas["Data_Inicio"] = pd.to_datetime(df_tarefas["Data_Inicio"], errors='coerce').dt.strftime("%Y-%m-%d")
                            df_tarefas["Data_Deadline"] = pd.to_datetime(df_tarefas["Data_Deadline"], errors='coerce').dt.strftime("%Y-%m-%d")
                            save_data(df_tarefas, "Tarefas")
                            st.rerun()

# ==============================================================================
# ABA 5: CONTROLE FINANCEIRO (COM FILTRO DE PROJETOS ATIVOS)
# ==============================================================================
elif aba == "Controle Financeiro":
    st.header("💰 Lançamentos e Baixas (Entradas)")
    
    # MUDANÇA: Filtra apenas projetos com Status "Ativo" para novos lançamentos
    lista_projetos = df_projetos[df_projetos["Status_Geral"] == "Ativo"]["Cliente"].unique().tolist()
    
    with st.expander("➕ Novo Lançamento (Receita)", expanded=True):
        with st.form("fin_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            proj_fin = c1.selectbox("Projeto", lista_projetos)
            desc_fin = c2.text_input("Descrição (Ex: Entrada 30%)")
            valor_fin = c3.number_input("Valor (R$)", min_value=0.0, step=100.0)
            
            c4, c5 = st.columns(2)
            venc_fin = c4.date_input("Vencimento")
            status_fin = c5.selectbox("Status Inicial", ["Pendente", "Pago"])
            
            if st.form_submit_button("Registrar"):
                if proj_fin:
                    id_p = df_projetos[df_projetos["Cliente"] == proj_fin]["ID_Projeto"].values[0]
                    data_pg = str(venc_fin) if status_fin == "Pago" else ""
                    val_imposto = (valor_fin * 0.155) if status_fin == "Pago" else 0.0
                    
                    novo_fin = pd.DataFrame([{
                        "ID_Lancamento": len(df_financeiro) + 1, "ID_Projeto": id_p,
                        "Descricao": desc_fin, "Valor": valor_fin,
                        "Vencimento": str(venc_fin), "Status": status_fin, 
                        "Data_Pagamento": data_pg, "Valor_Imposto": val_imposto
                    }])
                    df_final = pd.concat([df_financeiro, novo_fin], ignore_index=True)
                    df_final["Vencimento"] = pd.to_datetime(df_final["Vencimento"]).dt.strftime("%Y-%m-%d")
                    df_final["Valor_Imposto"] = df_final["Valor_Imposto"].fillna(0.0) 
                    save_data(df_final, "Financeiro")
                    st.success("Registrado!")
                    st.rerun()
    
    st.divider()
    if not df_financeiro.empty:
        st.subheader("Extrato por Projeto")
        df_view = pd.merge(df_financeiro, df_projetos[["ID_Projeto", "Cliente"]], on="ID_Projeto", how="left")
        
        # AQUI MANTEMOS TODOS PARA VER O HISTÓRICO (Mesmo de concluídos)
        projetos_com_fin = df_view["Cliente"].unique()
        
        for cliente in projetos_com_fin:
            subset = df_view[df_view["Cliente"] == cliente]
            tem_pendencia = subset[subset["Status"] == "Pendente"].shape[0] > 0
            icone = "🔴" if tem_pendencia else "✅"
            
            with st.expander(f"{icone} {cliente}"):
                for idx, row in subset.iterrows():
                    with st.container(border=True):
                        c_desc, c_val, c_btn = st.columns([3, 2, 2])
                        c_desc.markdown(f"**{row['Descricao']}**")
                        
                        if row['Status'] == 'Pendente':
                            c_desc.caption(f"Vence: {format_date_br(row['Vencimento'])}")
                            c_val.markdown(f"**{format_currency_br(row['Valor'])}**")
                            
                            if c_btn.button("Receber (15.5% Imposto)", key=f"rec_{row['ID_Lancamento']}"):
                                real_idx = df_financeiro[df_financeiro["ID_Lancamento"] == row["ID_Lancamento"]].index[0]
                                valor_recebido = df_financeiro.at[real_idx, "Valor"]
                                imposto_calculado = valor_recebido * 0.155
                                df_financeiro.at[real_idx, "Status"] = "Pago"
                                df_financeiro.at[real_idx, "Data_Pagamento"] = str(get_today_date())
                                df_financeiro.at[real_idx, "Valor_Imposto"] = imposto_calculado
                                df_financeiro["Vencimento"] = pd.to_datetime(df_financeiro["Vencimento"]).dt.strftime("%Y-%m-%d")
                                df_financeiro["Valor_Imposto"] = df_financeiro["Valor_Imposto"].fillna(0.0)
                                df_financeiro["Valor"] = df_financeiro["Valor"].fillna(0.0)
                                save_data(df_financeiro, "Financeiro")
                                st.balloons()
                                st.rerun()
                        else:
                            c_desc.caption(f"Pago: {format_date_br(row['Data_Pagamento'])}")
                            c_val.markdown(f"**{format_currency_br(row['Valor'])}**")
                            c_desc.caption(f"Imposto retido: {format_currency_br(row.get('Valor_Imposto', 0.0))}")
                            c_btn.success("Pago")
    else:
        st.info("Nenhum lançamento.")

# ==============================================================================
# ABA 6: CONTROLE DESPESAS
# ==============================================================================
elif aba == "Controle Despesas":
    st.header("📉 Custos Fixos e Despesas")
    
    with st.expander("➕ Lançar Despesa (Contador, Software...)", expanded=True):
        with st.form("desp_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            desc_dsp = c1.text_input("Descrição (Ex: Contador Mensal)")
            cat_dsp = c2.selectbox("Categoria", ["Contabilidade", "Software/Licenças", "Pro-labore", "Marketing", "Taxas", "Outros"])
            val_dsp = c3.number_input("Valor (R$)", min_value=0.0, step=100.0)
            
            c4, c5 = st.columns(2)
            venc_dsp = c4.date_input("Vencimento")
            status_dsp = c5.selectbox("Status", ["Pendente", "Pago"])
            
            if st.form_submit_button("Registrar Despesa"):
                data_pg = str(venc_dsp) if status_dsp == "Pago" else ""
                nova_dsp = pd.DataFrame([{
                    "ID_Despesa": len(df_despesas) + 1, "Descricao": desc_dsp, "Categoria": cat_dsp,
                    "Valor": val_dsp, "Vencimento": str(venc_dsp), "Status": status_dsp, "Data_Pagamento": data_pg
                }])
                df_final = pd.concat([df_despesas, nova_dsp], ignore_index=True)
                df_final["Vencimento"] = pd.to_datetime(df_final["Vencimento"]).dt.strftime("%Y-%m-%d")
                save_data(df_final, "Despesas")
                st.success("Despesa salva!")
                st.rerun()

    st.divider()
    if not df_despesas.empty:
        st.subheader("Histórico de Despesas")
        df_view = df_despesas.sort_values(by="Vencimento", ascending=False)
        for idx, row in df_view.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 2])
                c1.markdown(f"**{row['Descricao']}** ({row['Categoria']})")
                if row['Status'] == 'Pendente':
                    c1.caption(f"Vence: {format_date_br(row['Vencimento'])}")
                    c2.markdown(f"**{format_currency_br(row['Valor'])}**")
                    if c3.button("Pagar", key=f"pag_{row['ID_Despesa']}"):
                        real_idx = df_despesas[df_despesas["ID_Despesa"] == row["ID_Despesa"]].index[0]
                        df_despesas.at[real_idx, "Status"] = "Pago"
                        df_despesas.at[real_idx, "Data_Pagamento"] = str(get_today_date())
                        df_despesas["Vencimento"] = pd.to_datetime(df_despesas["Vencimento"]).dt.strftime("%Y-%m-%d")
                        save_data(df_despesas, "Despesas")
                        st.rerun()
                else:
                    c1.caption(f"Pago: {format_date_br(row['Data_Pagamento'])}")
                    c2.markdown(f"**{format_currency_br(row['Valor'])}**")
                    c3.success("Pago")
    else:
        st.info("Nenhuma despesa registrada.")
