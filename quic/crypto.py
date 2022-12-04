import os
from hashlib import sha256
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Diffie-Hellman parameters (2048-bit MODP group from RFC 3526)
P = 0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF
G = 2


def generate_private_key():
    return int.from_bytes(os.urandom(32), 'big')


def compute_public_key(private_key):
    return pow(G, private_key, P)


def compute_shared_secret(their_public, my_private):
    return pow(their_public, my_private, P)


def derive_aes_key(shared_secret):
    secret_bytes = shared_secret.to_bytes(256, 'big')
    return sha256(secret_bytes).digest()


def encrypt(key, plaintext):
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def decrypt(key, nonce_and_ciphertext):
    nonce = nonce_and_ciphertext[:12]
    ciphertext = nonce_and_ciphertext[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)
