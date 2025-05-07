from flask import Flask, jsonify, request
from flask_restful import Resource, Api
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import func
import os
import logging
import random

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
api = Api(app)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'FLASK_DATABASE_URI',
    'sqlite:///' + os.path.join(basedir, 'inventory.db')
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define categories
CATEGORIES = ['Skincare', 'Haircare', 'Bodycare']

# Define models
class Product(db.Model):
    __tablename__ = 'products'
    product_id = db.Column(db.Integer, primary_key=True)  # Using product_id for consistency
    product_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    stock_quantity = db.Column(db.Integer, default=0, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.String(100))

    def __repr__(self):
        return f"<Product ID: {self.product_id}>"

class StockHistory(db.Model):
    __tablename__ = 'stock_history'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    product = db.relationship('Product', backref='stock_history')

    def __repr__(self):
        return f"<StockHistory for Product {self.product_id}: {self.quantity}>"

@app.route('/api/inventory/summary')
def get_inventory_summary():
    """Get summary of inventory levels"""
    try:
        products = Product.query.all()
        total_products = len(products)
        total_items = sum(p.stock_quantity for p in products)
        
        categories = {}
        for category in db.session.query(Product.category).distinct():
            category_products = Product.query.filter_by(category=category[0])
            categories[category[0]] = {
                'product_count': category_products.count(),
                'total_items': sum(p.stock_quantity for p in category_products),
                'total_value': sum(p.stock_quantity * 100 for p in category_products) # Assuming fixed value per item
            }
        
        summary = {
            'overall': {
                'product_count': total_products,
                'total_items': total_items,
                'total_value': sum(p.stock_quantity * 100 for p in products)
            },
            'categories': categories
        }
        
        return jsonify(summary)
    except Exception as e:
        logger.error(f"Error getting inventory summary: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/analytics')
def get_stock_analytics():
    """Get analytics on product stock levels and sales velocity"""
    try:
        products = Product.query.all()
        analytics = []
        
        for product in products:
            history = StockHistory.query.filter_by(product_id=product.product_id)\
                .order_by(StockHistory.timestamp.desc())\
                .limit(30).all()
            
            if history:
                daily_changes = []
                for i in range(len(history)-1):
                    change = history[i].quantity - history[i+1].quantity
                    if change > 0:
                        daily_changes.append(change)
                
                sales_velocity = round(sum(daily_changes) / 30, 2) if daily_changes else 0
                days_remaining = round(product.stock_quantity / sales_velocity if sales_velocity > 0 else 0)
                
                if days_remaining < 7:
                    stock_status = "Critical"
                elif days_remaining < 14:
                    stock_status = "Low"
                else:
                    stock_status = "Good"
                
                analytics.append({
                    'product_id': product.product_id,
                    'name': product.product_name,
                    'category': product.category,
                    'current_stock': product.stock_quantity,
                    'sales_velocity': sales_velocity,
                    'days_remaining': days_remaining,
                    'stock_status': stock_status,
                    'reorder_point': max(sales_velocity * 7, 10)  # 7 days of stock or minimum 10
                })
        
        return jsonify({'analytics': analytics})
    except Exception as e:
        logger.error(f"Error getting stock analytics: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/low-stock')
def get_low_stock_alerts():
    """Get products with stock below threshold"""
    threshold = request.args.get('threshold', 10, type=int)
    
    try:
        low_stock_products = Product.query.filter(Product.stock_quantity <= threshold).all()
        alerts = []
        
        for product in low_stock_products:
            alerts.append({
                'product_id': product.product_id,
                'name': product.product_name,
                'category': product.category,
                'current_stock': product.stock_quantity,
                'threshold': threshold
            })
        
        return jsonify(alerts)
    except Exception as e:
        logger.error(f"Error getting low stock alerts: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/stock-history/<int:product_id>')
def get_stock_history(product_id):
    """Get historical stock data for a product"""
    period = request.args.get('period', 'months')
    
    try:
        product = Product.query.filter_by(product_id=product_id).first_or_404()
        
        if period == 'days':
            days = 30
        elif period == 'weeks':
            days = 90
        else:  # months
            days = 365
            
        history = StockHistory.query\
            .filter_by(product_id=product_id)\
            .filter(StockHistory.timestamp >= datetime.now() - timedelta(days=days))\
            .order_by(StockHistory.timestamp.asc())\
            .all()
            
        labels = [h.timestamp.strftime('%Y-%m-%d') for h in history]
        values = [h.quantity for h in history]
        
        return jsonify({
            'product_id': product_id,
            'product_name': product.product_name,
            'labels': labels,
            'values': values,
            'current_stock': product.stock_quantity
        })
    except Exception as e:
        logger.error(f"Error getting stock history for product {product_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

class UpdateStock(Resource):
    def post(self, product_id):
        logger.info(f"Executing UpdateStock.post for product {product_id}")
        product = Product.query.filter_by(product_id=product_id).first_or_404()
        data = request.get_json()
        
        try:
            quantity = int(data.get('quantity', 0))
            min_quantity = int(data.get('min_quantity', 0))
            
            if quantity < min_quantity:
                logger.warning(f"Stock update failed: quantity {quantity} < min_quantity {min_quantity}")
                return {'error': f'Stock quantity cannot be less than {min_quantity}'}, 400
            
            # Only create history entry if quantity is different
            if quantity != product.stock_quantity:
                stock_history_entry = StockHistory(
                    product_id=product_id,
                    quantity=quantity
                )
                db.session.add(stock_history_entry)
            
            # Update product details
            product.stock_quantity = quantity
            product.last_updated = datetime.utcnow()
            product.updated_by = data.get('updated_by', 'system')
            
            # Calculate sales velocity for response
            history = StockHistory.query.filter_by(product_id=product_id)\
                .order_by(StockHistory.timestamp.desc())\
                .limit(30).all()
            
            sales_velocity = 0
            days_remaining = float('inf')
            
            if history:
                daily_changes = []
                for i in range(len(history)-1):
                    change = history[i].quantity - history[i+1].quantity
                    if change > 0:
                        daily_changes.append(change)
                
                if daily_changes:
                    sales_velocity = round(sum(daily_changes) / 30, 2)
                    days_remaining = round(quantity / sales_velocity) if sales_velocity > 0 else float('inf')
            
            db.session.commit()
            
            logger.info(f"Stock updated for Product ID {product_id} to {quantity}")
            return {
                'message': f'Stock updated successfully for Product ID {product_id}',
                'current_stock': quantity,
                'sales_velocity': sales_velocity,
                'days_remaining': days_remaining,
                'stock_status': 'Critical' if days_remaining < 7 else 'Low' if days_remaining < 14 else 'Good'
            }
            
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid stock update: {str(e)}")
            return {'error': 'Invalid quantity value'}, 400

class AddProduct(Resource):
    def post(self):
        logger.info("Executing AddProduct.post")
        data = request.get_json()
        
        try:
            product_id = int(data.get('product_id'))
            product_name = data.get('product_name')
            category = data.get('category')
            stock_quantity = int(data.get('stock_quantity', 0))
            
            if not product_name or not category:
                return {'error': 'Product name and category are required'}, 400
            
            if category not in CATEGORIES:
                return {'error': f'Invalid category. Must be one of: {", ".join(CATEGORIES)}'}, 400
            
            existing_product = Product.query.filter_by(product_id=product_id).first()
            if existing_product:
                logger.warning(f"Product ID {product_id} already exists")
                return {'error': f'Product ID {product_id} already exists'}, 400
            
            product = Product(
                product_id=product_id,
                product_name=product_name,
                category=category,
                stock_quantity=stock_quantity,
                updated_by=data.get('updated_by', 'system')
            )
            db.session.add(product)
            
            stock_history_entry = StockHistory(
                product_id=product_id,
                quantity=stock_quantity
            )
            db.session.add(stock_history_entry)
            db.session.commit()
            
            logger.info(f"Added Product ID {product_id} with stock_quantity {stock_quantity}")
            return {'message': f'Product ID {product_id} added successfully'}
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid product add request: {str(e)}")
            return {'error': 'Invalid product_id or stock_quantity'}, 400

# Register API resources
api.add_resource(UpdateStock, '/api/inventory/update-stock/<int:product_id>')
api.add_resource(AddProduct, '/api/inventory/add-product')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        logger.info("Database tables created or verified.")
    app.run(debug=True, host='0.0.0.0', port=5000)
