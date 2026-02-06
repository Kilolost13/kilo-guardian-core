import base64
import json
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


# Implementation of Secure Secret Handling [cite: 94]
class KiloVault:
    def __init__(self, master_password):
        self.file_path = "kilo_secrets.enc"
        self.salt_file_path = "kilo_salt.bin"
        self._load_salt()
        if self.salt is None:
            self.salt = os.urandom(16)
            self._save_salt()
        self.key = self._derive_key(master_password, self.salt)
        self.fernet = Fernet(self.key)
        self.secrets = self._load_vault()

    def _derive_key(self, password, salt):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def _load_salt(self):
        if os.path.exists(self.salt_file_path):
            with open(self.salt_file_path, "rb") as f:
                self.salt = f.read()
        else:
            self.salt = None

    def _save_salt(self):
        with open(self.salt_file_path, "wb") as f:
            f.write(self.salt)

    def _load_vault(self):
        if not os.path.exists(self.file_path):
            return {}
        try:
            with open(self.file_path, "rb") as f:
                encrypted_data = f.read()
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data)
        except Exception as e:
            print(f"CRITICAL: Vault corruption or wrong password: {e}")
            return {}

    def save_vault(self):
        encrypted_data = self.fernet.encrypt(json.dumps(self.secrets).encode())
        with open(self.file_path, "wb") as f:
            f.write(encrypted_data)

    def get_secret(self, key):
        return self.secrets.get(key)

    def set_secret(self, key, value):
        self.secrets[key] = value
        self.save_vault()
