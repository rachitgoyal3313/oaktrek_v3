import os
import sys
import django
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oaktrek_v2.settings')
django.setup()

from Store.models import Product  # Replace 'your_app' with your app name

# Flask SQLAlchemy models
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship

Base = declarative_base()

class FlaskProduct(Base):
    __tablename__ = 'products'
    product_id = Column(Integer, primary_key=True)
    stock_quantity = Column(Integer, default=0, nullable=False)

class FlaskStockHistory(Base):
    __tablename__ = 'stock_history'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.product_id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    product = relationship('FlaskProduct', backref='stock_history')

def migrate_products():
    # Get Flask database URI from environment variable
    flask_db_uri = os.getenv('FLASK_DATABASE_URI', 'sqlite:///../oaktrek_flask/inventory.db')
    engine = create_engine(flask_db_uri)
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    flask_session = DBSession()

    try:
        # Fetch all products from Django
        django_products = Product.objects.all()
        logger.info(f"Found {len(django_products)} products in Django database.")

        for django_product in django_products:
            flask_product = flask_session.query(FlaskProduct).filter_by(product_id=django_product.id).first()

            if flask_product:
                flask_product.stock_quantity = django_product.stock_quantity
                logger.info(f"Updated Product ID {django_product.id} with stock_quantity {django_product.stock_quantity}")
            else:
                flask_product = FlaskProduct(
                    product_id=django_product.id,
                    stock_quantity=django_product.stock_quantity
                )
                flask_session.add(flask_product)
                logger.info(f"Added Product ID {django_product.id} with stock_quantity {django_product.stock_quantity}")

            # Create initial StockHistory entry
            stock_history_entry = FlaskStockHistory(
                product_id=django_product.id,
                quantity=django_product.stock_quantity,
                timestamp=datetime.utcnow()
            )
            flask_session.add(stock_history_entry)

        flask_session.commit()
        logger.info("Migration completed successfully.")

    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        flask_session.rollback()

    finally:
        flask_session.close()

if __name__ == '__main__':
    migrate_products()