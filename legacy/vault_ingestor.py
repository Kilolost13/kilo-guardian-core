import os
import time
import requests
import logging
import shutil

# Configuration
VAULT_DIR = os.path.expanduser("~/Desktop/Kilo_Vault")
PROCESSED_DIR = os.path.join(VAULT_DIR, "processed")
BRAIN_URL = "http://localhost:9004/chat"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VaultIngestor")

def process_vault():
    if not os.path.exists(VAULT_DIR):
        logger.error(f"Vault directory {VAULT_DIR} not found.")
        return 0

    files = [f for f in os.listdir(VAULT_DIR) if os.path.isfile(os.path.join(VAULT_DIR, f))]
    
    if not files:
        logger.info("Vault is empty.")
        return 0

    processed_count = 0
    for filename in files:
        file_path = os.path.join(VAULT_DIR, filename)
        
        # Only process text-based files for now (Safe & Light)
        if filename.endswith(('.txt', '.md', '.log')):
            try:
                logger.info(f"Reading: {filename}")
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if content.strip():
                    # Send to AI Brain as a memory
                    # Using the /remember command format we built into the chat endpoint
                    payload = {"message": f"/remember FROM FILE ({filename}): {content}"}
                    response = requests.post(BRAIN_URL, json=payload, timeout=30)
                    
                    if response.status_code == 200:
                        logger.info(f"Successfully memorized {filename}")
                        # Move to processed folder
                        shutil.move(file_path, os.path.join(PROCESSED_DIR, filename))
                        processed_count += 1
                    else:
                        logger.error(f"Brain rejected memory: {response.text}")
                
                # POWER SAFETY: Mandatory cooldown between files to prevent CPU/Voltage spikes
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed to process {filename}: {e}")
        else:
            logger.warning(f"Skipping unsupported file type: {filename}")

    return processed_count

if __name__ == "__main__":
    count = process_vault()
    print(f"Sync Complete. Processed {count} files.")
