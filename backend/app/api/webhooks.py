"""
backend/app/api/webhooks.py — Stripe webhook (za primanje uplata).
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from backend.app.core import config

logger = logging.getLogger("eu_grants_api")

router = APIRouter()


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """
    Stripe šalje event kad neko plati.
    Ovaj endpoint prima taj event i loguje ga.
    Kad dodaš Supabase, ovdje ćeš upisati pretplatu u bazu.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # Ako Stripe ključevi nisu konfigurisani, loguj i vrati OK
    if not config.STRIPE_SECRET or not config.STRIPE_WEBHOOK_SECRET:
        logger.warning("⚠️ Stripe webhook primljen ali ključevi nisu konfigurisani.")
        return {"status": "received", "configured": False}

    try:
        import stripe
        stripe.api_key = config.STRIPE_SECRET
        event = stripe.Webhook.construct_event(
            payload, sig_header, config.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except Exception as e:
        logger.error(f"❌ Stripe webhook verifikacija: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # Obradi event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_email = session.get("customer_email", "unknown")
        amount = session.get("amount_total", 0) / 100  # centi → euri
        logger.info(f"💰 NOVA UPLATA: {customer_email} platio €{amount}")

        # TODO: Kad dodaš Supabase, upiši ovdje:
        # supabase.table("subscriptions").insert({
        #     "email": customer_email,
        #     "plan": determine_plan(amount),
        #     "status": "active",
        #     "stripe_session_id": session["id"]
        # }).execute()

    elif event["type"] == "customer.subscription.deleted":
        logger.info(f"🚫 Pretplata otkazana: {event['data']['object'].get('customer', 'unknown')}")

    return {"status": "ok"}
