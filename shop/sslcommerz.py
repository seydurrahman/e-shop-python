import requests
import json
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives


def generate_sslcommerz_payment(request, order):
    post_data = {
        "store_id": settings.SSLCOMMERZ_STORE_ID,
        "store_passwd": settings.SSLCOMMERZ_STORE_PASSWORD,
        "total_amount": float(order.get_total_cost()),
        "currency": "BDT",
        "tran_id": str(order.id),
        "success_url": request.build_absolute_uri(f"/payment/success/{order.id}/"),
        "fail_url": request.build_absolute_uri(f"/payment/fail/{order.id}/"),
        "cancel_url": request.build_absolute_uri(f"/payment/cancel/{order.id}/"),
        "cus_name": f"{order.first_name} {order.last_name}",
        "cus_email": order.email,
        "cus_add1": order.address,
        "cus_city": order.city,
        "cus_postcode": order.postal_code,
        "cus_country": "Bangladesh",
        "shipping_method": "NO",
        "product_name": "Products from our store",
        "product_category": "General",
        "product_profile": "general",
    }

    response = requests.post(settings.SSLCOMMERZ_PAYMENT_URL, data=post_data)
    return json.loads(response.text)  # json --> Python obj


def send_order_confirmation_email(order):
    subject = f"Order Confirmation - Order #{order.id}"
    message = render_to_string(
        "shop/email/order_confirmation.html", {"order": order}
    )  # html code ke --> string e convert kore
    to = order.email
    send_email = EmailMultiAlternatives(subject, "", to=[to])
    send_email.attach_alternative(message, "text/html")
    send_email.send()


def verify_sslcommerz_payment(val_id, amount):
    """
    Verify the transaction with SSLCommerz validation API.
    Returns True if verified successfully, else False.
    """
    try:
        store_id = settings.SSLCOMMERZ_STORE_ID
        store_pass = settings.SSLCOMMERZ_STORE_PASSWORD
        validation_url = settings.SSLCOMMERZ_VALIDATION_URL

        params = {
            "val_id": val_id,
            "store_id": store_id,
            "store_passwd": store_pass,
            "format": "json",
        }

        response = requests.get(validation_url, params=params, timeout=10)
        data = response.json()

        # Check valid status and amount match
        status = data.get("status")
        resp_amount = data.get("amount") or data.get("amount", 0)

        if status and status.upper() == "VALID" and float(resp_amount) == float(amount):
            return True
        return False

    except Exception as e:
        # In production, log this exception
        print("SSLCommerz verification error:", e)
        return False


# def verify_sslcommerz_payment(tran_id, val_id, amount, order):
#     """
#     Verify the transaction with SSLCommerz validation API.
#     Returns True if verified successfully, else False.
#     """
#     try:
#         # Your SSLCommerz credentials
#         store_id = settings.SSLC_STORE_ID
#         store_pass = settings.SSLC_STORE_PASS
#         validation_url = f"https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php"

#         # API call to verify payment
#         params = {
#             "val_id": val_id,
#             "store_id": store_id,
#             "store_passwd": store_pass,
#             "format": "json"
#         }

#         response = requests.get(validation_url, params=params)
#         data = response.json()

#         # Check if status is VALID and amounts match
#         if data.get("status") == "VALID" and float(data.get("amount", 0)) == float(amount):
#             return True

#         return False

#     except Exception as e:
#         print("SSLCommerz verification error:", e)
#         return False
