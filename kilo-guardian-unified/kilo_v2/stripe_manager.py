"""
Stripe Payment Integration for Bastion AI
Handles subscriptions, one-time purchases, and webhook events
"""

import logging
import os
from typing import Any, Dict, Optional

import stripe

from kilo_v2.auth_manager import auth_manager

logger = logging.getLogger(__name__)

# Load Stripe keys from environment
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
else:
    logger.warning("STRIPE_SECRET_KEY not set - payment features disabled")


class StripeManager:
    """Manages Stripe payments and subscriptions"""

    def __init__(self):
        self.enabled = bool(STRIPE_SECRET_KEY)

    def create_customer(
        self, email: str, name: str = None, metadata: dict = None
    ) -> Optional[str]:
        """
        Create a Stripe customer.

        Returns:
            Stripe customer ID or None
        """
        if not self.enabled:
            logger.warning("Stripe not configured")
            return None

        try:
            customer = stripe.Customer.create(
                email=email, name=name, metadata=metadata or {}
            )

            logger.info(f"Created Stripe customer: {customer.id} for {email}")
            return customer.id

        except Exception as e:
            logger.exception(f"Error creating Stripe customer: {e}")
            return None

    def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        metadata: dict = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a Stripe Checkout session for subscription or one-time payment.

        Returns:
            dict with checkout URL and session ID
        """
        if not self.enabled:
            return None

        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",  # or 'payment' for one-time
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata or {},
            )

            logger.info(f"Created checkout session: {session.id}")

            return {"session_id": session.id, "checkout_url": session.url}

        except Exception as e:
            logger.exception(f"Error creating checkout session: {e}")
            return None

    def create_payment_intent(
        self,
        amount: int,
        currency: str = "usd",
        customer_id: str = None,
        metadata: dict = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a payment intent for one-time purchases (marketplace items).

        Args:
            amount: Amount in cents (e.g., 2999 = $29.99)
            currency: Currency code (default: usd)

        Returns:
            dict with client_secret and payment_intent_id
        """
        if not self.enabled:
            return None

        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                customer=customer_id,
                metadata=metadata or {},
            )

            logger.info(f"Created payment intent: {intent.id} for ${amount/100:.2f}")

            return {
                "payment_intent_id": intent.id,
                "client_secret": intent.client_secret,
            }

        except Exception as e:
            logger.exception(f"Error creating payment intent: {e}")
            return None

    def handle_webhook(
        self, payload: bytes, signature: str
    ) -> Optional[Dict[str, Any]]:
        """
        Handle Stripe webhook events.

        Returns:
            dict with event details or None if invalid
        """
        if not self.enabled or not STRIPE_WEBHOOK_SECRET:
            logger.warning("Stripe webhook not configured")
            return None

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, STRIPE_WEBHOOK_SECRET
            )

            logger.info(f"Received Stripe webhook: {event['type']}")

            # Handle different event types
            if event["type"] == "checkout.session.completed":
                return self._handle_checkout_completed(event["data"]["object"])

            elif event["type"] == "customer.subscription.updated":
                return self._handle_subscription_updated(event["data"]["object"])

            elif event["type"] == "customer.subscription.deleted":
                return self._handle_subscription_deleted(event["data"]["object"])

            elif event["type"] == "payment_intent.succeeded":
                return self._handle_payment_succeeded(event["data"]["object"])

            elif event["type"] == "payment_intent.payment_failed":
                return self._handle_payment_failed(event["data"]["object"])

            return {"event_type": event["type"], "handled": False}

        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            return None
        except Exception as e:
            logger.exception(f"Error handling webhook: {e}")
            return None

    def _handle_checkout_completed(self, session: Dict) -> Dict[str, Any]:
        """Handle successful checkout - create account or upgrade subscription"""
        customer_id = session.get("customer")
        customer_email = session.get("customer_details", {}).get("email")
        subscription_id = session.get("subscription")
        metadata = session.get("metadata", {})

        logger.info(f"Checkout completed for {customer_email}")

        # Check if this is a new user purchase (metadata will have signup=true)
        if metadata.get("signup") == "true":
            # Create user account
            # Generate temporary password and email it to user
            import secrets

            temp_password = secrets.token_urlsafe(12)

            result = auth_manager.create_user(
                email=customer_email,
                password=temp_password,
                full_name=metadata.get("name"),
                stripe_customer_id=customer_id,
            )

            if result["success"]:
                # Update subscription status
                auth_manager.update_subscription(
                    user_id=result["user_id"],
                    tier=metadata.get("tier", "pro"),
                    status="active",
                )

                # TODO: Send welcome email with login credentials
                logger.info(f"Created account for new customer: {customer_email}")

                return {
                    "event_type": "checkout.session.completed",
                    "action": "account_created",
                    "user_id": result["user_id"],
                    "email": customer_email,
                }

        return {"event_type": "checkout.session.completed", "handled": True}

    def _handle_subscription_updated(self, subscription: Dict) -> Dict[str, Any]:
        """Handle subscription changes"""
        customer_id = subscription.get("customer")
        status = subscription.get("status")

        # Find user by Stripe customer ID and update
        # TODO: Add method to auth_manager to find user by stripe_customer_id

        logger.info(f"Subscription updated: {customer_id} - {status}")
        return {"event_type": "subscription.updated", "handled": True}

    def _handle_subscription_deleted(self, subscription: Dict) -> Dict[str, Any]:
        """Handle subscription cancellation"""
        customer_id = subscription.get("customer")

        # Update user to free tier
        logger.info(f"Subscription cancelled: {customer_id}")
        return {"event_type": "subscription.deleted", "handled": True}

    def _handle_payment_succeeded(self, payment_intent: Dict) -> Dict[str, Any]:
        """Handle successful one-time payment (marketplace purchase)"""
        amount = payment_intent.get("amount")
        customer_id = payment_intent.get("customer")
        metadata = payment_intent.get("metadata", {})

        # Record purchase in database
        # metadata should contain: user_id, item_type, item_id
        user_id = metadata.get("user_id")
        if user_id:
            auth_manager.record_purchase(
                user_id=int(user_id),
                item_type=metadata.get("item_type", "unknown"),
                item_id=metadata.get("item_id", "unknown"),
                amount=amount / 100,  # Convert cents to dollars
                stripe_payment_id=payment_intent["id"],
            )

        logger.info(f"Payment succeeded: ${amount/100:.2f} for user {user_id}")
        return {"event_type": "payment.succeeded", "handled": True}

    def _handle_payment_failed(self, payment_intent: Dict) -> Dict[str, Any]:
        """Handle failed payment"""
        logger.warning(f"Payment failed: {payment_intent['id']}")
        return {"event_type": "payment.failed", "handled": True}

    def get_customer_subscriptions(self, customer_id: str) -> list:
        """Get all subscriptions for a customer"""
        if not self.enabled:
            return []

        try:
            subscriptions = stripe.Subscription.list(customer=customer_id)
            return [
                {
                    "id": sub.id,
                    "status": sub.status,
                    "current_period_end": sub.current_period_end,
                    "plan": sub.plan.nickname if sub.plan else None,
                }
                for sub in subscriptions.data
            ]
        except Exception as e:
            logger.exception(f"Error fetching subscriptions: {e}")
            return []

    def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription"""
        if not self.enabled:
            return False

        try:
            stripe.Subscription.delete(subscription_id)
            logger.info(f"Cancelled subscription: {subscription_id}")
            return True
        except Exception as e:
            logger.exception(f"Error cancelling subscription: {e}")
            return False


# Global instance
stripe_manager = StripeManager()
