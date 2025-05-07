# Store/services/inventory_service.py
import requests
from django.conf import settings
from django.db.models import Sum, Avg, F, ExpressionWrapper, FloatField
from django.utils import timezone
from datetime import timedelta
import random
import logging

logger = logging.getLogger(__name__)

class InventoryService:
    BASE_URL = getattr(settings, 'INVENTORY_API_URL', 'http://localhost:5000/api/inventory')
    
    @classmethod
    def get_stock_analytics(cls):
        """Get analytics on product stock levels and sales velocity"""
        try:
            response = requests.get(f"{cls.BASE_URL}/analytics")
            response.raise_for_status()
            data = response.json()
            # Ensure each product has product_id
            for item in data.get('analytics', []):
                if 'id' in item and 'product_id' not in item:
                    item['product_id'] = item['id']
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching analytics from Flask API: {str(e)}")
            # Return empty analytics if API fails
            return {'analytics': []}

    @classmethod
    def get_low_stock_alerts(cls, threshold=10):
        """Get products with stock below threshold"""
        try:
            response = requests.get(
                f"{cls.BASE_URL}/low-stock",
                params={'threshold': threshold}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching low stock alerts from Flask API: {str(e)}")
            return []

    @classmethod
    def get_inventory_summary(cls):
        """Get inventory summary by category"""
        try:
            response = requests.get(f"{cls.BASE_URL}/summary")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching inventory summary from Flask API: {str(e)}")
            return {
                'total_products': 0,
                'total_stock': 0,
                'categories': {}
            }

    @classmethod
    def update_stock_quantity(cls, product_id, quantity, updated_by='system'):
        """Update stock quantity via Flask API"""
        try:
            response = requests.post(
                f"{cls.BASE_URL}/update-stock/{product_id}",
                json={
                    'quantity': quantity,
                    'min_quantity': 0,
                    'updated_by': updated_by
                }
            )
            response.raise_for_status()
            result = response.json()

            # If Flask update successful, sync Django model
            if 'error' not in result:
                from Store.models import Product
                product = Product.objects.filter(id=product_id).first()
                if product:
                    product.stock_quantity = quantity
                    product.save(update_fields=['stock_quantity'])
                    logger.info(f"Synced Django product {product_id} stock to {quantity}")

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating stock via Flask API: {str(e)}")
            return {'error': str(e)}

    @classmethod
    def get_stock_history(cls, product_id, period='months'):
        """Get historical stock data for a product"""
        try:
            response = requests.get(
                f"{cls.BASE_URL}/stock-history/{product_id}",
                params={'period': period}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching stock history from Flask API: {str(e)}")
            return {'labels': [], 'values': []}
