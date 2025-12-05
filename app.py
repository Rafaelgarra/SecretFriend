import streamlit as st
import os
import time
import urllib.parse
import re
from service.service import run_draw, clean_sent_folder, send_emails_backend
from service.database import create_room, get_room_status, add_participant, get_participants, close_room

st.set_page_config(page_title="Amigo Secreto", page_icon="🎁", layout="centered")

def is_valid_email(email):
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None

sender_email = os.getenv("EMAIL_REMETENTE")
sender_pass = os.getenv("EMAIL_PASSWORD")

if not sender_email or not sender_pass:
    try:
        sender_email = st.secrets.get("EMAIL_REMETENTE")
        sender_pass = st.secrets.get("EMAIL_PASSWORD")
    except Exception:
        pass

params = st.query_params
current_room = params.get("sala", None)

with st.sidebar:
    st.header("Menu")
    
    if current_room:
        if st.button("🏠 Voltar ao Início", type="secondary"):
            if f"joined_{current_room}" in st.session_state:
                del st.session_state[f"joined_{current_room}"]
            st.query_params.clear()
            st.rerun()
            
    st.divider()
    st.header("Configurações")
    test_mode = st.checkbox("Modo de Teste (Sem envio)", value=False)
    
    if not sender_email or not sender_pass:
        st.error("⚠️ Senhas de e-mail não configuradas!")

st.title("🎅 Amigo Secreto Conectado ☁️")

if not current_room:
    st.header("Painel de Controle")
    st.info("👋 Visitantes devem usar o link compartilhado pelo organizador.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Novo Sorteio")
        if st.button("👑 Criar Nova Sala", type="primary"):
            if not sender_pass:
                st.error("Erro de configuração de e-mail.")
            else:
                with st.spinner("Gerando sala..."):
                    new_code = create_room()
                    st.session_state['is_master'] = True
                    st.query_params["sala"] = new_code
                    st.rerun()
                
    with col2:
        st.subheader("Sou o Organizador")
        st.caption("Já tem uma sala? Digite o código para gerenciar.")
        with st.form("admin_login"):
            code_input = st.text_input("Código da Sala:").upper()
            if st.form_submit_button("Acessar Painel"):
                if not code_input:
                    st.warning("Digite o código.")
                else:
                    status = get_room_status(code_input)
                    if status:
                        st.session_state['is_master'] = True
                        st.query_params["sala"] = code_input
                        st.rerun()
                    else:
                        st.error("Sala não encontrada.")

