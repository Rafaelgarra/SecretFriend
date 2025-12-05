import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import random
import string

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def get_connection():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    except:
        creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", SCOPE)
    
    client = gspread.authorize(creds)
    sheet = client.open("AmigoSecretoDB") 
    return sheet

def create_room():
    sheet = get_connection()
    rooms_sheet = sheet.worksheet("Salas")
    
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    rooms_sheet.append_row([code, "OPEN"])
    return code

def get_room_status(code):
    sheet = get_connection()
    rooms_sheet = sheet.worksheet("Salas")
    
    try:
        cell = rooms_sheet.find(code)
        if cell:
            return rooms_sheet.cell(cell.row, 2).value
    except:
        return None
    return None

def close_room(code):
    sheet = get_connection()
    rooms_sheet = sheet.worksheet("Salas")
    try:
        cell = rooms_sheet.find(code)
        if cell:
            rooms_sheet.update_cell(cell.row, 2, "CLOSED")
    except:
        pass

def add_participant(room_code, name, email):
    sheet = get_connection()
    participants_sheet = sheet.worksheet("Participantes")
    participants_sheet.append_row([room_code, name, email])

def get_participants(room_code):
    sheet = get_connection()
    participants_sheet = sheet.worksheet("Participantes")
    all_rows = participants_sheet.get_all_values()
    
    participants_map = {}
    for row in all_rows[1:]:
        if row[0] == room_code:
            participants_map[row[1]] = row[2]
            
    return participants_map