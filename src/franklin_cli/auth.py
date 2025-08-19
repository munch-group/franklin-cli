"""Authentication and encryption utilities for Franklin.

This module provides centralized encryption and authentication functionality
that can be used by both the core package and plugins.
"""

import base64
import os
from pathlib import Path
from typing import Optional, Union
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes


def derive_key(password: str, salt: bytes, iterations: int = 100_000) -> bytes:
    """
    Derive an encryption key from a password using PBKDF2.

    This function uses the Password-Based Key Derivation Function 2 (PBKDF2)
    algorithm to derive a cryptographically strong key from a password and salt.
    The derived key is suitable for use with AES encryption.

    Parameters
    ----------
    password : str
        The password string to derive the key from.
    salt : bytes
        Random salt bytes to prevent rainbow table attacks.
        Should be at least 16 bytes for security.
    iterations : int, default=100_000
        Number of iterations for the PBKDF2 algorithm.
        Higher values increase security but take more time.

    Returns
    -------
    bytes
        32-byte derived key suitable for AES-256 encryption.

    Examples
    --------
    >>> salt = get_random_bytes(16)
    >>> key = derive_key('my_password', salt)
    >>> len(key)
    32

    Notes
    -----
    - Uses SHA-256 as the underlying hash function (default for PBKDF2)
    - Produces a 32-byte key suitable for AES-256 encryption
    - The same password and salt will always produce the same key
    - Salt should be stored alongside encrypted data for decryption
    """
    return PBKDF2(password, salt, dkLen=32, count=iterations)


def encrypt_data(data: str, password: str) -> bytes:
    """
    Encrypt string data using AES-GCM with password-based key derivation.

    This function provides authenticated encryption using AES in Galois/Counter
    Mode (GCM). It automatically generates a random salt and nonce, derives an
    encryption key from the password, and returns all necessary components
    for decryption in a single byte string.

    Parameters
    ----------
    data : str
        The string data to encrypt.
    password : str
        The password to use for key derivation and encryption.

    Returns
    -------
    bytes
        Encrypted data containing salt, nonce, authentication tag, and
        ciphertext concatenated in that order:
        - bytes 0-15: salt (16 bytes)
        - bytes 16-31: nonce (16 bytes)
        - bytes 32-47: authentication tag (16 bytes)
        - bytes 48+: encrypted ciphertext

    Examples
    --------
    >>> encrypted = encrypt_data('secret message', 'my_password')
    >>> len(encrypted) >= 48  # minimum size with headers
    True

    Notes
    -----
    - Uses AES-256-GCM for authenticated encryption
    - Automatically generates random 16-byte salt and nonce
    - Authentication tag prevents tampering detection
    - UTF-8 encoding is used for string to bytes conversion
    - Each encryption produces different output due to random salt/nonce
    """
    salt = get_random_bytes(16)
    key = derive_key(password, salt)
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(data.encode())
    # Store: salt + nonce + tag + ciphertext
    return salt + cipher.nonce + tag + ciphertext


