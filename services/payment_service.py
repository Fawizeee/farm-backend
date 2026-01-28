import requests
import os
import json 

class PaymentService:
    def __init__(self):
        self.secret_key = os.getenv("PAYSTACK_SECRET_KEY")
        self.base_url = "https://api.paystack.co"
        
        if not self.secret_key:
            print("Warning: PAYSTACK_SECRET_KEY not set")
            
    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }

    def initialize_transaction(self, email: str, amount: int, callback_url: str = None, metadata: dict = None):
        """
        Initialize a Paystack transaction.
        amount is in kobo (e.g. 10000 = 100 NGN)
        """
        if not self.secret_key:
             return {"status": False, "message": "Paystack not configured"}

        url = f"{self.base_url}/transaction/initialize"
        
        payload = {
            "email": email,
            "amount": str(amount), # Paystack expects string or integer
            "metadata": json.dumps(metadata) if metadata else "{}"
        }
        
        if callback_url:
            payload["callback_url"] = callback_url

        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("status"):
                return response_data
            else:
                print(f"Paystack Initialize Error: {response_data}")
                return {"status": False, "message": response_data.get("message", "Initialization failed")}
                
        except Exception as e:
            print(f"Paystack Initialize Exception: {str(e)}")
            return {"status": False, "message": str(e)}

    def verify_transaction(self, reference: str):
        """
        Verify a Paystack transaction.
        """
        if not self.secret_key:
             return {"status": False, "message": "Paystack not configured"}

        url = f"{self.base_url}/transaction/verify/{reference}"

        try:
            response = requests.get(url, headers=self._get_headers())
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("status"):
                return response_data
            else:
                print(f"Paystack Verify Error: {response_data}")
                return {"status": False, "message": response_data.get("message", "Verification failed")}
                
        except Exception as e:
             print(f"Paystack Verify Exception: {str(e)}")
             return {"status": False, "message": str(e)}

payment_service = PaymentService()
