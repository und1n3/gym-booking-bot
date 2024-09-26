import json
import boto3
import re

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

class_mapper = json.load(open("class_mapper.json"))
ssm = boto3.client("ssm")
telegram_token_parameter = ssm.get_parameter(Name="fitness_bot_telegram_token")
TELEGRAM_TOKEN = telegram_token_parameter["Parameter"]["Value"]

def login(username, password):
    # Define the login URL and the action URL (form action)
    login_url = "https://gimnasiomataro.provis.es/Login"

    # Start a session to persist cookies
    session = requests.Session()

    # First, GET the login page to get the CSRF token (hidden field)
    response = session.get(login_url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract the CSRF token from the hidden input field
    csrf_token = soup.find("input", {"name": "__RequestVerificationToken"})["value"]

    # Create the payload with the necessary form data
    payload = {
        "__RequestVerificationToken": csrf_token,
        "Username": username,
        "Password": password,
        "RememberMe": "true",
    }

    # Send the POST request to login
    login_response = session.post(login_url, data=payload)
    return session


def find_class_id_by_name_and_time(session, schedule_url, nombre, hora_inicio):
    response = session.get(schedule_url)
    soup = BeautifulSoup(response.text, "html.parser")
    timeline_div = soup.find("div", class_="timeline")
    # Convert the input HoraInicio to a datetime object
    target_time = datetime.strptime(hora_inicio, "%Y-%m-%dT%H:%M:%S")

    # Search through the schedule, assuming each class is inside an <li> tag
    for li in timeline_div.find_all("li"):
        # Extract class name (Nombre) and start time (HoraInicio) from the HTML
        class_name = li.find("h2").text
        time_tag = li.find("time", {"class": "tm-datetime"})
        if time_tag:
            class_time_str = time_tag["datetime"]
            class_time = datetime.strptime(class_time_str, "%d/%m/%Y %H:%M:%S")
            # Step 3: Compare the class name and start time
            if class_name == class_mapper[nombre] and class_time == target_time:
                # If there's a match, extract and return the idClasecolectiva from the button or other attribute
                button = li.find("button")
                if button:
                    id_clasecolectiva = button["id"]
                    print(id_clasecolectiva)
                    return id_clasecolectiva

    return None  # Return None if no matching class is found


def book_class(session, class_name, class_time):
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    tomorrow_formatted = tomorrow.strftime("%Y-%m-%d")
    class_time = tomorrow_formatted + "T" + class_time + ":00"

    base_url = f"https://gimnasiomataro.provis.es/ActividadesColectivas/ClasesColectivasTimeLine?fecha={tomorrow_formatted}T00:00:00"
    class_id = find_class_id_by_name_and_time(session, base_url, class_name, class_time)
    booking_data_json = {
        "idClasecolectiva": class_id,
        "idPlaza": None,
        "idBonoPersona": None,
    }

    # Send the POST request to book the class
    headers = {"Content-Type": "application/json"}

    booking_response = session.post(
        "https://gimnasiomataro.provis.es/ActividadesColectivas/ReservarClaseColectiva",
        # data=booking_data_json,
        json=booking_data_json,
        headers=headers,
    )
    print(booking_response)
    print(booking_response.text)

def send_message(chat_id, message):
    token = TELEGRAM_TOKEN
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}
    requests.post(url, data=data)

def notify_booking(chat_id, class_name, class_time):
    message = f"Reserva feta de {class_name} a les {class_time}"
    send_message(chat_id, message)

def handler(event, _):
    # Extract parameters from the event
    event_name = event["resources"][0].split("/")[-1]
    pattern = r"(?P<telegram_user>.+)_(?P<class_name>[^_]+)_(?P<class_day>[^_]+)_(?P<class_time>\d+)"
    match = re.match(pattern, event_name)
    telegram_user = match.group("telegram_user")
    class_name = match.group("class_name")
    class_day = match.group("class_day")
    class_time = match.group("class_time")

    class_time = f"{class_time[:2]}:{class_time[2:]}"

    # Your logic to book the gym class
    print(f"Booking {class_name} class at {class_time} on {class_day}")

    # Implement your booking logic here
    username = ssm.get_parameter(Name=f"{telegram_user}_user")["Parameter"]["Value"]
    password = ssm.get_parameter(Name=f"{telegram_user}_password")["Parameter"]["Value"]
    chat_id = ssm.get_parameter(Name=f"{telegram_user}_chat_id")["Parameter"]["Value"]

    session = login(username, password)
    session = book_class(session, class_name, class_time)

    notify_booking(chat_id, class_name, class_time)

    return {
        "statusCode": 200,
        "body": json.dumps(
            f"{class_name} class booked successfully for {class_day} at {class_time}!"
        ),
    }
