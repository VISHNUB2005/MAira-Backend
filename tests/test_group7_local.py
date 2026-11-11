import os
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("JWT_SECRET_KEY", "a" * 40)
os.environ.setdefault("EMAIL_PROVIDER", "console")

import re
from types import SimpleNamespace

import pytest
from xsc_lib.xsc_lib_app import xsc_lib_a_email as email_mod
from xsc_lib.xsc_lib_app.xsc_lib_a_config import Settings


# ---------- file provider ----------
def test_file_provider_saves_html_and_text(monkeypatch, tmp_path):
    content = email_mod.build_login_email("482916")          # built with the real settings
    monkeypatch.setattr(email_mod, "settings", SimpleNamespace(email_outbox_dir=str(tmp_path / "box")))
    name = email_mod.FileProvider().send("alice@organization.com", content)
    box = tmp_path / "box"
    assert "482916" in (box / "latest.html").read_text(encoding="utf-8")
    assert "482916" in (box / "latest.txt").read_text(encoding="utf-8")
    assert (box / f"{name}.html").exists()
    assert "alice@organization.com" in (box / "latest.txt").read_text(encoding="utf-8")

@pytest.mark.parametrize("env", ["staging", "production"])
def test_file_provider_blocked_outside_dev(monkeypatch, env):
    monkeypatch.setenv("ENVIRONMENT", env)
    monkeypatch.setenv("EMAIL_PROVIDER", "file")
    with pytest.raises(RuntimeError, match="file"):
        Settings().validate()

def test_file_provider_allowed_in_dev(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("EMAIL_PROVIDER", "file")
    Settings().validate()


# ---------- app password spaces ----------
def test_password_whitespace_is_removed(monkeypatch):
    monkeypatch.setenv("EMAIL_PASSWORD", "abcd efgh ijkl mnop ")
    assert Settings().smtp_password == "abcdefghijklmnop"

def test_old_smtp_password_name_also_cleaned(monkeypatch):
    monkeypatch.delenv("EMAIL_PASSWORD", raising=False)
    monkeypatch.setenv("SMTP_PASSWORD", "ab cd")
    assert Settings().smtp_password == "abcd"


# ---------- the interactive demo, driven by a script ----------
def _script(email_mod_, answers_first):
    """Returns an ask() that answers prompts; for the code prompt it reads the mock outbox."""
    state = {"codes": list(answers_first)}
    def ask(prompt):
        if "email address" in prompt.lower():
            return "bob@example.com"
        if "flow" in prompt.lower():
            return "2"
        if "code" in prompt.lower():
            nxt = state["codes"].pop(0)
            if nxt == "REAL":
                return re.search(r"code: (\d+)", email_mod_.MockProvider.outbox[-1]["text"]).group(1)
            return nxt
        raise AssertionError(prompt)
    return ask

@pytest.fixture
def demo(monkeypatch):
    import run_demo
    monkeypatch.setattr(email_mod, "_get_provider", lambda: email_mod.MockProvider())
    email_mod.MockProvider.clear()
    return run_demo

def test_demo_accepts_the_real_code(demo):
    out = []
    assert demo.run(ask=_script(email_mod, ["REAL"]), say=out.append) is True
    assert any("VERIFIED" in line for line in out)

def test_demo_rejects_wrong_code_then_accepts_real(demo):
    out = []
    assert demo.run(ask=_script(email_mod, ["000000x", "REAL"]), say=out.append) is True
    assert any("Incorrect code" in line for line in out)

def test_demo_locks_after_too_many_wrong_codes(demo):
    out = []
    assert demo.run(ask=_script(email_mod, ["bad"] * 5), say=out.append) is False
    assert sum("Incorrect code" in line for line in out) == 5
