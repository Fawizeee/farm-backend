from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from models import Order, OrderItem, Product
from typing import List, Optional
from datetime import datetime

class OrderService:
    @staticmethod
    def get_orders(db: Session, skip: int = 0, limit: int = 100, status_filter: str = None, 
                   date_str: str = None, search: str = None) -> List[Order]:
        query = db.query(Order).options(joinedload(Order.order_items))
        
        if status_filter: 
            query = query.filter(Order.status == status_filter)
        
        if date_str:
            try:
                filter_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                start_of_day = datetime.combine(filter_date, datetime.min.time())
                end_of_day = datetime.combine(filter_date, datetime.max.time())
                query = query.filter(Order.created_at >= start_of_day, Order.created_at <= end_of_day)
            except ValueError:
                pass # Or raise exception
        
        if search:
            try:
                search_id = search.replace('#', '').strip()
                order_id = int(search_id)
                query = query.filter(Order.id == order_id)
            except ValueError:
                query = query.filter(Order.id == -1)
        
        return query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_order(db: Session, order_id: int) -> Optional[Order]:
        return db.query(Order).options(joinedload(Order.order_items)).filter(Order.id == order_id).first()

    @staticmethod
    def create_order(db: Session, order_data: dict, items_data: List[dict]) -> Order:
        try:
            db_order = Order(**order_data)
            db.add(db_order)
            db.flush()  # Get order.id for items
            
            for item_data in items_data:
                db_order_item = OrderItem(order_id=db_order.id, **item_data)
                db.add(db_order_item)
            
            db.commit()
            db.refresh(db_order)
            return db_order
        except Exception as e:
            # Rollback entire transaction if any part fails
            db.rollback()
            print(f"Error creating order: {e}")
            raise

    @staticmethod
    def update_order_status(db: Session, db_order: Order, status: str) -> Order:
        db_order.status = status
        db.commit()
        db.refresh(db_order)
        return db_order

    @staticmethod
    def delete_order(db: Session, db_order: Order):
        db.delete(db_order)
        db.commit()

    @staticmethod
    def get_dashboard_stats(db: Session) -> dict:
        total_orders = db.query(func.count(Order.id)).scalar()
        pending_orders = db.query(func.count(Order.id)).filter(Order.status == "pending").scalar()
        completed_orders = db.query(func.count(Order.id)).filter(Order.status == "completed").scalar()
        
        # Use SQL aggregate function instead of loading all orders into memory
        # This prevents memory exhaustion with large datasets
        total_revenue = db.query(func.sum(Order.total_amount)).filter(
            Order.status == "completed"
        ).scalar() or 0
        
        total_products = db.query(func.count(Product.id)).scalar()
        active_products = db.query(func.count(Product.id)).filter(Product.available == True).scalar()
        
        return {
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "completed_orders": completed_orders,
            "total_revenue": float(total_revenue),  # Ensure it's a float
            "total_products": total_products,
            "active_products": active_products
        }

