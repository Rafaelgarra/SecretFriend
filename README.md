# 🎁 Amigo Secreto Conectado

App em [Streamlit](https://streamlit.io) para organizar amigo secreto online: o organizador cria a sala, compartilha o convite, os participantes confirmam ou recusam pelo link e, no sorteio, cada um recebe por e-mail quem tirou.

**No ar:** https://appfriend-dyhgtzh8udytssfjcul2rh.streamlit.app/ (Streamlit Community Cloud, publicado a partir da branch `main`).

## Como funciona

1. **Criar sala:** o organizador informa nome da sala, o próprio nome e e-mail e, opcionalmente, o dia da troca de presentes. O app gera um **código** (4 caracteres) e uma **chave do organizador**, mostra a chave na tela uma única vez e envia o código e a chave para o e-mail do organizador.
2. **Painel do organizador:** acessado com código + chave (ou pelo link `?organizador=CÓDIGO` do e-mail). Nele o organizador:
   - escolhe se também participa (toggle "Também vou participar", ligado por padrão);
   - compartilha o convite (WhatsApp, Facebook, X, Telegram, menu de compartilhar do celular ou texto para copiar);
   - adiciona participantes manualmente, um por vez ou colando uma lista (`Nome, e-mail` por linha);
   - vê quem confirmou e quem recusou (com recado);
   - realiza o sorteio e, depois, pode reenviar o e-mail de um participante.
3. **Convite (`?sala=CÓDIGO`):** quem recebe o link vê "Você foi convidado(a)…", com o nome do organizador, e escolhe **Vou participar** (nome e e-mail) ou **Não vou participar** (nome e recado opcional).
4. **Sorteio:** ninguém tira a si mesmo; o resultado fica salvo criptografado (para reenvios), cada participante recebe um e-mail e as mensagens são movidas para a lixeira da conta que envia, para manter o segredo. Não existe modo de teste: o sorteio é sempre real e encerra a sala.

Salas antigas, criadas antes da chave do organizador, abrem o painel só com o código.

## Estrutura do código

| Arquivo | O que tem |
|---|---|
| `app.py` | Telas e fluxo (início, painel, convite, política de privacidade) |
| `ui.py` | Identidade visual: CSS, ícones, logo e blocos de HTML |
| `service/database.py` | Leitura e gravação na planilha do Google, criptografia |
| `service/service.py` | Sorteio e envio/limpeza de e-mails (API do Gmail ou SMTP) |
| `scripts/autorizar_gmail.py` | Gera a autorização da API do Gmail (rodado uma vez, localmente) |
| `.streamlit/config.toml` | Tema (cores e fonte Nunito) |
| `.streamlit/secrets.toml.example` | Modelo dos secrets, sem valores reais |

## Banco de dados (Google Sheets)

Planilha **`AmigoSecretoDB`**, acessada por uma conta de serviço do Google Cloud (precisa ser **Editor** da planilha). `Salas` e `Participantes` **não têm linha de cabeçalho** (`Respostas` é criada com uma); o app lê todas as linhas e filtra pelo código da sala na coluna A.

| Aba | Colunas |
|---|---|
| `Salas` | A código · B status (`OPEN`/`CLOSED`) · C hash da chave · D nome · E data da troca · F sorteio* · G nome do organizador* · H e-mail do organizador* |
| `Participantes` | A código da sala · B nome* · C e-mail* |
| `Respostas` | A código da sala · B nome* · C recado* · D data — criada automaticamente na primeira recusa |

\* criptografado com Fernet (`ENCRYPTION_KEY`).

Todas as gravações usam `table_range="A1"`: sem isso o Sheets pode gravar a linha deslocada de coluna quando a anterior tem células vazias. Para apagar uma sala, exclua a linha dela em `Salas` e as linhas com o mesmo código em `Participantes` e `Respostas` (o **Histórico de versões** da planilha desfaz erros).

## Secrets

Configurados em **Streamlit Cloud → App → Settings → Secrets** (no seu PC, em `.streamlit/secrets.toml`, que o git ignora). O formato completo está em [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example).

| Chave | Para quê |
|---|---|
| `EMAIL_REMETENTE` | Conta Gmail que envia os e-mails (`friendsecreto.online@gmail.com`) |
| `[gmail_api]` | `client_id`, `client_secret` e `refresh_token` para enviar pela API do Gmail (recomendado) |
| `EMAIL_PASSWORD` | Só para envio por SMTP: **senha de app** do Gmail (exige verificação em duas etapas). Desnecessário com `[gmail_api]` |
| `ENCRYPTION_KEY` | Chave Fernet. **Nunca troque**: com outra chave os dados já salvos ficam ilegíveis |
| `APP_URL` | Link do app usado nos convites (opcional) |
| `[gcp_service_account]` | Conteúdo do JSON da conta de serviço que acessa a planilha |

No TOML, as chaves soltas (`EMAIL_REMETENTE`, `ENCRYPTION_KEY`…) precisam vir **antes** das seções `[gmail_api]` e `[gcp_service_account]`.

## Envio de e-mails pela API do Gmail

O Streamlit Cloud não conseguiu enviar por SMTP (o Gmail fechava a conexão nas portas 465 e 587), e a conta não permitia criar senha de app. Por isso o envio usa a **API do Gmail via HTTPS**, autorizada uma única vez. Se a seção `[gmail_api]` não existir, o app volta a tentar SMTP com `EMAIL_PASSWORD`.

Para refazer a autorização (por exemplo, se o `refresh_token` for revogado ou a senha da conta mudar):

1. **Google Cloud Console**, no mesmo projeto da conta de serviço: a **Gmail API** precisa estar ativada.
2. **Google Auth Platform → Branding:** nome "Amigo Secreto", e-mail de suporte e de contato do desenvolvedor `friendsecreto.online@gmail.com`, e:
   - Página inicial: `https://appfriend-dyhgtzh8udytssfjcul2rh.streamlit.app/`
   - Política de Privacidade: `https://appfriend-dyhgtzh8udytssfjcul2rh.streamlit.app/?pagina=privacidade`
   - Domínio autorizado: `appfriend-dyhgtzh8udytssfjcul2rh.streamlit.app` (o endereço completo: `streamlit.app` é sufixo público)
   - Não envie logotipo (isso passa a exigir verificação do Google).
3. **Público-alvo:** tipo **Externo** e status **Em produção**. Em "Testando", a autorização expira em 7 dias.
4. **Clientes → Criar cliente → "App para computador"** → baixe o JSON como `client_secret.json` na pasta do projeto.
5. No terminal, na pasta do projeto:
   ```bash
   pip install google-auth-oauthlib
   python scripts/autorizar_gmail.py client_secret.json
   ```
   Entre com a conta que envia. No aviso "O Google não verificou este app": **Avançado → Acessar Amigo Secreto → Continuar**. Se o Google bloquear a permissão completa, rode de novo com `--so-envio` (o envio funciona, mas os e-mails não são tirados da pasta Enviados).
6. Cole o bloco `[gmail_api]` que o script mostrar nos Secrets do Streamlit Cloud e salve.
7. **Apague o `client_secret.json`** da pasta (o `.gitignore` já ignora `*.json`, mas ele não precisa ficar no computador). Para refazer o passo 5, baixe de novo em **Google Auth Platform → Clientes → Amigo Secreto → Baixar JSON**.

Nunca cole `client_secret`, `refresh_token` ou senhas em chats, issues ou commits.

## Rodar localmente

```bash
pip install -r requirements.txt
```
```bash
streamlit run app.py
```

Precisa de `.streamlit/secrets.toml` preenchido (copie do `.example`). Atenção: localmente o app usa a **mesma planilha e a mesma conta de e-mail** de produção, então salas e sorteios feitos assim são reais.

## Publicar

Todo push na `main` é publicado automaticamente pelo Streamlit Cloud em cerca de 1 minuto. Mudanças em `requirements.txt` fazem o Cloud reinstalar os pacotes no deploy.

## Limitações conhecidas

- **Prévia do link no WhatsApp:** mostra "Streamlit — This app was built in Streamlit!". O plano gratuito do Streamlit Cloud não permite trocar o título e a imagem da prévia.
- **Emojis no convite:** só emojis de 2 bytes (✨ ❄️ ⏰ #️⃣ ➡️). Os de 4 bytes (🎁 🎄 📅) viravam "�" no link de compartilhar do WhatsApp; por isso o botão também usa `api.whatsapp.com/send` em vez de `wa.me`.
- **Facebook** ignora o texto do convite e compartilha só o link. O **Instagram** não tem link de compartilhamento: use o texto para copiar.
- **Cota do Google Sheets:** 60 leituras por minuto. O app guarda as abas em cache e tenta de novo automaticamente quando o Google responde "muitas requisições".
- **Botões "Aceitar/Recusar" dentro da mensagem** não existem no WhatsApp comum (só na API do WhatsApp Business); por isso o convite leva a uma página com os dois botões.
