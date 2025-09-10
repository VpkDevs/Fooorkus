"""
Enhanced Authentication Module for Fooorkus

Provides secure user authentication with improved security practices including:
- Secure password hashing with salt
- Rate limiting protection
- Input validation and sanitization
- Comprehensive error handling and logging
"""

import json
import hashlib
import hmac
import secrets
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from os.path import exists
from dataclasses import dataclass, field
from collections import defaultdict

import modules.constants as constants

# Set up logging for security events
logger = logging.getLogger(__name__)


@dataclass
class LoginAttempt:
    """Track login attempts for rate limiting."""
    timestamp: float
    success: bool
    ip_address: Optional[str] = None


@dataclass
class AuthConfig:
    """Configuration for authentication system."""
    max_login_attempts: int = 5
    lockout_duration: int = 300  # 5 minutes
    session_timeout: int = 3600  # 1 hour
    password_min_length: int = 8
    require_special_chars: bool = True


class AuthenticationManager:
    """Enhanced authentication manager with security features."""
    
    def __init__(self, config: Optional[AuthConfig] = None):
        self.config = config or AuthConfig()
        self.login_attempts: Dict[str, List[LoginAttempt]] = defaultdict(list)
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
    def _generate_salt(self) -> str:
        """Generate a cryptographically secure salt."""
        return secrets.token_hex(32)
    
    def _hash_password_with_salt(self, password: str, salt: str) -> str:
        """Create secure password hash with salt using PBKDF2."""
        try:
            # Use PBKDF2 with SHA-256 for better security
            password_bytes = password.encode('utf-8')
            salt_bytes = salt.encode('utf-8')
            
            # 100,000 iterations for good security vs performance balance
            hashed = hashlib.pbkdf2_hmac('sha256', password_bytes, salt_bytes, 100000)
            return hashed.hex()
        except Exception as e:
            logger.error(f"Password hashing failed: {e}")
            raise
    
    def _validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """Validate password meets security requirements."""
        if len(password) < self.config.password_min_length:
            return False, f"Password must be at least {self.config.password_min_length} characters"
        
        if self.config.require_special_chars:
            if not any(c.isdigit() for c in password):
                return False, "Password must contain at least one digit"
            if not any(c.isupper() for c in password):
                return False, "Password must contain at least one uppercase letter"
            if not any(c.islower() for c in password):
                return False, "Password must contain at least one lowercase letter"
            if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
                return False, "Password must contain at least one special character"
        
        return True, "Password meets requirements"
    
    def _is_rate_limited(self, username: str, ip_address: Optional[str] = None) -> bool:
        """Check if user/IP is rate limited due to failed attempts."""
        current_time = time.time()
        
        # Clean old attempts
        self._cleanup_old_attempts(username, current_time)
        
        # Count recent failed attempts
        recent_failures = sum(
            1 for attempt in self.login_attempts[username] 
            if not attempt.success and 
            current_time - attempt.timestamp < self.config.lockout_duration
        )
        
        return recent_failures >= self.config.max_login_attempts
    
    def _cleanup_old_attempts(self, username: str, current_time: float):
        """Remove old login attempts to prevent memory bloat."""
        cutoff_time = current_time - self.config.lockout_duration
        self.login_attempts[username] = [
            attempt for attempt in self.login_attempts[username]
            if attempt.timestamp > cutoff_time
        ]
    
    def _record_login_attempt(self, username: str, success: bool, ip_address: Optional[str] = None):
        """Record a login attempt for rate limiting."""
        attempt = LoginAttempt(
            timestamp=time.time(),
            success=success,
            ip_address=ip_address
        )
        self.login_attempts[username].append(attempt)
        
        # Log security events
        if success:
            logger.info(f"Successful login for user: {username}")
        else:
            logger.warning(f"Failed login attempt for user: {username}")


