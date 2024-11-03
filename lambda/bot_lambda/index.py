import os
import json
import requests
import re
import boto3
import pytz
from datetime import datetime, timedelta

if os.path.exists('whitelist.json'):
    whitelist = json.load(open('whitelist.json'))['whitelist']
else:
    whitelist = json.loads(os.environ['WHITELIST'])['whitelist']
    

ssm = boto3.client("ssm")
events = boto3.client("events")

telegram_token_parameter = ssm.get_parameter(Name="fitness_bot_telegram_token")
TELEGRAM_TOKEN = telegram_token_parameter["Parameter"]["Value"]

class_mapper = json.load(open("class_mapper.json"))
mapping_class_day = {
    "dilluns": "SUN",
    "dimarts": "MON",
    "dimecres": "TUE",
    "dijous": "WED",
    "divendres": "THU",
    "dissabte": "FRI",
    "diumenge": "SAT",
}


def start_command(chat_id):
    message = "Hola, apunt pel gimnàs? Necessitaré un usuari. Per configurar-ho escriu el teu usuari (és el mail) en el següent format: /user el_teu_usuari."
    send_message(chat_id, message)


def info_command(chat_id):
    message = (
        "Tens les següents comandes disponibles:\n"
        "- /start: La comanda d'inicialització del bot. No cal tornar-la a fer servir. \n "
        "- /user [usuari] : Passant juntament amb la comanda el nom de l'usuari es guardarà "
        "el teu usuari del Fitness Factory. És necessari posar també la contrassenya. \n "
        "- /password [contrasenya]: Passar juntament amb la comanda la contrasenya pel Fitness"
        "Factory per acabar de configurar l'usuari. Només és necessari la primera vegada tret que es canvïi la contrasenya. \n "
        "- /reserva [classe dia HH:MM]: Passar amb el format corresponent la classe dia i hora que es vol reservar. \n "
        "- /horari: Per veure les classes guardades actualment. \n "
        "- /elimina [classe dia HH:MM]: En cas que hi hagi una classe programada pel dia especificat, s'esborrarà de la setmana."
    )
    send_message(chat_id, message)


def elimina_command(chat_id, username, text):
    text = text.lower().rstrip().lstrip()
    pattern = r"^\/elimina (.+?) (dilluns|dimarts|dimecres|dijous|divendres|dissabte|diumenge) (([01]\d|2[0-3]):[0-5]\d$)"
    format_ok = re.match(pattern, text) is not None
    if format_ok:
        # we book the class
        m = re.search(pattern, text)
        class_name = m.group(1)
        class_name = "".join(ch for ch in class_name if ch.isalnum())
        class_day = m.group(2)
        class_hour = m.group(3)
        scheduler_name = f"{username}_{class_name.replace(' ','')}_{class_day}_{class_hour.replace(':','')}"
        list_events = events.list_rules(NamePrefix=username)
        list_events = [x["Name"] for x in list_events["Rules"]]
        if scheduler_name in list_events:
            events.remove_targets(Rule=scheduler_name, Ids=["RANDOM_ID"])
            events.delete_rule(Name=scheduler_name)
            message = f"Perfecte! S'ha eliminat la classe: {class_name} - {class_day} - {class_hour}"
    else:
        message = (
            "Aquest format de classe no sembla correcte. Pots tornar-lo a escriure?"
        )
    send_message(chat_id, message)


def reserva_command(chat_id, username, text):
    # text should be in the format /reserva class_name day_of_week HH:MM
    # let's check if it's ok
    text = text.lower().rstrip().lstrip()
    pattern = r"^\/reserva (.+?) (dilluns|dimarts|dimecres|dijous|divendres|dissabte|diumenge) (([01]\d|2[0-3]):[0-5]\d$)"
    format_ok = re.match(pattern, text) is not None
    if format_ok:
        # we book the class
        m = re.search(pattern, text)
        class_name = m.group(1)
        class_name = "".join(ch for ch in class_name if ch.isalnum())
        if class_name not in class_mapper:
            message = (
                "Sembla que no tinc aquesta classe entre les opcions, està ben escrita?"
            )
        else:
            class_day = m.group(2)
            class_hour = m.group(3)
            scheduler(username, class_name, class_day, class_hour)
            message = f"Perfecte! S'ha reservat la classe: {class_name} - {class_day} - {class_hour}"
    else:
        message = (
            "Aquest format de classe no sembla correcte. Pots tornar-lo a escriure?"
        )
    send_message(chat_id, message)


