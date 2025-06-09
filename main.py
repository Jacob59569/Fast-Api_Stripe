import uvicorn
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, Request, HTTPException
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


books = [
    {
        "id": 1,
        "title": 'War and Peace',
        "author": "Jacob"
    }
]

class NewBook(BaseModel):
    title: str
    author: str

@app.post("/books")
def create_book(book: NewBook):
    books.append({
        "id": len(books) + 1,
        "title": book.title,
        "author": book.author
    })


@app.get("/books")
def get_books():
    return books




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

# Отдаём главную страницу
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

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


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)