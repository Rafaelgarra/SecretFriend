import base64
import random
import smtplib
import ssl
import imaplib
import re
import time
import html
import streamlit as st
from email.message import EmailMessage

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_STARTTLS_PORT = 587
IMAP_SERVER = "imap.gmail.com"

_rng = random.SystemRandom()


# API do Gmail via HTTPS: usada quando os secrets têm a seção [gmail_api]. Não depende de senha de app
# nem das portas de SMTP/IMAP. A autorização é gerada uma vez com scripts/autorizar_gmail.py.
GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


def _gmail_api_config():
    try:
        config = st.secrets.get("gmail_api")
    except Exception:
        return None
    if config and all(config.get(k) for k in ("client_id", "client_secret", "refresh_token")):
        return dict(config)
    return None


def gmail_api_configured():
    return _gmail_api_config() is not None


def _api_call(session, method, path, **kwargs):
    response = session.request(method, f"{GMAIL_API}{path}", timeout=30, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(f"API do Gmail respondeu {response.status_code}: {response.text[:300]}")
    return response.json() if response.content else {}


class _GmailApiMailer:
    """Usado como o servidor SMTP: with ... as server: server.send_message(msg)."""

    def __init__(self):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import AuthorizedSession
        config = _gmail_api_config()
        credentials = Credentials(None, refresh_token=config["refresh_token"], client_id=config["client_id"],
                                  client_secret=config["client_secret"], token_uri="https://oauth2.googleapis.com/token")
        self.session = AuthorizedSession(credentials)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.session.close()
        return False

    def send_message(self, msg):
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        _api_call(self.session, "POST", "/messages/send", json={"raw": raw})


def _open_mailer(sender, password):
    """API do Gmail se estiver configurada; senão SMTP com a senha de app."""
    if gmail_api_configured():
        mailer = _GmailApiMailer()
        try:
            _api_call(mailer.session, "GET", "/profile")  # confere se a autorização ainda vale
        except Exception:
            mailer.session.close()
            raise
        return mailer
    return _smtp_login(sender, password)


def email_subject(room_code):
    # O trecho "Sala XXXX" é ASCII para permitir a busca (IMAP ou API) na limpeza dos enviados
    return f"🎁 Seu Amigo Secreto - Sala {room_code}"


def run_draw(names):
    """
    Realiza o sorteio garantindo que ninguém tire a si mesmo.
    """
    givers = list(names)
    receivers = list(givers)

    _rng.shuffle(receivers)
    while any(g == r for g, r in zip(givers, receivers)):
        _rng.shuffle(receivers)

    return dict(zip(givers, receivers))


def _smtp_login(sender, password):
    """
    Conecta e faz login no Gmail. Tenta SSL na porta 465 e, se o servidor fechar a conexão,
    STARTTLS na 587. Senha recusada não adianta tentar de novo, então sobe direto.
    """
    context = ssl.create_default_context()
    errors = []
    attempts = [
        ("porta 465", lambda: smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context, timeout=20)),
        ("porta 587", lambda: smtplib.SMTP(SMTP_SERVER, SMTP_STARTTLS_PORT, timeout=20)),
    ]
    for label, connect in attempts:
        server = None
        try:
            server = connect()
            if label == "porta 587":
                server.starttls(context=context)
            server.login(sender, password)
            return server
        except smtplib.SMTPAuthenticationError:
            raise
        except Exception as e:
            errors.append(f"{label}: {type(e).__name__}: {e}")
            if server is not None:
                try: server.close()
                except Exception: pass
    raise ConnectionError(" | ".join(errors))


def _smtp_error_message(e):
    if isinstance(e, smtplib.SMTPAuthenticationError):
        return ("o Gmail recusou o usuário ou a senha de app (confira EMAIL_REMETENTE e EMAIL_PASSWORD "
                f"nos secrets): {e}")
    return str(e)


def check_email_login(sender, password):
    """
    Testa as credenciais antes do sorteio, para não fechar a sala se o envio for falhar.
    """
    try:
        with _open_mailer(sender, password):
            pass
        return None
    except Exception as e:
        return _smtp_error_message(e)


