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
IMAP_SERVER = "imap.gmail.com"

_rng = random.SystemRandom()


def email_subject(room_code):
    # O trecho "Sala XXXX" é ASCII para permitir a busca via IMAP na limpeza dos enviados
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


def check_smtp_login(sender, password):
    """
    Testa as credenciais antes do sorteio, para não fechar a sala se o envio for falhar.
    """
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(sender, password)
        return None
    except Exception as e:
        return str(e)


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


def send_emails_backend(draw_dict, email_map, sender, password, room, test_mode, only=None):
    """
    Conecta ao SMTP e envia os e-mails um por um.
    Retorna (enviados, falhas): listas de e-mails e de nomes, respectivamente.
    """
    givers = [g for g in draw_dict if only is None or g in only]
    sent_list = []
    failed = []

    progress = st.progress(0)
    status = st.empty()

    if test_mode:
        for giver in givers:
            st.info(f"[TESTE] {giver} tirou {draw_dict[giver]} (simulação de envio para {email_map.get(giver, '?')})")
        progress.empty()
        return sent_list, failed

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(sender, password)

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


def clean_sent_folder(username, password, recipient_list, room_code):
    """
    Move para a lixeira os e-mails do sorteio que ficaram na caixa de enviados, para manter o segredo.
    Só apaga mensagens com o assunto desta sala, nada mais.
    """
    if not recipient_list: return

    status_text = st.empty()
    status_text.info("🧹 Limpando rastros da caixa de saída...")

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(username, password)

        sent_folder = _find_special_folder(mail, "\\Sent", ['"[Gmail]/Sent Mail"', '"[Gmail]/Enviados"', '"[Gmail]/E-mails enviados"'])
        trash_folder = _find_special_folder(mail, "\\Trash", ['"[Gmail]/Trash"', '"[Gmail]/Lixeira"'])
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

        status_text.success(f"✨ Pronto! {len(ids)} e-mails removidos dos enviados.")
        time.sleep(2)
        status_text.empty()

    except Exception as e:
        status_text.warning(f"Não foi possível apagar os rastros automaticamente: {e}")
