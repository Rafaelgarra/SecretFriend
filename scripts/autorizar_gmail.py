"""
Autoriza o app a enviar e-mails pela API do Gmail (sem senha de app nem verificação em duas etapas).

Uso, uma vez só, no seu computador:
    pip install google-auth-oauthlib
    python scripts/autorizar_gmail.py caminho/do/client_secret.json

O navegador abre: entre com a conta que envia os e-mails (ex.: friendsecreto.online@gmail.com) e permita.
No fim o script mostra a seção [gmail_api] para colar nos Secrets do Streamlit Cloud.
Não compartilhe esses valores: eles dão acesso para enviar e-mails por essa conta.

Se o Google bloquear a permissão completa, rode de novo com --so-envio: o app envia normalmente,
só não consegue tirar os e-mails do sorteio da pasta Enviados.
"""
import argparse
import json
import sys

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    sys.exit("Instale antes: pip install google-auth-oauthlib")

FULL_SCOPE = "https://www.googleapis.com/auth/gmail.modify"  # enviar + mover os enviados para a lixeira
SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("client_secret", help="JSON do ID do cliente OAuth (tipo App para computador)")
    parser.add_argument("--so-envio", action="store_true", help="pede só a permissão de enviar")
    args = parser.parse_args()

    scope = SEND_SCOPE if args.so_envio else FULL_SCOPE
    flow = InstalledAppFlow.from_client_secrets_file(args.client_secret, scopes=[scope])
    # access_type=offline + prompt=consent garantem o refresh_token, que é o que o app usa
    credentials = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    if not credentials.refresh_token:
        sys.exit("O Google não devolveu o refresh_token. Rode de novo e aceite todas as permissões.")

    print("\nPronto! Cole isto nos Secrets do Streamlit Cloud (App > Settings > Secrets):\n")
    print("[gmail_api]")
    print(f"client_id = {json.dumps(credentials.client_id)}")
    print(f"client_secret = {json.dumps(credentials.client_secret)}")
    print(f"refresh_token = {json.dumps(credentials.refresh_token)}")
    print("\nMantenha também EMAIL_REMETENTE com o e-mail que você acabou de autorizar.")


if __name__ == "__main__":
    main()