def _build_message(sender, dest_email, giver, receiver, room):
    room_name = room.get("name") or "Amigo Secreto"
    date_line = ""
    if room.get("date_label"):
        date_line = f"Data da troca de presentes: {room['date_label']}"

    msg = EmailMessage()
    msg["Subject"] = email_subject(room["code"])
    msg["From"] = sender
    msg["To"] = dest_email

    msg.set_content(
        f"Olá, {giver}!\n\n"
        f"O sorteio de \"{room_name}\" foi realizado.\n"
        f"Você tirou: {receiver}\n\n"
        f"{date_line}\n\n"
        "Shhh! Guarde este segredo!"
    )

    g, r, n = html.escape(giver), html.escape(receiver), html.escape(room_name)
    date_html = f'<p style="margin:16px 0 0;font-size:14px;color:#0E7C59;font-weight:700;">📅 {html.escape(date_line)}</p>' if date_line else ""
    msg.add_alternative(f"""
    <html>
      <body style="margin:0;padding:32px 12px;background:#FFF8E6;font-family:Nunito,'Segoe UI',Arial,sans-serif;color:#1F2937;">
        <div style="max-width:480px;margin:0 auto;background:#FFFFFF;border-radius:20px;overflow:hidden;box-shadow:0 6px 20px rgba(198,40,40,0.12);border:1px solid #F1E3C4;">
          <div style="background:#C62828;padding:22px 24px;text-align:center;">
            <div style="font-size:34px;line-height:1;">🎁</div>
            <div style="color:#FFFFFF;font-size:22px;font-weight:800;margin-top:6px;">Amigo Secreto Conectado</div>
            <div style="color:#FFE7A3;font-size:14px;margin-top:4px;">{n}</div>
          </div>
          <div style="padding:28px 24px;text-align:center;">
            <p style="margin:0;font-size:18px;font-weight:700;">Olá, {g}! 🎄</p>
            <p style="margin:8px 0 20px;font-size:15px;color:#4B5563;">O sorteio foi realizado. Você tirou:</p>
            <div style="display:inline-block;background:#FFF8E6;border:2px dashed #D4A017;border-radius:16px;padding:16px 28px;">
              <span style="font-size:28px;font-weight:800;color:#C62828;">{r}</span>
            </div>
            {date_html}
            <p style="margin:24px 0 0;font-size:13px;color:#6B7280;">🤫 Shhh! Guarde este segredo!</p>
          </div>
          <div style="background:#0E7C59;height:6px;"></div>
        </div>
      </body>
    </html>
    """, subtype='html')
    return msg


def send_admin_key_email(sender, password, owner_name, owner_email, room, admin_key, panel_url):
    """
    Manda ao organizador o código e a chave da sala, para ele não perder o acesso ao painel.
    Retorna None se deu certo, ou a mensagem de erro.
    """
    room_name = room.get("name") or "Amigo Secreto"
    msg = EmailMessage()
    msg["Subject"] = f"🔑 Chave do organizador - Sala {room['code']}"
    msg["From"] = sender
    msg["To"] = owner_email

    msg.set_content(
        f"Olá, {owner_name}!\n\n"
        f"Sua sala \"{room_name}\" foi criada.\n\n"
        f"Código da sala: {room['code']}\n"
        f"Chave do organizador: {admin_key}\n\n"
        f"Para abrir o painel: {panel_url}\n"
        "Lá, use \"Sou o organizador\" com o código e a chave.\n\n"
        "Não compartilhe a chave: com ela qualquer pessoa consegue sortear e gerenciar a sala."
    )

    o, n = html.escape(owner_name), html.escape(room_name)
    c, k, u = html.escape(room["code"]), html.escape(admin_key), html.escape(panel_url, quote=True)
    msg.add_alternative(f"""
    <html>
      <body style="margin:0;padding:32px 12px;background:#FFF8E6;font-family:Nunito,'Segoe UI',Arial,sans-serif;color:#1F2937;">
        <div style="max-width:480px;margin:0 auto;background:#FFFFFF;border-radius:20px;overflow:hidden;box-shadow:0 6px 20px rgba(198,40,40,0.12);border:1px solid #F1E3C4;">
          <div style="background:#C62828;padding:22px 24px;text-align:center;">
            <div style="font-size:34px;line-height:1;">🔑</div>
            <div style="color:#FFFFFF;font-size:22px;font-weight:800;margin-top:6px;">Sua sala foi criada!</div>
            <div style="color:#FFE7A3;font-size:14px;margin-top:4px;">{n}</div>
          </div>
          <div style="padding:28px 24px;text-align:center;">
            <p style="margin:0 0 18px;font-size:16px;">Olá, <b>{o}</b>! Guarde este e-mail: ele tem tudo o que você precisa para voltar ao painel.</p>
            <table role="presentation" style="margin:0 auto 20px;border-collapse:separate;border-spacing:8px;">
              <tr>
                <td style="background:#FFF8E6;border:2px dashed #D4A017;border-radius:14px;padding:12px 18px;">
                  <div style="font-size:12px;color:#6B7280;">Código da sala</div>
                  <div style="font-size:20px;font-weight:800;color:#1F2937;letter-spacing:1px;">{c}</div>
                </td>
                <td style="background:#FFF8E6;border:2px dashed #D4A017;border-radius:14px;padding:12px 18px;">
                  <div style="font-size:12px;color:#6B7280;">Chave do organizador</div>
                  <div style="font-size:20px;font-weight:800;color:#C62828;letter-spacing:1px;white-space:nowrap;">{k}</div>
                </td>
              </tr>
            </table>
            <a href="{u}" style="display:inline-block;background:#C62828;color:#FFFFFF;text-decoration:none;font-weight:800;padding:12px 26px;border-radius:999px;">Abrir o painel do organizador</a>
            <p style="margin:20px 0 0;font-size:13px;color:#6B7280;">🔒 Não compartilhe a chave: com ela qualquer pessoa consegue sortear e gerenciar a sala.</p>
          </div>
          <div style="background:#0E7C59;height:6px;"></div>
        </div>
      </body>
    </html>
    """, subtype='html')

    try:
        with _open_mailer(sender, password) as server:
            server.send_message(msg)
        return None
    except Exception as e:
        return _smtp_error_message(e)


