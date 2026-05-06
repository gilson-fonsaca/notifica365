# Notifica365

Programa de notificações de calendário para Linux que lê uma agenda do **Microsoft Office 365** via URL ICS e envia alertas para um canal do **Discord** antes dos eventos.

Devido às restrições impostas pela Microsoft ao ambiente Linux, as agendas de reuniões nem sempre são exibidas nas notificações da interface gráfica. Este programa elimina este problema enviando ao Discord todas as agendas de reuniões que chegam ao Outlook.

## Support

If this extension helps you, consider buying me a coffee:

[![Buy Me a Coffee](https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png)](https://www.buymeacoffee.com/Gilsonf)

## Como funciona

1. Baixa o arquivo ICS da URL configurada (com cache local para evitar requisições excessivas).
2. Varre os eventos do dia atual.
3. Para cada evento que ainda não foi notificado, envia uma mensagem via **webhook do Discord** nos intervalos configurados antes do horário do evento (ex.: 15 min, 10 min, 5 min e na hora).
4. A mensagem inclui o título da reunião, horário de início, tempo restante e, quando disponível, o link de acesso (Teams, Google Meet, Zoom ou Webex).
5. Persiste o estado das notificações já enviadas para evitar repetições.

O programa é projetado para ser executado periodicamente via **cron** (ex.: a cada minuto).

## Dependências do sistema operacional

Apenas Python 3 é necessário para executar ou compilar:

```bash
sudo apt install python3 python3-venv python3-pip
```

## Dependências Python

Listadas em `requirements.txt`:

| Pacote | Versão mínima | Uso |
|---|---|---|
| `requests` | 2.31.0 | Download do ICS via HTTP e envio ao webhook Discord |
| `ics` | 0.7.2 | Parsing do calendário iCalendar |
| `python-dotenv` | 1.0.0 | Carregamento do arquivo `.env` |

> O `pyinstaller` é instalado automaticamente pelo `build.sh` apenas para gerar o binário, não é uma dependência de execução.

## Configuração

Crie um arquivo `.env` na mesma pasta do binário/script com as variáveis abaixo:

```dotenv
# Obrigatório: URL ICS do seu calendário Office 365
ICS_URL=https://outlook.office365.com/owa/calendar/.../.../calendar.ics

# Obrigatório: URL do webhook do Discord para onde as notificações serão enviadas
DISCORD_WEBHOOK_URL=https://discordapp.com/api/webhooks/SEU_ID/SEU_TOKEN

# Opcional: minutos antes do evento para disparar o alerta (padrão: 15,5,0)
ALERT_MINUTES=15,10,5,0

# Opcional: fuso horário em horas (padrão: -3 para BRT)
TZ_OFFSET=-3

# Opcional: intervalo em minutos para recarregar o ICS (padrão: 30)
ICS_UPDATE_INTERVAL=30

# Opcional: arquivo de cache do ICS (padrão: /tmp/calendar_cache.ics)
CACHE_FILE=/tmp/calendar_cache.ics

# Opcional: arquivo de estado das notificações (padrão: /tmp/calendar_notifications.json)
STATE_FILE=/tmp/calendar_notifications.json

# Opcional: arquivo de log (padrão: /tmp/notifica365.log)
LOG_FILE=/tmp/notifica365.log
```

### Como criar um webhook no Discord

1. Abra as configurações do canal desejado no Discord.
2. Acesse **Integrações → Webhooks → Novo Webhook**.
3. Dê um nome (ex.: `Notifica365`), escolha o canal e clique em **Copiar URL do Webhook**.
4. Cole o valor em `DISCORD_WEBHOOK_URL` no arquivo `.env`.

### Como obter a URL ICS do Office 365

1. Acesse o [Outlook na Web](https://outlook.office.com).
2. Vá em **Configurações → Ver todas as configurações → Calendário → Calendários compartilhados**.
3. Em "Publicar um calendário", selecione o calendário e escolha **"Todos os detalhes"**.
4. Copie a URL do formato **ICS** e cole em `ICS_URL`.

## Compilando o binário

```bash
chmod +x build.sh
./build.sh
```

O binário será gerado em `./dist/notifica365`.

## Executando

### Diretamente com Python

```bash
pip install -r requirements.txt
python3 notifica.py
```

### Com o binário compilado

```bash
./dist/notifica365
```

Certifique-se de que o arquivo `.env` está na mesma pasta de onde o comando é executado.

## Configurando execução automática via cron

Para executar a cada minuto:

```bash
crontab -e
```

Adicione a linha (ajuste o caminho conforme necessário):

```cron
* * * * * /caminho/para/notifica365 >> /tmp/notifica365-cron.log 2>&1
```

## Logs

O programa registra todas as atividades no arquivo definido em `LOG_FILE` (padrão: `/tmp/notifica365.log`).

Para acompanhar em tempo real:

```bash
tail -f /tmp/notifica365.log
```

## Resolução de problemas

| Problema | Causa provável | Solução |
|---|---|---|
| Notificação não chega ao Discord | `DISCORD_WEBHOOK_URL` ausente ou inválida | Verifique o valor no `.env` e a URL do webhook no Discord |
| Notificação chega sem link de reunião | URL não encontrada no evento | Verifique se o convite contém o link de Teams/Meet no corpo ou local |
| Horário errado nos eventos | Fuso horário incorreto | Ajuste `TZ_OFFSET` no `.env` |
| Eventos do Office 365 sem horário correto | Bug da biblioteca `ics` com timezones do O365 | Use `TZ_OFFSET` para corrigir |
