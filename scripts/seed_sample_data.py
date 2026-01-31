import os
import requests

GATEWAY = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8001")

print("Seeding sample data via gateway...")

# Sample meds
med = {
    "name": "Aspirin",
    "schedule": "08:00",
    "dosage": "100mg",
    "quantity": 30,
    "prescriber": "Dr. Example",
    "instructions": "Take with water"
}
resp = requests.post(f"{GATEWAY}/ai_brain/ingest/meds", json=med)
print("meds:", resp.status_code, resp.text)

# Sample finance
fin = {"amount": 12.5, "description": "Coffee", "date": "2025-12-16"}
resp = requests.post(f"{GATEWAY}/ai_brain/ingest/finance", json=fin)
print("finance:", resp.status_code, resp.text)

# Sample receipt
receipt = {"text": "Milk 2.50\nBread 1.90\nEggs 3.00"}
resp = requests.post(f"{GATEWAY}/ai_brain/ingest/receipt", json=receipt)
print("receipt:", resp.status_code, resp.text)

# Sample cam observation
obs = {"timestamp": "2025-12-16T12:00:00", "posture": "sitting", "pose_match": True}
resp = requests.post(f"{GATEWAY}/ai_brain/ingest/cam", json=obs)
print("cam:", resp.status_code, resp.text)

print("Seeding completed")
