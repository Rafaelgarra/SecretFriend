import streamlit as st
import os
import time
import urllib.parse
from service.service import run_draw, clean_sent_folder, send_emails_backend
from service.database import create_room, get_room_status, add_participant, get_participants, close_room

st.set_page_config(page_title="Amigo Secreto", page_icon="🎁", layout="centered")

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
        
        st.markdown(
            f"""
            <style>
                .share-container {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 12px;
                    margin-bottom: 20px;
                }}
                .share-btn {{
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    width: auto;
                    padding: 10px 20px;
                    border-radius: 8px;
                    text-decoration: none;
                    font-weight: 900; /* Negrito Forte */
                    font-family: sans-serif;
                    font-size: 16px;
                    color: #000000 !important; /* TEXTO PRETO */
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    transition: transform 0.2s, opacity 0.2s;
                    border: 1px solid rgba(0,0,0,0.1);
                }}
                .share-btn:hover {{
                    opacity: 0.9;
                    transform: translateY(-2px);
                    text-decoration: none;
                }}
                
                /* CORES DE FUNDO CLARAS (Para destacar o texto preto) */
                .wa {{ background-color: #86EFAC; }} /* WhatsApp Verde Claro */
                .fb {{ background-color: #93C5FD; }} /* Facebook Azul Claro */
                .tw {{ background-color: #E5E7EB; }} /* Twitter Cinza Claro */
                .tg {{ background-color: #7DD3FC; }} /* Telegram Azul Celeste */
            </style>

            <div class="share-container">
                <a href="https://wa.me/?text={msg_encoded}" target="_blank" class="share-btn wa">
                    📱 WhatsApp
                </a>
                <a href="https://www.facebook.com/sharer/sharer.php?u={url_encoded}" target="_blank" class="share-btn fb">
                    📘 Facebook
                </a>
                <a href="https://twitter.com/intent/tweet?text={msg_encoded}" target="_blank" class="share-btn tw">
                    ✖️ Twitter
                </a>
                <a href="https://t.me/share/url?url={url_encoded}&text={msg_encoded}" target="_blank" class="share-btn tg">
                    ✈️ Telegram
                </a>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
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
                        add_participant(current_room, m_name, m_email)
                        st.success("Você entrou na lista!")
                        time.sleep(1)
                        st.rerun()

        st.subheader("Participantes Confirmados")
        participants = get_participants(current_room)
        
        if participants:
            for name, email in participants.items():
                st.write(f"👤 {name} | {email}")
            
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
        
        if room_status == "CLOSED":
            st.warning("🚫 Inscrições encerradas.")
        else:
            st.write("### 👋 Confirme sua presença")
            with st.form("guest_form"):
                g_name = st.text_input("Nome Completo")
                g_email = st.text_input("E-mail")
                
                if st.form_submit_button("Entrar no Sorteio"):
                    if g_name and g_email:
                        add_participant(current_room, g_name, g_email)
                        st.success("Confirmado! Aguarde o sorteio.")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Preencha todos os campos.")
        
        st.divider()