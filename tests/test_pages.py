"""Every page, run headless against the throwaway database: it draws empty and
with data, the sign-in keeps it private, and the look is a saved choice."""

from datetime import date
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import data
import theme
import ui

ROOT = Path(__file__).resolve().parent.parent
HOME = ROOT / "app" / "Home.py"
PAGES = sorted((ROOT / "app" / "pages").glob("*.py"))
TODAY = date(2026, 10, 14)


PASSWORD = "correct horse"


@pytest.fixture(autouse=True)
def fixed_today(database, monkeypatch):
    monkeypatch.setattr(data, "today", lambda: TODAY)
    monkeypatch.setenv("APP_PASSWORD", PASSWORD)


def new_app(path: Path, signed_in: bool = True) -> AppTest:
    at = AppTest.from_file(str(path), default_timeout=30)
    if signed_in:
        at.session_state[ui.SIGNED_IN] = True
    return at


def run(path: Path) -> AppTest:
    at = new_app(path).run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def widget(elements, label, nth: int = 0):
    """The nth widget with this label (-1: the last, e.g. a form below the add form)."""
    matches = [w for w in elements if w.label == label]
    assert matches, f"no widget labelled {label!r}: {[w.label for w in elements]}"
    return matches[nth]


def click(at: AppTest, label: str) -> AppTest:
    widget(at.button, label).click().run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def html(at: AppTest) -> str:
    """Everything the page drew with st.html (empty states, subtitles)."""
    return "\n".join(e.proto.body for e in at.get("html"))


def opened(at: AppTest) -> bool:
    """The page got past the sign-in and drew its content."""
    return any(h.value == "Needs attention" for h in at.subheader)


def seed() -> None:
    """A little of everything, for the draws-with-data tests (grows with each page)."""
    data.set_setting("theme", "light")


@pytest.mark.parametrize("path", [HOME, *PAGES], ids=lambda p: p.stem)
def test_every_page_draws_empty(path):
    run(path)


@pytest.mark.parametrize("path", [HOME, *PAGES], ids=lambda p: p.stem)
def test_every_page_draws_with_data(path):
    seed()
    run(path)


def test_home_says_what_it_will_show_while_empty():
    at = run(HOME)
    assert at.title[0].value == "Finance Tracker"
    assert opened(at) and "Nothing to show yet" in html(at)
    assert "Wednesday, October 14" in html(at)


@pytest.mark.parametrize("path", [HOME, *PAGES], ids=lambda p: p.stem)
def test_every_page_asks_for_the_password_first(path):
    at = new_app(path, signed_in=False).run()
    assert [t.label for t in at.text_input] == ["Password"]
    assert not at.metric and not at.dataframe and not opened(at)


def test_the_right_password_opens_the_app_and_a_wrong_one_does_not(monkeypatch):
    monkeypatch.setattr(ui.time, "sleep", lambda s: None)
    at = new_app(HOME, signed_in=False).run()
    widget(at.text_input, "Password").set_value("guess")
    click(at, "Sign in")
    assert at.error[0].value == "Wrong password."
    assert not opened(at)
    widget(at.text_input, "Password").set_value(PASSWORD)
    click(at, "Sign in")
    assert opened(at)


def test_dark_mode_is_a_saved_choice_and_light_is_the_default():
    at = run(HOME)
    assert theme.current() == "light" and data.get_setting("theme") is None
    widget(at.toggle, "Dark mode").set_value(True).run()
    assert not at.exception
    assert data.get_setting("theme") == "dark" and theme.current() == "dark"
    for path in PAGES:                                    # every page follows
        assert run(path).toggle[0].value is True
    widget(at.toggle, "Dark mode").set_value(False).run()
    assert data.get_setting("theme") == "light" and theme.current() == "light"


def test_the_switch_follows_a_change_made_on_another_device():
    at = run(HOME)
    assert widget(at.toggle, "Dark mode").value is False
    data.set_setting("theme", "dark")                 # flipped on the phone, say
    at.run()
    assert not at.exception
    assert widget(at.toggle, "Dark mode").value is True
    assert data.get_setting("theme") == "dark" and theme.current() == "dark"
    data.set_setting("theme", "light")
    at.run()
    assert widget(at.toggle, "Dark mode").value is False and theme.current() == "light"


def test_signing_out_locks_the_app_again():
    at = run(HOME)
    click(at, "Sign out")
    assert [t.label for t in at.text_input] == ["Password"] and not opened(at)


def test_no_way_to_sign_in_set_up_keeps_the_app_locked(monkeypatch):
    monkeypatch.delenv("APP_PASSWORD")
    at = new_app(HOME, signed_in=False).run()
    assert "no way to sign in is set up" in at.error[0].value
    assert not at.text_input and not opened(at) and not at.button


@pytest.fixture
def google(monkeypatch):
    """Sign in with Google set up, for you; who is signed in is set per test."""
    monkeypatch.setattr(ui, "_google_ready", lambda: True)
    monkeypatch.setenv("ALLOWED_EMAILS", "Me@Example.com, other@example.com")

    def signed_in_as(email):
        monkeypatch.setattr(ui, "_google_email", lambda: email)
    return signed_in_as


def test_google_offers_both_ways_in_until_someone_signs_in(google):
    google(None)
    at = new_app(HOME, signed_in=False).run()
    assert [b.label for b in at.button] == ["Sign in with Google", "Sign in with password"]
    assert not opened(at)


def test_an_allowed_google_account_goes_straight_in(google):
    google("me@example.com")
    at = new_app(HOME, signed_in=False).run()
    assert opened(at)
    for path in PAGES:                              # and stays in on every page
        assert not new_app(path, signed_in=False).run().exception


def test_any_other_google_account_is_turned_away(google):
    google("stranger@example.com")
    at = new_app(HOME, signed_in=False).run()
    assert "stranger@example.com isn't allowed" in at.error[0].value
    assert [b.label for b in at.button] == ["Sign out"]
    assert not opened(at)


def test_the_sidebar_is_hidden_only_while_signed_out(google, monkeypatch):
    shown = []
    original = st.html
    monkeypatch.setattr(st, "html", lambda body, **kw: (shown.append(body), original(body, **kw)))
    google("me@example.com")
    new_app(HOME, signed_in=False).run()
    assert shown and not any(theme.LOCKED in body for body in shown)
    shown.clear()
    google(None)
    new_app(HOME, signed_in=False).run()
    assert any(theme.LOCKED in body for body in shown)


def test_google_without_allowed_emails_lets_nobody_in(google, monkeypatch):
    monkeypatch.delenv("ALLOWED_EMAILS")
    google("me@example.com")
    at = new_app(HOME, signed_in=False).run()
    assert "isn't allowed" in at.error[0].value and not opened(at)
