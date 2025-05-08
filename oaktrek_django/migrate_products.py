import os
import sys
import django
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oaktrek_v2.settings')
django.setup()

from Store.models import Product

Base = declarative_base()

class FlaskProduct(Base):
    __tablename__ = 'products'
    product_id = Column(Integer, primary_key=True)
    product_name = Column(String(100), nullable=False)
    category = Column(String(50))
    stock_quantity = Column(Integer, default=0, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow)
    updated_by = Column(String(100))

    def __repr__(self):
        return f"<Product ID: {self.product_id}>"

class FlaskStockHistory(Base):
    __tablename__ = 'stock_history'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.product_id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    product = relationship('FlaskProduct', backref='stock_history')

def migrate_products():
    flask_db_uri = os.getenv('FLASK_DATABASE_URI', 'sqlite:///../oaktrek_flask/inventory.db')
    engine = create_engine(flask_db_uri)
    Base.metadata.bind = engine
    
    Base.metadata.create_all(engine)
    logger.info("Created Flask database tables")
    
    DBSession = sessionmaker(bind=engine)
    flask_session = DBSession()

    try:
        # Clear existing data
        flask_session.query(FlaskStockHistory).delete()
        flask_session.query(FlaskProduct).delete()
        flask_session.commit()
        logger.info("Cleared existing Flask database data")

        # Fetch all products from Django
        django_products = Product.objects.all()
        logger.info(f"Found {len(django_products)} products in Django database")

        now = datetime.utcnow()

        for django_product in django_products:
            # Only migrate fields that exist in Django Product model
            flask_product = FlaskProduct(
                product_id=django_product.id,
                product_name=django_product.product_name,
                category=django_product.category,
                stock_quantity=django_product.stock_quantity,
                last_updated=now,  # Use current timestamp
                updated_by='initial_migration'  # Set default value
            )
            flask_session.add(flask_product)
            
            # Create initial stock history entry
            stock_history = FlaskStockHistory(
                product_id=django_product.id,
                quantity=django_product.stock_quantity,
                timestamp=now
            )
            flask_session.add(stock_history)
            
            logger.info(f"Migrated Product ID {django_product.id}: {django_product.product_name}")

        flask_session.commit()
        logger.info("Migration completed successfully")

    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        flask_session.rollback()
        raise

    finally:
        flask_session.close()

if __name__ == '__main__':
    try:
        migrate_products()
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)