from sqlalchemy.orm import Session
from models import Product
from typing import List, Optional

class ProductService:
    @staticmethod
    def get_products(db: Session, skip: int = 0, limit: int = 100, available_only: bool = False) -> List[Product]:
        query = db.query(Product)
        if available_only:
            query = query.filter(Product.available == True)
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get_product(db: Session, product_id: int) -> Optional[Product]:
        return db.query(Product).filter(Product.id == product_id).first()

    @staticmethod
    def create_product(db: Session, product_data: dict) -> Product:
        db_product = Product(**product_data)
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product

    @staticmethod
    def update_product(db: Session, db_product: Product, update_data: dict) -> Product:
        for key, value in update_data.items():
            if value is not None:
                setattr(db_product, key, value)
        db.commit()
        db.refresh(db_product)
        return db_product

    @staticmethod
    def delete_product(db: Session, db_product: Product):
        db.delete(db_product)
        db.commit()
