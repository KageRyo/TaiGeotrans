"""Tests for the authenticated TGOS HTTP contract."""

import json
from pathlib import Path

import httpx
import pytest

from taigeotrans.providers.tgos import (
    TGOSClient,
    TGOSConfigurationError,
    TGOSRequestError,
    TGOSResponseError,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "tgos_queryaddr_exact_match.json"
FIXTURE_ADDRESS = "臺北市中山區行政里1鄰松江路469巷4號"


def _load_success_fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _client_with_response(
    payload: object,
    address: str = FIXTURE_ADDRESS,
) -> TGOSClient:
    client = TGOSClient(app_id="test-app", api_key="test-key", max_retries=1)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["oAPPId"] == "test-app"
        assert request.url.params["oAPIKey"] == "test-key"
        assert request.url.params["oAddress"] == address
        assert request.url.params["oSRS"] == "EPSG:4326"
        return httpx.Response(200, json=payload, request=request)

    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    return client


def test_geocode_uses_documented_parameters() -> None:
    client = _client_with_response(_load_success_fixture())

    try:
        lon, lat, matched_address, confidence = client.geocode_address(FIXTURE_ADDRESS)
    finally:
        client.close()

    assert lon == pytest.approx(121.53417880249)
    assert lat == pytest.approx(25.066292181482446)
    assert matched_address == FIXTURE_ADDRESS
    assert confidence == 1.0


def test_geocode_retries_server_error_then_succeeds() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(503, request=request)
        return httpx.Response(200, json=_load_success_fixture(), request=request)

    client = TGOSClient(
        app_id="test-app",
        api_key="test-key",
        max_retries=3,
        retry_delay=0,
    )
    client._client = httpx.Client(transport=httpx.MockTransport(handler))

    try:
        result = client.geocode_address(FIXTURE_ADDRESS)
    finally:
        client.close()

    assert calls == 3
    assert result[0] == pytest.approx(121.53417880249)


def test_geocode_retries_timeout_then_raises_request_error() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("simulated timeout", request=request)

    client = TGOSClient(
        app_id="test-app",
        api_key="test-key",
        max_retries=2,
        retry_delay=0,
    )
    client._client = httpx.Client(transport=httpx.MockTransport(handler))

    try:
        with pytest.raises(TGOSRequestError, match="after 2 attempts"):
            client.geocode_address(FIXTURE_ADDRESS)
    finally:
        client.close()

    assert calls == 2


def test_geocode_does_not_retry_client_error() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"error": "bad request"}, request=request)

    client = TGOSClient(
        app_id="test-app",
        api_key="test-key",
        max_retries=3,
        retry_delay=0,
    )
    client._client = httpx.Client(transport=httpx.MockTransport(handler))

    try:
        with pytest.raises(TGOSRequestError, match="HTTP 400"):
            client.geocode_address(FIXTURE_ADDRESS)
    finally:
        client.close()

    assert calls == 1


def test_geocode_rejects_invalid_json_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=(
                '<?xml version="1.0" encoding="utf-8"?>'
                '<string xmlns="http://tempuri.org/">'
                "認證授權失敗:應用程式 IP 不正確"
                "</string>"
            ),
            request=request,
        )

    client = TGOSClient(app_id="test-app", api_key="test-key", max_retries=1)
    client._client = httpx.Client(transport=httpx.MockTransport(handler))

    try:
        with pytest.raises(TGOSResponseError, match="invalid JSON"):
            client.geocode_address(FIXTURE_ADDRESS)
    finally:
        client.close()


def test_geocode_returns_empty_result_when_address_is_not_found() -> None:
    client = _client_with_response({"Info": [], "AddressList": []}, address="不存在的地址")
    try:
        result = client.geocode_address("不存在的地址")
    finally:
        client.close()

    assert result == (None, None, None, 0.0)


def test_geocode_rejects_missing_credentials() -> None:
    with pytest.raises(TGOSConfigurationError):
        TGOSClient().geocode_address("臺北市信義區市府路1號")


def test_geocode_rejects_unrecognized_response() -> None:
    client = _client_with_response(
        {"Info": []},
        address="臺北市信義區市府路1號",
    )
    try:
        with pytest.raises(TGOSResponseError):
            client.geocode_address("臺北市信義區市府路1號")
    finally:
        client.close()
