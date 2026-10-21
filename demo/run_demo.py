"""
Scripted walkthrough of the running app, for the project demo.

Drives the real web UI in Chromium (Playwright) the way a new user would:
register, run several practical tasks, watch one live, cancel one, export a
result, check run history, and confirm a second user can't see the first
user's runs. Saves screenshots, a video per browser session, each run's
Markdown export and API record, and a summary (`summary.json`).

Usage (API on :8000 and frontend dev server on :5173 already running):
    python demo/run_demo.py --base-url http://localhost:5173 --out demo-output
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page, expect, sync_playwright

PASSWORD = "demo-password-123"

# Practical tasks a student or engineer might bring to the tool.
SCENARIOS = [
    {
        "key": "scheduling",
        "title": "Choose a real-time scheduler for an embedded project",
        "task": (
            "Compare rate-monotonic (RMS) and earliest-deadline-first (EDF) scheduling for a "
            "small embedded system with three periodic tasks, and recommend one."
        ),
        "watch_live": True,
    },
    {
        "key": "study-plan",
        "title": "Plan exam preparation",
        "task": (
            "Plan a two-week study schedule for a ROS 1 practical exam covering nodes, topics, "
            "services, launch files and turtlesim."
        ),
    },
    {
        "key": "explainer",
        "title": "Understand a design pattern",
        "task": (
            "Explain how the circuit breaker pattern protects a web service that calls an "
            "unreliable external API, with a concrete example."
        ),
    },
]

CANCEL_TASK = (
    "Survey recent approaches to space debris detection from ground-based optical "
    "telescopes, with their main limitations."
)


class Recorder:
    def __init__(self, out: Path) -> None:
        self.out = out
        (out / "screenshots").mkdir(parents=True, exist_ok=True)
        (out / "runs").mkdir(exist_ok=True)
        (out / "video").mkdir(exist_ok=True)
        self.shots: list[dict] = []
        self.runs: list[dict] = []
        self.notes: list[str] = []

    def shot(self, page: Page, name: str, caption: str, full_page: bool = True) -> None:
        index = len(self.shots) + 1
        filename = f"{index:02d}-{name}.png"
        page.screenshot(path=str(self.out / "screenshots" / filename), full_page=full_page)
        self.shots.append({"file": f"screenshots/{filename}", "caption": caption})
        print(f"[shot] {filename}: {caption}", flush=True)


def new_context(browser: Browser, rec: Recorder, name: str, **kwargs) -> BrowserContext:
    return browser.new_context(
        viewport=kwargs.pop("viewport", {"width": 1366, "height": 900}),
        record_video_dir=str(rec.out / "video" / name),
        record_video_size={"width": 1366, "height": 900},
        accept_downloads=True,
        **kwargs,
    )


def register(page: Page, base_url: str, email: str, rec: Recorder | None = None) -> None:
    page.goto(f"{base_url}/")
    expect(page.get_by_role("heading", name="Sign in")).to_be_visible()
    if rec:
        rec.shot(page, "sign-in", "Visiting the app while signed out leads to the sign-in page.")
    page.get_by_role("link", name="Create an account").click()
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(PASSWORD)
    if rec:
        rec.shot(page, "register", "Creating an account (password at least 8 characters).")
    page.get_by_role("button", name="Create account").click()
    expect(page.get_by_role("button", name="Sign out")).to_be_visible()


def start_run(page: Page, task: str) -> str:
    page.get_by_label("What should the agents work on?").fill(task)
    page.get_by_role("button", name="Run task").click()
    page.wait_for_url(re.compile(r".*/tasks/[0-9a-f-]+$"))
    return page.url.rsplit("/", 1)[-1]


def main_badge(page: Page, label: str):
    return page.locator("main").get_by_text(label, exact=True).first


def finished_badge(page: Page):
    """The run's status badge once it has finished successfully or partially."""
    return main_badge(page, "Passed").or_(main_badge(page, "Partial result"))


def save_run(page: Page, base_url: str, rec: Recorder, task_id: str, key: str, title: str) -> dict:
    record = page.request.get(f"{base_url}/tasks/{task_id}").json()
    (rec.out / "runs" / f"{key}.json").write_text(json.dumps(record, indent=2))
    summary = {
        "key": key,
        "title": title,
        "task": record["input_task"],
        "status": record["status"],
        "retries_used": record["retries_used"],
        "steps": [
            {k: s.get(k) for k in ("seq", "step_name", "status", "sub_task_id", "latency_seconds")}
            for s in record["steps"] or []
        ],
        "usage": record["usage"],
        "sub_tasks": {
            sid: {
                "query": sub.get("query"),
                "findings": (sub.get("findings") or sub.get("error") or "")[:400],
                "sources": sub.get("sources", []),
            }
            for sid, sub in (record["result"] or {}).items()
        },
        "error": record["error"],
    }
    rec.runs.append(summary)
    return record


