"""Choose an installed iPhone simulator and record the source of real screenshots."""
import json
import os
from pathlib import Path
import re
import subprocess


def run(*args):
    return subprocess.check_output(args, text=True).strip()


devices = json.loads(run("xcrun", "simctl", "list", "devices", "available", "--json"))["devices"]
sdk_version = tuple(map(int, run("xcrun", "--sdk", "iphonesimulator", "--show-sdk-version").split(".")))
candidates = [
    (runtime, device)
    for runtime, group in devices.items()
    if ".iOS-" in runtime
    if tuple(map(int, re.findall(r"\d+", runtime))) <= sdk_version
    for device in group
    if device.get("isAvailable") and "iPhone" in device["name"] and "Pro Max" in device["name"]
]
if not candidates:
    raise SystemExit("No installed iPhone Pro Max simulator is available; no screenshot will be fabricated.")


def version_key(candidate):
    runtime, device = candidate
    return tuple(map(int, re.findall(r"\d+", runtime))), tuple(map(int, re.findall(r"\d+", device["name"])))


runtime, device = max(candidates, key=version_key)
udid = device["udid"]
evidence = Path("build/evidence")
evidence.mkdir(parents=True, exist_ok=True)
(evidence / "simulator.json").write_text(json.dumps({
    "device": device["name"], "runtime": runtime, "udid": udid, "sdk_version": sdk_version,
    "tested_commit": run("git", "rev-parse", "HEAD"),
    "source_commit": os.environ.get("RADAR_SOURCE_COMMIT"),
    "workflow_run": f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
    "xcode": run("xcodebuild", "-version"),
    "capture_method": "XCUIScreen screenshot attachment from the running app; no seeded results",
    "scope": "Launch, clear controls, live public-source report and comparison, Safari return, native share cancellation, relaunch recovery, privacy and deletion. Consult test-summary.json for actual pass/failure; no physical-device claim.",
}, ensure_ascii=False, indent=2) + "\n")
print(f"Selected {device['name']} / {runtime} ({udid}); SDK {sdk_version}", flush=True)
if device["state"] != "Booted":
    subprocess.run(["xcrun", "simctl", "boot", udid], check=True, timeout=60)
# A hosted Mac's first boot migrates iOS data. Keep a finite allowance for it,
# independent of the app's own launch timeout in RadarUITests.
subprocess.run(["xcrun", "simctl", "bootstatus", udid, "-b"], check=True, timeout=600)
# Normalizing the status bar is cosmetic. SpringBoard can still be busy after
# bootstatus completes; a timeout here must not prevent actual app validation.
status_bar = {"applied": False}
try:
    subprocess.run([
        "xcrun", "simctl", "status_bar", udid, "override", "--time", "9:41",
        "--dataNetwork", "wifi", "--wifiMode", "active", "--wifiBars", "3",
        "--batteryState", "charged", "--batteryLevel", "100",
    ], check=True, timeout=30)
    status_bar["applied"] = True
except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
    status_bar["error"] = str(error)
    print(f"::warning::Status-bar appearance was not normalized: {error}", flush=True)
(evidence / "status-bar.json").write_text(json.dumps(status_bar, indent=2) + "\n")
with open(os.environ["GITHUB_ENV"], "a") as env_file:
    env_file.write(f"SIMULATOR_UDID={udid}\n")