def scheduler(username, class_name, class_day, class_hour):
    minutes = class_hour.split(":")[1]
    hours = class_hour.split(":")[0]
    scheduler_name = f"{username}_{class_name.replace(' ','')}_{class_day}_{class_hour.replace(':','')}"
    print(scheduler_name, hours, class_hour)
    now = datetime.now()
    if now.hour > 20:
        now = now - timedelta(hours=8)
    if now.hour < 4:
        now = now + timedelta(hours=8)
    hours_diff = (
        now.astimezone(pytz.timezone("Europe/Madrid")).hour
        - now.astimezone(pytz.timezone("utc")).hour
    )
    print(int(hours) - hours_diff)
    cron_expression = (
        f"{minutes} {int(hours)-hours_diff} ? * {mapping_class_day[class_day]} *"
    )
    print(cron_expression)
    # Create cloudwatch event rule
    events.put_rule(
        Name=scheduler_name,
        ScheduleExpression=f"cron({cron_expression})",
        State="ENABLED",
    )
    # add Lambda target to cloudwatch event rule
    events.put_targets(
        Rule=scheduler_name,
        Targets=[{"Arn": os.getenv("BOOKING_LAMBDA_ARN"), "Id": "RANDOM_ID"}],
    )


def horari_command(chat_id, username):
    """
    Retrieve the info of the bookings
    """
    # lets get the cloudwatch events.
    list_events = events.list_rules(NamePrefix=username)
    list_events = [x["Name"] for x in list_events["Rules"]]
    message = (
        "  ".join(list_events) if list_events != [] else "No tens cap classe reservada."
    )
    send_message(chat_id, message)


def user_command(chat_id, username, user_text):
    ssm.put_parameter(
        Name=f"{username}_user", Value=user_text, Type="String", Overwrite=True
    )
    message = "Perfecte! Ara per guardar la contrasenya, escriu /password la_teva_contrasenya."
    send_message(chat_id, message)


def password_command(chat_id, username, password_text):
    ssm.put_parameter(
        Name=f"{username}_password", Value=password_text, Type="String", Overwrite=True
    )
    message = "Fet! Pots veure les opcions del bot escrivint /info."
    send_message(chat_id, message)

def save_chat_id(chat_id, username):
    ssm.put_parameter(
        Name=f"{username}_chat_id", Value=str(chat_id), Type="String", Overwrite=True
    )

def send_message(chat_id, message):
    token = TELEGRAM_TOKEN
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}
    requests.post(url, data=data)


def handler(event, _):
    try:
        print(event)
        body = json.loads(event["body"])
        print(body)
        if "message" in body.keys():
            body_message = body['message']
        else:
            body_message = body['edited_message']
        chat_id = body_message["chat"]["id"]
        username = body_message["chat"]["username"]
        message_text = body_message["text"]
        command_text = re.search(r"/\w+", message_text).group(0)
        if username in whitelist:
            match command_text:
                case "/start":
                    start_command(chat_id)
                case "/info":
                    info_command(chat_id)
                case "/reserva":
                    reserva_command(chat_id, username, message_text)
                case "/elimina":
                    elimina_command(chat_id, username, message_text)
                case "/horari":
                    horari_command(chat_id, username)
                case "/user":
                    user_text = message_text.replace(command_text, "").replace(" ", "")
                    user_command(chat_id, username, user_text)
                case "/password":
                    password_text = message_text.replace(command_text, "").replace(
                        " ", ""
                    )
                    password_command(chat_id, username, password_text)
                case _:
                    send_message(chat_id, "No entenc aquesta comanda.")
            save_chat_id(chat_id,username)        
        else:
            send_message(chat_id, "Unauthorised User.")
        return {"statusCode": 200, "body": json.dumps("Message processed!")}
    except Exception as e:
        print(e)
        print("Something went wrong")
        send_message(chat_id, "Sembla que hi ha hagut algun problema.")
        return {"statusCode": 200, "body": json.dumps("Message processed!")}
