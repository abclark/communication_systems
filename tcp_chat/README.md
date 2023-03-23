# Project Log: A Secure TCP Chat Application

This document logs the creation of a secure, multi-client TCP chat application
with end-to-end encryption.

https://github.com/user-attachments/assets/68519b19-c7f7-499a-b1c2-e1922bdc2da2

## 1. Project Progression

The project had four phases:

1.  **Basic TCP Chat:** I first built a multi-client chat application using
Python's `socket` and `threading` modules. It handled multiple, simultaneous
client connections and the core client-server workflow.

2.  **Transport Layer Security (TLS):** The second phase secured the transport
layer. I used `openssl` to generate a self-signed certificate and then used
Python's `ssl` module to wrap the server and client sockets, creating an
encrypted channel.

3.  **End-to-End Encryption (E2EE):** The third phase implemented a hybrid E2EE
system based on RSA and AES. This made messages unreadable by the server.

4.  **Code Refactoring:** The final phase improved the design. The refactoring
included:
    *   **Object-Oriented Design:** Converted the procedural scripts into
	`ChatClient` and `ChatServer` classes.
    *   **Stateful vs. Stateless Logic:** Abstracted stateless
	message-framing logic to a `protocol.py` module and stateful
cryptographic operations into a `CryptoHelper` class, which holds the keys it
needs to operate.

## 2. Final Architecture

The final system is a multi-client chat application with E2EE where the server
acts as a blind relayer.

*   **`ChatServer`:** Manages connections, assigns session IDs, and relays
    messages. It cannot decrypt any user-to-user communication.

*   **`ChatClient`:** Generates an ephemeral RSA key pair for the session and
    exchanges keys to get a shared secret. It then encrypts/decrypts all chat
messages.

*   **`protocol.py`:** Contains functions for message framing, wrapping all
    JSON messages with a 4-byte length header.

*   **`crypto_helper.py`:** Encapsulates all cryptographic logic, holding the
    client's private key and the group's shared symmetric key.

## 3. Core Concepts

#### Networking and Sockets
*   The application implements the full socket lifecycle (`socket`, `bind`,
    `listen`, `accept`, `connect`).
*   A custom, length-prefixing application-level protocol handles TCP as a
    stream-based protocol to ensure reliable message framing.

#### Concurrency
*   The `threading` module handles concurrent clients, preventing blocking I/O
    from stalling the server.
*   `threading.Lock` protects shared state (the dictionary of clients) from
    race conditions.

#### Software Design
*   The codebase uses an object-oriented design with classes for the client
    and server.
*   The design applies the Don't Repeat Yourself (DRY) principle by
    abstracting logic into stateless and stateful modules.

---

## 4. Cryptography Deep Dive: RSA and AES

### Asymmetric Encryption: RSA (Rivest-Shamir-Adleman)

The system uses RSA for securely exchanging the shared symmetric key.

**How RSA Keys Are Used**
*   **Encryption (Public Key):** `c = m^e (mod n)` **Decryption (Private
*   Key):** `m = c^d (mod n)` **Digital Signature (Signing):** `s = hash(m)^d
*   (mod n)` **Signature Verification:** Check if `hash(m) == s^e (mod n)`

**Key Generation Steps** 1.  Generate two distinct large prime numbers, `p` and
`q`.  2.  Compute the modulus, `n = p * q`.  3.  Compute `φ(n) = (p - 1) * (q -
1)`. This is **Euler's Totient Function**, which counts the positive integers
up to `n` that are relatively prime to `n`.  4.  Choose a public exponent `e`,
coprime to `φ(n)`.  5.  Compute the private exponent `d`, the modular
multiplicative inverse of `e` modulo `φ(n)`, satisfying `d * e ≡ 1 (mod φ(n))`.
The existence of `d` is guaranteed by **Bézout's Identity**, and it is
calculated using the **Extended Euclidean Algorithm**.

*   **Public Key:** `(n, e)` **Private Key:** `(n, d)`

**Proof of Correctness** Our goal is to prove that `(m^e)^d ≡ m (mod n)`.

*   This simplifies to `m^(ed) ≡ m (mod n)`.  From key generation, we can write
*   `ed` as `1 + kφ(n)` for some integer `k`.  Substituting this gives: `m^(1 +
*   kφ(n)) ≡ m (mod n)`.  This expression can be rewritten as `m * (m^φ(n))^k ≡
*   m (mod n)`.  Applying **Euler's Totient Theorem** (`m^φ(n) ≡ 1 (mod n)`)
*   gives us
    `m * (1)^k ≡ m (mod n)`, which simplifies to `m ≡ m (mod n)`. This proves
that decryption works for the general case.

**Foundational Mathematical Theorems**
*   **Bézout's Identity:** If `a` and `b` are integers with a greatest common
    divisor `g`, then there exist integers `x` and `y` such that `ax + by = g`.
For RSA, since `e` and `φ(n)` are chosen to be coprime (`g=1`), this guarantees
that an integer `d` exists to solve the congruence `d * e ≡ 1 (mod φ(n))`.

*   **Euler's Totient Theorem:** If `a` and `n` are coprime positive
    integers, then `a^φ(n) ≡ 1 (mod n)`. This is the core theorem that makes
RSA decryption work by allowing the large exponents to wrap around `φ(n)` and
cancel out, revealing the original message.

*   **Chinese Remainder Theorem (CRT):** States that if you know the
    remainders of an integer `x` when divided by several pairwise coprime
integers, you can determine the remainder of `x` when divided by their product.
This is used to prove that RSA still works in the edge case where `m` is not
coprime to `n`, and it also provides a major speed optimization for private key
operations.

### Symmetric Encryption: AES (Advanced Encryption Standard)

The system uses AES to efficiently encrypt chat data. It is a block cipher that
processes data in a series of rounds.

**AES Steps Per Round:**
*   **`SubBytes`:** A non-linear substitution using a lookup table (S-box).
*   **`ShiftRows`:** A permutation that shifts bytes in each row.
*   **`MixColumns`:** A permutation that mixes bytes within each column.
*   **`AddRoundKey`:** The round key is XORed with the internal state.

**Mode of Operation:**
*   **GCM (Galois/Counter Mode):** An **AEAD** (Authenticated Encryption with
    Associated Data) mode that provides both confidentiality and integrity.

---

## 5. `openssl` Command Reference

*   **Generate self-signed certificate and key:**
    ```bash openssl req -x509 -newkey rsa:2048 -nodes \ -keyout ssl/key.pem
-out ssl/cert.pem -days 365 \ -subj "/CN=localhost" ```
*   **View certificate contents:**
    ```bash openssl x509 -in ssl/cert.pem -text -noout ```
*   **View private key contents:**
    ```bash openssl rsa -in ssl/key.pem -text -noout ``` ---

## 6. Future Work

*   **Build a Minimal 1-to-1 E2EE Example:** Create a server-less chat that
    connects two peers directly to test the reusability of the `CryptoHelper`
and `protocol` modules.
*   **Implement a Custom TCP/IP Stack:** The original, long-term goal of
    this entire learning path.
*   **Study the Extended Euclidean Algorithm:** Fully understand the specific
    computational method used to calculate the RSA private exponent `d`.
