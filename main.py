import uvicorn
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, Request, HTTPException, Form
import stripe
import os
from dotenv import load_dotenv
from database import database, payments  # импорт из database.py
import datetime
from pydantic import BaseModel
from email_utils import send_payment_email

load_dotenv()  # Загружаем переменные из .env

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

app = FastAPI()

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


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
            success_url="https://jacob-python.ru/success",
            cancel_url="https://jacob-python.ru/cancel",
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        query = payments.insert().values(
            session_id=session["id"],
            customer_email=session["customer_details"]["email"],
            amount=session["amount_total"],
            currency=session["currency"],
            created_at=datetime.datetime.utcnow()
        )
        await database.execute(query)
        print("✅ Платёж сохранён в базу")

        # send_payment_email(
        #     to_email=session["customer_details"]["email"],
        #     amount=session["amount_total"],
        #     currency=session["currency"]
        # )

        print("📧 Email отправлен клиенту")

    return {"status": "success"}

templates = Jinja2Templates(directory="templates")



# Страница успеха
@app.get("/success", response_class=HTMLResponse)
async def success(request: Request):
    return templates.TemplateResponse("success.html", {"request": request})

# Страница отмены
@app.get("/cancel", response_class=HTMLResponse)
async def cancel(request: Request):
    return templates.TemplateResponse("cancel.html", {"request": request})

@app.get("/payments")
async def get_payments():
    query = payments.select().order_by(payments.c.created_at.desc())
    result = await database.fetch_all(query)

    # Преобразуем для удобства
    return [
        {
            "id": row["id"],
            "session_id": row["session_id"],
            "email": row["customer_email"],
            "amount_usd": f"${row['amount'] / 100:.2f}",
            "currency": row["currency"].upper(),
            "created_at": row["created_at"].isoformat()
        }
        for row in result
    ]

@app.get("/payments_html", response_class=HTMLResponse)
async def get_payments_html(request: Request):
    query = payments.select().order_by(payments.c.created_at.desc())
    result = await database.fetch_all(query)
    return templates.TemplateResponse("payments.html", {"request": request, "payments": result})


# Отдаём главную страницу
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    products = [
        {"name": "Coffee Mug", "price_cents": 1500},
        {"name": "T-Shirt", "price_cents": 2500},
        {"name": "Sticker Pack", "price_cents": 500},
        {"name": "Water Bottle", "price_cents": 2000},
        {"name": "Notebook", "price_cents": 1000},
        {"name": "Hoodie", "price_cents": 4000},
    ]
    return templates.TemplateResponse("index.html", {"request": request, "products": products})

# ----------------- Cart -------------------------------

class CartItem(BaseModel):
    name: str
    price_cents: int
    quantity: int

cart = []

# @app.post("/cart/add")
# def add_to_cart(item: CartItem):
#     cart.append(item)
#     return {"message": f"{item.quantity}x {item.name} добавлено в корзину"}

@app.post("/cart/add", response_class=HTMLResponse)
def add_to_cart(request: Request, name: str = Form(...), price_cents: int = Form(...), quantity: int = Form(...)):
    cart.append(CartItem(name=name, price_cents=price_cents, quantity=quantity))
    total = sum(item.price_cents * item.quantity for item in cart)
    return templates.TemplateResponse("cart.html", {"request": request, "cart": cart, "total": total})


@app.get("/cart")
def view_cart():
    return {"cart": cart}

@app.delete("/cart/clear")
def clear_cart():
    cart.clear()
    return {"message": "Корзина очищена"}

@app.post("/cart/checkout")
async def checkout():
    if not cart:
        raise HTTPException(status_code=400, detail="Корзина пуста")

    line_items = [
        {
            "price_data": {
                "currency": "usd",
                "product_data": {"name": item.name},
                "unit_amount": item.price_cents
            },
            "quantity": item.quantity
        } for item in cart
    ]

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=line_items,
        mode="payment",
        success_url="https://jacob-python.ru/success",
        cancel_url="https://jacob-python.ru/cancel"
    )

    cart.clear()  # очищаем корзину после оформления
    return {"checkout_url": session.url}

# ----------------- End -------------------------------

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)