def run_demo(base_url: str, out: Path, provider: str) -> None:
    rec = Recorder(out)
    rec.notes.append(f"LLM provider: {provider}")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = new_context(browser, rec, "ada")
        page = context.new_page()
        try:
            register(page, base_url, "ada@example.com", rec)
            rec.shot(page, "empty-home", "Signed in: the start page explains the three agents.")

            first_run_url = ""
            for scenario in SCENARIOS:
                task_id = start_run(page, scenario["task"])
                first_run_url = first_run_url or page.url
                if scenario.get("watch_live"):
                    # Catch the run mid-flight: some steps done, the rest still running.
                    page.locator("main li").first.wait_for(timeout=30_000)
                    rec.shot(
                        page,
                        f"{scenario['key']}-live",
                        "While the run is going, each agent step appears as it finishes, "
                        "with a Cancel button.",
                    )
                expect(finished_badge(page)).to_be_visible(timeout=180_000)
                rec.shot(
                    page,
                    f"{scenario['key']}-result",
                    f"{scenario['title']}: finished run with step trace and findings.",
                )
                with page.expect_download() as download:
                    page.get_by_role("button", name="Download as Markdown").click()
                download.value.save_as(str(out / "runs" / f"{scenario['key']}.md"))
                save_run(page, base_url, rec, task_id, scenario["key"], scenario["title"])

            # Cancel a run part-way through.
            task_id = start_run(page, CANCEL_TASK)
            page.locator("main li").first.wait_for(timeout=30_000)
            page.get_by_role("button", name="Cancel run").click()
            expect(main_badge(page, "Cancelled")).to_be_visible(timeout=120_000)
            rec.shot(page, "cancelled", "A run cancelled part-way: finished steps are kept.")
            save_run(page, base_url, rec, task_id, "cancelled", "Cancel a run part-way")

            page.get_by_role("link", name="Multi-Agent Runs").click()
            rec.shot(page, "history", "Run history in the left rail, newest first.")

            # The same result on a phone-sized screen.
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(first_run_url)
            expect(finished_badge(page)).to_be_visible()
            rec.shot(page, "mobile", "The same run on a phone-sized screen.")
            ada_task_url = first_run_url
        except Exception as exc:  # keep whatever was captured, plus the failing screen
            rec.notes.append(f"FAILED: {exc!r}")
            rec.shot(page, "failure", f"Screen at the moment of failure: {exc!r}"[:300])
            raise
        finally:
            context.close()
            _write_summary(rec)

        # A second user can't see the first user's runs.
        context = new_context(browser, rec, "bob")
        page = context.new_page()
        try:
            register(page, base_url, "bob@example.com")
            rec.shot(page, "second-user-empty", "A second user starts with an empty history.")
            page.goto(ada_task_url)
            expect(page.get_by_role("alert")).to_be_visible(timeout=15_000)
            rec.shot(
                page,
                "second-user-blocked",
                "Opening the first user's run link as the second user: not found.",
            )
        except Exception as exc:
            rec.notes.append(f"FAILED (second user): {exc!r}")
            rec.shot(page, "failure-second-user", f"Failure: {exc!r}"[:300])
            raise
        finally:
            context.close()
            browser.close()
            _write_summary(rec)
    _name_videos(out)


def _write_summary(rec: Recorder) -> None:
    (rec.out / "summary.json").write_text(
        json.dumps(
            {
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "notes": rec.notes,
                "screenshots": rec.shots,
                "runs": rec.runs,
            },
            indent=2,
        )
    )


def _name_videos(out: Path) -> None:
    """Playwright names videos randomly; give each session's video a stable name."""
    for session_dir in (out / "video").iterdir():
        if session_dir.is_dir():
            for i, video in enumerate(sorted(session_dir.glob("*.webm"))):
                suffix = "" if i == 0 else f"-{i + 1}"
                video.rename(out / "video" / f"{session_dir.name}{suffix}.webm")
            session_dir.rmdir()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:5173")
    parser.add_argument("--out", type=Path, default=Path("demo-output"))
    parser.add_argument("--provider", default="mock")
    args = parser.parse_args()
    run_demo(args.base_url.rstrip("/"), args.out, args.provider)
