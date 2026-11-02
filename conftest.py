from __future__ import annotations

import logging
import os
import re
import shutil
from pathlib import Path

import allure
import pytest
from playwright.sync_api import sync_playwright

from utils.browser_logs import BrowserLogCollector
from utils.config_loader import load_config, load_scenarios

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
CATEGORIES = ROOT / "config" / "allure" / "categories.json"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")


def pytest_addoption(parser):
    parser.addoption("--profile", default=None, help="config profile (local / ci)")
    parser.addoption("--data", default=None, help="path to scenarios JSON")
    mode = parser.getgroup("browser mode")
    mode.addoption("--headless", dest="headless_cli", action="store_const", const=True, default=None,
                   help="run the browser headless")
    mode.addoption("--headed", dest="headless_cli", action="store_const", const=False,
                   help="show the browser window")
    parser.addini("headless", "true/false - run the browser headless (default: from config profile)",
                  default="")


def pytest_generate_tests(metafunc):
    """Data-driven: one test run per scenario in data/test_data.json."""
    if "scenario" in metafunc.fixturenames:
        scenarios = load_scenarios(metafunc.config.getoption("--data"))
        metafunc.parametrize("scenario", scenarios, ids=[s["id"] for s in scenarios])


def _resolve_headless(pytestconfig, profile_value: bool) -> bool:
    """--headless/--headed > HEADLESS env > pytest.ini `headless` > config profile."""
    cli = pytestconfig.getoption("headless_cli")
    if cli is not None:
        return cli
    env = os.getenv("HEADLESS")
    if env is not None and env != "":
        return env.strip().lower() in ("1", "true", "yes")
    ini = str(pytestconfig.getini("headless")).strip().lower()
    if ini:
        return ini in ("1", "true", "yes")
    return profile_value


@pytest.fixture(scope="session")
def config(pytestconfig):
    cfg = load_config(pytestconfig.getoption("--profile"))
    cfg["headless"] = _resolve_headless(pytestconfig, cfg["headless"])
    logging.getLogger(__name__).info("Profile '%s', headless=%s", cfg["profile"], cfg["headless"])
    return cfg


@pytest.fixture(scope="session")
def browser(config):
    with sync_playwright() as p:
        browser = getattr(p, config["browser"]).launch(
            headless=config["headless"], slow_mo=config["slow_mo_ms"]
        )
        yield browser
        browser.close()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    setattr(item, f"rep_{outcome.get_result().when}", outcome.get_result())


@pytest.fixture
def page(browser, config, request):
    context = browser.new_context(viewport=config["viewport"], locale=config["locale"])
    tracing = config["trace"] != "off"
    if tracing:
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()
    browser_logs = BrowserLogCollector().attach_to(page)
    yield page

    # setup failures (e.g. login in the `flow` fixture) count too, not only the test body
    failed = any(getattr(getattr(request.node, f"rep_{when}", None), "failed", False)
                 for when in ("setup", "call"))
    safe = re.sub(r"[^\w\-]+", "_", request.node.name)
    if failed:
        allure.attach(page.screenshot(full_page=True), name="failure_screenshot",
                      attachment_type=allure.attachment_type.PNG)
        if browser_logs:
            allure.attach(browser_logs.as_text(), name="browser_console_log",
                          attachment_type=allure.attachment_type.TEXT)
    if tracing:
        if config["trace"] == "on" or failed:
            trace = REPORTS / "traces" / f"{safe}.zip"
            trace.parent.mkdir(parents=True, exist_ok=True)
            context.tracing.stop(path=str(trace))
            allure.attach.file(str(trace), name="playwright_trace", extension="zip")
        else:
            context.tracing.stop()
    context.close()


def pytest_sessionfinish(session):
    """Copy Allure categories next to the results so the report groups failures by cause."""
    results_dir = session.config.getoption("allure_report_dir", default=None)
    if results_dir and CATEGORIES.exists():
        Path(results_dir).mkdir(parents=True, exist_ok=True)
        shutil.copy(CATEGORIES, Path(results_dir) / "categories.json")
