import streamlit as st
import pandas as pd
import random
import smtplib
import ssl
import os
import imaplib
import time
from email.message import EmailMessage

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Amigo Secreto",
    page_icon="🎁",
    layout="centered"
)

# --- TENTA CARREGAR .ENV (Para rodar local) ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Variável global
ASSUNTO_EMAIL = "🎁 Seu Amigo Secreto (Sorteio Oficial)"

# --- FUNÇÕES (Backend) ---
def fazer_sorteio(nomes):
    doadores = list(nomes)
    recebedores = list(nomes)
    sorteio_final = {}
    random.shuffle(recebedores)
    while any(doadores[i] == recebedores[i] for i in range(len(doadores))):
        random.shuffle(recebedores)
    for i in range(len(doadores)):
        sorteio_final[doadores[i]] = recebedores[i]
    return sorteio_final

def limpar_caixa_saida(usuario, senha, lista_destinatarios):
    if not lista_destinatarios: return
    status_text = st.empty()
    status_text.info("🧹 Limpando rastros da caixa de saída...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(usuario, senha)
        try:
            mail.select('"[Gmail]/Sent Mail"')
        except:
            mail.select('"[Gmail]/Enviados"')

        count = 0
        for email_dest in lista_destinatarios:
            status, data = mail.search(None, f'(TO "{email_dest}")')
            email_ids = data[0].split()
            for e_id in email_ids:
                mail.store(e_id, '+FLAGS', '\\Deleted')
                count += 1
        mail.expunge()
        mail.close()
        mail.logout()
        status_text.success(f"✨ Pronto! {count} e-mails apagados dos enviados.")
        time.sleep(2)
        status_text.empty()
    except Exception as e:
        status_text.warning(f"Não foi possível apagar os rastros automaticamente: {e}")

def enviar_emails_backend(sorteio, lista_emails, remetente, senha, modo_teste):
    smtp_server = "smtp.gmail.com"
    port = 465
    contexto = ssl.create_default_context()
    enviados = []
    
    progress = st.progress(0)
    status = st.empty()
    
    try:
        with smtplib.SMTP_SSL(smtp_server, port, context=contexto) as server:
            if not modo_teste:
                server.login(remetente, senha)
            
            total = len(sorteio)
            for i, (doador, recebedor) in enumerate(sorteio.items()):
                status.text(f"Enviando para {doador}...")
                progress.progress((i + 1) / total)
                
                email_dest = lista_emails[doador]
                
                # --- CRIA O E-MAIL (AGORA SÓ TEXTO/HTML) ---
                msg = EmailMessage()
                msg["Subject"] = ASSUNTO_EMAIL
                msg["From"] = remetente
                msg["To"] = email_dest
                
                html = f"""
                <html>
                    <body style="text-align:center; font-family:sans-serif; background:#f4f4f4; padding:30px;">
                        <div style="background:#fff; padding:30px; border-radius:10px; display:inline-block; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                            <h2 style="color:#333;">Olá, {doador}! 🌴</h2>
                            <p style="font-size: 16px;">O sorteio do Amigo foi realizado!</p>
                            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                            <p style="font-size: 14px; color: #666;">Você tirou:</p>
                            
                            <h1 style="color: #E91E63; font-size: 28px; margin: 10px 0;">👉 {recebedor} 👈</h1>
                            
                            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                            <p style="color:#999; font-size:12px;">🤫 Shhh! Guarde este segredo!</p>
                        </div>
                    </body>
                </html>
                """
                msg.add_alternative(html, subtype='html')

                if modo_teste:
                    st.info(f"[TESTE] {doador} tirou {recebedor} (Simulação de envio para {email_dest})")
                else:
                    server.send_message(msg)
                    enviados.append(email_dest)
                    
        progress.empty()
        status.empty()
        return enviados
    except Exception as e:
        st.error(f"Erro no envio: {e}")
        return []

# --- INTERFACE GRÁFICA ---

st.title("🎅 Amigo Secreto 🌴")

with st.sidebar:
    st.header("Configurações")
    
    email_remetente = os.getenv("EMAIL_REMETENTE")
    senha_remetente = os.getenv("EMAIL_PASSWORD")
    
    # Tenta pegar dos secrets se não tiver no env
    if not email_remetente or not senha_remetente:
        try:
            email_remetente = st.secrets.get("EMAIL_REMETENTE")
            senha_remetente = st.secrets.get("EMAIL_PASSWORD")
        except FileNotFoundError:
            pass

    if not email_remetente or not senha_remetente:
        st.warning("⚠️ Credenciais não encontradas. Verifique o arquivo .env")
    
    modo_teste = st.checkbox("Modo de Teste (Sem envio)", value=False)

st.subheader("Lista de Participantes")

# Template da tabela
df_template = pd.DataFrame(columns=["Nome", "Email"])
column_config = {
    "Nome": st.column_config.TextColumn("Nome", required=True),
    "Email": st.column_config.TextColumn("Email", required=True)
}

df_participantes = st.data_editor(
    df_template, 
    num_rows="dynamic", 
    column_config=column_config,
    hide_index=True
)

st.write("")
if st.button("🎲 Realizar Sorteio e Enviar", type="primary"):
    
    # --- CORREÇÃO DO ERRO 'LIST' ---
    # Garante que é texto puro
    df_participantes["Nome"] = df_participantes["Nome"].astype(str)
    df_participantes["Email"] = df_participantes["Email"].astype(str)
    
    # Filtra vazios
    df_clean = df_participantes[
        (df_participantes["Nome"] != "nan") & (df_participantes["Nome"] != "") &
        (df_participantes["Email"] != "nan") & (df_participantes["Email"] != "")
    ]
    
    if len(df_clean) < 2:
        st.error("Erro: Insira pelo menos 2 participantes.")
        st.stop()
        
    if not modo_teste and (not email_remetente or not senha_remetente):
        st.error("Erro: Credenciais de e-mail incompletas.")
        st.stop()

    participantes_dict = dict(zip(df_clean["Nome"], df_clean["Email"]))

    with st.spinner("Sorteando..."):
        mapa_sorteio = fazer_sorteio(participantes_dict.keys())

    with st.spinner("Enviando e-mails..."):
        enviados = enviar_emails_backend(mapa_sorteio, participantes_dict, email_remetente, senha_remetente, modo_teste)

    if enviados and not modo_teste:
        limpar_caixa_saida(email_remetente, senha_remetente, enviados)
        st.balloons()
        st.success("✅ Processo finalizado com sucesso!")
        
    elif modo_teste:
        st.success("Simulação concluída.")