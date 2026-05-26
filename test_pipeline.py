"""
Pipeline Test Script — ทดสอบ backend API ทั้งหมดบน PC
เรียกใช้หลังจาก docker compose up แล้ว

วิธีใช้:
  pip install httpx
  python test_pipeline.py
  python test_pipeline.py --base-url http://192.168.1.100:8000  # ถ้า backend อยู่ IP อื่น
"""

import argparse
import json
import sys
import time

import httpx

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
GRAY   = "\033[90m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

DEVICE_ID = "pi4_home_001"
PASSED = 0
FAILED = 0


def check(label: str, response: httpx.Response, expected_status: int = 200):
    global PASSED, FAILED
    ok = response.status_code == expected_status
    icon = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
    code_color = GREEN if ok else RED
    print(f"  {icon}  {label:<45} {code_color}[{response.status_code}]{RESET}")
    if not ok:
        FAILED += 1
        try:
            print(f"     {GRAY}{response.json()}{RESET}")
        except Exception:
            print(f"     {GRAY}{response.text[:120]}{RESET}")
    else:
        PASSED += 1
    return ok


def section(title: str):
    print(f"\n  {BOLD}{CYAN}── {title} {'─'*(42-len(title))}{RESET}")


def run_tests(base_url: str):
    global PASSED, FAILED

    print(f"\n{'═'*60}")
    print(f"  {BOLD}AirGuard Pi — Pipeline Test{RESET}")
    print(f"  Backend: {CYAN}{base_url}{RESET}")
    print(f"{'═'*60}")

    client = httpx.Client(base_url=base_url, timeout=10)

    # ── 1. Health check ───────────────────────────────────────────
    section("Health & Root")
    r = client.get("/health")
    check("GET /health", r)
    if r.status_code == 200:
        print(f"     {GRAY}{r.json()}{RESET}")

    r = client.get("/")
    check("GET /  (root info)", r)
    if r.status_code == 200:
        d = r.json()
        print(f"     {GRAY}app={d.get('app')}  standard={d.get('standard')}{RESET}")

    # ── 2. Sensor endpoints ───────────────────────────────────────
    section("Sensor API")
    r = client.get(f"/api/sensor/latest/{DEVICE_ID}")
    check(f"GET /api/sensor/latest/{DEVICE_ID}", r)
    if r.status_code == 200 and "pm2_5" in (r.json() or {}):
        d = r.json()
        print(f"     {GRAY}PM2.5={d.get('pm2_5')} AQI={d.get('aqi')} Temp={d.get('temperature')}{RESET}")

    r = client.get(f"/api/sensor/history/{DEVICE_ID}?hours=1")
    check("GET /api/sensor/history  (1h)", r)
    if r.status_code == 200:
        d = r.json()
        print(f"     {GRAY}count={d.get('count')} records{RESET}")

    r = client.get(f"/api/sensor/daily-avg/{DEVICE_ID}?days=7")
    check("GET /api/sensor/daily-avg  (7d)", r)

    # ── 3. Fan control ────────────────────────────────────────────
    section("Fan Control API")
    r = client.post(f"/api/fan/set/{DEVICE_ID}", json={"speed": 60, "mode": "manual"})
    check("POST /api/fan/set  speed=60 manual", r)

    r = client.post(f"/api/fan/auto/{DEVICE_ID}")
    check("POST /api/fan/auto", r)

    r = client.post(f"/api/fan/off/{DEVICE_ID}")
    check("POST /api/fan/off", r)

    # validation: speed > 100 ต้องได้ 422
    r = client.post(f"/api/fan/set/{DEVICE_ID}", json={"speed": 999})
    check("POST /api/fan/set  speed=999  (expect 422)", r, expected_status=422)

    # ── 4. Alert rules ────────────────────────────────────────────
    section("Alert Rules API")
    rule_payload = {
        "device_id":    DEVICE_ID,
        "metric":       "pm2_5",
        "operator":     ">",
        "threshold":    37.5,
        "channel":      "line",
        "cooldown_min": 30,
        "owner_id":     1,
    }
    r = client.post("/api/alert/rules", json=rule_payload)
    check("POST /api/alert/rules  (create)", r)
    rule_id = None
    if r.status_code == 200:
        rule_id = r.json().get("id")
        print(f"     {GRAY}Created rule id={rule_id}{RESET}")

    r = client.get(f"/api/alert/rules/{DEVICE_ID}")
    check("GET  /api/alert/rules/{device_id}", r)
    if r.status_code == 200:
        print(f"     {GRAY}{len(r.json())} rules found{RESET}")

    r = client.get(f"/api/alert/logs/{DEVICE_ID}")
    check("GET  /api/alert/logs/{device_id}", r)

    if rule_id:
        r = client.delete(f"/api/alert/rules/{rule_id}")
        check(f"DELETE /api/alert/rules/{rule_id}", r)

    # ── 5. AI endpoints ───────────────────────────────────────────
    section("AI API")
    r = client.post("/api/ai/chat", json={"device_id": DEVICE_ID, "message": "ค่า PM2.5 ตอนนี้เป็นอย่างไร?"})
    if r.status_code == 503:
        print(f"  {YELLOW}⚠{RESET}  POST /api/ai/chat   {YELLOW}[503 — Ollama ไม่ได้เปิด, ปกติในการทดสอบ PC]{RESET}")
        PASSED += 1   # ถือว่า ok เพราะ Ollama อาจไม่ได้ติดตั้ง
    else:
        check("POST /api/ai/chat", r)
        if r.status_code == 200:
            print(f"     {GRAY}{str(r.json().get('response',''))[:80]}...{RESET}")

    r = client.get(f"/api/ai/predict/{DEVICE_ID}?hours_ahead=1")
    check("GET  /api/ai/predict/{device_id}", r)
    if r.status_code == 200:
        d = r.json()
        print(f"     {GRAY}predicted={d.get('predicted_pm25')} µg/m³{RESET}")

    # ── 6. Summary ────────────────────────────────────────────────
    total = PASSED + FAILED
    pct   = int(PASSED / total * 100) if total else 0
    color = GREEN if FAILED == 0 else (YELLOW if FAILED <= 2 else RED)

    print(f"\n{'═'*60}")
    print(f"  {BOLD}Results: {color}{PASSED}/{total} passed  ({pct}%){RESET}")
    if FAILED == 0:
        print(f"  {GREEN}{BOLD}✓ Pipeline ทำงานถูกต้องทุกขั้นตอน!{RESET}")
    else:
        print(f"  {RED}✗ มี {FAILED} endpoint ที่ต้องตรวจสอบ{RESET}")
    print(f"{'═'*60}\n")

    client.close()
    return FAILED == 0


def main():
    parser = argparse.ArgumentParser(description="Test AirGuard Pi backend pipeline")
    parser.add_argument("--base-url", "-u", default="http://localhost:8000",
                        help="Backend base URL (default: http://localhost:8000)")
    args = parser.parse_args()

    # รอให้ backend พร้อมก่อน
    print(f"\n  รอ backend พร้อม ({args.base_url})...")
    for attempt in range(10):
        try:
            r = httpx.get(f"{args.base_url}/health", timeout=3)
            if r.status_code == 200:
                break
        except Exception:
            pass
        print(f"  {GRAY}  attempt {attempt+1}/10 ...{RESET}")
        time.sleep(2)
    else:
        print(f"\n  {RED}✗ Backend ไม่ตอบสนอง — ตรวจสอบว่า docker compose up แล้ว{RESET}\n")
        sys.exit(1)

    ok = run_tests(args.base_url)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
