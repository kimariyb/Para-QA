from abc import ABCMeta, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any

import requests


class ResponseMode(Enum):
    STREAMING = "streaming"
    BLOCKING = "blocking"


class BaseClient(metaclass=ABCMeta):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        user: str | None = None,
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.user = user
        self.timeout = timeout
        self.session = requests.Session()

    @abstractmethod
    def request(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Execute the concrete API request."""

    def _auth_headers(self, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _request_json(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        response = self.session.request(method, url, timeout=self.timeout, **kwargs)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError as exc:
            raise ValueError(f"Response is not valid JSON: {response.text[:200]}") from exc

    def get_api_key(self) -> str | None:
        return self.api_key

    def get_base_url(self) -> str | None:
        return self.base_url

    def get_user(self) -> str | None:
        return self.user

    def set_api_key(self, api_key: str) -> None:
        self.api_key = api_key

    def set_base_url(self, base_url: str) -> None:
        self.base_url = base_url

    def set_user(self, user: str) -> None:
        self.user = user


class FileUploadClient(BaseClient):
    def request(self, file_path: str) -> dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if self.base_url is None:
            raise ValueError("base_url is required for file upload.")

        with path.open("rb") as file:
            return self._request_json(
                "POST",
                self.base_url,
                headers=self._auth_headers(),
                data={"user": self.user or ""},
                files={"file": (path.name, file, "application/octet-stream")},
            )


class WorkFlowRunClient(BaseClient):
    def request(
        self,
        param_name: str,
        upload_file_id: str,
        response_mode: ResponseMode | str = ResponseMode.BLOCKING,
    ) -> dict[str, Any]:
        if self.base_url is None:
            raise ValueError("base_url is required for workflow run.")

        mode = response_mode.value if isinstance(response_mode, ResponseMode) else response_mode
        payload = {
            "inputs": {
                param_name: {
                    "type": "document",
                    "transfer_method": "local_file",
                    "upload_file_id": upload_file_id,
                }
            },
            "response_mode": mode,
            "user": self.user,
        }
        return self._request_json(
            "POST",
            self.base_url,
            headers=self._auth_headers({"Content-Type": "application/json"}),
            json=payload,
        )

    def get_info(self, run_id: str) -> dict[str, Any]:
        if self.base_url is None:
            raise ValueError("base_url is required for workflow run info.")

        return self._request_json(
            "GET",
            f"{self.base_url}/{run_id}",
            headers=self._auth_headers(),
        )


class WorkFlowLogClient(BaseClient):
    def request(self, page: int, limit: int) -> dict[str, Any]:
        if self.base_url is None:
            raise ValueError("base_url is required for workflow logs.")

        return self._request_json(
            "GET",
            self.base_url,
            headers=self._auth_headers(),
            params={"page": page, "limit": limit},
        )


class ChatMessageClient(BaseClient):
    def request(self, message: str) -> dict[str, Any]:
        if self.base_url is None:
            raise ValueError("base_url is required for chat messages.")

        payload = {
            "inputs": {},
            "query": message,
            "conversation_id": "",
            "response_mode": ResponseMode.BLOCKING.value,
            "user": self.user,
            "files": [],
        }
        return self._request_json(
            "POST",
            self.base_url,
            headers=self._auth_headers({"Content-Type": "application/json"}),
            json=payload,
        )
