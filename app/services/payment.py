"""
Payment processing with Stripe.
"""
import stripe
from flask import current_app
from app.models import Payment, db
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

def create_payment_intent(user_id: int, institution_id: int, amount: Decimal, 
                          currency: str = 'usd', description: str = '') -> dict:
    """
    Create a Stripe PaymentIntent and store payment record.
    """
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),  # cents
            currency=currency.lower(),
            metadata={'user_id': str(user_id), 'institution_id': str(institution_id)}
        )
        payment = Payment(
            user_id=user_id,
            institution_id=institution_id,
            amount=amount,
            currency=currency.upper(),
            stripe_payment_intent_id=intent.id,
            description=description,
            status='pending'
        )
        db.session.add(payment)
        db.session.commit()
        logger.info(f"PaymentIntent created: {intent.id} for user {user_id}")
        return {
            'client_secret': intent.client_secret,
            'payment_id': payment.id
        }
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        return {'error': str(e)}

def handle_webhook(payload: bytes, sig: str) -> dict:
    """
    Handle Stripe webhook events.
    """
    webhook_secret = current_app.config['STRIPE_WEBHOOK_SECRET']
    try:
        event = stripe.Webhook.construct_event(
            payload, sig, webhook_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.error(f"Webhook signature verification failed: {e}")
        return {'error': str(e)}

    logger.info(f"Stripe webhook received: {event['type']}")

    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        payment = Payment.query.filter_by(
            stripe_payment_intent_id=payment_intent['id']
        ).first()
        if payment:
            payment.status = 'completed'
            db.session.commit()
            # Trigger enrollment or subscription activation
            # (e.g., enroll user in course after payment)
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        payment = Payment.query.filter_by(
            stripe_payment_intent_id=payment_intent['id']
        ).first()
        if payment:
            payment.status = 'failed'
            db.session.commit()
    
    return {'status': 'success'}
