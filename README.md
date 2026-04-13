# MultiMart 🛍️

> A modern, feature-rich Django-based multi-vendor e-commerce platform with real-time notifications, secure payments, and role-based access control.

[![Django](https://img.shields.io/badge/Django-5.2.5-darkgreen?logo=django)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)]()
[![Live Demo](https://img.shields.io/badge/Live%20Demo-multimart.duckdns.org-blue?logo=heroku)](https://multimart.duckdns.org)

## 🎯 Overview

MultiMart is a comprehensive multi-vendor e-commerce solution that enables customers to browse and purchase products, sellers to manage inventory and orders, and administrators to oversee the entire platform. Built with Django and Django Channels for real-time notifications, MultiMart provides a seamless shopping experience.

**Live Demo:** [https://multimart.duckdns.org](https://multimart.duckdns.org)

## ✨ Key Features

### 👥 Multi-Role Authentication
- Custom user model with role-based access (Customer, Seller, Admin)
- OTP-based password reset via email
- Google & Facebook social login via Django-allauth
- Secure session management

### 🛒 Customer Experience
- **Product Catalog** - Browse by category, search, filter, and sort
- **Shopping Cart** - Add/remove items, persistent cart storage
- **Wishlist** - Save favorite products for later
- **Checkout** - One-click and standard checkout flows
- **Order Tracking** - Real-time order status with timeline
- **Reviews** - Submit and read product reviews with admin approval

### 🏪 Seller Dashboard
- **Product Management** - Create, edit, delete products with images
- **Order Management** - Track and manage customer orders
- **Review Monitoring** - View and respond to customer reviews
- **Sales Analytics** - Track sales and inventory
- **Real-time Notifications** - Get instant alerts on new orders and reviews

### 🔐 Admin Dashboard
- **User Management** - Manage customers and sellers
- **Product Oversight** - Monitor and moderate products
- **Order Management** - Track all platform orders
- **Review Approval** - Approve/reject customer reviews
- **Category Management** - Organize products by categories
- **Analytics** - Platform-wide insights and reports

### 💳 Payment Integration
- **Razorpay** - Secure online payments with signature verification
- **Cash on Delivery** - Traditional payment option
- PCI-DSS compliant checkout flow

### 🔔 Real-Time Notifications
- Order creation alerts for sellers
- Order status updates for customers
- Review submission notifications
- Review approval alerts
- Powered by Django Channels

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Django 5.2.5 |
| **Database** | SQLite (dev) / MySQL (prod) |
| **Real-time** | Django Channels + WebSocket |
| **Payments** | Razorpay API |
| **Authentication** | Django Auth + Django-allauth |
| **API** | Django REST Framework |
| **Image Processing** | Pillow |
| **Config** | Python-dotenv |

---

## 📦 Project Structure

```
multimart/
├── core/                      # Central authentication & admin
│   ├── models.py             # User, Category, SubCategory
│   ├── views.py              # Authentication flows
│   └── middleware.py         # Request processing
├── user/                      # Customer features
│   ├── models.py             # Cart, Wishlist, Order, Review
│   ├── views.py              # Shopping & checkout logic
│   └── forms.py              # User-facing forms
├── seller/                    # Seller dashboard
│   ├── models.py             # SellerDetails, Product
│   ├── views.py              # Seller operations
│   └── management/commands/  # Seed & repair utilities
├── notifications/            # Real-time messaging
│   ├── models.py             # Notification model
│   ├── signals.py            # Auto-notification triggers
│   ├── consumers.py          # WebSocket handlers
│   └── routing.py            # Channel routing
├── templates/                # HTML templates
├── static/                   # CSS, JS, images
├── media/                    # Uploaded files
├── project/                  # Django settings
├── manage.py                 # Django CLI
└── requirements.txt          # Dependencies
```

---

## 📊 Database Models

### Core Models
- **User** - Custom auth model with roles, phone, address, and profile image
- **Category** - Product categories with descriptions and images
- **SubCategory** - Child categories with parent reference

### Seller Models
- **SellerDetails** - Seller profile and business info
- **Product** - Product listings with pricing and inventory
- **ProductImage** - Product images (main + gallery)

### Customer Models
- **Cart** - Shopping cart items
- **Wishlist** - Saved products
- **Order** - Purchase orders with Razorpay references
- **OrderItem** - Individual line items in orders
- **Review** - Product ratings and comments
- **Address** - Delivery addresses

### Notification Model
- **Notification** - Real-time alerts with read status and timestamps

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip & virtualenv
- MySQL (optional, SQLite used by default)

### Installation

**1. Clone the repository**
```bash
git clone <your-repository-url>
cd multimart
```

**2. Create virtual environment**

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure environment variables**

Create a `.env` file in the project root:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
SITE_ID=1

# Database (Optional - defaults to SQLite)
DB_NAME=multimart
DB_USER=root
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=3306

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@multimart.com

# Razorpay API Keys
RAZORPAY_KEY_ID=your-razorpay-key
RAZORPAY_KEY_SECRET=your-razorpay-secret

# Social Authentication
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_SECRET=your-google-secret
```

**5. Apply database migrations**
```bash
python manage.py migrate
```

**6. Create superuser account**
```bash
python manage.py createsuperuser
```

**7. Run development server**
```bash
python manage.py runserver
```

**8. Access the application**
- 🏠 **Home:** http://localhost:8000/user/home/
- 🔐 **Login:** http://localhost:8000/login/
- 🎛️ **Admin:** http://localhost:8000/admin-dashboard/

---

## 📚 Management Commands

The project includes helpful utility commands:

```bash
# Populate sample data for testing
python manage.py populate_dummy_data

# Seed realistic product catalog
python manage.py seed_real_catalog

# Fix product image paths
python manage.py repair_product_image_paths

# Repair user email records
python manage.py repair_user_emails
```

---

## 🌐 URL Routes

### Authentication Routes
- `POST /login/` - User login
- `POST /registration/` - New user registration
- `GET /forgot-password/` - Forgot password form
- `POST /verify-otp/` - OTP verification
- `POST /reset-password/` - Reset password
- `GET /accounts/` - Social authentication (django-allauth)

### Customer Routes
| Route | Purpose |
|-------|---------|
| `/user/home/` | Dashboard |
| `/user/products/` | Product listing |
| `/user/product/<slug>/` | Product detail |
| `/user/cart/` | Shopping cart |
| `/user/wishlist/` | Wishlist |
| `/user/checkout/` | Checkout page |
| `/user/my-orders/` | Order history |
| `/user/profile/` | User profile |

### Seller Routes
| Route | Purpose |
|-------|---------|
| `/seller/seller_dashboard/` | Dashboard |
| `/seller/seller_dashboard/product/add/` | Add product |
| `/seller/seller_dashboard/order/` | Manage orders |
| `/seller/seller_dashboard/reviews/` | Review management |
| `/seller/notifications/` | Notifications |

### Admin Routes
| Route | Purpose |
|-------|---------|
| `/admin-dashboard/` | Dashboard |
| `/admin-dashboard/users/` | User management |
| `/admin-dashboard/sellers/` | Seller management |
| `/admin-dashboard/products/` | Product moderation |
| `/admin-dashboard/orders/` | Order tracking |
| `/admin-dashboard/reviews/` | Review approval |
| `/admin-dashboard/categories/` | Category management |
| `/admin-dashboard/subcategories/` | Subcategory management |

---

## 💳 Payment Flow

```
Customer → Checkout → Create Razorpay Order
    ↓
Razorpay Payment Gateway → Payment Processing
    ↓
Signature Verification → Order Finalization
    ↓
Confirmation & Notifications
```

**Supported Methods:**
- 💰 Razorpay (Credit/Debit Card, UPI, Wallets)
- 📦 Cash on Delivery (COD)

---

## 🔔 Real-Time Notifications

The application uses Django Channels with WebSocket support:

**Automated Notifications:**
- ✅ Seller notified when order is placed
- ✅ Customer notified when order status changes
- ✅ Seller notified when review is submitted
- ✅ Customer notified when review is approved

**Architecture:**
- Development: In-memory channel layer
- Production: Redis-backed channel layer (recommended)

---

## 🔧 Configuration

### Environment Variables

All configuration is managed through `.env` file. See `.env.example` for complete list.

### Database Selection

**SQLite (Default)**
```python
# No configuration needed - automatic fallback
```

**MySQL**
```env
DB_NAME=multimart
DB_USER=root
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=3306
```

### Email Backend

- **Development:** Console output
- **Production:** SMTP (Gmail, Sendgrid, etc.)

### Channels Configuration

- **Development:** InMemoryChannelLayer
- **Production:** Redis (must enable in settings)

---

## ⚙️ Validation & Testing

```bash
# Check project configuration
python manage.py check

# Run tests
python manage.py test

# Create test data
python manage.py populate_dummy_data
```

---

## 🚨 Security Considerations

- ✅ CSRF protection enabled
- ✅ Password hashing with Django's default
- ✅ Razorpay signature verification
- ✅ OTP-based password reset
- ✅ Role-based access control
- ⚠️ Update `ALLOWED_HOSTS` for production
- ⚠️ Use environment variables for secrets
- ⚠️ Enable HTTPS in production
- ⚠️ Restrict DEBUG mode in production

---

## 🎯 Production Deployment

### Recommended Steps:

1. **Security Hardening**
   ```env
   DEBUG=False
   ALLOWED_HOSTS=your-domain.com,www.your-domain.com
   SECURE_SSL_REDIRECT=True
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   ```

2. **Database Migration**
   - Switch from SQLite to MySQL/PostgreSQL
   - Use managed database service (AWS RDS, Azure Database, etc.)

3. **Static Files & Media**
   ```bash
   python manage.py collectstatic
   # Serve from CDN (AWS S3, Cloudflare, etc.)
   ```

4. **Realtime Backend**
   - Install and configure Redis
   - Update Channels configuration in settings

5. **Deployment Platforms**
   - Heroku
   - AWS (EC2, Elastic Beanstalk)
   - DigitalOcean
   - Azure App Service
   - Railway, Render, etc.

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🐛 Known Issues & Future Improvements

### Known Issues
- [ ] `django-allauth` deprecation warnings (non-blocking)
- [ ] Razorpay keys logged on startup (should be removed)
- [ ] Settings need modernization for latest `django-allauth`

### Future Enhancements
- [ ] Redis-backed Channels for production
- [ ] Advanced analytics dashboard
- [ ] Inventory management system
- [ ] Seller commission tracking
- [ ] Mobile app (React Native/Flutter)
- [ ] Multi-language support
- [ ] Advanced search with Elasticsearch
- [ ] Email marketing integration
- [ ] Automated test suite
- [ ] Docker containerization
- [ ] CI/CD pipeline

---



## 🙏 Acknowledgments

- [Django Documentation](https://docs.djangoproject.com/)
- [Django Channels Documentation](https://channels.readthedocs.io/)
- [Razorpay Documentation](https://razorpay.com/docs/)
- [Django-allauth](https://django-allauth.readthedocs.io/)

---

<div align="center">

**[Live Demo](https://multimart.duckdns.org)** • **[Report Bug](https://github.com/yourusername/multimart/issues)** • **[Request Feature](https://github.com/yourusername/multimart/issues)**

Made with ❤️ for e-commerce enthusiasts

</div>
