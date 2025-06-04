# %%
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime, timedelta, timezone
import os
import logging
from typing import List, Optional
from calendar_alias import resolve_calendar_id
from validators import EventConfirmation, CalendarRequestType, EventDetails, ModifyEventDetails
import httpx
from fastapi import HTTPException
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
# def create_service(client_secret_file, api_name, api_version, *scopes, prefix=''):
#     CLIENT_SECRET_FILE = client_secret_file
#     API_SERVICE_NAME = api_name
#     API_VERSION = api_version
#     SCOPES = [scope for scope in scopes[0]]

#     creds = None
#     working_dir = os.getcwd()
#     token_dir = 'token files'
#     token_file = f'token_{API_SERVICE_NAME}_{API_VERSION}{prefix}.json'

#     ### CHECK if token dir exists first, if not, create the folder (for authorization purposes)
#     if not os.path.exists(os.path.join(working_dir, token_dir)):
#         os.mkdir(os.path.join(working_dir, token_dir))

#     if os.path.exists(os.path.join(working_dir, token_dir, token_file)):
#         creds = Credentials.from_authorized_user_file(os.path.join(working_dir, token_dir, token_file), SCOPES)

#     # If there are no (valid) credentials available, let the user log in.
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
#             creds = flow.run_local_server(port=0)

#         with open(os.path.join(working_dir, token_dir, token_file), 'w') as token:
#             token.write(creds.to_json())
    
#     try: 
#         service = build(API_SERVICE_NAME, API_VERSION, credentials=creds, static_discovery=False)
#         print(API_SERVICE_NAME, 'service created successfully')
#         logger.info(f"{API_SERVICE_NAME} service created successfully")
#         return service
    
#     except Exception as e:
#         print(f"Failed to create {API_SERVICE_NAME} service")
#         logger.error(f"An error occurred: {e}")
#         logger.error(f"Failed to create {API_SERVICE_NAME} service")
#         os.remove(os.path.join(working_dir, token_dir, token_file))
#         return None
    
# # %%
# client_secret = 'client_secret_145603579151-36vn54c6vd2cijg4moa222blpusmpdik.apps.googleusercontent.com.json'

# def construct_google_calendar_service(client_secret):
#     """
#     Construct and return a Google Calendar service object.
#     Parameters:
#     - client_secret: The path to the client secret JSON file.

#     Returns:
#     - service: A Google Calendar service object/instance.
#     """
#     API_NAME = 'calendar'
#     API_VERSION = 'v3'
#     SCOPES = ['https://www.googleapis.com/auth/calendar']
#     service = create_service(client_secret, API_NAME, API_VERSION, SCOPES)

#     return service

# # Build Calendar API service
# calendar_service = construct_google_calendar_service(client_secret)

# # Default calendar ID (can be changed later to a specific user's)

CALENDAR_ID = 'primary'  # Use the alias resolver to get the calendar ID
# %%
async def create_calendar_event(event : dict, access_token : str):
    """
    Create a new event in the user's Google Calendar.
    Parameters:
    - event: A dictionary containing the event details.

    Returns:
    - event: The created event objec.
    """

    headers = {
        'Authorization': f'Bearer {access_token}',
        "Content-Type": "application/json"
    }

    start_time = event.date.strftime('%Y-%m-%dT%H:%M:%S')
    end_time = (event.date + timedelta(minutes=event.duration_minutes)).strftime('%Y-%m-%dT%H:%M:%S')

    attendees = [{
        'email': participant.email,
        'displayName': participant.name,
    } for participant in event.participants ]
    
    event_body = {
        'summary': event.name,  # Use description if available, otherwise use name
        'description': event.description,
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

    # ✅ Use the resolved calendar ID from the model (defaults to 'primary' if not resolved)
    # calendar_id = event.calendar_id or "primary"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://www.googleapis.com/calendar/v3/calendars/{CALENDAR_ID}/events",
            headers=headers,
            json=event_body 
        )


    if response.status_code >= 400:
        logger.error(f"Google API error: {response.status_code} - {response.text}")
        raise HTTPException(status_code=response.status_code, detail="Google Calendar API call failed")

    logger.info(f"Created event: {response}")
    return response.json()

   
# %%
# def modify_calendar_event(event_id: str, updated_event):
#     """
#     Update an existing event in the user's Google Calendar.
#     Parameters:
#     - event_id: The ID of the event to update.
#     - updated_event: A dictionary containing the updated event details.

#     Returns:
#     - event: The updated event object.
#     """

#     try:
#         start_time = updated_event.date.strftime('%Y-%m-%dT%H:%M:%S')
#         end_time = (updated_event.date + timedelta(minutes=updated_event.duration_minutes)).strftime('%Y-%m-%dT%H:%M:%S')

