import streamlit as st
import pandas as pd
import os

from backend import run_draw, clean_sent_folder, send_emails_backend

st.set_page_config(
    page_title="Amigo Secreto",
    page_icon="🎁",
    layout="centered"
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.title("🎅 Amigo Secreto 🌴")

with st.sidebar:
    st.header("Configurações")
    
    sender_email = os.getenv("EMAIL_REMETENTE")
    sender_password = os.getenv("EMAIL_PASSWORD")
    
    if not sender_email or not sender_password:
        try:
            sender_email = st.secrets.get("EMAIL_REMETENTE")
            sender_password = st.secrets.get("EMAIL_PASSWORD")
        except FileNotFoundError:
            pass

    if not sender_email or not sender_password:
        st.warning("⚠️ Credenciais não encontradas. Verifique o arquivo .env ou secrets.")
    
    test_mode = st.checkbox("Modo de Teste (Sem envio)", value=False)

st.subheader("Lista de Participantes")

df_template = pd.DataFrame(columns=["Nome", "Email"])
column_config = {
    "Nome": st.column_config.TextColumn("Nome", required=True),
    "Email": st.column_config.TextColumn("Email", required=True)
}

df_participants = st.data_editor(
    df_template, 
    num_rows="dynamic", 
    column_config=column_config,
    hide_index=True
)

st.write("")

if st.button("🎲 Realizar Sorteio e Enviar", type="primary"):
    
    df_participants["Nome"] = df_participants["Nome"].astype(str)
    df_participants["Email"] = df_participants["Email"].astype(str)
    
    df_clean = df_participants[
        (df_participants["Nome"] != "nan") & (df_participants["Nome"] != "") &
        (df_participants["Email"] != "nan") & (df_participants["Email"] != "")
    ]
    
    if len(df_clean) < 2:
        st.error("Erro: Insira pelo menos 2 participantes.")
        st.stop()
        
    if not test_mode and (not sender_email or not sender_password):
        st.error("Erro: Credenciais de e-mail incompletas.")
        st.stop()

    participants_dict = dict(zip(df_clean["Nome"], df_clean["Email"]))

    with st.spinner("Sorteando..."):
        draw_result = run_draw(participants_dict.keys())

    with st.spinner("Enviando e-mails..."):
        sent_emails = send_emails_backend(draw_result, participants_dict, sender_email, sender_password, test_mode)

    if sent_emails and not test_mode:
        clean_sent_folder(sender_email, sender_password, sent_emails)
        st.balloons()
        st.success("✅ Processo finalizado com sucesso!")
        
    elif test_mode:
        st.success("Simulação concluída.")