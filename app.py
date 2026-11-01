import streamlit as st
import time
import urllib.parse
import re
from datetime import date
import ui
from service.service import run_draw, clean_sent_folder, send_emails_backend, check_smtp_login
from service.database import (create_room, get_room, verify_admin, add_participant, get_participants,
                              close_room, get_draw, get_secret)

DEFAULT_APP_URL = "https://appfriend-dyhgtzh8udytssfjcul2rh.streamlit.app/"

st.set_page_config(page_title="Amigo Secreto Conectado", page_icon="🎁", layout="wide")
ui.inject_styles()


def is_valid_email(email):
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None


def mask_email(email):
    user, _, domain = email.partition("@")
    return f"{user[:3]}***@{domain}" if domain else "***"


def format_date(iso):
    try:
        return date.fromisoformat(iso).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return ""


def master_rooms():
    return st.session_state.setdefault("master_rooms", set())


def register_participant(room_code, name, email):
    """Valida e cadastra. Retorna a mensagem de erro, ou None se deu certo."""
    clean_name = " ".join(name.split())
    clean_email = email.strip().lower()

    if not clean_name or not clean_email:
        return "Preencha todos os campos."
    if len(clean_name) > 60:
        return "Nome muito longo (máximo 60 caracteres)."
    if not is_valid_email(clean_email):
        return "E-mail inválido. Verifique se digitou corretamente."

    existing = get_participants(room_code)
    if clean_email in [e.strip().lower() for e in existing.values()]:
        return "Este e-mail já está cadastrado nesta sala!"
    if clean_name.lower() in [n.strip().lower() for n in existing.keys()]:
        return "Este nome já existe! Adicione um sobrenome."

    add_participant(room_code, clean_name, clean_email)
    return None


sender_email = get_secret("EMAIL_REMETENTE")
sender_pass = get_secret("EMAIL_PASSWORD")
app_url = (get_secret("APP_URL") or DEFAULT_APP_URL).rstrip("/")

current_room = st.query_params.get("sala", None)
if current_room:
    current_room = current_room.strip().upper()

if not current_room:
    ui.hero()
    if not sender_email or not sender_pass:
        st.error("⚠️ E-mail de envio não configurado (EMAIL_REMETENTE / EMAIL_PASSWORD).")

    col1, col2, col3 = st.columns(3, gap="medium")

    with col1:
        with st.container(key="card_create"):
            ui.card_header("gift", "red", "Criar sala", "Organize um Amigo Secreto em minutos.")
            with st.form("create_room", border=False):
                room_name = st.text_input("Nome da sala", placeholder="Ex.: Amigo Secreto da Equipe", max_chars=60)
                draw_date = st.date_input("Data da troca (opcional)", value=None, min_value=date.today(), format="DD/MM/YYYY")
                if st.form_submit_button("Criar sala", type="primary", icon=":material/add:", width="stretch"):
                    if not sender_pass:
                        st.error("Erro de configuração de e-mail.")
                    else:
                        with st.spinner("Criando sala..."):
                            new_code, admin_key = create_room(room_name.strip(), draw_date.isoformat() if draw_date else "")
                        master_rooms().add(new_code)
                        st.session_state.setdefault("new_admin_keys", {})[new_code] = admin_key
                        st.query_params["sala"] = new_code
                        st.rerun()

    with col2:
        with st.container(key="card_join"):
            ui.card_header("users", "green", "Participar da sala", "Recebeu um código? Entre e faça sua inscrição.")
            with st.form("join_room", border=False):
                join_code = st.text_input("Código da sala", placeholder="Ex.: K7Q2", max_chars=4).strip().upper()
                st.caption("Ou abra direto o link que o organizador compartilhou.")
                if st.form_submit_button("Entrar na sala", type="primary", icon=":material/login:", width="stretch"):
                    if not join_code:
                        st.warning("Digite o código.")
                    elif not get_room(join_code):
                        st.error("Sala não encontrada.")
                    else:
                        st.query_params["sala"] = join_code
                        st.rerun()

    with col3:
        with st.container(key="card_admin"):
            ui.card_header("crown", "gold", "Sou o organizador", "Acesse o painel com o código e a chave da sala.")
            with st.form("admin_login", border=False):
                code_input = st.text_input("Código da sala", placeholder="Ex.: K7Q2", max_chars=4, key="admin_code").strip().upper()
                key_input = st.text_input("Chave do organizador", placeholder="XXXX-XXXX", type="password")
                if st.form_submit_button("Acessar painel", icon=":material/admin_panel_settings:", width="stretch"):
                    if not code_input:
                        st.warning("Digite o código.")
                    else:
                        with st.spinner("Buscando sala..."):
                            room = get_room(code_input)
                        if not room:
                            st.error("Sala não encontrada.")
                        elif not verify_admin(room, key_input):
                            st.error("Chave do organizador incorreta.")
                        else:
                            master_rooms().add(code_input)
                            st.query_params["sala"] = code_input
                            st.rerun()

    ui.features()

