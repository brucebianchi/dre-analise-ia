# app.py

import pandas as pd
import openai
import streamlit as st
from io import BytesIO
from fpdf import FPDF

# Configuração da API Groq
openai.api_key = st.secrets["APP_KEY_GROQ"]
openai.api_base = "https://api.groq.com/openai/v1"

st.set_page_config(page_title="Análise de DRE com IA", layout="wide")

st.title("📊 Análise de DRE com IA (Groq)")

# 1. Upload do arquivo
st.header("📂 Envie sua planilha de DRE (.xlsx)")
uploaded_file = st.file_uploader("Upload do arquivo", type=["xlsx"])

if uploaded_file is not None:
    dre_df = pd.read_excel(uploaded_file)
    dre_df.columns = [col.strip() for col in dre_df.columns]
    dre_df.dropna(inplace=True)

    coluna_descricao = next((col for col in dre_df.columns if "desc" in col.lower()), dre_df.columns[0])
    coluna_valor = next((col for col in dre_df.columns if "valor" in col.lower()), dre_df.columns[-1])

    st.subheader("📋 Prévia da DRE")
    st.dataframe(dre_df[[coluna_descricao, coluna_valor]])

    # 2. Informações tributárias
    st.sidebar.header("🔧 Parâmetros")
    regime_tributario = st.sidebar.selectbox("Regime Tributário", ['Lucro Real', 'Lucro Presumido'])
    atividade_economica = st.sidebar.text_input("Atividade Econômica", value="Comércio varejista de roupas")

    # 3. Resumo com IA
    def gerar_resumo_dre(df):
        texto_tabela = df.to_string(index=False)
        prompt = f"""
Você é uma consultora contábil sênior. Analise a DRE abaixo e gere um resumo executivo com os seguintes pontos:
1. Lucro Bruto
2. Margem Operacional
3. Principais Despesas
4. Eficiência de Custos
5. Recomendações contábeis
Responda de forma objetiva, usando tópicos numerados, e evite repetir valores já visíveis na tabela.
DRE:
{texto_tabela}
"""
        resposta = openai.ChatCompletion.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "Você é uma consultora contábil sênior."},
                {"role": "user", "content": prompt}
            ]
        )
        return resposta['choices'][0]['message']['content']

    st.header("📖 Resumo com IA")
    if st.button("Gerar Resumo"):
        with st.spinner("Analisando a DRE..."):
            resumo = gerar_resumo_dre(dre_df)
        st.text_area("Resumo da DRE", resumo, height=300)

    # 4. Simulação de Tributos
    st.header("📈 Simulação de Tributos")

    receita = dre_df[dre_df[coluna_descricao].str.contains("Receita", case=False, na=False)][coluna_valor].sum()
    lucro = dre_df[dre_df[coluna_descricao].str.contains("Lucro", case=False, na=False)][coluna_valor].sum()

    if regime_tributario == 'Lucro Real':
        irpj = lucro * 0.15
        adicional_irpj = (lucro - 60000) * 0.10 if lucro > 60000 else 0
        csll = lucro * 0.09
        pis = receita * 0.0165
        cofins = receita * 0.076
    else:
        if 'comércio' in atividade_economica.lower():
            presuncao_irpj = 0.08
            presuncao_csll = 0.12
        elif 'serviço' in atividade_economica.lower():
            presuncao_irpj = 0.32
            presuncao_csll = 0.32
        else:
            presuncao_irpj = 0.08
            presuncao_csll = 0.12

        base_irpj = receita * presuncao_irpj
        base_csll = receita * presuncao_csll

        irpj = base_irpj * 0.15
        adicional_irpj = (base_irpj - 60000) * 0.10 if base_irpj > 60000 else 0
        csll = base_csll * 0.09
        pis = receita * 0.0065
        cofins = receita * 0.03

    total = irpj + adicional_irpj + csll + pis + cofins

    resultados = {
        'Receita': receita,
        'Lucro': lucro,
        'IRPJ': irpj,
        'Adicional IRPJ': adicional_irpj,
        'CSLL': csll,
        'PIS': pis,
        'COFINS': cofins,
        'Total Tributos': total
    }

    st.table(pd.DataFrame(resultados.items(), columns=["Imposto", "Valor (R$)"]))

    # 5. Exportar resultados
    st.header("📤 Exportar Resultados")
    if st.button("Baixar PDF com Resumo"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Resumo da Análise DRE", ln=True, align='C')
        pdf.set_font("Arial", '', 12)
        pdf.ln(10)

        for indicador, valor in resultados.items():
            linha = f"{indicador}: R$ {valor:,.2f}"
            pdf.cell(0, 10, linha, ln=True)

    import tempfile

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
    pdf.output(tmp_file.name)
    tmp_file.seek(0)
    with open(tmp_file.name, "rb") as file:
    st.download_button("📄 Baixar PDF", data=file.read(), file_name="resumo_dre.pdf", mime="application/pdf")

