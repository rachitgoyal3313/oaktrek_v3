from django.db.models.signals import post_save
from django.dispatch import receiver
from Store.models import Product  # Replace 'your_app' with your app name
import requests
import logging
from time import sleep
import os
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

FLASK_API_URL = os.getenv('FLASK_API_URL', 'http://localhost:5000/api/inventory')
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

@receiver(post_save, sender=Product)
def sync_new_product_to_flask(sender, instance, created, **kwargs):
    if created:
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    f'{FLASK_API_URL}/add-product',
                    json={
                        'product_id': instance.id,
                        'stock_quantity': instance.stock_quantity
                    },
                    timeout=10
                )
                response.raise_for_status()
                logger.info(f"Successfully added Product ID {instance.id} to Flask")
                break
            except requests.RequestException as e:
                logger.error(f"Attempt {attempt + 1}/{MAX_RETRIES} failed to sync Product ID {instance.id} to Flask: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    sleep(RETRY_DELAY)
                else:
                    logger.critical(f"Failed to sync Product ID {instance.id} to Flask after {MAX_RETRIES} attempts")