else:
    if st.button("Voltar ao início", icon=":material/arrow_back:", type="tertiary"):
        st.session_state.pop(f"joined_{current_room}", None)
        st.query_params.clear()
        st.rerun()

    ui.hero(compact=True)

    room = get_room(current_room)
    if not room:
        ui.note("closed", "Sala não encontrada", "Esta sala não existe ou foi excluída. Confira o código com o organizador.")
        st.stop()

    room_name = room["name"] or "Amigo Secreto"
    date_label = format_date(room["date"])
    room_ctx = {"code": current_room, "name": room["name"], "date_label": date_label}
    subtitle = f"{room_name} · Sala {current_room}" + (f" · {date_label}" if date_label else "")

    if current_room in master_rooms():
        new_key = st.session_state.get("new_admin_keys", {}).get(current_room)
        if new_key:
            with st.container(key="adminkey"):
                ui.admin_key_notice(current_room)
                st.code(new_key, language="text")
                if st.button("Já guardei a chave", icon=":material/check:"):
                    st.session_state["new_admin_keys"].pop(current_room, None)
                    st.rerun()

        participants = get_participants(current_room)
        is_open = room["status"] == "OPEN"

        with st.container(key="card_panel"):
            ui.card_header("crown", "gold", "Painel do organizador", subtitle)
            ui.stats([
                ("users", "green", len(participants), "Participantes"),
                ("door", "gold", "Abertas" if is_open else "Encerradas", "Inscrições"),
                ("gift", "red", "Não realizado" if is_open else "Realizado", "Sorteio"),
            ] + ([("calendar", "green", date_label, "Troca de presentes")] if date_label else []))

            if not sender_email or not sender_pass:
                st.error("⚠️ E-mail de envio não configurado. O sorteio só funciona no modo de teste.")

            if is_open:
                test_mode = st.toggle("Modo de teste (sorteia na tela, sem enviar e sem fechar a sala)", value=False)
                if st.button("Realizar sorteio", type="primary", icon=":material/shuffle:", width="stretch"):
                    if len(participants) < 2:
                        st.error("Mínimo de 2 pessoas!")
                    elif test_mode:
                        send_emails_backend(run_draw(participants.keys()), participants, sender_email, sender_pass, room_ctx, True)
                        st.info("Modo de teste: nenhum e-mail foi enviado e a sala continua aberta.")
                    else:
                        with st.spinner("Conferindo o e-mail de envio..."):
                            login_error = check_smtp_login(sender_email, sender_pass)
                        if login_error:
                            st.error(f"Não foi possível entrar no e-mail de envio. Nada foi sorteado. ({login_error})")
                        else:
                            with st.spinner("Realizando sorteio e enviando e-mails..."):
                                draw_result = run_draw(participants.keys())
                                close_room(current_room, draw_result)
                                sent_list, failed = send_emails_backend(draw_result, participants, sender_email, sender_pass, room_ctx, False)
                                clean_sent_folder(sender_email, sender_pass, sent_list, current_room)
                            st.session_state[f"failed_{current_room}"] = failed
                            if not failed:
                                st.balloons()
                                time.sleep(3)
                            st.rerun()
            else:
                failed = st.session_state.get(f"failed_{current_room}", [])
                if failed:
                    st.warning(f"⚠️ Não foi possível enviar para: {', '.join(failed)}. Confira os e-mails e tente reenviar abaixo.")
                else:
                    st.success("🎉 Sorteio realizado! Cada participante recebeu por e-mail quem tirou.")

        if is_open:
            with st.container(key="card_invite"):
                ui.card_header("link", "green", "Enviar convite", "Compartilhe o link para as pessoas entrarem na sala.")
                invite_url = f"{app_url}/?sala={current_room}"
                msg_texto = f"Participe do meu Amigo Secreto! Código da Sala: {current_room}. Entre aqui: {invite_url}"
                ui.share_buttons(urllib.parse.quote(msg_texto), urllib.parse.quote(invite_url))
                st.caption("Para Instagram ou outras redes, copie o texto abaixo:")
                st.code(msg_texto, language="text", wrap_lines=True)

        with st.container(key="card_people"):
            ui.card_header("users", "red", "Participantes confirmados", f"Total: {len(participants)}")
            if participants:
                ui.people_list([(name, mask_email(email)) for name, email in participants.items()])
            else:
                st.caption("Aguardando participantes entrarem pelo link...")

            if is_open:
                with st.expander("Quero participar do sorteio também", icon=":material/person_add:"):
                    with st.form("master_join", border=False):
                        c1, c2 = st.columns(2)
                        m_name = c1.text_input("Seu nome", max_chars=60)
                        m_email = c2.text_input("Seu e-mail")
                        if st.form_submit_button("Me cadastrar"):
                            with st.spinner("Validando e salvando..."):
                                error = register_participant(current_room, m_name, m_email)
                            if error:
                                st.error(error)
                            else:
                                st.success("Você entrou na lista!")
                                time.sleep(1)
                                st.rerun()

            elif sender_email and sender_pass:
                with st.expander("Reenviar e-mail do sorteio", icon=":material/forward_to_inbox:"):
                    draw_result = get_draw(current_room)
                    if not draw_result:
                        st.caption("Esta sala foi sorteada antes do reenvio existir, então não há resultado salvo.")
                    else:
                        failed = st.session_state.get(f"failed_{current_room}", [])
                        target = st.selectbox("Participante", list(draw_result.keys()),
                                              index=list(draw_result.keys()).index(failed[0]) if failed and failed[0] in draw_result else 0)
                        st.caption("Ele recebe de novo o mesmo resultado. Você não vê quem ele tirou.")
                        if st.button("Reenviar", icon=":material/send:"):
                            sent_list, still_failed = send_emails_backend(draw_result, participants, sender_email, sender_pass,
                                                                          room_ctx, False, only=[target])
                            clean_sent_folder(sender_email, sender_pass, sent_list, current_room)
                            if still_failed:
                                st.error(f"Falha ao reenviar para {target}.")
                            else:
                                st.session_state[f"failed_{current_room}"] = [f for f in failed if f != target]
                                st.success(f"E-mail reenviado para {target}!")

    else:
        _, center, _ = st.columns([1, 1.6, 1])
        with center:
            with st.container(key="card_guest"):
                ui.card_header("users", "green", "Participar da sala", subtitle)

                if room["status"] == "CLOSED":
                    ui.note("closed", "Inscrições encerradas 🚫",
                            "O sorteio já foi realizado. Se você se inscreveu, confira seu e-mail (e a caixa de spam).")

                elif st.session_state.get(f"joined_{current_room}", False):
                    st.balloons()
                    ui.note("success", "Tudo certo! ✅",
                            "Você já está na lista. Fique de olho no seu e-mail (e no spam) para descobrir quem você tirou!")
                    st.write("")
                    if st.button("Cadastrar outra pessoa", icon=":material/refresh:"):
                        st.session_state[f"joined_{current_room}"] = False
                        st.rerun()

                else:
                    with st.form("guest_form", border=False):
                        g_name = st.text_input("Seu nome", placeholder="Ex.: Ana", max_chars=60)
                        g_email = st.text_input("E-mail", placeholder="Ex.: ana@exemplo.com")
                        if st.form_submit_button("Participar", type="primary", icon=":material/check:", width="stretch"):
                            with st.spinner("Carregando..."):
                                error = register_participant(current_room, g_name, g_email)
                            if error:
                                st.error(f"❌ {error}")
                            else:
                                st.session_state[f"joined_{current_room}"] = True
                                st.rerun()
