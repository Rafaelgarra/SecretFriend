import streamlit as st
import time
import re
from datetime import date
import ui
from service.service import run_draw, clean_sent_folder, send_emails_backend, check_smtp_login
from service.database import (create_room, get_room, verify_admin, add_participant, add_participants,
                              get_participants, close_room, get_draw, get_secret)

DEFAULT_APP_URL = "https://appfriend-dyhgtzh8udytssfjcul2rh.streamlit.app/"

st.set_page_config(page_title="Amigo Secreto Conectado", page_icon="🎁", layout="wide")
ui.inject_styles()


EMAIL_PATTERN = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"


def is_valid_email(email):
    return re.fullmatch(EMAIL_PATTERN, email) is not None


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


def validate_participant(name, email, taken_names, taken_emails):
    """Retorna (nome, e-mail, erro) já normalizados; erro é None se estiver tudo certo."""
    clean_name = " ".join(name.split())
    clean_email = email.strip().lower()

    if not clean_name or not clean_email:
        return clean_name, clean_email, "Preencha nome e e-mail."
    if len(clean_name) > 60:
        return clean_name, clean_email, "Nome muito longo (máximo 60 caracteres)."
    if not is_valid_email(clean_email):
        return clean_name, clean_email, "E-mail inválido. Verifique se digitou corretamente."
    if clean_email in taken_emails:
        return clean_name, clean_email, "Este e-mail já está cadastrado nesta sala!"
    if clean_name.lower() in taken_names:
        return clean_name, clean_email, "Este nome já existe! Adicione um sobrenome."
    return clean_name, clean_email, None


def taken_sets(participants):
    return ({n.strip().lower() for n in participants}, {e.strip().lower() for e in participants.values()})


def register_participant(room_code, name, email):
    """Valida e cadastra. Retorna a mensagem de erro, ou None se deu certo."""
    clean_name, clean_email, error = validate_participant(name, email, *taken_sets(get_participants(room_code)))
    if error:
        return error
    add_participant(room_code, clean_name, clean_email)
    return None


def parse_people_list(text):
    """Lê uma lista colada, um participante por linha ("Nome, e-mail", "Nome - e-mail", "Nome <e-mail>"...)."""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.search(EMAIL_PATTERN, line)
        if not match:
            yield line, ""
            continue
        name = (line[:match.start()] + " " + line[match.end():]).strip(" \t,;:|<>()-")
        yield name, match.group()


def register_many(room_code, text):
    """Cadastra uma lista colada. Retorna (quantos entraram, lista de erros por linha)."""
    taken_names, taken_emails = taken_sets(get_participants(room_code))
    to_add, errors = [], []
    for name, email in parse_people_list(text):
        if not email:
            errors.append(f"{name}: não encontrei um e-mail válido nesta linha.")
            continue
        clean_name, clean_email, error = validate_participant(name, email, taken_names, taken_emails)
        if error:
            errors.append(f"{name or email}: {error}")
            continue
        to_add.append((clean_name, clean_email))
        taken_names.add(clean_name.lower())
        taken_emails.add(clean_email)
    add_participants(room_code, to_add)
    return len(to_add), errors


def invite_message(room_name, code, date_label, url, bold=False, with_url=True):
    """Texto do convite. bold=True usa o *negrito* do WhatsApp; as outras redes mostrariam os asteriscos."""
    b = (lambda t: f"*{t}*") if bold else (lambda t: t)
    lines = [f"🎁 {b('Você foi convidado(a) para o Amigo Secreto!')}"]
    if room_name and room_name != "Amigo Secreto":
        lines.append(f"🎄 {room_name}")
    if date_label:
        lines.append(f"📅 Troca de presentes: {date_label}")
    lines.append(f"🔑 Código da sala: {b(code)}")
    if with_url:
        lines += ["", "👉 Entre e confirme sua participação:", url]
    else:
        lines += ["", "👉 Entre pelo link e confirme sua participação."]
    return "\n".join(lines)


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

    col1, col2, col3 = st.container(key="home_cards").columns(3, gap="medium")

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
                plain_text = invite_message(room_name, current_room, date_label, invite_url)
                ui.native_share_button(f"Amigo Secreto · Sala {current_room}",
                                       invite_message(room_name, current_room, date_label, invite_url, with_url=False),
                                       invite_url)
                ui.share_buttons(
                    whatsapp=invite_message(room_name, current_room, date_label, invite_url, bold=True),
                    twitter=plain_text,
                    telegram=invite_message(room_name, current_room, date_label, invite_url, with_url=False),
                    url=invite_url,
                )
                st.caption("Para Instagram ou outras redes, copie o texto abaixo:")
                st.code(plain_text, language="text", wrap_lines=True)

        with st.container(key="card_people"):
            ui.card_header("users", "red", "Participantes confirmados", f"Total: {len(participants)}")
            if participants:
                ui.people_list([(name, mask_email(email)) for name, email in participants.items()])
            else:
                st.caption("Aguardando participantes entrarem pelo link...")

            if is_open:
                flash = st.session_state.pop(f"flash_{current_room}", None)
                if flash:
                    added, errors = flash
                    if added:
                        st.success(f"✅ {added} participante(s) adicionado(s).")
                    for error in errors:
                        st.error(error)

                with st.expander("Adicionar participantes manualmente", icon=":material/person_add:", expanded=not participants):
                    st.caption("Para quem não vai entrar pelo link. Se você também vai participar, adicione-se aqui.")
                    one_tab, list_tab = st.tabs(["Um por vez", "Colar uma lista"])

                    with one_tab:
                        if st.session_state.pop("clear_add_one", False):
                            st.session_state["add_name"] = st.session_state["add_email"] = ""
                        with st.form("master_add", border=False):
                            c1, c2 = st.columns(2)
                            m_name = c1.text_input("Nome", max_chars=60, key="add_name")
                            m_email = c2.text_input("E-mail", key="add_email")
                            if st.form_submit_button("Adicionar", icon=":material/person_add:"):
                                with st.spinner("Validando e salvando..."):
                                    error = register_participant(current_room, m_name, m_email)
                                if error:
                                    st.error(error)
                                else:
                                    st.session_state[f"flash_{current_room}"] = (1, [])
                                    st.session_state["clear_add_one"] = True
                                    st.rerun()

                    with list_tab:
                        if st.session_state.pop("clear_add_list", False):
                            st.session_state["add_list"] = ""
                        with st.form("master_bulk", border=False):
                            people_text = st.text_area(
                                "Um participante por linha: nome e e-mail",
                                placeholder="Ana Souza, ana@exemplo.com\nBruno Lima, bruno@exemplo.com",
                                height=150, key="add_list")
                            if st.form_submit_button("Adicionar todos", icon=":material/group_add:"):
                                with st.spinner("Validando e salvando..."):
                                    added, errors = register_many(current_room, people_text)
                                st.session_state[f"flash_{current_room}"] = (added, errors)
                                st.session_state["clear_add_list"] = not errors
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
        _, center, _ = st.container(key="guest_cols").columns([1, 1.6, 1])
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
