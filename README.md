E-Commerce Backend API

This is a Django REST Framework backend for a full-stack e-commerce application.
It handles authentication, products, reviews, cart, orders, and payment processing with Paystack.

Technologies Used

Python 3.x

Django 5.x

Django REST Framework (DRF)

Django REST Framework Simple JWT

Paystack integration

PostgreSQL / SQLite (your choice)

Project Structure

eccomm-backend/
├─ accounts/ User authentication and profile management
├─ cart/ Cart management (CRUD)
├─ orders/ Orders (create, cancel, update, list)
├─ payments/ Payment verification & webhook
├─ gadjet_shop/ Products and reviews
├─ manage.py
└─ README.md

API Endpoints

1. Authentication (/api/auth/)

   Method Endpoint Description
   POST /register/ Register new user
   POST /login/ Login user
   POST /token/refresh/ Refresh JWT token
   GET /verify-email/ Verify user's email
   POST /forgot-password/ Request password reset
   POST /reset-password/ Reset password
   GET /me/ Get current logged-in user
   PATCH /update/ Update profile
   PATCH /change-password/ Change password

Authentication required for most endpoints except registration, login, forgot/reset password.

2. Products (/api/)

   Method Endpoint Description
   GET /products/ List all products
   GET /products/<slug>/ Get product details
   GET /products/<product_id>/reviews/ List product reviews
   POST /products/<product_id>/reviews/create/ Add a review

3. Cart (/api/cart/)
   Method Endpoint Description
   GET /api/cart/ Get all items in the user's cart
   POST /api/cart/ Add item to cart
   GET /api/cart/<id>/ Retrieve a single cart item
   PUT /api/cart/<id>/ Update cart item
   PATCH /api/cart/<id>/ Partial update cart item
   DELETE /api/cart/<id>/ Remove item from cart

All pricing and validation is calculated on the backend.

4. Orders (/api/orders/)

   Method Endpoint Description
   POST / Create new order
   GET /my-orders/ List current user's orders
   GET /my-orders/<id>/ Get order details
   POST /my-orders/<order_id>/cancel/ Cancel an order
   PATCH /admin/<order_id>/update-status/ Admin updates order status
   POST /create_pending/ Create a pending order (before payment verification)

5. Payments (/api/payments/)

   Method Endpoint Description
   POST /paystack/verify/ Verify Paystack payment (requires authentication)
   POST /paystack/webhook/ Paystack webhook for payment events (CSRF exempt)

Authentication & JWT

Uses JWT tokens via djangorestframework-simplejwt

Login returns access and refresh tokens

Attach Authorization: Bearer <token> to secure endpoints

Payment Flow

Frontend creates a pending order

User is redirected to Paystack payment page

On payment success, frontend calls /api/payments/paystack/verify/

Backend updates the order status (completed, failed)

Webhook ensures consistency for payments processed outside frontend

Installation

Clone repo:

git clone https://github.com/Gentlestan/eccomm-backend.git
cd eccomm-backend

Create virtual environment and install dependencies:

python -m venv venv
source venv/bin/activate # Linux / Mac
venv\Scripts\activate # Windows
pip install -r requirements.txt

Setup environment variables (.env):

SECRET*KEY=your-secret-key
DEBUG=True
DATABASE_URL=postgres://user:password@localhost:5432/dbname
PAYSTACK_SECRET_KEY=sk_test*...

Apply migrations:

python manage.py migrate

Create superuser (optional):

python manage.py createsuperuser

Run server:

python manage.py runserver

Notes

All API endpoints are backend-driven; frontend should not trust client-side pricing

Cart, order, and payment endpoints require authentication

Email verification required for account activation

Reviews can only be added to existing products

Order cancellation allowed only for user orders not completed

Repository

GitHub Repo Link: https://github.com/Gentlestan/fullstack-eccomm

Progress Reflection

Migrated frontend-driven payments and orders to backend-driven

Implemented JWT authentication with email verification

Challenges faced:

Merging updates to ProductCard caused conflicts

TypeScript frontend required matching prop types (CheckoutFormProps)

Next steps:

Integrate frontend fully with backend

Add automated tests for payments and orders

Improve API documentation

License

MIT License