else:
    room_status = get_room_status(current_room)
    
    if not room_status:
        st.error("Esta sala não existe ou foi excluída.")
        if st.button("Voltar ao Início"):
            st.query_params.clear()
            st.rerun()
        st.stop()

    if st.session_state.get('is_master'):
        st.success(f"👑 PAINEL DO ORGANIZADOR | Sala: **{current_room}**")
        
        base_url = f"https://appfriend-dyhgtzh8udytssfjcul2rh.streamlit.app/?sala={current_room}"
        
        msg_texto = f"Participe do meu Amigo Secreto! Código da Sala: {current_room}. Entre aqui: {base_url}"
        msg_encoded = urllib.parse.quote(msg_texto)
        url_encoded = urllib.parse.quote(base_url)
        
        st.markdown("### 📤 Enviar Convite:")
        
        html_buttons = f"""
<style>
.share-container {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }}
.share-btn {{ display: inline-flex; align-items: center; justify-content: center; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 900; font-family: sans-serif; font-size: 16px; color: #000000 !important; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid rgba(0,0,0,0.1); transition: transform 0.2s, opacity 0.2s; }}
.share-btn:hover {{ opacity: 0.9; transform: translateY(-2px); text-decoration: none; }}
.wa {{ background-color: #86EFAC; }} 
.fb {{ background-color: #93C5FD; }} 
.tw {{ background-color: #E5E7EB; }} 
.tg {{ background-color: #7DD3FC; }} 
</style>
<div class="share-container">
<a href="https://wa.me/?text={msg_encoded}" target="_blank" class="share-btn wa">📱 WhatsApp</a>
<a href="https://www.facebook.com/sharer/sharer.php?u={url_encoded}" target="_blank" class="share-btn fb">📘 Facebook</a>
<a href="https://twitter.com/intent/tweet?text={msg_encoded}" target="_blank" class="share-btn tw">✖️ Twitter</a>
<a href="https://t.me/share/url?url={url_encoded}&text={msg_encoded}" target="_blank" class="share-btn tg">✈️ Telegram</a>
</div>
"""
        st.markdown(html_buttons, unsafe_allow_html=True)
        st.caption("Para Instagram ou outras redes, copie o texto abaixo:")
        st.code(msg_texto, language="text")
        st.divider()
        
        if room_status == "OPEN":
            with st.expander("📝 Quero participar do sorteio também", expanded=False):
                with st.form("master_join"):
                    c1, c2 = st.columns(2)
                    m_name = c1.text_input("Seu Nome")
                    m_email = c2.text_input("Seu E-mail")
                    
                    if st.form_submit_button("Me Cadastrar"):
                        if not m_name or not m_email:
                            st.error("Preencha todos os campos.")
                        elif not is_valid_email(m_email):
                            st.error("Por favor, insira um e-mail válido (ex: nome@gmail.com)")
                        else:
                            current_data = get_participants(current_room)
                            clean_email = m_email.strip().lower()
                            clean_name = m_name.strip()
                            db_emails = [e.strip().lower() for e in current_data.values()]
                            db_names = [n.strip().lower() for n in current_data.keys()]

                            if clean_email in db_emails:
                                st.error("E-mail já cadastrado!")
                            elif clean_name.lower() in db_names:
                                st.error("Nome já em uso! Use sobrenome.")
                            else:
                                add_participant(current_room, clean_name, clean_email)
                                st.success("Você entrou na lista!")
                                time.sleep(1)
                                st.rerun()

        st.subheader("Participantes Confirmados")
        participants = get_participants(current_room)
        
        if participants:
            for name, email in participants.items():
                email_masked = email.split('@')[0][:3] + "***@" + email.split('@')[1]
                st.write(f"👤 {name} | {email_masked}")
            st.caption(f"Total: {len(participants)}")
            
            if room_status == "OPEN":
                st.divider()
                if st.button("🎲 FECHAR E SORTEAR", type="primary"):
                    if len(participants) < 2:
                        st.error("Mínimo de 2 pessoas!")
                    else:
                        close_room(current_room)
                        st.info("Sorteando e enviando e-mails...")
                        draw_result = run_draw(participants.keys())
                        sent_list = send_emails_backend(draw_result, participants, sender_email, sender_pass, test_mode)
                        if not test_mode:
                            clean_sent_folder(sender_email, sender_pass, sent_list)
                        st.balloons()
                        st.success("Sorteio Realizado!")
                        time.sleep(3)
                        st.rerun()
        else:
            st.warning("Aguardando participantes entrarem pelo link...")

    else:
        st.info(f"📍 Você está na sala: **{current_room}**")
        
        ja_cadastrou = st.session_state.get(f"joined_{current_room}", False)

        if room_status == "CLOSED":
            st.warning("🚫 Inscrições encerradas.")

        elif ja_cadastrou:
            st.balloons()
            st.markdown("""
            <div style="
                text-align: center; 
                padding: 40px 20px; 
                background-color: #262730; 
                border-radius: 15px; 
                margin-top: 20px; 
                border: 1px solid #4F4F4F;
                box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            ">
                <h2 style="margin:0; font-size: 28px; color: #86EFAC;">Tudo certo! ✅</h2>
                <p style="margin:15px 0; font-size: 20px; color: #FFFFFF; font-weight: 500;">
                    Você já está na lista.
                </p>
                <p style="font-size: 16px; color: #DDDDDD; margin-top: 10px;">
                    Fique de olho no seu e-mail (e no spam) para descobrir quem você tirou!
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("")
            st.write("")
            if st.button("↻ Cadastrar outra pessoa"):
                st.session_state[f"joined_{current_room}"] = False
                st.rerun()

        else:
            st.write("### 👋 Confirme sua presença")
            with st.form("guest_form"):
                g_name = st.text_input("Nome Completo")
                g_email = st.text_input("E-mail")
                
                submitted = st.form_submit_button("Entrar no Sorteio")
                
                if submitted:
                    if not g_name or not g_email:
                        st.error("Preencha todos os campos.")
                    elif not is_valid_email(g_email):
                        st.error("E-mail inválido. Verifique se digitou corretamente.")
                    else:
                        existing_data = get_participants(current_room)
                        clean_email = g_email.strip().lower()
                        clean_name = g_name.strip()
                        db_emails = [e.strip().lower() for e in existing_data.values()]
                        db_names = [n.strip().lower() for n in existing_data.keys()]
                        
                        if clean_email in db_emails:
                            st.error("❌ Este e-mail já está cadastrado nesta sala!")
                        elif clean_name.lower() in db_names:
                            st.error("❌ Este nome já existe! Adicione um sobrenome.")
                        else:
                            add_participant(current_room, clean_name, clean_email)
                            st.session_state[f"joined_{current_room}"] = True
                            st.rerun()