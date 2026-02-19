"""Paystack payment integration for Nigerian institutions."""
import requests
from flask import current_app


def initialize_payment(email: str, amount: int, reference: str = None, metadata: dict = None) -> dict:
    """Initialize Paystack transaction."""
    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {current_app.config['PAYSTACK_SECRET_KEY']}",
        "Content-Type": "application/json"
    }
    data = {
        "email": email,
        "amount": amount,  # in kobo
        "reference": reference,
        "metadata": metadata
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()


def verify_payment(reference: str) -> dict:
    """Verify Paystack transaction."""
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {current_app.config['PAYSTACK_SECRET_KEY']}"}
    response = requests.get(url, headers=headers)
    return response.json()
