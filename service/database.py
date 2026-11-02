import gspread
import streamlit as st
import secrets
import string
import hashlib
import hmac
import json
import os
from datetime import datetime
from cryptography.fernet import Fernet, InvalidToken

# Colunas da aba "Salas": Código | Status | Hash da chave | Nome | Data | Sorteio (criptografado)
COL_STATUS = 2
COL_ADMIN_HASH = 3
COL_NAME = 4
COL_DATE = 5
COL_DRAW = 6

CODE_CHARS = string.ascii_uppercase + string.digits
KEY_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem 0/O e 1/I para evitar confusão


def get_secret(name):
    value = os.getenv(name)
    if value:
        return value
    try:
        return st.secrets.get(name)
    except Exception:
        return None


@st.cache_resource
def get_cipher():
    key = get_secret("ENCRYPTION_KEY")
    if not key:
        raise ValueError("Chave de criptografia (ENCRYPTION_KEY) não encontrada!")
    return Fernet(key)


def encrypt_data(text):
    if not text: return ""
    return get_cipher().encrypt(text.encode()).decode()


def decrypt_data(text):
    if not text: return ""
    try:
        return get_cipher().decrypt(text.encode()).decode()
    except InvalidToken:
        # Registros antigos foram salvos sem criptografia
        return text


@st.cache_resource(ttl=3600)
def get_connection():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
    except Exception:
        creds_dict = None

    if creds_dict:
        client = gspread.service_account_from_dict(creds_dict)
    else:
        client = gspread.service_account(filename="service_account.json")
    return client.open("AmigoSecretoDB")


def _rooms_sheet():
    return get_connection().worksheet("Salas")


def _participants_sheet():
    return get_connection().worksheet("Participantes")


def _find_room_row(rooms_sheet, code):
    codes = rooms_sheet.col_values(1)
    if code in codes:
        return codes.index(code) + 1
    return None


def _hash_admin_key(code, key):
    return hashlib.sha256(f"{code}:{key.strip().upper()}".encode()).hexdigest()


def create_room(name="", draw_date=""):
    """Cria a sala e devolve (código, chave do organizador)."""
    rooms_sheet = _rooms_sheet()
    existing = set(rooms_sheet.col_values(1))

    code = ''.join(secrets.choice(CODE_CHARS) for _ in range(4))
    while code in existing:
        code = ''.join(secrets.choice(CODE_CHARS) for _ in range(4))

    admin_key = ''.join(secrets.choice(KEY_CHARS) for _ in range(8))
    admin_key = f"{admin_key[:4]}-{admin_key[4:]}"

    rooms_sheet.append_row([code, "OPEN", _hash_admin_key(code, admin_key), name, draw_date, ""])
    return code, admin_key


def get_room(code):
    """Retorna os dados da sala ou None se ela não existir."""
    if not code:
        return None
    rooms_sheet = _rooms_sheet()
    row = _find_room_row(rooms_sheet, code)
    if not row:
        return None

    values = rooms_sheet.row_values(row)
    values += [""] * (COL_DRAW - len(values))
    return {
        "code": code,
        "status": values[COL_STATUS - 1] or "OPEN",
        "admin_hash": values[COL_ADMIN_HASH - 1],
        "name": values[COL_NAME - 1],
        "date": values[COL_DATE - 1],
        "has_draw": bool(values[COL_DRAW - 1]),
    }


def verify_admin(room, key):
    """Confere a chave do organizador. Salas antigas, criadas sem chave, continuam acessíveis só pelo código."""
    if not room["admin_hash"]:
        return True
    if not key:
        return False
    return hmac.compare_digest(room["admin_hash"], _hash_admin_key(room["code"], key))


def close_room(code, draw_result):
    """Fecha as inscrições e guarda o sorteio criptografado para permitir reenvios."""
    rooms_sheet = _rooms_sheet()
    row = _find_room_row(rooms_sheet, code)
    if not row:
        raise ValueError(f"Sala {code} não encontrada.")

    enc_draw = encrypt_data(json.dumps(draw_result, ensure_ascii=False))
    rooms_sheet.batch_update([
        {"range": gspread.utils.rowcol_to_a1(row, COL_STATUS), "values": [["CLOSED"]]},
        {"range": gspread.utils.rowcol_to_a1(row, COL_DRAW), "values": [[enc_draw]]},
    ])


def get_draw(code):
    rooms_sheet = _rooms_sheet()
    row = _find_room_row(rooms_sheet, code)
    if not row:
        return None
    enc_draw = rooms_sheet.cell(row, COL_DRAW).value
    if not enc_draw:
        return None
    return json.loads(decrypt_data(enc_draw))


def add_participant(room_code, name, email):
    _participants_sheet().append_row([room_code, encrypt_data(name), encrypt_data(email)])


def add_participants(room_code, people):
    """Cadastra vários (nome, e-mail) de uma vez, numa única escrita na planilha."""
    if people:
        _participants_sheet().append_rows([[room_code, encrypt_data(n), encrypt_data(e)] for n, e in people])


def _responses_sheet():
    """Aba "Respostas" com quem recusou o convite. É criada na primeira recusa."""
    sheet = get_connection()
    try:
        return sheet.worksheet("Respostas")
    except gspread.WorksheetNotFound:
        responses = sheet.add_worksheet(title="Respostas", rows=1000, cols=4)
        responses.append_row(["Sala", "Nome", "Recado", "Data"])
        return responses


def add_decline(room_code, name, message=""):
    _responses_sheet().append_row([room_code, encrypt_data(name), encrypt_data(message),
                                   datetime.now().strftime("%Y-%m-%d %H:%M")])


def get_declines(room_code):
    """Lista de (nome, recado) de quem respondeu que não vai participar."""
    try:
        rows = get_connection().worksheet("Respostas").get_all_values()
    except gspread.WorksheetNotFound:
        return []
    return [(decrypt_data(r[1]), decrypt_data(r[2])) for r in rows[1:] if len(r) >= 3 and r[0] == room_code]


def get_participants(room_code):
    all_rows = _participants_sheet().get_all_values()

    participants_map = {}
    for row in all_rows[1:]:
        if len(row) >= 3 and row[0] == room_code:
            participants_map[decrypt_data(row[1])] = decrypt_data(row[2])

    return participants_map
