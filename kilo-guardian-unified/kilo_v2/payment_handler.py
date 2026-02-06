"""
Payment Integration - Stripe Webhook Handler

Handles Stripe webhooks for subscription management:
- subscription.created
- subscription.updated
- subscription.deleted
- invoice.payment_succeeded
- invoice.payment_failed
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

logger = logging.getLogger("PaymentHandler")


class StripeWebhookHandler:
    """Handles Stripe webhook events for subscription management"""

    def __init__(self, webhook_secret: str = None):
        self.webhook_secret = webhook_secret or ""
        self.license_file = Path("/var/lib/bastion/license.json")

    def verify_signature(self, payload: bytes, signature: str, timestamp: str) -> bool:
        """Verify Stripe webhook signature"""
        if not self.webhook_secret:
            logger.warning("No webhook secret configured, skipping verification")
            return True

        try:
            # Construct signed payload
            signed_payload = f"{timestamp}.{payload.decode()}"

            # Calculate expected signature
            expected = hmac.new(
                self.webhook_secret.encode(), signed_payload.encode(), hashlib.sha256
            ).hexdigest()

            # Compare signatures
            return hmac.compare_digest(signature, f"v1={expected}")

        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

    def handle_webhook(self, event_type: str, data: Dict) -> Dict:
        """Handle incoming webhook event"""
        try:
            if event_type == "customer.subscription.created":
                return self._handle_subscription_created(data)
            elif event_type == "customer.subscription.updated":
                return self._handle_subscription_updated(data)
            elif event_type == "customer.subscription.deleted":
                return self._handle_subscription_deleted(data)
            elif event_type == "invoice.payment_succeeded":
                return self._handle_payment_succeeded(data)
            elif event_type == "invoice.payment_failed":
                return self._handle_payment_failed(data)
            else:
                return {
                    "success": True,
                    "message": f"Unhandled event type: {event_type}",
                }

        except Exception as e:
            logger.error(f"Webhook handling failed: {e}")
            return {"success": False, "error": str(e)}

    def _handle_subscription_created(self, data: Dict) -> Dict:
        """Handle new subscription"""
        try:
            subscription = data["object"]
            customer_email = data.get("customer_email", "")

            # Extract subscription details
            plan_id = subscription["items"]["data"][0]["price"]["id"]
            tier = self._map_plan_to_tier(plan_id)

            # Calculate expiration
            current_period_end = subscription["current_period_end"]
            expires_at = datetime.fromtimestamp(current_period_end).isoformat()

            # Update license
            license_data = self._load_license()
            license_data.update(
                {
                    "tier": tier,
                    "status": "active",
                    "customer_email": customer_email,
                    "subscription_id": subscription["id"],
                    "stripe_customer_id": subscription["customer"],
                    "expires_at": expires_at,
                    "updated_at": datetime.now().isoformat(),
                }
            )
            self._save_license(license_data)

            logger.info(f"Subscription created: {tier} tier for {customer_email}")

            return {"success": True, "tier": tier}

        except Exception as e:
            logger.error(f"Failed to handle subscription.created: {e}")
            return {"success": False, "error": str(e)}

    def _handle_subscription_updated(self, data: Dict) -> Dict:
        """Handle subscription update (upgrade/downgrade)"""
        try:
            subscription = data["object"]

            # Extract new plan
            plan_id = subscription["items"]["data"][0]["price"]["id"]
            tier = self._map_plan_to_tier(plan_id)

            # Update expiration
            current_period_end = subscription["current_period_end"]
            expires_at = datetime.fromtimestamp(current_period_end).isoformat()

            # Get subscription status
            status = subscription["status"]  # active, past_due, canceled, etc.

            # Update license
            license_data = self._load_license()
            license_data.update(
                {
                    "tier": tier,
                    "status": status,
                    "expires_at": expires_at,
                    "updated_at": datetime.now().isoformat(),
                }
            )
            self._save_license(license_data)

            logger.info(f"Subscription updated: {tier} tier, status: {status}")

            return {"success": True, "tier": tier, "status": status}

        except Exception as e:
            logger.error(f"Failed to handle subscription.updated: {e}")
            return {"success": False, "error": str(e)}

    def _handle_subscription_deleted(self, data: Dict) -> Dict:
        """Handle subscription cancellation"""
        try:
            subscription = data["object"]

            # Downgrade to free tier
            license_data = self._load_license()
            license_data.update(
                {
                    "tier": "free",
                    "status": "active",
                    "expires_at": None,
                    "subscription_id": None,
                    "updated_at": datetime.now().isoformat(),
                    "downgraded_at": datetime.now().isoformat(),
                    "previous_tier": license_data.get("tier", "unknown"),
                }
            )
            self._save_license(license_data)

            logger.info("Subscription deleted, downgraded to free tier")

            return {"success": True, "tier": "free"}

        except Exception as e:
            logger.error(f"Failed to handle subscription.deleted: {e}")
            return {"success": False, "error": str(e)}

    def _handle_payment_succeeded(self, data: Dict) -> Dict:
        """Handle successful payment"""
        try:
            invoice = data["object"]
            subscription_id = invoice.get("subscription")

            if not subscription_id:
                return {"success": True, "message": "No subscription associated"}

            # Update license expiration
            license_data = self._load_license()

            if license_data.get("subscription_id") == subscription_id:
                # Extend license by billing period (usually 30 days)
                period_end = invoice.get("period_end")
                if period_end:
                    expires_at = datetime.fromtimestamp(period_end).isoformat()
                    license_data["expires_at"] = expires_at
                    license_data["status"] = "active"
                    license_data["last_payment_at"] = datetime.now().isoformat()
                    self._save_license(license_data)

                    logger.info(f"Payment succeeded, license extended to {expires_at}")

            return {"success": True}

        except Exception as e:
            logger.error(f"Failed to handle payment.succeeded: {e}")
            return {"success": False, "error": str(e)}

    def _handle_payment_failed(self, data: Dict) -> Dict:
        """Handle failed payment"""
        try:
            invoice = data["object"]
            subscription_id = invoice.get("subscription")

            if not subscription_id:
                return {"success": True, "message": "No subscription associated"}

            # Mark license as suspended
            license_data = self._load_license()

            if license_data.get("subscription_id") == subscription_id:
                license_data["status"] = "suspended"
                license_data["payment_failed_at"] = datetime.now().isoformat()
                self._save_license(license_data)

                logger.warning(f"Payment failed for subscription {subscription_id}")

            return {"success": True, "action": "suspended"}

        except Exception as e:
            logger.error(f"Failed to handle payment.failed: {e}")
            return {"success": False, "error": str(e)}

    def _map_plan_to_tier(self, plan_id: str) -> str:
        """Map Stripe plan ID to license tier"""
        # Map your Stripe price IDs to tiers
        PLAN_MAPPING = {
            "price_pro_monthly": "pro",
            "price_pro_yearly": "pro",
            "price_business_monthly": "business",
            "price_business_yearly": "business",
        }

        return PLAN_MAPPING.get(plan_id, "free")

    def _load_license(self) -> Dict:
        """Load license data"""
        if self.license_file.exists():
            with open(self.license_file, "r") as f:
                return json.load(f)
        return {}

    def _save_license(self, data: Dict):
        """Save license data"""
        self.license_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.license_file, "w") as f:
            json.dump(data, f, indent=2)


def create_stripe_checkout_session(
    tier: str, customer_email: str, bastion_id: str
) -> Dict:
    """
    Create Stripe checkout session for subscription

    This would be called from your billing portal/website, not from the appliance.
    The appliance only receives webhooks after successful purchase.
    """
    try:
        import stripe
        from config import STRIPE_PRICE_IDS, STRIPE_SECRET_KEY

        stripe.api_key = STRIPE_SECRET_KEY

        # Get price ID for tier
        price_id = STRIPE_PRICE_IDS.get(tier)
        if not price_id:
            return {"success": False, "error": f"Unknown tier: {tier}"}

        # Create checkout session
        session = stripe.checkout.Session.create(
            customer_email=customer_email,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=f"https://bastion.ai/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url="https://bastion.ai/canceled",
            metadata={"bastion_id": bastion_id, "tier": tier},
        )

        return {"success": True, "checkout_url": session.url, "session_id": session.id}

    except Exception as e:
        logger.error(f"Failed to create checkout session: {e}")
        return {"success": False, "error": str(e)}


def cancel_subscription(subscription_id: str) -> Dict:
    """Cancel a Stripe subscription"""
    try:
        import stripe
        from config import STRIPE_SECRET_KEY

        stripe.api_key = STRIPE_SECRET_KEY

        # Cancel at period end (don't immediately revoke access)
        subscription = stripe.Subscription.modify(
            subscription_id, cancel_at_period_end=True
        )

        return {
            "success": True,
            "canceled": True,
            "cancel_at": datetime.fromtimestamp(subscription.cancel_at).isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to cancel subscription: {e}")
        return {"success": False, "error": str(e)}
