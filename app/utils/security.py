"""
Security helpers: CSP nonce, etc.
"""
import secrets
from flask import request, g

def generate_nonce():
    """Generate a random nonce for CSP."""
    if 'csp_nonce' not in g:
        g.csp_nonce = secrets.token_urlsafe(16)
    return g.csp_nonce

def sanitize_input(data):
    """Basic input sanitization (can be expanded)."""
    if isinstance(data, str):
        # Remove any potentially dangerous characters
        return data.replace('<', '&lt;').replace('>', '&gt;')
    return data
