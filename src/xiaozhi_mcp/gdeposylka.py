"""
Обертка для API ГдеПосылка v4.

API документация: https://gdeposylka.ru/tracking-api/api-v4
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import httpx


class DetectResult(str, Enum):
    """Результат определения службы доставки."""

    SUCCESS = "success"
    UNSURE = "unsure"
    UNKNOWN = "unknown"


class TrackResult(str, Enum):
    """Результат отслеживания посылки."""

    SUCCESS = "success"
    WAITING = "waiting"


@dataclass
class Courier:
    """Служба доставки."""

    slug: str
    name: str
    country_code: str
    name_alt: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Courier":
        return cls(
            slug=data["slug"],
            name=data["name"],
            country_code=data["country_code"],
            name_alt=data.get("name_alt"),
        )


@dataclass
class DetectedCourier:
    """Результат определения службы по трек-номеру."""

    tracking_number: str
    courier: Courier
    tracker_url: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DetectedCourier":
        return cls(
            tracking_number=data["tracking_number"],
            courier=Courier.from_dict(data["courier"]),
            tracker_url=data.get("tracker_url", ""),
        )


@dataclass
class Checkpoint:
    """Контрольная точка отслеживания."""

    time: datetime
    courier: Courier
    status_code: str
    status_name: str | None
    status_raw: str
    location_translated: str | None
    location_raw: str | None
    location_zip_code: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Checkpoint":
        time_str = data["time"]
        time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return cls(
            time=time,
            courier=Courier.from_dict(data["courier"]),
            status_code=data.get("status_code", "other"),
            status_name=data.get("status_name"),
            status_raw=data.get("status_raw", ""),
            location_translated=data.get("location_translated"),
            location_raw=data.get("location_raw"),
            location_zip_code=data.get("location_zip_code"),
        )


@dataclass
class ExtraInfo:
    """Дополнительная информация о посылке."""

    courier_slug: str
    data: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExtraInfo":
        return cls(
            courier_slug=data["courier_slug"],
            data=data.get("data", {}),
        )


@dataclass
class Track:
    """Результат отслеживания посылки."""

    id: int
    tracking_number: str
    courier: Courier
    is_active: bool
    is_delivered: bool
    last_check: datetime | None
    checkpoints: list[Checkpoint]
    extra: list[ExtraInfo]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Track":
        last_check = None
        if data.get("last_check"):
            last_check = datetime.strptime(data["last_check"], "%Y-%m-%d %H:%M:%S")

        return cls(
            id=data["id"],
            tracking_number=data["tracking_number"],
            courier=Courier.from_dict(data["courier"]),
            is_active=data["is_active"],
            is_delivered=data["is_delivered"],
            last_check=last_check,
            checkpoints=[Checkpoint.from_dict(cp) for cp in data.get("checkpoints", [])],
            extra=[ExtraInfo.from_dict(e) for e in data.get("extra", [])],
        )


@dataclass
class CouriersResponse:
    """Ответ на запрос списка служб доставки."""

    result: str
    length: int
    couriers: list[Courier]


@dataclass
class DetectResponse:
    """Ответ на запрос определения службы по трек-номеру."""

    result: DetectResult
    length: int
    tracking_number: str
    data: list[DetectedCourier]


@dataclass
class TrackResponse:
    """Ответ на запрос отслеживания посылки."""

    result: TrackResult
    track: Track
    messages: list[str] = field(default_factory=list)


class GdeposylkaError(Exception):
    """Базовое исключение для ошибок API."""

    def __init__(self, error: str, messages: list[str] | None = None):
        self.error = error
        self.messages = messages or []
        super().__init__(error)


class GdeposylkaClient:
    """
    Клиент для API ГдеПосылка v4.

    Пример использования:
        ```python
        async with GdeposylkaClient(api_key="YOUR_API_KEY") as client:
            # Получить список служб доставки
            couriers = await client.get_couriers()

            # Определить службу по трек-номеру
            detected = await client.detect_courier("LM951174329CN")

            # Отследить посылку
            track = await client.track("china-post", "LM951174329CN")
        ```
    """

    BASE_URL = "https://gdeposylka.ru/api/v4"

    def __init__(self, api_key: str, timeout: float = 30.0):
        """
        Инициализация клиента.

        Args:
            api_key: API ключ (получить на https://gdeposylka.ru/auth/profile)
            timeout: Таймаут запросов в секундах
        """
        self.api_key = api_key
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "GdeposylkaClient":
        self._client = httpx.AsyncClient(
            headers={
                "X-Authorization-Token": self.api_key,
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        return self._client

    async def _request(self, method: str, endpoint: str) -> dict[str, Any]:
        """Выполнить HTTP запрос к API."""
        url = f"{self.BASE_URL}{endpoint}"
        response = await self.client.request(method, url)
        response.raise_for_status()
        data = response.json()

        if data.get("result") == "error":
            raise GdeposylkaError(
                error=data.get("error", "Unknown error"),
                messages=data.get("messages", []),
            )

        return data

    async def get_couriers(self) -> CouriersResponse:
        """
        Получить список доступных служб доставки.

        Returns:
            CouriersResponse с списком служб доставки
        """
        data = await self._request("GET", "/couriers")
        return CouriersResponse(
            result=data["result"],
            length=data["length"],
            couriers=[Courier.from_dict(c) for c in data["data"]],
        )

    async def detect_courier(self, tracking_number: str) -> DetectResponse:
        """
        Определить службу доставки по трек-номеру.

        Args:
            tracking_number: Трек-номер посылки

        Returns:
            DetectResponse с результатом определения.
            result может быть:
            - "success" - служба успешно определена
            - "unsure" - служба определена неточно (несколько вариантов)
            - "unknown" - служба не определена
        """
        data = await self._request("GET", f"/tracker/detect/{tracking_number}")
        return DetectResponse(
            result=DetectResult(data["result"]),
            length=data["length"],
            tracking_number=data["tracking_number"],
            data=[DetectedCourier.from_dict(d) for d in data["data"]],
        )

    async def track(self, courier_slug: str, tracking_number: str) -> TrackResponse:
        """
        Отследить посылку по службе и трек-номеру.

        Args:
            courier_slug: Идентификатор службы доставки (например, "russian-post", "china-post")
            tracking_number: Трек-номер посылки

        Returns:
            TrackResponse с информацией о посылке.
            result может быть:
            - "success" - информация получена
            - "waiting" - трек добавлен, информация собирается
        """
        data = await self._request("GET", f"/tracker/{courier_slug}/{tracking_number}")
        return TrackResponse(
            result=TrackResult(data["result"]),
            track=Track.from_dict(data["data"]),
            messages=data.get("messages", []),
        )

    async def auto_track(self, tracking_number: str) -> TrackResponse:
        """
        Автоматически определить службу и отследить посылку.

        Сначала определяет службу доставки, затем отслеживает посылку.

        Args:
            tracking_number: Трек-номер посылки

        Returns:
            TrackResponse с информацией о посылке

        Raises:
            GdeposylkaError: Если служба не определена
        """
        detect_response = await self.detect_courier(tracking_number)

        if detect_response.result == DetectResult.UNKNOWN or not detect_response.data:
            raise GdeposylkaError(
                error=f"Could not detect courier for tracking number: {tracking_number}"
            )

        # Используем первую определенную службу
        detected = detect_response.data[0]
        return await self.track(detected.courier.slug, tracking_number)
