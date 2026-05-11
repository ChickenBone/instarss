import requests
import responses as responses_lib

from app.instapaper import InstapaperClient, InstapaperAuthError

API_URL = "https://www.instapaper.com/api/add"


@responses_lib.activate
def test_add_url_success_201():
    responses_lib.add(responses_lib.POST, API_URL, status=201)
    client = InstapaperClient("user@example.com", "pass")
    client.add_url("https://example.com/article", title="Test")


@responses_lib.activate
def test_add_url_success_200():
    responses_lib.add(responses_lib.POST, API_URL, status=200)
    client = InstapaperClient("user@example.com", "pass")
    client.add_url("https://example.com/article", title="Test")


@responses_lib.activate
def test_add_url_403_raises_auth_error():
    responses_lib.add(responses_lib.POST, API_URL, status=403)
    client = InstapaperClient("user@example.com", "wrong")
    try:
        client.add_url("https://example.com/article")
        assert False, "Expected InstapaperAuthError"
    except InstapaperAuthError:
        pass
    assert len(responses_lib.calls) == 1


@responses_lib.activate
def test_add_url_500_retries_then_raises():
    for _ in range(5):
        responses_lib.add(responses_lib.POST, API_URL, status=500)
    client = InstapaperClient("user@example.com", "pass")
    try:
        client.add_url("https://example.com/article")
        assert False, "Expected exception after retries"
    except Exception:
        pass
    assert len(responses_lib.calls) == 5


@responses_lib.activate
def test_add_url_succeeds_on_second_try():
    responses_lib.add(responses_lib.POST, API_URL, status=503)
    responses_lib.add(responses_lib.POST, API_URL, status=201)
    client = InstapaperClient("user@example.com", "pass")
    client.add_url("https://example.com/article")
    assert len(responses_lib.calls) == 2
