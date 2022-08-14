import os
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class CryptoHelper:
    def __init__(self, private_key):
        self.private_key = private_key
        self.k_group = None

    def set_group_key(self, k_group):
        self.k_group = k_group

    def get_group_key(self):
        return self.k_group

    def decrypt_group_key(self, encrypted_k_group_b64):
        encrypted_k_group = base64.b64decode(encrypted_k_group_b64)
        decrypted_k_group = self.private_key.decrypt(
            encrypted_k_group,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        self.set_group_key(decrypted_k_group)
        return decrypted_k_group

    def encrypt_group_key_for(self, k_group, recipient_pubkey):
        encrypted_k_group = recipient_pubkey.encrypt(
            k_group,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return base64.b64encode(encrypted_k_group).decode('utf-8')

    def encrypt_chat_message(self, plaintext_str):
        if not self.k_group:
            return None, None
        
        nonce = os.urandom(12)
        aesgcm = AESGCM(self.k_group)
        ciphertext = aesgcm.encrypt(nonce, plaintext_str.encode('utf-8'), None)
        
        encoded_nonce = base64.b64encode(nonce).decode('utf-8')
        encoded_ciphertext = base64.b64encode(ciphertext).decode('utf-8')
        return encoded_nonce, encoded_ciphertext

    def decrypt_chat_message(self, nonce_b64, ciphertext_b64):
        if not self.k_group:
            return None
        
        nonce = base64.b64decode(nonce_b64)
        ciphertext = base64.b64decode(ciphertext_b64)
        aesgcm = AESGCM(self.k_group)
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted_bytes.decode('utf-8')
