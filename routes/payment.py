import hmac
import hashlib
import os
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from services import payment_service, OrderService, NotificationService
from models import Order

router = APIRouter(prefix="/api/payment", tags=["Payment"])

# Import Firebase messaging if available
firebase_admin_initialized = False
messaging = None
try:
    import firebase_admin
    from firebase_admin import messaging as fcm_messaging
    firebase_admin_initialized = True
    messaging = fcm_messaging
except ImportError:
    pass

class PaymentInitializeRequest(BaseModel):
    email: str
    amount: float  # In Naira
    order_id: int
    callback_url: str

@router.post("/initialize")
async def initialize_payment(
    data: PaymentInitializeRequest,
    db: Session = Depends(get_db)
):
    """
    Initialize a payment transaction with Paystack.
    """
    # Verify order exists
    order = OrderService.get_order(db, data.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    amount_kobo = int(data.amount * 100)
    metadata = {"order_id": data.order_id}

    response = payment_service.initialize_transaction(
        email=data.email,
        amount=amount_kobo,
        callback_url=data.callback_url,
        metadata=metadata
    )

    if not response.get("status"):
        raise HTTPException(status_code=400, detail=response.get("message", "Payment initialization failed"))

    return response["data"]

@router.get("/verify/{reference}")
async def verify_payment(
    reference: str,
    db: Session = Depends(get_db)
):
    """
    Verify a payment transaction.
    """
    response = payment_service.verify_transaction(reference)
    
    if not response.get("status"):
        return {"status": False, "message": response.get("message", "Verification failed")}

    data = response["data"]
    if data["status"] == "success":
        if "metadata" in data and "order_id" in data["metadata"]:
             order_id = data["metadata"]["order_id"]
             order = OrderService.get_order(db, order_id)
             if order:
                 # Update order status to confirmed if it is pending
                 if order.status == 'pending': 
                     OrderService.update_order_status(db, order, "confirmed")
                     
                     # Send notification to admin
                     if firebase_admin_initialized and messaging:
                        try:
                            NotificationService.send_notification_to_admin(
                                db=db,
                                title="New Paystack Order",
                                message_text=f"New order verified from {order.customer_name} - ₦{order.total_amount:,.2f}",
                                redirect_url="/admin/orders",
                                messaging_instance=messaging
                            )
                        except Exception as e:
                            print(f"Error sending notification: {e}")
        
        return {"status": True, "message": "Payment successful", "data": data}
    else:
        return {"status": False, "message": "Payment failed or pending", "data": data}

@router.post("/webhook")
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Paystack Webhooks.
    """
    secret = os.getenv("PAYSTACK_SECRET_KEY")
    if not secret:
        return Response(status_code=500, content="Backend configuration error")

    signature = request.headers.get("x-paystack-signature")
    if not signature:
        return Response(status_code=400, content="Missing signature")
    
    body = await request.body()
    
    # Verify signature
    hash_obj = hmac.new(secret.encode('utf-8'), body, hashlib.sha512)
    expected_signature = hash_obj.hexdigest()
    
    if signature != expected_signature:
        return Response(status_code=400, content="Invalid signature")

    # Process event
    try:
        payload = await request.json()
        event = payload.get("event")
        data = payload.get("data", {})
        
        if event == "charge.success":
            # Handle success
            # Try to get order_id from metadata
            metadata = data.get("metadata", {})
            order_id = metadata.get("order_id")
            
            if order_id:
                order = OrderService.get_order(db, order_id)
                if order:
                    print(f"Webhook: Payment successful for Order #{order_id}")
                    if order.status == 'pending':
                        OrderService.update_order_status(db, order, "confirmed")
                        
                        # Send notification to admin
                        if firebase_admin_initialized and messaging:
                            try:
                                NotificationService.send_notification_to_admin(
                                    db=db,
                                    title="New Paystack Order",
                                    message_text=f"New order verified from {order.customer_name} - ₦{order.total_amount:,.2f}",
                                    redirect_url="/admin/orders",
                                    messaging_instance=messaging
                                )
                            except Exception as e:
                                print(f"Error sending notification: {e}")
            else:
                 print("Webhook: No order_id in metadata")

    except Exception as e:
        print(f"Webhook Error: {e}")
        return Response(status_code=500, content="Error processing webhook")
        
    return Response(status_code=200, content="Webhook received")
