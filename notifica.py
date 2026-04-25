import re
import sys
import requests
from ics import Calendar
from datetime import datetime, timezone, timedelta
import json
import os
import logging
from dotenv import load_dotenv

# Quando congelado pelo PyInstaller, sys.executable é o próprio binário.
# Quando executado como script, usa o diretório do arquivo .py.
# Isso garante que o .env seja encontrado independente do cwd (ex.: cron).
if getattr(sys, 'frozen', False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(_BASE_DIR, '.env'))

ICS_URL = os.getenv("ICS_URL")
STATE_FILE = os.getenv("STATE_FILE", "/tmp/calendar_notifications.json")
LOG_FILE = os.getenv("LOG_FILE", "/tmp/notifica365.log")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

ALERT_MINUTES = list(map(int, os.getenv("ALERT_MINUTES", "15,5,0").split(",")))

ICS_UPDATE_INTERVAL = int(os.getenv("ICS_UPDATE_INTERVAL", "30"))
CACHE_FILE = os.getenv("CACHE_FILE", "/tmp/calendar_cache.ics")

TZ_OFFSET = int(os.getenv("TZ_OFFSET", "-3"))
LOCAL_TZ = timezone(timedelta(hours=TZ_OFFSET))

# Padrões de URL para reuniões online
_MEETING_URL_RE = re.compile(
    r'https?://\S*(?:teams\.microsoft\.com|meet\.google\.com|zoom\.us|webex\.com)\S*',
    re.IGNORECASE
)


def extract_meeting_link(event) -> str | None:
    """Extrai o primeiro link de reunião (Teams, Meet, Zoom, Webex) do evento."""
    sources = []
    if getattr(event, "url", None):
        sources.append(str(event.url))
    if getattr(event, "location", None):
        sources.append(str(event.location))
    if getattr(event, "description", None):
        sources.append(str(event.description))

    for text in sources:
        match = _MEETING_URL_RE.search(text)
        if match:
            # Remove caracteres que o Outlook às vezes adiciona ao final
            url = match.group(0).rstrip(">\"'\\")
            return url
    return None


def notify_discord(title: str, start_time: str, end_time: str | None, diff_min: int, meeting_link: str | None):
    """Envia uma notificação de reunião para o webhook do Discord."""
    if not DISCORD_WEBHOOK_URL:
        logging.error("DISCORD_WEBHOOK_URL não configurada.")
        return

    if diff_min == 0:
        time_label = "agora!"
        color = 0xFF0000  # vermelho
    elif diff_min <= 5:
        time_label = f"em {diff_min} min"
        color = 0xFF8C00  # laranja escuro
    else:
        time_label = f"em {diff_min} min"
        color = 0xFFA500  # laranja

    horario = f"{start_time} → {end_time}" if end_time else start_time
    description_parts = [f"🕐 **Horário:** {horario}"]
    if meeting_link:
        description_parts.append(f"🔗 [Entrar na reunião]({meeting_link})")

    embed = {
        "title": title,
        "description": "\n".join(description_parts),
        "color": color,
        "footer": {"text": f"Faltam {diff_min} min" if diff_min > 0 else "Começando agora!"},
    }

    payload = {
        "username": "Notifica365",
        "content": f"🔔 **Lembrete de reunião** — {time_label}",
        "embeds": [embed],
    }

    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=15)
        resp.raise_for_status()
        logging.info(f"Notificação enviada ao Discord: {title} ({time_label})")
    except Exception as e:
        logging.error(f"Erro ao enviar notificação ao Discord: {e}")


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def get_events():
    if os.path.exists(CACHE_FILE):
        mtime = datetime.fromtimestamp(os.path.getmtime(CACHE_FILE), tz=timezone.utc)
        now = datetime.now(timezone.utc)
        diff_minutes = (now - mtime).total_seconds() / 60

        if diff_minutes < ICS_UPDATE_INTERVAL:
            try:
                with open(CACHE_FILE, "r") as f:
                    return Calendar(f.read())
            except Exception as e:
                logging.warning(f"Erro ao ler o cache do ICS: {e}")

    try:
        r = requests.get(ICS_URL, timeout=60)
        r.raise_for_status()

        with open(CACHE_FILE, "w") as f:
            f.write(r.text)

        return Calendar(r.text)
    except Exception as e:
        logging.warning(f"Erro ao baixar ICS: {e}")
        if os.path.exists(CACHE_FILE):
            logging.info("Usando cache antigo do ICS como fallback.")
            try:
                with open(CACHE_FILE, "r") as f:
                    return Calendar(f.read())
            except Exception:
                pass
        return None


def main():
    logging.info("=========================================")
    logging.info("Iniciando verificação de eventos do calendário...")

    now = datetime.now(LOCAL_TZ)
    state = load_state()
    updated_state = {}

    cal = get_events()
    if not cal:
        logging.warning("Nenhum calendário pôde ser carregado ou ocorreu um erro de rede.")
        return

    eventos_hoje = 0
    notificacoes_enviadas = 0

    for event in cal.events:
        if not event.begin:
            continue

        # A biblioteca ICS lê os eventos do Office 365 e os define como UTC (+00:00) ignorando os Timezones.
        # Corrigimos forçando a hora interpretada a ser do fuso local sem alterar os números do relógio.
        start = event.begin.datetime.replace(tzinfo=LOCAL_TZ)
        local_start = start

        diff_min = round((start - now).total_seconds() / 60)

        if diff_min < 0:
            continue

        if local_start.date() != now.date():
            continue

        eventos_hoje += 1
        event_id = f"{event.uid}_{start}"
        updated_state[event_id] = state.get(event_id, [])

        for alert in sorted(ALERT_MINUTES):
            if diff_min <= alert:
                if alert not in updated_state[event_id]:
                    data_hora = local_start.strftime('%d/%m/%Y %H:%M')
                    logging.info(f"[{event.name}] Disparando alerta referente aos {alert} min (Faltam {diff_min} min na realidade)")

                    meeting_link = extract_meeting_link(event)
                    end_time = None
                    if event.end:
                        end_local = event.end.datetime.replace(tzinfo=LOCAL_TZ)
                        end_time = end_local.strftime('%H:%M')
                    notify_discord(
                        title=event.name,
                        start_time=data_hora,
                        end_time=end_time,
                        diff_min=diff_min,
                        meeting_link=meeting_link,
                    )
                    updated_state[event_id].append(alert)
                    notificacoes_enviadas += 1

                break

    logging.info(f"Verificação concluída. {eventos_hoje} eventos agendados para hoje a partir de agora. {notificacoes_enviadas} alertas disparados nesta execução.")

    cleaned_state = {}
    today = datetime.now().date()

    for k, v in updated_state.items():
        try:
            date_part = k.split("_")[-1]
            event_date = datetime.fromisoformat(date_part).date()
            if event_date == today:
                cleaned_state[k] = v
        except Exception:
            continue

    save_state(cleaned_state)


if __name__ == "__main__":
    main()
