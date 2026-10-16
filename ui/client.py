"""Talks to the InvoiceIQ API. The UI never imports app/ -- it could run on another machine."""

from __future__ import annotations

import os

import httpx

API_URL = os.environ.get("INVOICEIQ_API_URL", "http://localhost:8000")
API_KEY = os.environ.get("APP_API_KEY")


class ApiError(RuntimeError):
    pass


class ApiClient:
    def __init__(self, base_url: str = API_URL, api_key: str | None = API_KEY) -> None:
        headers = {"X-API-Key": api_key} if api_key else {}
        # Extraction of a long PDF on the free tier can take a minute.
        self._http = httpx.Client(base_url=base_url, headers=headers, timeout=180)

    def _check(self, r: httpx.Response) -> httpx.Response:
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text
            raise ApiError(f"{r.status_code}: {detail}")
        return r

    def health(self) -> dict:
        try:
            return self._check(self._http.get("/health")).json()
        except httpx.HTTPError as exc:
            return {"status": "down", "detail": str(exc)}

    def extract(self, name: str, data: bytes) -> dict:
        try:
            return self._check(self._http.post("/extract", files={"file": (name, data)})).json()
        except httpx.HTTPError as exc:
            raise ApiError(str(exc)) from exc

    def validate(self, invoice: dict) -> dict:
        return self._check(self._http.post("/validate", json={"invoice": invoice})).json()

    def export(self, approved: list[dict], fmt: str = "xlsx") -> bytes:
        return self._check(self._http.post("/export", params={"format": fmt}, json=approved)).content

    def samples(self) -> list[str]:
        return self._check(self._http.get("/samples")).json()

    def sample(self, name: str) -> bytes:
        return self._check(self._http.get(f"/samples/{name}")).content
