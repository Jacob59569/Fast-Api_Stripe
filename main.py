from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import stripe
from dotenv import load_dotenv
import os

load_dotenv()  # Загружаем переменные из .env

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Stripe + FastAPI = ❤️"}


@app.post("/create-checkout-session")
async def create_checkout_session():
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Coffee Mug",
                    },
                    "unit_amount": 1500,  # 15.00 USD
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url="http://localhost:8000/success",
            cancel_url="http://localhost:8000/cancel",
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
