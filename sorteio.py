import random
import smtplib
import ssl
# import getpass <-- Removido, não é mais necessário
import os
from dotenv import load_dotenv
from email.message import EmailMessage

load_dotenv()

MODO_TESTE = False # Mude para True para testar

# --- 1. CONFIGURE AQUI ---

participantes = {
    "Jessica": "jessicacaetano2050@gmail.com",
    "Janine": "Janineferreirasantos192@gmail.com",
    "Aldenice": "Aldenicemaria193@gmail.com",
    "Jaqueline": "Jaquelineoliveiraaa12@gmail.com",
}

email_remetente = "Rafaelgaara1@gmail.com"
assunto_email = "Sorteio do Amigo Havaianas 2025!"

# --- FIM DA CONFIGURAÇÃO ---


def fazer_sorteio(nomes):
    """
    Sorteia os pares, garantindo que ninguém tire a si mesmo.
    Retorna um dicionário: {doador: recebedor}
    """
    print("Iniciando sorteio...")
    doadores = list(nomes)
    recebedores = list(nomes)
    sorteio_final = {}
    
    random.shuffle(recebedores)

    while any(doadores[i] == recebedores[i] for i in range(len(doadores))):
        print("Opa, alguém tirou a si mesmo. Re-sorteando...")
        random.shuffle(recebedores)

    for i in range(len(doadores)):
        sorteio_final[doadores[i]] = recebedores[i]
        
    print("Sorteio concluído com sucesso!")
    return sorteio_final


def criar_corpo_email(doador, recebedor):
    """
    Cria a mensagem de e-mail estruturada.
    """
    return f"""
    Olá, {doador}!
    
    O sorteio do nosso Amigo Havaianas foi realizado!
    
    Você tirou:
    
    >>>>>   {recebedor}   <<<<<
    
    Guarde este e-mail em segredo!
    
    Boas festas!
    """

# --- FUNÇÃO DE ENVIO MODIFICADA COM VALIDAÇÃO ---
def enviar_emails(sorteio, lista_emails, remetente, senha):
    
    if MODO_TESTE:
        print("\n******************************")
        print("*** MODO DE TESTE ATIVADO ***")
        print("Os e-mails NÃO serão enviados. Os pares sorteados foram:")
        for doador, recebedor in sorteio.items():
            print(f"   {doador}  ->  {recebedor}")
        print("******************************")
        return # Sai da função para não enviar
    
    # --- Início da Validação ---
    # Listas para guardar o status de cada envio
    sucessos = []
    falhas = []
    # --- Fim da Validação ---

    smtp_server = "smtp.gmail.com"
    port = 465  # Para SSL
    contexto = ssl.create_default_context()
    
    print("\nIniciando conexão com o servidor SMTP...")
    
    try:
        # Usa 'with' para garantir que a conexão seja fechada
        with smtplib.SMTP_SSL(smtp_server, port, context=contexto) as server:
            server.login(remetente, senha)
            print("Login no servidor de e-mail bem-sucedido.")
            print("Iniciando envio dos e-mails individuais...")
            
            # Loop principal de envio
            for doador, recebedor in sorteio.items():
                email_destinatario = lista_emails[doador]
                
                # Cria o objeto de e-mail
                msg = EmailMessage()
                msg.set_content(criar_corpo_email(doador, recebedor))
                msg["Subject"] = assunto_email
                msg["From"] = remetente
                msg["To"] = email_destinatario
                
                # --- Bloco de try individual ---
                try:
                    # Tenta enviar este e-mail específico
                    server.send_message(msg)
                    # Se deu certo, registra o sucesso
                    print(f"-> [Sucesso] E-mail enviado para {doador} ({email_destinatario})")
                    sucessos.append(doador)
                
                except smtplib.SMTPException as e:
                    # Se falhar, registra a falha e continua o loop
                    print(f"-> [FALHA] E-mail para {doador} ({email_destinatario}). Erro: {e}")
                    falhas.append((doador, email_destinatario, str(e)))
                # --- Fim do bloco individual ---
                
    except smtplib.SMTPException as e:
        print(f"\n[ERRO FATAL] Não foi possível conectar ou fazer login no servidor SMTP: {e}")
        print("Verifique seu e-mail ('{remetente}'), sua 'Senha de App' e a conexão.")
        print("Nenhum e-mail foi enviado.")
        return # Interrompe a função se o login falhar

    # --- Relatório Final de Validação ---
    print("\n--- Relatório Final de Envio ---")
    print(f"Total de participantes: {len(sorteio)}")
    print(f"E-mails enviados com sucesso: {len(sucessos)}")
    print(f"Falhas no envio: {len(falhas)}")
    
    if falhas:
        print("\n[ATENÇÃO] Os seguintes e-mails não puderam ser enviados:")
        for (doador, email, erro) in falhas:
            print(f"  - {doador} (Email: {email})")
            print(f"    Motivo: {erro}\n")
    else:
        print("\nTodos os e-mails foram enviados com sucesso!")
        print("O amigo secreto está valendo!")
    # --- Fim do Relatório ---
    
