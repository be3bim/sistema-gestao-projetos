# ==============================================================================
# ABA 2: DASHBOARD FINANCEIRO (COM ANÁLISE DE HORAS/EFICIÊNCIA)
# ==============================================================================
elif aba == "Dash Financeiro":
    ano_atual = datetime.now().year
    st.header(f"💰 Dashboard Financeiro ({ano_atual})")
    st.markdown("---")
    
    if df_financeiro.empty:
        st.warning("Sem dados financeiros.")
    else:
        # --- PREPARAÇÃO DOS DADOS (Bloco padrão mantido) ---
        df_fin_calc = df_financeiro.dropna(subset=["Vencimento"]).copy()
        df_fin_calc["Vencimento"] = pd.to_datetime(df_fin_calc["Vencimento"], errors="coerce")
        df_fin_calc["Data_Pagamento"] = pd.to_datetime(df_fin_calc["Data_Pagamento"], errors="coerce")
        
        # Data Híbrida
        df_fin_calc["Data_Considerada"] = df_fin_calc.apply(
            lambda x: x["Data_Pagamento"] if (x["Status"] == "Pago" and pd.notnull(x["Data_Pagamento"])) else x["Vencimento"], 
            axis=1
        )
        df_fin_calc["Data_Considerada"] = pd.to_datetime(df_fin_calc["Data_Considerada"], errors="coerce")
        df_fin_calc["Ano_Ref"] = df_fin_calc["Data_Considerada"].dt.year
        
        # Despesas
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
        c5.metric("Previsão Futura", format_currency_br(a_receber - a_pagar), help="A Receber - A Pagar")

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
            # SEÇÃO 2: EFICIÊNCIA E HORAS (AQUI ESTÁ A NOVIDADE)
            # =========================================================
            st.markdown("---")
            st.subheader("⏱️ Eficiência e Lucratividade Real (Horas Gastas)")
            
            # 1. Agrupar horas gastas por projeto (Tabela Tarefas)
            horas_por_proj = df_tarefas.groupby("ID_Projeto")["Horas_Gastas"].sum().reset_index()
            
            # 2. Pegar valor de contrato (Tabela Projetos) - Pegamos apenas projetos ATIVOS ou CONCLUÍDOS RECENTES
            proj_financeiro = df_projetos[["ID_Projeto", "Cliente", "Proposta_Aceita_R$"]].copy()
            
            # 3. Cruzar os dados
            df_eficiencia = pd.merge(proj_financeiro, horas_por_proj, on="ID_Projeto", how="inner")
            
            # 4. Calcular Valor por Hora (R$/h)
            # Evita divisão por zero
            df_eficiencia = df_eficiencia[df_eficiencia["Horas_Gastas"] > 0] 
            df_eficiencia["Valor_Hora_Real"] = df_eficiencia["Proposta_Aceita_R$"] / df_eficiencia["Horas_Gastas"]
            
            if not df_eficiencia.empty:
                # Ordenar: Quem paga melhor primeiro
                df_eficiencia = df_eficiencia.sort_values(by="Valor_Hora_Real", ascending=True)
                
                c_efic1, c_efic2 = st.columns([2, 1])
                
                with c_efic1:
                    st.markdown("**🏆 Ranking: Valor Real da Hora Trabalhada (R$/h)**")
                    st.caption("Quanto cada cliente está pagando efetivamente pelo seu tempo.")
                    fig_hour = px.bar(df_eficiencia, x="Valor_Hora_Real", y="Cliente", orientation='h', text_auto=".2f",
                                      color="Valor_Hora_Real", color_continuous_scale="RdYlGn")
                    fig_hour.update_layout(xaxis_title="Valor por Hora (R$)", yaxis_title="")
                    st.plotly_chart(fig_hour, use_container_width=True)
                    
                with c_efic2:
                    st.markdown("**📉 Total de Horas Consumidas**")
                    st.caption("Onde a equipe gastou mais tempo.")
                    fig_pizza_h = px.pie(df_eficiencia, values="Horas_Gastas", names="Cliente", hole=0.4)
                    st.plotly_chart(fig_pizza_h, use_container_width=True)
            else:
                st.info("Nenhuma hora registrada nos projetos ainda. Preencha o 'Timesheet' na aba Tarefas.")
