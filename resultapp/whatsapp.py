import os
import re
import logging
import requests
from django.conf import settings
from .models import WhatsAppLog

logger = logging.getLogger(__name__)

def clean_indian_phone(phone_str):
    """
    Cleans and validates Indian phone numbers.
    - Strips all non-digit characters.
    - If length is 10 digits, prepends '91'.
    - If length is 12 digits starting with '91', returns as-is.
    - Returns None if number is invalid.
    """
    if not phone_str:
        return None
    # Extract digits only
    digits = re.sub(r'\D', '', str(phone_str))
    
    if len(digits) == 10:
        return "91" + digits
    elif len(digits) == 12 and digits.startswith("91"):
        return digits
    return None

def send_whatsapp_message(phone_str, message_text, message_type):
    """
    Sends a text message via Meta's WhatsApp Cloud API.
    Logs the outcome in the WhatsAppLog model.
    """
    cleaned_number = clean_indian_phone(phone_str)
    if not cleaned_number:
        logger.error(f"Invalid phone number formatted: {phone_str}")
        WhatsAppLog.objects.create(
            recipient_number=str(phone_str),
            message_type=message_type,
            status='failed',
            response_payload="Invalid phone number format (must be 10 or 12 digits with 91 prefix)."
        )
        return False, "Invalid phone number"

    # Fetch token and number ID from environment
    token = os.environ.get("WHATSAPP_TOKEN")
    phone_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")

    if not token or not phone_id:
        msg = "WhatsApp Cloud API credentials are not configured in environment variables."
        logger.warning(msg)
        WhatsAppLog.objects.create(
            recipient_number=cleaned_number,
            message_type=message_type,
            status='failed',
            response_payload=msg
        )
        return False, msg

    url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": cleaned_number,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message_text
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        resp_data = response.text
        if response.status_code in [200, 201]:
            WhatsAppLog.objects.create(
                recipient_number=cleaned_number,
                message_type=message_type,
                status='sent',
                response_payload=resp_data
            )
            return True, "Message sent successfully"
        else:
            WhatsAppLog.objects.create(
                recipient_number=cleaned_number,
                message_type=message_type,
                status='failed',
                response_payload=f"HTTP {response.status_code}: {resp_data}"
            )
            return False, f"API returned status {response.status_code}"
    except Exception as e:
        err_msg = str(e)
        logger.exception("Failed to send WhatsApp message")
        WhatsAppLog.objects.create(
            recipient_number=cleaned_number,
            message_type=message_type,
            status='failed',
            response_payload=err_msg
        )
        return False, err_msg
