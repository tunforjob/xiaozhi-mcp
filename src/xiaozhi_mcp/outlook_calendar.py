"""
Microsoft Outlook / Teams Calendar wrapper using the O365 library.

Provides async operations to fetch events and calendars from Microsoft 365
using Microsoft Graph API via the O365 Python library.

First-run authentication opens a browser for OAuth 2.0 consent.
Subsequent runs reuse the persisted token stored at ~/.config/xiaozhi/o365_token.txt.
"""

import asyncio
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

DEFAULT_TOKEN_PATH = Path.home() / '.config' / 'xiaozhi'
DEFAULT_TOKEN_FILENAME = 'o365_token.txt'

O365_CLIENT_ID: str | None = os.getenv('O365_CLIENT_ID')
O365_CLIENT_SECRET: str | None = os.getenv('O365_CLIENT_SECRET')
O365_TENANT_ID: str = os.getenv('O365_TENANT_ID', 'common')

SCOPES = ['Calendars.Read']


@dataclass
class OutlookEvent:
    """Represents a Microsoft Outlook / Teams calendar event."""

    id: str
    subject: str
    start: datetime
    end: datetime
    location: str | None = None
    is_online_meeting: bool = False
    teams_link: str | None = None
    organizer: str | None = None
    description: str | None = None
    all_day: bool = False

    def __str__(self) -> str:
        """Human-readable string representation."""
        time_str = self.start.strftime('%Y-%m-%d') if self.all_day else self.start.strftime('%Y-%m-%d %H:%M')
        return f'{time_str}: {self.subject}'


@dataclass
class OutlookCalendar:
    """Represents a Microsoft Outlook calendar."""

    id: str
    name: str
    is_default: bool = False


class OutlookCalendarClient:
    """
    Async client for Microsoft Outlook Calendar via the O365 library.

    On first use, triggers an interactive OAuth 2.0 browser flow to authenticate.
    The token is persisted to disk and refreshed automatically on subsequent calls.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        token_path: Path | str = DEFAULT_TOKEN_PATH,
        token_filename: str = DEFAULT_TOKEN_FILENAME,
        tenant_id: str | None = None,
    ) -> None:
        self.client_id = client_id or O365_CLIENT_ID
        self.client_secret = client_secret or O365_CLIENT_SECRET
        self.tenant_id = tenant_id or O365_TENANT_ID
        self.token_path = Path(token_path)
        self.token_filename = token_filename
        self._account: Any | None = None

        if not self.client_id or not self.client_secret:
            raise ValueError(
                'O365_CLIENT_ID and O365_CLIENT_SECRET must be set as environment variables '
                'or passed explicitly to OutlookCalendarClient.'
            )

    async def __aenter__(self) -> 'OutlookCalendarClient':
        """Async context manager entry."""
        await self.authenticate()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        self._account = None

    def _build_and_auth_sync(self) -> Any:
        """Build the Account object and authenticate (synchronous, runs in executor)."""
        from O365 import Account, FileSystemTokenBackend

        self.token_path.mkdir(parents=True, exist_ok=True)
        token_backend = FileSystemTokenBackend(
            token_path=str(self.token_path),
            token_filename=self.token_filename,
        )
        account = Account(
            (self.client_id, self.client_secret),
            auth_flow_type='authorization',
            tenant_id=self.tenant_id,
            token_backend=token_backend,
        )
        if not account.is_authenticated:
            account.authenticate(scopes=SCOPES)
        return account

    async def authenticate(self) -> None:
        """Authenticate with Microsoft 365. Triggers browser OAuth on first run."""
        loop = asyncio.get_event_loop()
        self._account = await loop.run_in_executor(None, self._build_and_auth_sync)

    @property
    def account(self) -> Any:
        """Return the authenticated Account, raising if not authenticated."""
        if self._account is None:
            raise RuntimeError('Not authenticated. Call authenticate() or use as async context manager.')
        return self._account

    async def get_calendars(self) -> list[OutlookCalendar]:
        """Return all calendars accessible to the authenticated user."""
        loop = asyncio.get_event_loop()

        def _fetch() -> list[OutlookCalendar]:
            schedule = self.account.schedule()
            result: list[OutlookCalendar] = []
            for cal in schedule.list_calendars():
                result.append(
                    OutlookCalendar(
                        id=cal.calendar_id,
                        name=cal.name,
                        is_default=cal.is_default_calendar,
                    )
                )
            return result

        return await loop.run_in_executor(None, _fetch)

    async def get_events(
        self,
        calendar_id: str | None = None,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        limit: int = 50,
    ) -> list[OutlookEvent]:
        """
        Get events from a calendar within a given time range.

        Args:
            calendar_id: Calendar ID. If None, uses the default calendar.
            time_min: Start of time range (default: now).
            time_max: End of time range (default: 7 days from now).
            limit: Maximum number of events to return.

        Returns:
            List of OutlookEvent objects sorted by start time.

        """
        if time_min is None:
            time_min = datetime.now(UTC)
        if time_max is None:
            time_max = time_min + timedelta(days=7)

        loop = asyncio.get_event_loop()

        def _fetch() -> list[OutlookEvent]:
            schedule = self.account.schedule()
            calendar = (
                schedule.get_calendar(calendar_id=calendar_id)
                if calendar_id
                else schedule.get_default_calendar()
            )

            q = calendar.new_query('start').greater_equal(time_min)
            q.chain('and').on_attribute('end').less_equal(time_max)

            result: list[OutlookEvent] = []
            for event in calendar.get_events(limit=limit, query=q, include_recurring=True):
                loc: str | None = None
                if event.location:
                    loc = (
                        event.location.get('displayName') or None
                        if isinstance(event.location, dict)
                        else str(event.location) or None
                    )

                organizer: str | None = None
                if event.organizer:
                    organizer = (
                        event.organizer.address
                        if hasattr(event.organizer, 'address')
                        else str(event.organizer)
                    )

                teams_link: str | None = None
                try:
                    teams_link = event.online_meeting_url
                except AttributeError:
                    pass

                result.append(
                    OutlookEvent(
                        id=event.object_id or '',
                        subject=event.subject or '(No title)',
                        start=event.start,
                        end=event.end,
                        location=loc,
                        is_online_meeting=bool(getattr(event, 'is_online_meeting', False)),
                        teams_link=teams_link,
                        organizer=organizer,
                        description=getattr(event, 'body_preview', None),
                        all_day=bool(getattr(event, 'is_all_day', False)),
                    )
                )
            return result

        return await loop.run_in_executor(None, _fetch)
