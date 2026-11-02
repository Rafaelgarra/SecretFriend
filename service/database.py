import gspread
from gspread.http_client import BackOffHTTPClient
import streamlit as st
import secrets
import string
import hashlib
import hmac
import json
import os
from datetime import datetime
from cryptography.fernet import Fernet, InvalidToken

# Colunas da aba "Salas": Código | Status | Hash da chave | Nome | Data | Sorteio |
# Nome do organizador | E-mail do organizador (os três últimos criptografados)
COL_STATUS = 2
COL_ADMIN_HASH = 3
COL_NAME = 4
COL_DATE = 5
COL_DRAW = 6
COL_OWNER_NAME = 7
COL_OWNER_EMAIL = 8

# Sem isso o Sheets procura a "tabela" na aba inteira e, se uma linha tiver células vazias no meio,
# grava a próxima deslocada para outras colunas (o código da sala some da coluna A).
APPEND_FROM = "A1"

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

    # BackOffHTTPClient espera e tenta de novo quando o Google responde "muitas requisições" (429)
    if creds_dict:
        client = gspread.service_account_from_dict(creds_dict, http_client=BackOffHTTPClient)
    else:
        client = gspread.service_account(filename="service_account.json", http_client=BackOffHTTPClient)
    return client.open("AmigoSecretoDB")


@st.cache_resource(ttl=3600)
def _worksheet(title):
    # No gspread 6 cada worksheet() relê os metadados da planilha; guardar a aba evita estourar
    # a cota de leituras do Google (60 por minuto) com várias chamadas por página.
    return get_connection().worksheet(title)


def _rooms_sheet():
    return _worksheet("Salas")


def _participants_sheet():
    return _worksheet("Participantes")


def _find_room_row(rooms_sheet, code):
    codes = rooms_sheet.col_values(1)
    if code in codes:
        return codes.index(code) + 1
    return None


def _hash_admin_key(code, key):
    return hashlib.sha256(f"{code}:{key.strip().upper()}".encode()).hexdigest()


def create_room(name="", draw_date="", owner_name="", owner_email=""):
    """Cria a sala e devolve (código, chave do organizador)."""
    rooms_sheet = _rooms_sheet()
    existing = set(rooms_sheet.col_values(1))

    code = ''.join(secrets.choice(CODE_CHARS) for _ in range(4))
    while code in existing:
        code = ''.join(secrets.choice(CODE_CHARS) for _ in range(4))

    admin_key = ''.join(secrets.choice(KEY_CHARS) for _ in range(8))
    admin_key = f"{admin_key[:4]}-{admin_key[4:]}"

    rooms_sheet.append_row([code, "OPEN", _hash_admin_key(code, admin_key), name, draw_date, "",
                            encrypt_data(owner_name), encrypt_data(owner_email)], table_range=APPEND_FROM)
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
    values += [""] * (COL_OWNER_EMAIL - len(values))
    return {
        "code": code,
        "status": values[COL_STATUS - 1] or "OPEN",
        "admin_hash": values[COL_ADMIN_HASH - 1],
        "name": values[COL_NAME - 1],
        "date": values[COL_DATE - 1],
        "has_draw": bool(values[COL_DRAW - 1]),
        "owner_name": decrypt_data(values[COL_OWNER_NAME - 1]),
        "owner_email": decrypt_data(values[COL_OWNER_EMAIL - 1]),
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
    _participants_sheet().append_row([room_code, encrypt_data(name), encrypt_data(email)], table_range=APPEND_FROM)


def add_participants(room_code, people):
    """Cadastra vários (nome, e-mail) de uma vez, numa única escrita na planilha."""
    if people:
        _participants_sheet().append_rows([[room_code, encrypt_data(n), encrypt_data(e)] for n, e in people],
                                          table_range=APPEND_FROM)


def remove_participant(room_code, email):
    """Tira da sala o participante com este e-mail."""
    participants_sheet = _participants_sheet()
    rows = participants_sheet.get_all_values()
    target = email.strip().lower()
    matches = [i + 1 for i, r in enumerate(rows) if i > 0 and len(r) >= 3 and r[0] == room_code
               and decrypt_data(r[2]).strip().lower() == target]
    for row_number in reversed(matches):
        participants_sheet.delete_rows(row_number)


def _responses_sheet():
    """Aba "Respostas" com quem recusou o convite. É criada na primeira recusa."""
    try:
        return _worksheet("Respostas")
    except gspread.WorksheetNotFound:
        responses = get_connection().add_worksheet(title="Respostas", rows=1000, cols=4)
        responses.append_row(["Sala", "Nome", "Recado", "Data"], table_range=APPEND_FROM)
        return responses


def add_decline(room_code, name, message=""):
    _responses_sheet().append_row([room_code, encrypt_data(name), encrypt_data(message),
                                   datetime.now().strftime("%Y-%m-%d %H:%M")], table_range=APPEND_FROM)


def get_declines(room_code):
    """Lista de (nome, recado) de quem respondeu que não vai participar."""
    try:
        rows = _worksheet("Respostas").get_all_values()
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