#         attendees = [{
#             'email': participant.email,
#             'displayName': participant.name,
#         } for participant in updated_event.participants ]

#         event_body = {
#             'summary': updated_event.name,
#             'location': updated_event.location,
#             'start': {
#                 'dateTime': start_time,
#                 'timeZone': 'UTC',
#             },
#             'end' : {
#                 'dateTime': end_time,
#                 'timeZone': 'UTC',
#             },
#             'attendees': attendees,
#             'reminders': {
#                 'useDefault': False,
#                 'overrides': [
#                     {'method': 'email', 'minutes': 24 * 60},  # 1 day before
#                     {'method': 'popup', 'minutes': 10},
#                 ],
#             }
#         }

#         modify_event = calendar_service.events().update(
#             calendarId=CALENDAR_ID,
#             eventId=event_id,
#             body=event_body,
#             sendNotifications=True,
#             sendUpdates='all'
#         ).execute()

#         logger.info(f"Updated event: {modify_event}")


#         return modify_event #structured info to be sent to the frontend

#     except Exception as e:
#         logger.error(f"An error occurred: {e}")
#         return None
# # %%  
# def delete_calendar_event(event_id: str, calendar_id: str = CALENDAR_ID):
#     """
#     Delete an event from the user's Google Calendar.
#     Parameters:
#     - event_id: The ID of the event to delete.
#     - calendar_id: The ID of the calendar from which to delete the event.

#     Returns:
#     - None
#     """
#     try:
#         calendar_service.events().delete(
#             calendarId=calendar_id,
#             eventId=event_id,
#             sendNotifications=True
#         ).execute()

#         logger.info(f"Deleted event with ID: {event_id}")

#     except Exception as e:
#         logger.error(f"An error occurred while deleting the event: {e}")

# # %%
# def find_event_by_summary(summary: str, calendar_id: str = CALENDAR_ID):
#     """
#     Find an event by its summary in the user's Google Calendar.
#     Parameters:
#     - summary: The summary of the event to search for.
#     - calendar_id: The ID of the calendar to search in.

#     Returns:
#     - events: A list of events matching the summary.
#     """
#     try:
#         events_result = calendar_service.events().list(
#             calendarId=calendar_id,
#             q=summary,
#             singleEvents=True,
#             orderBy='startTime'
#         ).execute()

#         events = events_result.get('items', [])
#         logger.info(f"Found {len(events)} events with summary '{summary}'")

#         return events

#     except Exception as e:
#         logger.error(f"An error occurred while searching for events: {e}")
#         return []
# # %%

# def list_calendar_events(calendar_id: str = CALENDAR_ID, max_results: int = 10):
#     """
#     List upcoming events in the user's Google Calendar.
#     Parameters:
#     - calendar_id: The ID of the calendar to list events from.
#     - max_results: The maximum number of events to return.

#     Returns:
#     - events: A list of upcoming events.
#     """
#     try:
#         now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
#         events_result = calendar_service.events().list(
#             calendarId=calendar_id,
#             timeMin=now,
#             maxResults=max_results,
#             singleEvents=True,
#             orderBy='startTime'
#         ).execute()

#         events = events_result.get('items', [])
#         logger.info(f"Found {len(events)} upcoming events")

#         return events

#     except Exception as e:
#         logger.error(f"An error occurred while listing events: {e}")
#         return []
# # %%

# def list_calendar_calendars():
#     """
#     List all calendars in the user's Google Calendar.
#     Returns:
#     - calendars: A list of calendars.
#     """
#     try:
#         calendars_result = calendar_service.calendarList().list().execute()
#         calendars = calendars_result.get('items', [])
#         logger.info(f"Found {len(calendars)} calendars")

#         return calendars

#     except Exception as e:
#         logger.error(f"An error occurred while listing calendars: {e}")
#         return []
# # %%





# # class Participant:
# #     def __init__(self, name:str, email:str):
# #         self.name = name
# #         self.email = email
    
# # class EventDetails:
# #     def __init__(self, name:str, date:datetime, duration_minutes:int, participants:List[Participant],  location: Optional[str]):
# #         self.name = name
# #         self.date = date
# #         self.duration_minutes = duration_minutes
# #         self.participants = participants
# #         self.location = location

# # event_date = datetime.fromisoformat("2025-05-30T14:00:00")

# # participants = [
# #     Participant(name="Alice", email="uniqueifeyinwa@gmail.com"),
# #     Participant(name="Bob", email="oguguofrank246@gmail.com")
# # ]

# # event_create = EventDetails(
# #     name="Team Meeting",
# #     date=event_date,
# #     duration_minutes=60,
# #     participants=participants,
# #     location=None
# # )

# # results = create_calendar_event(event_create)

# # logger.info(results)
# # %%
