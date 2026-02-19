from flask import Blueprint, request, jsonify, current_app
from app.services.payment import handle_webhook
import stripe
import logging

bp = Blueprint('webhooks', __name__)
logger = logging.getLogger(__name__)

@bp.route('/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, current_app.config['STRIPE_WEBHOOK_SECRET']
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        from app.services.payment import handle_webhook as payment_webhook
        result = payment_webhook(payload, sig_header)  # but we already constructed event
        # Actually we need to update payment status
        from app.models import Payment, db
        payment = Payment.query.filter_by(stripe_payment_intent_id=payment_intent['id']).first()
        if payment:
            payment.status = 'completed'
            db.session.commit()
            logger.info(f"Payment {payment.id} completed")
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        payment = Payment.query.filter_by(stripe_payment_intent_id=payment_intent['id']).first()
        if payment:
            payment.status = 'failed'
            db.session.commit()
            logger.info(f"Payment {payment.id} failed")

    return jsonify({'status': 'success'}), 200
