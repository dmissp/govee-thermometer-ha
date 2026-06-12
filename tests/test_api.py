"""Tests for the Govee API client."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.govee_thermometer.api import (
    GoveeApi, GoveeAuthError, GoveeApiError, _normalise,
)


# ── _normalise ───────────────────────────────────────────────────────────────

def test_normalise_plain_float():
    assert _normalise(25.6) == 25.6

def test_normalise_times100():
    assert _normalise(2560.0) == 25.6

def test_normalise_humidity_plain():
    assert _normalise(80.3) == 80.3

def test_normalise_humidity_scaled():
    assert _normalise(8030.0) == 80.3


# ── async_get_reading ─────────────────────────────────────────────────────────

def _mock_session(json_response: dict, status: int = 200):
    mock_resp = AsyncMock()
    mock_resp.status = status
    mock_resp.json   = AsyncMock(return_value=json_response)
    mock_resp.text   = AsyncMock(return_value="")
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_resp)
    ctx.__aexit__  = AsyncMock(return_value=False)
    session = MagicMock()
    session.post = MagicMock(return_value=ctx)
    session.get  = MagicMock(return_value=ctx)
    return session


@pytest.mark.asyncio
async def test_get_reading_h5103():
    session = _mock_session({
        "code": 200, "msg": "success",
        "payload": {"capabilities": [
            {"instance": "online",          "state": {"value": True}},
            {"instance": "sensorTemperature","state": {"value": 25.6}},
            {"instance": "sensorHumidity",  "state": {"value": 60.0}},
        ]},
    })
    api = GoveeApi("key", session)
    r = await api.async_get_reading("AA:BB:CC:DD:EE:FF:00:11", "H5103")
    assert r.online is True
    assert r.temperature == 25.6
    assert r.humidity    == 60.0


@pytest.mark.asyncio
async def test_get_reading_scaled():
    session = _mock_session({
        "code": 200, "msg": "success",
        "payload": {"capabilities": [
            {"instance": "online",          "state": {"value": True}},
            {"instance": "sensorTemperature","state": {"value": 2560}},
            {"instance": "sensorHumidity",  "state": {"value": 6000}},
        ]},
    })
    api = GoveeApi("key", session)
    r = await api.async_get_reading("XX", "H5103")
    assert r.temperature == 25.6
    assert r.humidity    == 60.0


@pytest.mark.asyncio
async def test_get_reading_pool_no_humidity():
    """Pool thermometer returns temperature only — humidity stays None."""
    session = _mock_session({
        "code": 200, "msg": "success",
        "payload": {"capabilities": [
            {"instance": "online",           "state": {"value": True}},
            {"instance": "sensorTemperature","state": {"value": 28.5}},
        ]},
    })
    api = GoveeApi("key", session)
    r = await api.async_get_reading("YY", "H5055")
    assert r.temperature == 28.5
    assert r.humidity    is None


@pytest.mark.asyncio
async def test_auth_error_on_401():
    session = _mock_session({}, status=401)
    api = GoveeApi("bad", session)
    with pytest.raises(GoveeAuthError):
        await api.async_get_reading("XX", "H5103")