def auth_list_to_dict(auth_list: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    """
    Convert authentication list to dictionary with enhanced security.
    
    Args:
        auth_list: List of user authentication data
        
    Returns:
        Dictionary mapping usernames to auth data with salt and hash
        
    Raises:
        ValueError: If auth_list format is invalid
    """
    if not isinstance(auth_list, list):
        raise ValueError("auth_list must be a list")
    
    auth_dict = {}
    auth_manager = AuthenticationManager()
    
    for auth_data in auth_list:
        if not isinstance(auth_data, dict):
            logger.warning("Skipping invalid auth_data entry (not a dictionary)")
            continue
            
        if 'user' not in auth_data:
            logger.warning("Skipping auth_data entry without 'user' field")
            continue
        
        username = auth_data['user']
        
        # Validate username
        if not username or not isinstance(username, str):
            logger.warning(f"Skipping invalid username: {username}")
            continue
        
        # Handle existing hash with salt (new format)
        if 'hash' in auth_data and 'salt' in auth_data:
            auth_dict[username] = {
                'hash': auth_data['hash'],
                'salt': auth_data['salt']
            }
        # Handle plain password (legacy format) - convert to secure format
        elif 'pass' in auth_data:
            password = auth_data['pass']
            
            # Validate password strength for new entries
            is_valid, message = auth_manager._validate_password_strength(password)
            if not is_valid:
                logger.warning(f"Weak password for user {username}: {message}")
                # Still allow but warn - don't break existing setups
            
            salt = auth_manager._generate_salt()
            password_hash = auth_manager._hash_password_with_salt(password, salt)
            
            auth_dict[username] = {
                'hash': password_hash,
                'salt': salt
            }
        # Handle legacy hash-only format
        elif 'hash' in auth_data:
            # Keep legacy format but warn about security
            logger.warning(f"User {username} using legacy hash format without salt - consider upgrading")
            auth_dict[username] = {
                'hash': auth_data['hash'],
                'salt': None  # Legacy format indicator
            }
        else:
            logger.warning(f"Skipping user {username} - no valid password/hash found")
    
    return auth_dict


def load_auth_data(filename: Optional[str] = None) -> Optional[Dict[str, Dict[str, str]]]:
    """
    Load authentication data from file with enhanced error handling.
    
    Args:
        filename: Path to authentication file
        
    Returns:
        Authentication dictionary or None if loading fails
    """
    if filename is None or not exists(filename):
        logger.info("No authentication file found - authentication disabled")
        return None
    
    try:
        with open(filename, 'r', encoding='utf-8') as auth_file:
            auth_obj = json.load(auth_file)
            
            if not isinstance(auth_obj, list):
                logger.error("Authentication file must contain a list of user objects")
                return None
            
            if len(auth_obj) == 0:
                logger.warning("Authentication file is empty - authentication disabled")
                return None
            
            return auth_list_to_dict(auth_obj)
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in authentication file: {e}")
        return None
    except PermissionError as e:
        logger.error(f"Permission denied reading authentication file: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading authentication data: {e}")
        return None


# Global authentication state
auth_dict = load_auth_data(constants.AUTH_FILENAME)
auth_enabled = auth_dict is not None
auth_manager = AuthenticationManager() if auth_enabled else None


def check_auth(user: str, password: str, ip_address: Optional[str] = None) -> bool:
    """
    Enhanced authentication check with rate limiting and security features.
    
    Args:
        user: Username to authenticate
        password: Password to verify
        ip_address: Optional IP address for rate limiting
        
    Returns:
        True if authentication successful, False otherwise
    """
    if not auth_enabled or auth_dict is None or auth_manager is None:
        logger.warning("Authentication attempted but not enabled")
        return False
    
    # Input validation
    if not user or not password or not isinstance(user, str) or not isinstance(password, str):
        logger.warning("Invalid authentication input format")
        return False
    
    # Check rate limiting
    if auth_manager._is_rate_limited(user, ip_address):
        logger.warning(f"Rate limit exceeded for user: {user}")
        auth_manager._record_login_attempt(user, False, ip_address)
        return False
    
    # Check if user exists
    if user not in auth_dict:
        logger.warning(f"Authentication attempted for non-existent user: {user}")
        auth_manager._record_login_attempt(user, False, ip_address)
        return False
    
    user_auth = auth_dict[user]
    
    try:
        # Handle new format with salt
        if 'salt' in user_auth and user_auth['salt'] is not None:
            salt = user_auth['salt']
            expected_hash = user_auth['hash']
            provided_hash = auth_manager._hash_password_with_salt(password, salt)
            
            # Use constant-time comparison to prevent timing attacks
            is_valid = hmac.compare_digest(expected_hash, provided_hash)
        else:
            # Handle legacy format (less secure)
            expected_hash = user_auth['hash']
            provided_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            
            # Use constant-time comparison
            is_valid = hmac.compare_digest(expected_hash, provided_hash)
        
        # Record attempt
        auth_manager._record_login_attempt(user, is_valid, ip_address)
        
        return is_valid
        
    except Exception as e:
        logger.error(f"Error during authentication for user {user}: {e}")
        auth_manager._record_login_attempt(user, False, ip_address)
        return False


def get_auth_status() -> Dict[str, Any]:
    """
    Get current authentication system status.
    
    Returns:
        Dictionary with authentication system information
    """
    return {
        'enabled': auth_enabled,
        'users_count': len(auth_dict) if auth_dict else 0,
        'rate_limiting_enabled': auth_manager is not None,
        'config': auth_manager.config.__dict__ if auth_manager else None
    }
