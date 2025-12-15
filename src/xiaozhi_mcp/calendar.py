"""
Google Calendar events wrapper.

Provides async operations to fetch events from Google Calendar
using the Google Calendar API v3.
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# OAuth 2.0 scopes for read-only calendar access
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Default paths for credentials
DEFAULT_CREDENTIALS_FILE = Path.home() / '.config' / 'xiaozhi' / 'credentials.json'
DEFAULT_TOKEN_FILE = Path.home() / '.config' / 'xiaozhi' / 'token.json'


@dataclass
class CalendarEvent:
    """Represents a Google Calendar event."""

    id: str
    summary: str
    start: datetime
    end: datetime
    location: str | None = None
    description: str | None = None
    all_day: bool = False
    calendar_id: str = 'primary'

    @classmethod
    def from_api_response(cls, event: dict[str, Any], calendar_id: str = 'primary') -> 'CalendarEvent':
        """Create CalendarEvent from Google Calendar API response."""
        start_data = event.get('start', {})
        end_data = event.get('end', {})

        # Handle all-day events (date) vs timed events (dateTime)
        all_day = 'date' in start_data
        if all_day:
            start = datetime.fromisoformat(start_data['date'])
            end = datetime.fromisoformat(end_data['date'])
        else:
            start = datetime.fromisoformat(start_data.get('dateTime', ''))
            end = datetime.fromisoformat(end_data.get('dateTime', ''))

        return cls(
            id=event.get('id', ''),
            summary=event.get('summary', '(No title)'),
            start=start,
            end=end,
            location=event.get('location'),
            description=event.get('description'),
            all_day=all_day,
            calendar_id=calendar_id,
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        if self.all_day:
            time_str = self.start.strftime('%Y-%m-%d')
        else:
            time_str = self.start.strftime('%Y-%m-%d %H:%M')
        return f'{time_str}: {self.summary}'


@dataclass
class Calendar:
    """Represents a Google Calendar."""

    id: str
    summary: str
    description: str | None = None
    primary: bool = False
    access_role: str = 'reader'

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> 'Calendar':
        """Create Calendar from API response."""
        return cls(
            id=data.get('id', ''),
            summary=data.get('summary', ''),
            description=data.get('description'),
            primary=data.get('primary', False),
            access_role=data.get('accessRole', 'reader'),
        )


class GoogleCalendarClient:
    """
    Async client for Google Calendar API.

    Provides methods to authenticate and fetch events from Google Calendar.
    """

    def __init__(
        self,
        credentials_file: Path | str = DEFAULT_CREDENTIALS_FILE,
        token_file: Path | str = DEFAULT_TOKEN_FILE,
    ) -> None:
        """
        Initialize the Google Calendar client.

        Args:
            credentials_file: Path to OAuth 2.0 client credentials JSON file
            token_file: Path to store/load the user's access token

        """
        self.credentials_file = Path(credentials_file)
        self.token_file = Path(token_file)
        self._credentials: Credentials | None = None
        self._service: Any = None

    async def __aenter__(self) -> 'GoogleCalendarClient':
        """Async context manager entry."""
        await self.authenticate()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        self._service = None

    def _load_or_refresh_credentials(self) -> Credentials | None:
        """Load existing credentials or refresh if expired."""
        creds = None

        if self.token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self._save_credentials(creds)

        return creds if creds and creds.valid else None

    def _run_oauth_flow(self) -> Credentials:
        """Run OAuth 2.0 flow to get new credentials."""
        if not self.credentials_file.exists():
            raise FileNotFoundError(
                f'Credentials file not found: {self.credentials_file}\n'
                'Download OAuth 2.0 client credentials from Google Cloud Console.'
            )

        flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_file), SCOPES)
        creds = flow.run_local_server(port=0)
        self._save_credentials(creds)
        return creds

    def _save_credentials(self, creds: Credentials) -> None:
        """Save credentials to token file."""
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(creds.to_json())

    async def authenticate(self) -> None:
        """
        Authenticate with Google Calendar API.

        Will use existing token if valid, refresh if expired,
        or run OAuth flow if no valid credentials exist.
        """
        loop = asyncio.get_event_loop()

        # Try to load existing credentials
        creds = await loop.run_in_executor(None, self._load_or_refresh_credentials)

        # If no valid credentials, run OAuth flow
        if not creds:
            creds = await loop.run_in_executor(None, self._run_oauth_flow)

        self._credentials = creds
        self._service = await loop.run_in_executor(None, partial(build, 'calendar', 'v3', credentials=creds))

    @property
    def service(self) -> Any:
        """Get the Calendar API service, raising if not authenticated."""
        if self._service is None:
            raise RuntimeError('Not authenticated. Call authenticate() first.')
        return self._service

    async def get_calendars(self) -> list[Calendar]:
        """Get all calendars the user has access to."""
        loop = asyncio.get_event_loop()

        def _fetch() -> list[dict[str, Any]]:
            result = self.service.calendarList().list().execute()
            return result.get('items', [])

        items = await loop.run_in_executor(None, _fetch)
        return [Calendar.from_api_response(item) for item in items]

    async def get_events(
        self,
        calendar_id: str = 'primary',
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        max_results: int = 100,
        single_events: bool = True,
        order_by: str = 'startTime',
    ) -> list[CalendarEvent]:
        """
        Get events from a calendar.

        Args:
            calendar_id: Calendar ID (default: "primary" for user's primary calendar)
            time_min: Start of time range (default: now)
            time_max: End of time range (default: 7 days from now)
            max_results: Maximum number of events to return
            single_events: If True, expand recurring events into instances
            order_by: Order results by "startTime" or "updated"

        Returns:
            List of CalendarEvent objects

        """
        if time_min is None:
            time_min = datetime.now(UTC)
        if time_max is None:
            time_max = time_min + timedelta(days=7)

        loop = asyncio.get_event_loop()

        def _fetch() -> list[dict[str, Any]]:
            result = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min.isoformat(),
                    timeMax=time_max.isoformat(),
                    maxResults=max_results,
                    singleEvents=single_events,
                    orderBy=order_by,
                )
                .execute()
            )
            return result.get('items', [])

        items = await loop.run_in_executor(None, _fetch)
        return [CalendarEvent.from_api_response(item, calendar_id) for item in items]

    async def get_today_events(self, calendar_id: str = 'primary') -> list[CalendarEvent]:
        """Get all events for today."""
        now = datetime.now(UTC)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        return await self.get_events(
            calendar_id=calendar_id,
            time_min=start_of_day,
            time_max=end_of_day,
        )

    async def get_upcoming_events(
        self,
        calendar_id: str = 'primary',
        days: int = 7,
        max_results: int = 50,
    ) -> list[CalendarEvent]:
        """
        Get upcoming events for the next N days.

        Args:
            calendar_id: Calendar ID
            days: Number of days to look ahead
            max_results: Maximum number of events

        Returns:
            List of upcoming CalendarEvent objects

        """
        now = datetime.now(UTC)
        return await self.get_events(
            calendar_id=calendar_id,
            time_min=now,
            time_max=now + timedelta(days=days),
            max_results=max_results,
        )

    async def get_events_from_all_calendars(
        self,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        max_results_per_calendar: int = 50,
    ) -> list[CalendarEvent]:
        """
        Get events from all accessible calendars.

        Args:
            time_min: Start of time range
            time_max: End of time range
            max_results_per_calendar: Max events per calendar

        Returns:
            List of all events, sorted by start time

        """
        calendars = await self.get_calendars()
        all_events: list[CalendarEvent] = []

        for cal in calendars:
            events = await self.get_events(
                calendar_id=cal.id,
                time_min=time_min,
                time_max=time_max,
                max_results=max_results_per_calendar,
            )
            all_events.extend(events)

        # Sort by start time
        all_events.sort(key=lambda e: e.start)
        return all_events


# ==================== Convenience Functions ====================


async def quick_get_events(
    days: int = 7,
    credentials_file: Path | str = DEFAULT_CREDENTIALS_FILE,
    token_file: Path | str = DEFAULT_TOKEN_FILE,
) -> list[CalendarEvent]:
    """
    Quickly get upcoming events from primary calendar.

    Args:
        days: Number of days to look ahead
        credentials_file: Path to OAuth credentials
        token_file: Path to token file

    Returns:
        List of upcoming events

    """
    async with GoogleCalendarClient(credentials_file, token_file) as client:
        return await client.get_upcoming_events(days=days)


async def quick_get_today() -> list[CalendarEvent]:
    """Get today's events from primary calendar."""
    async with GoogleCalendarClient() as client:
        return await client.get_today_events()


# ==================== Example Usage ====================

if __name__ == '__main__':

    async def main() -> None:
        print('Google Calendar Events Demo')
        print('=' * 40)

        try:
            async with GoogleCalendarClient() as client:
                # List calendars
                calendars = await client.get_calendars()
                print(f'\nFound {len(calendars)} calendars:')
                for cal in calendars:
                    primary = ' (primary)' if cal.primary else ''
                    print(f'  - {cal.summary}{primary}')

                # Get upcoming events
                print('\nUpcoming events (next 7 days):')
                events = await client.get_upcoming_events()
                if events:
                    for event in events:
                        print(f'  - {event}')
                else:
                    print('  No upcoming events')

                # Get today's events
                print("\nToday's events:")
                today_events = await client.get_today_events()
                if today_events:
                    for event in today_events:
                        print(f'  - {event}')
                else:
                    print('  No events today')

        except FileNotFoundError as e:
            print(f'\nSetup required: {e}')
            print('\nTo set up Google Calendar API access:')
            print('1. Go to https://console.cloud.google.com/')
            print('2. Create a project and enable Google Calendar API')
            print('3. Create OAuth 2.0 credentials (Desktop app)')
            print(f'4. Download and save as: {DEFAULT_CREDENTIALS_FILE}')

    asyncio.run(main())