def send_emails_backend(draw_dict, email_map, sender, password, room, only=None):
    """
    Conecta ao e-mail de envio (API do Gmail ou SMTP) e envia os e-mails um por um.
    Retorna (enviados, falhas): listas de e-mails e de nomes, respectivamente.
    """
    givers = [g for g in draw_dict if only is None or g in only]
    sent_list = []
    failed = []

    progress = st.progress(0)
    status = st.empty()

    try:
        with _open_mailer(sender, password) as server:
            for i, giver in enumerate(givers):
                status.text(f"Enviando para {giver}...")
                progress.progress((i + 1) / len(givers))

                dest_email = email_map.get(giver)
                if not dest_email:
                    failed.append(giver)
                    continue
                try:
                    server.send_message(_build_message(sender, dest_email, giver, draw_dict[giver], room))
                    sent_list.append(dest_email)
                except smtplib.SMTPServerDisconnected:
                    raise
                except Exception:
                    failed.append(giver)

    except Exception as e:
        st.error(f"Erro no envio: {e}")
        failed += [g for g in givers if email_map.get(g) not in sent_list and g not in failed]

    progress.empty()
    status.empty()
    return sent_list, failed


def _find_special_folder(mail, flag, fallbacks):
    status, folders = mail.list()
    if status == "OK":
        for line in folders:
            if not line:
                continue
            match = re.match(rb'\((?P<flags>[^)]*)\) "[^"]*" (?P<name>.+)', line)
            if match and flag.encode() in match.group("flags"):
                return match.group("name").decode()
    for name in fallbacks:
        if mail.select(name)[0] == "OK":
            return name
    return None


def _trash_sent_imap(username, password, recipient_list, room_code):
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(username, password)

    sent_folder = _find_special_folder(mail, "\\Sent",['"[Gmail]/Sent Mail"', '"[Gmail]/Enviados"', '"[Gmail]/E-mails enviados"'])
    trash_folder = _find_special_folder(mail, "\\Trash",['"[Gmail]/Trash"', '"[Gmail]/Lixeira"'])
    if not sent_folder or mail.select(sent_folder)[0] != "OK":
        raise RuntimeError("pasta de enviados não encontrada")

    ids = []
    for recipient in set(recipient_list):
        status, data = mail.search(None, f'(TO "{recipient}" SUBJECT "Sala {room_code}")')
        if status == "OK":
            ids += data[0].split()

    if ids:
        id_set = b",".join(ids).decode()
        if trash_folder:
            mail.copy(id_set, trash_folder)
        mail.store(id_set, '+FLAGS', '\\Deleted')
        mail.expunge()

    mail.close()
    mail.logout()
    return len(ids)


def _trash_sent_api(recipient_list, room_code):
    count = 0
    with _GmailApiMailer() as mailer:
        for recipient in set(recipient_list):
            query = f'in:sent to:{recipient} subject:"Sala {room_code}"'
            found = _api_call(mailer.session, "GET", "/messages", params={"q": query})
            for message in found.get("messages", []):
                _api_call(mailer.session, "POST", f"/messages/{message['id']}/trash")
                count += 1
    return count


def clean_sent_folder(username, password, recipient_list, room_code, quiet=False):
    """
    Move para a lixeira os e-mails do sorteio que ficaram na caixa de enviados, para manter o segredo.
    Só apaga mensagens com o assunto desta sala, nada mais. quiet=True não mostra nada na tela.
    """
    if not recipient_list: return

    status_text = st.empty()
    if not quiet:
        status_text.info("🧹 Limpando rastros da caixa de saída...")

    try:
        if gmail_api_configured():
            count = _trash_sent_api(recipient_list, room_code)
        else:
            count = _trash_sent_imap(username, password, recipient_list, room_code)

        if not quiet:
            status_text.success(f"✨ Pronto! {count} e-mails removidos dos enviados.")
            time.sleep(2)
        status_text.empty()

    except Exception as e:
        if not quiet:
            status_text.warning(f"Não foi possível apagar os rastros automaticamente: {e}")
