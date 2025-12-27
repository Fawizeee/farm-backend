# Mufu Farm Backend API

Production-level backend API for Mufu Catfish Farm built with FastAPI and SQLAlchemy.

## Features

- **RESTful API** with comprehensive endpoints
- **JWT Authentication** for admin users
- **SQLite Database** (easily switchable to PostgreSQL)
- **CORS Support** for frontend integration
- **Database Models**: Products, Orders, Testimonials, Contact Messages, Admin Users
- **Automatic Database Initialization** with seed data

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
- Update `SECRET_KEY` and `JWT_SECRET_KEY` for production
- Change `ADMIN_USERNAME` and `ADMIN_PASSWORD`
- Configure database URL if using PostgreSQL
- Set CORS origins for your frontend

### 3. Initialize Database

```bash
python init_db.py
```

This will:
- Create all database tables
- Create an admin user
- Seed initial products
- Add sample testimonials

### 4. Run the Server

```bash
# Development
uvicorn app:app --reload --port 8000

# Production
uvicorn app:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Public Endpoints

- `GET /` - Health check
- `GET /api/products` - Get all products
- `GET /api/products/{id}` - Get product by ID
- `POST /api/orders` - Create new order
- `GET /api/testimonials` - Get all testimonials
- `POST /api/contact` - Submit contact form

### Admin Endpoints (Requires Authentication)

- `POST /api/admin/login` - Admin login
- `GET /api/admin/me` - Get current admin info
- `GET /api/admin/dashboard-stats` - Get dashboard statistics
- `POST /api/products` - Create product
- `PUT /api/products/{id}` - Update product
- `DELETE /api/products/{id}` - Delete product
- `GET /api/orders` - Get all orders
- `PUT /api/orders/{id}` - Update order status
- `DELETE /api/orders/{id}` - Delete order
- `GET /api/contact-messages` - Get contact messages
- `PUT /api/contact-messages/{id}/read` - Mark message as read

## Authentication

Admin endpoints require JWT token authentication:

1. Login via `/api/admin/login` with username and password
2. Receive JWT token in response
3. Include token in Authorization header: `Bearer <token>`

Default admin credentials (change in production):
- Username: `admin`
- Password: `admin123`

## Database Schema

### Products
- id, name, description, price, unit, icon, available, timestamps

### Orders
- id, customer info, delivery address, total amount, payment proof, status, timestamps
- Related OrderItems with product details

### Testimonials
- id, name, role, text, rating, is_active, timestamp

### Contact Messages
- id, name, email, phone, subject, message, is_read, timestamp

### Admins
- id, username, hashed_password, email, is_active, timestamp

## Production Deployment

1. Use PostgreSQL instead of SQLite:
   ```
   DATABASE_URL=postgresql://user:password@localhost/mufu_farm
   ```

2. Set strong secret keys in `.env`

3. Use a reverse proxy (nginx) for SSL

4. Run with gunicorn:
   ```bash
   gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

5. Set up process manager (systemd/supervisor)

## Security Notes

- Change default admin credentials immediately
- Use strong SECRET_KEY and JWT_SECRET_KEY
- Enable HTTPS in production
- Implement rate limiting for production
- Regular backup of database

## Support

For issues or questions, contact: info@mufufarm.com