def apagar_rastro_imap(usuario, senha, destinatario):
    """
    Conecta via IMAP para apagar o e-mail da pasta de Enviados.
    Isso evita que você veja quem tirou quem.
    """
    print(f"   [IMAP] Apagando rastro do envio para {destinatario}...")
    try:
        # Conecta no Gmail
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(usuario, senha)
        
        # Seleciona a pasta de enviados. 
        # NOTA: O Gmail geralmente usa "[Gmail]/Sent Mail" via código, 
        # mesmo que no site apareça "Enviados".
        try:
            mail.select('"[Gmail]/Sent Mail"')
        except:
            # Se der erro, tenta o nome em português (raro via IMAP, mas possível)
            mail.select('"[Gmail]/Enviados"')

        # Procura emails enviados PARA o destinatário específico
        # Search retorna IDs dos emails encontrados
        status, data = mail.search(None, f'(TO "{destinatario}")')
        
        email_ids = data[0].split()
        
        if not email_ids:
            print("   [IMAP] Nenhum e-mail encontrado para apagar (talvez delay do servidor).")
            return

        # Marca todos os emails encontrados para deleção (normalmente é só 1)
        for e_id in email_ids:
            mail.store(e_id, '+FLAGS', '\\Deleted')
        
        # Confirma a exclusão definitiva
        mail.expunge()
        
        # Fecha conexão
        mail.close()
        mail.logout()
        print("   [IMAP] Rastro apagado com sucesso!")
        
    except Exception as e:
        print(f"   [IMAP] Erro ao tentar apagar: {e}")

# --- Função Principal (Limpando as mensagens desnecessárias) ---
def main():
    if len(participantes) < 2:
        print("Erro: São necessários pelo menos 2 participantes.")
        return

    # Carrega a senha do .env
    senha_remetente = os.getenv("EMAIL_PASSWORD")
    
    # Validação da senha
    if not senha_remetente and not MODO_TESTE:
        print("\n[ERRO FATAL]")
        print("A variável 'EMAIL_PASSWORD' não foi encontrada no ambiente.")
        print("Verifique se você:")
        print("1. Criou o arquivo '.env' no mesmo diretório.")
        print("2. Adicionou a linha 'EMAIL_PASSWORD=sua_senha_de_app' nele.")
        return # Para o script

    print(f"Iniciando sorteio com o e-mail: {email_remetente}")
    if not MODO_TESTE:
        print("Senha carregada com sucesso do arquivo .env.")

    # 1. Realiza o sorteio
    mapa_sorteio = fazer_sorteio(participantes.keys())
    
    # 2. Envia os e-mails (com a nova validação)
    enviar_emails(mapa_sorteio, participantes, email_remetente, senha_remetente)

# Executa o script
if __name__ == "__main__":
    main()