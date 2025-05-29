# %%
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime, timedelta, timezone
import os
import logging
from typing import List, Optional

import json


# %%
# Set up logging configuration so it can display logs in the terminal or interactive mode
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
# %%
def create_service(client_secret_file, api_name, api_version, *scopes, prefix=''):
    CLIENT_SECRET_FILE = client_secret_file
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = [scope for scope in scopes[0]]

    creds = None
    working_dir = os.getcwd()
    token_dir = 'token files'
    token_file = f'token_{API_SERVICE_NAME}_{API_VERSION}{prefix}.json'

    ### CHECK if token dir exists first, if not, create the folder (for authorization purposes)
    if not os.path.exists(os.path.join(working_dir, token_dir)):
        os.mkdir(os.path.join(working_dir, token_dir))

    if os.path.exists(os.path.join(working_dir, token_dir, token_file)):
        creds = Credentials.from_authorized_user_file(os.path.join(working_dir, token_dir, token_file), SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(os.path.join(working_dir, token_dir, token_file), 'w') as token:
            token.write(creds.to_json())
    
    try: 
        service = build(API_SERVICE_NAME, API_VERSION, credentials=creds, static_discovery=False)
        print(API_SERVICE_NAME, 'service created successfully')
        logger.info(f"{API_SERVICE_NAME} service created successfully")
        return service
    
    except Exception as e:
        print(f"Failed to create {API_SERVICE_NAME} service")
        logger.error(f"An error occurred: {e}")
        logger.error(f"Failed to create {API_SERVICE_NAME} service")
        os.remove(os.path.join(working_dir, token_dir, token_file))
        return None
    
# %%
client_secret = ''

def construct_google_calendar_service(client_secret):
    """
    Construct and return a Google Calendar service object.
    Parameters:
    - client_secret: The path to the client secret JSON file.

    Returns:
    - service: A Google Calendar service object/instance.
    """
    API_NAME = 'calendar'
    API_VERSION = 'v3'
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    service = create_service(client_secret, API_NAME, API_VERSION, SCOPES)

    return service

# Build Calendar API service
calendar_service = construct_google_calendar_service(client_secret)

# Default calendar ID (can be changed later to a specific user's)
CALENDAR_ID = "primary"
# %%
def create_calendar_event(event):
    """
    Create a new event in the user's Google Calendar.
    Parameters:
    - event: A dictionary containing the event details.

    Returns:
    - event: The created event objec.
    """
    start_time = event.date.strftime('%Y-%m-%dT%H:%M:%S')
    end_time = (event.date + timedelta(minutes=event.duration_minutes)).strftime('%Y-%m-%dT%H:%M:%S')

    attendees = [{
        'email': participant.email,
        'displayName': participant.name,
    } for participant in event.participants ]
    
    event_body = {
        'summary': event.name,
        'location': event.location,
        'start': {
            'dateTime': start_time,
            'timeZone': 'UTC',
        },
        'end' : {
            'dateTime': end_time,
            'timeZone': 'UTC',
        },
        'attendees': attendees,
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                {'method': 'popup', 'minutes': 10},
            ],
        }
    }

    created_event = calendar_service.events().insert(
        calendarId="primary",  # ✅ FIXED typo here
        body=event_body,
        sendNotifications=True,
        sendUpdates='all'
    ).execute()

    logger.info(f"Created event: {created_event}")

    return created_event #structured info to be sent to the frontend
# %%
def update_calendar_event(event_id: str, updated_event):
    """
    Update an existing event in the user's Google Calendar.
    Parameters:
    - event_id: The ID of the event to update.
    - updated_event: A dictionary containing the updated event details.

    Returns:
    - event: The updated event object.
    """

    try:
        start_time = updated_event.date.strftime('%Y-%m-%dT%H:%M:%S')
        end_time = (updated_event.date + timedelta(minutes=updated_event.duration_minutes)).strftime('%Y-%m-%dT%H:%M:%S')

        attendees = [{
            'email': participant.email,
            'displayName': participant.name,
        } for participant in updated_event.participants ]

        event_body = {
            'summary': updated_event.name,
            'location': updated_event.location,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end' : {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
            'attendees': attendees,
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                    {'method': 'popup', 'minutes': 10},
                ],
            }
        }

        updated_event = calendar_service.events().update(
            calendarId=CALENDAR_ID,
            eventId=event_id,
            body=event_body,
            sendNotifications=True,
            sendUpdates='all'
        ).execute()

        logger.info(f"Updated event: {updated_event}")


        return updated_event #structured info to be sent to the frontend

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None
# %%   
class Participant:
    def __init__(self, name:str, email:str):
        self.name = name
        self.email = email
    
class EventDetails:
    def __init__(self, name:str, date:datetime, duration_minutes:int, participants:List[Participant],  location: Optional[str]):
        self.name = name
        self.date = date
        self.duration_minutes = duration_minutes
        self.participants = participants
        self.location = location

event_date = datetime.fromisoformat("2025-05-30T14:00:00")

participants = [
    Participant(name="Alice", email="uniqueifeyinwa@gmail.com"),
    Participant(name="Bob", email="oguguofrank246@gmail.com")
]

event_create = EventDetails(
    name="Team Meeting",
    date=event_date,
    duration_minutes=60,
    participants=participants,
    location=None
)

results = create_calendar_event(event_create)

logger.info(results)
# %%
