import random
import smtplib
import ssl
import imaplib
import time
import streamlit as st
from email.message import EmailMessage

EMAIL_SUBJECT = "🎁 Seu Amigo Secreto (Sorteio Oficial)"

def run_draw(names):
    """
    Realiza o sorteio garantindo que ninguém tire a si mesmo.
    """
    givers = list(names)
    receivers = list(names)
    final_draw = {}
    
    random.shuffle(receivers)
    
    while any(givers[i] == receivers[i] for i in range(len(givers))):
        random.shuffle(receivers)
        
    for i in range(len(givers)):
        final_draw[givers[i]] = receivers[i]
        
    return final_draw

def clean_sent_folder(username, password, recipient_list):
    """
    Apaga os e-mails da caixa de saída para manter o segredo.
    """
    if not recipient_list: return
    
    status_text = st.empty()
    status_text.info("🧹 Limpando rastros da caixa de saída...")
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(username, password)
        
        try:
            mail.select('"[Gmail]/Sent Mail"')
        except:
            mail.select('"[Gmail]/Enviados"')

        deleted_count = 0
        for recipient in recipient_list:
            status, data = mail.search(None, f'(TO "{recipient}")')
            email_ids = data[0].split()
            
            for e_id in email_ids:
                mail.store(e_id, '+FLAGS', '\\Deleted')
                deleted_count += 1
                
        mail.expunge()
        mail.close()
        mail.logout()
        
        status_text.success(f"✨ Pronto! {deleted_count} e-mails apagados dos enviados.")
        time.sleep(2)
        status_text.empty()
        
    except Exception as e:
        status_text.warning(f"Não foi possível apagar os rastros automaticamente: {e}")

def send_emails_backend(draw_dict, email_map, sender, password, test_mode):
    """
    Conecta ao SMTP e envia os e-mails um por um.
    """
    smtp_server = "smtp.gmail.com"
    port = 465
    context = ssl.create_default_context()
    sent_list = []
    
    progress = st.progress(0)
    status = st.empty()
    
    try:
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            if not test_mode:
                server.login(sender, password)
            
            total = len(draw_dict)
            
            for i, (giver, receiver) in enumerate(draw_dict.items()):
                status.text(f"Enviando para {giver}...")
                progress.progress((i + 1) / total)
                
                dest_email = email_map[giver]
                
                # Cria o E-mail HTML
                msg = EmailMessage()
                msg["Subject"] = EMAIL_SUBJECT
                msg["From"] = sender
                msg["To"] = dest_email
                
                html_content = f"""
                <html>
                    <body style="text-align:center; font-family:sans-serif; background:#f4f4f4; padding:30px;">
                        <div style="background:#fff; padding:30px; border-radius:10px; display:inline-block; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                            <h2 style="color:#333;">Olá, {giver}! 🌴</h2>
                            <p style="font-size: 16px;">O sorteio do Amigo Secreto foi realizado!</p>
                            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                            <p style="font-size: 14px; color: #666;">Você tirou:</p>
                            
                            <h1 style="color: #E91E63; font-size: 28px; margin: 10px 0;">👉 {receiver} 👈</h1>
                            
                            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                            <p style="color:#999; font-size:12px;">🤫 Shhh! Guarde este segredo!</p>
                        </div>
                    </body>
                </html>
                """
                msg.add_alternative(html_content, subtype='html')

                if test_mode:
                    st.info(f"[TESTE] {giver} tirou {receiver} (Simulação de envio para {dest_email})")
                else:
                    server.send_message(msg)
                    sent_list.append(dest_email)
                    
        progress.empty()
        status.empty()
        return sent_list
        
    except Exception as e:
        st.error(f"Erro no envio: {e}")
        return []