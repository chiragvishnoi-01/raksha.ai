"""RAKSHA AI - Live Endpoint Verification"""
import requests
import time

def main():
    base_url = "http://127.0.0.1:8000"
    
    # 1. Dashboard
    r1 = requests.get(f"{base_url}/")
    print(f"1. Dashboard HTML status: {r1.status_code}")
    assert r1.status_code == 200, "Dashboard failed to load"
    assert "RAKSHA" in r1.text, "RAKSHA branding not found in HTML"

    # 2. Telemetry
    r2 = requests.get(f"{base_url}/api/telemetry")
    print(f"2. Telemetry JSON status: {r2.status_code}")
    print(f"   Telemetry data: {r2.json()}")
    assert r2.status_code == 200

    # 3. Trigger Simulated Collision
    r3 = requests.post(f"{base_url}/api/simulate-collision")
    print(f"3. Simulated collision trigger status: {r3.status_code}")
    sim_data = r3.json()
    incident_id = sim_data["incident"]["incident_id"]
    print(f"   Created Incident ID: {incident_id}")
    assert r3.status_code == 200

    time.sleep(1.5)

    # 4. Check Incidents Archive
    r4 = requests.get(f"{base_url}/api/incidents")
    print(f"4. Incidents archive status: {r4.status_code}")
    incidents = r4.json()
    print(f"   Total logged incidents in DB: {len(incidents)}")
    assert len(incidents) > 0, "No incidents found in DB"
    first = incidents[0]
    print(f"   Latest Incident in DB: {first['incident_id']} | Severity: {first['severity']} | Hospital: {first['hospital_name']}")

    # 5. Download Generated PDF Report
    r5 = requests.get(f"{base_url}/api/reports/{first['incident_id']}/pdf")
    print(f"5. PDF Report endpoint status: {r5.status_code}")
    print(f"   PDF content-type: {r5.headers.get('content-type')} | size: {len(r5.content)} bytes")
    assert r5.status_code == 200
    assert r5.headers.get("content-type") == "application/pdf"
    assert len(r5.content) > 1000

    # 6. Check Screenshot Evidence endpoint
    r6 = requests.get(f"{base_url}/api/screenshots/{first['incident_id']}")
    print(f"6. Screenshot evidence endpoint status: {r6.status_code}")
    print(f"   Screenshot size: {len(r6.content)} bytes")
    assert r6.status_code == 200

    print("\n=======================================================")
    print(" ALL LIVE FASTAPI ENDPOINTS VERIFIED SUCCESSFULLY! ")
    print("=======================================================")

if __name__ == "__main__":
    main()
