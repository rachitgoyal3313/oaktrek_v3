
## 🛍️ Oaktrek – E-Commerce Shoe Store

**Oaktrek** is a full-featured online e-commerce application for buying shoes. Built with **Django** as the core backend and **Flask** for inventory microservices, it supports a seamless user experience with features like auctions, user reviews, multiple user profiles, product sorting, integrated chatbot support, and Razorpay payment gateway.

---

### 🔧 Technologies Used

- **Django** – Web framework powering the main backend
- **Flask** – Microservice for inventory management
- **SQLite** – Lightweight development database
- **HTML/CSS/JS** – Frontend technologies
- **OpenRouter API** – GenAI-powered chatbot integration
- **Razorpay** – Payment gateway for secure transactions

---

### 📁 Folder Structure

```
oaktrek_v3/
│
├── oaktrek_django/             # Main Django project
│   ├── auctions/               # Auction feature implementation
│   ├── CustomerSupportAI/      # Chatbot using OpenRouter API
│   ├── media/                  # Uploaded media files
│   ├── oaktrek_v2/             # Core project settings
│   ├── Profile/                # User profiles and auth system
│   ├── static/                 # CSS, JS, and image files
│   ├── Store/                  # Product listings, cart, orders
│   ├── templates/              # HTML templates
│   ├── db.sqlite3              # Main development database
│   ├── django_error.log        # Error logs
│   ├── manage.py               # Django entry point
│   ├── seed.py                 # Initial data seeding
│
├── oaktrek_flask/              # Flask inventory microservice
│   ├── app.py                  # Main Flask app
│   ├── inventory.db            # Inventory database
│   ├── migrate_products.py     # Inventory sync script
│
├── .gitignore
├── requirements.txt
└── .env                        # Environment variables
```

---

### 🚀 Installation & Setup Guide

#### 1. Clone the repository

```bash
git clone https://github.com/yourusername/oaktrek_v3.git
cd oaktrek_v3
```

#### 2. Create and activate a virtual environment

```bash
python -m venv env
source env/bin/activate      # For macOS/Linux
env\Scripts\activate         # For Windows
```

#### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

### ⚙️ Running the Django Server (Port 8000)

In **Terminal 1**:

```bash
cd oaktrek_django
python manage.py migrate
python manage.py runserver 8000
```

---

### ⚙️ Running the Flask Inventory API (Port 5000)

In **Terminal 2**:

```bash
cd oaktrek_flask
python app.py
```

---

### 🔐 Environment Variables (`.env`)

Create a `.env` file in the root directory with the following content:

```
OPENROUTER_API_KEY=your_openrouter_api_key
RAZORPAY_KEY_ID=your_razorpay_key
RAZORPAY_KEY_SECRET=your_razorpay_secret
DEBUG=True
```

---

### ✨ Features

- 🔍 **Product Sorting** by price and latest
- 📧 **Email Notifications** for signup and password changes via SMTP
- 👥 **Multiple User Profiles** (buyers, admins, etc.)
- 💬 **Chatbot** powered by OpenRouter for customer support
- 📦 **Inventory Microservice** built with Flask
- 💸 **Integrated Payments** using Razorpay
- 📝 **User Reviews** for products
- 🔨 **Live Auctions** feature for selected shoes

---


### 👥 Team

- **Rachit Goyal** – Project Lead & Full Stack Developer ([GitHub](https://github.com/rachitgoyal3313/))
- **Divyansh Chawla** – Full Stack Developer ([GitHub](https://github.com/Divy13ansh))
- **Pushkar Sharma** – BackEnd Developer ([GitHub](https://github.com/PushkarSharma18))
- **Pawani** – Frontend Developer ([GitHub](https://github.com/Pawani-29))

---

### 📄 License

This project is licensed under the MIT License.

---
