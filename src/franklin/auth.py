"""Authentication and encryption utilities for Franklin.

This module provides centralized encryption and authentication functionality
that can be used by both the core package and plugins.
"""

import base64
import os
from pathlib import Path
from typing import Optional
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes


def derive_key(password: str, salt: bytes, iterations: int = 100_000) -> bytes:
    """Derive an encryption key from a password using PBKDF2.
    
    Args:
        password: The password to derive from.
        salt: Salt bytes for the derivation.
        iterations: Number of iterations for PBKDF2.
    
    Returns:
        Derived key bytes.
    """
    return PBKDF2(password, salt, dkLen=32, count=iterations)


def encrypt_data(data: str, password: str) -> bytes:
    """Encrypt data using AES-GCM with a password-derived key.
    
    Args:
        data: The data to encrypt.
        password: Password to use for encryption.
    
    Returns:
        Encrypted data with salt, nonce, tag, and ciphertext.
    """
    salt = get_random_bytes(16)
    key = derive_key(password, salt)
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(data.encode())
    # Store: salt + nonce + tag + ciphertext
    return salt + cipher.nonce + tag + ciphertext


def decrypt_data(encrypted_data: bytes, password: str) -> str:
    """Decrypt data that was encrypted with encrypt_data.
    
    Args:
        encrypted_data: The encrypted data bytes.
        password: Password to use for decryption.
    
    Returns:
        Decrypted data as a string.
    
    Raises:
        ValueError: If decryption fails.
    """
    try:
        salt = encrypted_data[:16]
        nonce = encrypted_data[16:32]
        tag = encrypted_data[32:48]
        ciphertext = encrypted_data[48:]
        key = derive_key(password, salt)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag).decode()
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}")


def encrypt_token(api_token: str, password: str) -> bytes:
    """Encrypt an API token.
    
    Args:
        api_token: The API token to encrypt.
        password: Password to use for encryption.
    
    Returns:
        Encrypted token bytes.
    """
    return encrypt_data(api_token, password)


def decrypt_token(token_encrypted: bytes, password: str) -> str:
    """Decrypt an API token.
    
    Args:
        token_encrypted: The encrypted token bytes.
        password: Password to use for decryption.
    
    Returns:
        Decrypted API token.
    """
    return decrypt_data(token_encrypted, password)


def get_encrypted_token_path(user: str, token_dir: Optional[Path] = None) -> Path:
    """Get the path for a user's encrypted token file.
    
    Args:
        user: Username for the token.
        token_dir: Optional directory for token storage.
                  Defaults to Franklin's data directory.
    
    Returns:
        Path to the encrypted token file.
    """
    if token_dir is None:
        from franklin import config
        token_dir = Path(config.data_dir()) / "tokens"
    
    token_dir = Path(token_dir)
    token_dir.mkdir(parents=True, exist_ok=True)
    return token_dir / f"{user}_token.enc"


def store_encrypted_token(user: str, password: str, token: str, 
                         token_dir: Optional[Path] = None) -> None:
    """Store an encrypted API token.
    
    Args:
        user: Username for the token.
        password: Password to use for encryption.
        token: The API token to store.
        token_dir: Optional directory for token storage.
    """
    encrypted = encrypt_token(token, password)
    token_path = get_encrypted_token_path(user, token_dir)
    
    with open(token_path, "wb") as f:
        f.write(encrypted)


def get_api_token(user: str, password: str, 
                  token_dir: Optional[Path] = None) -> str:
    """Retrieve and decrypt an API token.
    
    Args:
        user: Username for the token.
        password: Password to use for decryption.
        token_dir: Optional directory for token storage.
    
    Returns:
        Decrypted API token.
    
    Raises:
        FileNotFoundError: If the token file doesn't exist.
        ValueError: If decryption fails.
    """
    token_path = get_encrypted_token_path(user, token_dir)
    
    if not token_path.exists():
        raise FileNotFoundError(f"No token found for user {user}")
    
    with open(token_path, "rb") as f:
        encrypted = f.read()
    
    return decrypt_token(encrypted, password)