def decrypt_data(encrypted_data: bytes, password: str) -> str:
    """
    Decrypt data that was encrypted using encrypt_data.

    This function reverses the encryption performed by encrypt_data by
    extracting the salt, nonce, and authentication tag, deriving the
    decryption key, and performing authenticated decryption.

    Parameters
    ----------
    encrypted_data : bytes
        The encrypted data bytes as returned by encrypt_data.
        Must contain salt, nonce, tag, and ciphertext in the expected format.
    password : str
        The password used for the original encryption.

    Returns
    -------
    str
        The decrypted data as a UTF-8 decoded string.

    Raises
    ------
    ValueError
        If decryption fails due to:
        - Incorrect password
        - Corrupted or invalid encrypted data
        - Authentication tag verification failure
        - Malformed data structure

    Examples
    --------
    >>> encrypted = encrypt_data('secret message', 'my_password')
    >>> decrypted = decrypt_data(encrypted, 'my_password')
    >>> decrypted
    'secret message'

    Notes
    -----
    - Verifies authentication tag to detect tampering
    - Uses UTF-8 decoding for bytes to string conversion
    - Expects exact format produced by encrypt_data
    - Wrong password will raise ValueError, not return wrong data
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
    """
    Encrypt an API token using password-based encryption.

    This is a convenience wrapper around encrypt_data specifically for
    API tokens. It provides the same security guarantees with a more
    descriptive function name for token-specific use cases.

    Parameters
    ----------
    api_token : str
        The API token string to encrypt (e.g., GitLab personal access token).
    password : str
        The password to use for encryption.

    Returns
    -------
    bytes
        Encrypted token data suitable for secure storage.

    Examples
    --------
    >>> token = 'glpat-xxxxxxxxxxxxxxxxxxxx'
    >>> encrypted = encrypt_token(token, 'secure_password')
    >>> isinstance(encrypted, bytes)
    True

    Notes
    -----
    - Functionally identical to encrypt_data
    - Provided for semantic clarity in token management contexts
    - Uses same AES-GCM encryption with PBKDF2 key derivation
    """
    return encrypt_data(api_token, password)


def decrypt_token(token_encrypted: bytes, password: str) -> str:
    """
    Decrypt an API token that was encrypted using encrypt_token.

    This is a convenience wrapper around decrypt_data specifically for
    API tokens. It provides the same security guarantees with a more
    descriptive function name for token-specific use cases.

    Parameters
    ----------
    token_encrypted : bytes
        The encrypted token bytes as returned by encrypt_token.
    password : str
        The password used for the original encryption.

    Returns
    -------
    str
        The decrypted API token string.

    Raises
    ------
    ValueError
        If decryption fails due to incorrect password or corrupted data.

    Examples
    --------
    >>> encrypted = encrypt_token('glpat-xxxxxxxxxxxxxxxxxxxx', 'password')
    >>> decrypted = decrypt_token(encrypted, 'password')
    >>> decrypted.startswith('glpat-')
    True

    Notes
    -----
    - Functionally identical to decrypt_data
    - Provided for semantic clarity in token management contexts
    - Verifies authentication to prevent tampering
    """
    return decrypt_data(token_encrypted, password)


def get_encrypted_token_path(user: str, token_dir: Optional[Path] = None) -> Path:
    """
    Get the filesystem path for a user's encrypted token file.

    This function constructs the path where encrypted tokens are stored
    for a specific user. It ensures the token directory exists and follows
    Franklin's file naming conventions.

    Parameters
    ----------
    user : str
        The username for which to get the token path.
        Used as part of the filename.
    token_dir : Optional[Path], default=None
        The directory where tokens should be stored.
        If None, uses Franklin's default data directory + 'tokens'.

    Returns
    -------
    Path
        The complete path to the encrypted token file.
        Format: {token_dir}/{user}_token.enc

    Examples
    --------
    >>> path = get_encrypted_token_path('john.doe')
    >>> str(path).endswith('john.doe_token.enc')
    True
    
    >>> custom_dir = Path('/custom/tokens')
    >>> path = get_encrypted_token_path('jane', custom_dir)
    >>> path.parent == custom_dir
    True

    Notes
    -----
    - Creates the token directory if it doesn't exist
    - Uses '.enc' extension to indicate encrypted files
    - Follows pattern: {username}_token.enc
    - Directory creation is recursive (parents=True)
    """
    if token_dir is None:
        from franklin import config
        token_dir = Path(config.data_dir()) / "tokens"
    
    token_dir = Path(token_dir)
    token_dir.mkdir(parents=True, exist_ok=True)
    return token_dir / f"{user}_token.enc"


def store_encrypted_token(user: str, password: str, token: str, 
                         token_dir: Optional[Path] = None) -> None:
    """
    Encrypt and store an API token to disk.

    This function encrypts an API token using the provided password and
    stores it securely in the filesystem. The token can later be retrieved
    using get_api_token with the same user and password.

    Parameters
    ----------
    user : str
        The username to associate with this token.
    password : str
        The password to use for encrypting the token.
    token : str
        The API token to encrypt and store.
    token_dir : Optional[Path], default=None
        The directory where the encrypted token should be stored.
        If None, uses Franklin's default data directory.

    Returns
    -------
    None
        This function performs file I/O operations and has no return value.

    Examples
    --------
    >>> store_encrypted_token('john', 'password123', 'glpat-xxxxxxxxxxxxxxxxxxxx')
    >>> # Token is now stored encrypted on disk

    Notes
    -----
    - Overwrites any existing token file for the user
    - Creates the token directory if it doesn't exist
    - File is written in binary mode to preserve encryption bytes
    - No backup is created - existing tokens are replaced
    """
    encrypted = encrypt_token(token, password)
    token_path = get_encrypted_token_path(user, token_dir)
    
    with open(token_path, "wb") as f:
        f.write(encrypted)


def get_api_token(user: str, password: str, 
                  token_dir: Optional[Path] = None) -> str:
    """
    Retrieve and decrypt a stored API token.

    This function locates the encrypted token file for a user, reads the
    encrypted data, and decrypts it using the provided password to return
    the original API token.

    Parameters
    ----------
    user : str
        The username whose token should be retrieved.
    password : str
        The password used when the token was originally stored.
    token_dir : Optional[Path], default=None
        The directory where tokens are stored.
        If None, uses Franklin's default data directory.

    Returns
    -------
    str
        The decrypted API token string.

    Raises
    ------
    FileNotFoundError
        If no encrypted token file exists for the specified user.
    ValueError
        If decryption fails due to:
        - Incorrect password
        - Corrupted token file
        - Invalid encryption format

    Examples
    --------
    >>> # After storing a token
    >>> store_encrypted_token('john', 'password123', 'glpat-xxxxxxxxxxxxxxxxxxxx')
    >>> # Retrieve it later
    >>> token = get_api_token('john', 'password123')
    >>> token.startswith('glpat-')
    True

    Notes
    -----
    - Password must match the one used during storage
    - File is read in binary mode to handle encrypted bytes
    - Authentication prevents returning incorrect data on wrong password
    - Used by Franklin plugins to access stored credentials securely
    """
    token_path = get_encrypted_token_path(user, token_dir)
    
    if not token_path.exists():
        raise FileNotFoundError(f"No token found for user {user}")
    
    with open(token_path, "rb") as f:
        encrypted = f.read()
    
    return decrypt_token(encrypted, password)