# 💰 Personal Finance Tracker (Django + PostgreSQL + AI)

A robust, feature-rich financial management application built with **Django 5.1**. Designed to help users track income/expenses, visualize spending trends, set budgets, and receive **AI-powered financial insights**.


## 📌 Introduction

The **Personal Finance Tracker** is a modern web application that simplifies financial management. It goes beyond simple tracking by integrating **DeepSeek AI** to provide personalized financial advice and spending anomaly detection. With a responsive dark-themed UI, bank statement parsing, and comprehensive reporting, it serves as a complete solution for personal finance.

---

## 🏗️ System Architecture

The application follows a monolithic architecture with modular Django apps, integrated with external services for AI, Email, and Authentication.

```mermaid
graph TD
    User([Clients Web/Mobile]) -->|HTTPS| Nginx[Web Server]
    Nginx -->|WSGI| Django[Django App Server]
    
    subgraph "Core Backend (Django)"
        Django --> Auth[Authentication Allauth]
        Django --> Trans[Transaction Engine]
        Django --> Report[Reporting System]
        Django --> AI[AI Service Layer]
    end
    
    subgraph "Data Layer"
        Django -->|SQL| DB[(PostgreSQL Database)]
        Django -->|Media| Storage[File Storage Receipts/PDFs]
    end
    
    subgraph "External Services"
        AI -->|API| DeepSeek[OpenRouter / DeepSeek API]
        Auth -->|OAuth| Google[Google Identity Platform]
        Django -->|SMTP/API| SendGrid[SendGrid Email Service]
    end
```

---

## 🔄 Data Flow: AI Insights

The AI Assistant flow demonstrates how user data is securely processed to generate insights.

```mermaid
sequenceDiagram
    participant User
    participant View as Django View
    participant DB as PostgreSQL
    participant AI as AI Service
    participant LLM as DeepSeek API
    
    User->>View: Request AI Chat / Insights
    View->>DB: Fetch Recent Transactions (30 days)
    DB-->>View: Transaction Data
    View->>View: Aggregate Totals (Income/Expense/Savings)
    View->>AI: Prepare Prompt with Context
    AI->>LLM: Send Context + User Query
    LLM-->>AI: Financial Advice / Answer
    AI-->>View: Formatted Markdown Response
    View-->>User: Display Chat Response
```
---
## 🚀 Key Features

### 📊 Interactive Dashboard
- **Real-time Overview**: Instant view of total balance, income, expenses, and savings.
- **Visual Analytics**: Dynamic charts (Income vs Expense, Category Breakdown) using **Chart.js**.
- **Recent Activity**: Quick access to latest transactions with color-coded status.

### 🤖 AI Financial Assistant
- **Smart Chat Interface**: Chat with your financial data using **DeepSeek AI** (via OpenRouter).
- **Context-Aware**: The AI automatically knows your monthly spending, income, and savings context.
- **Spending Insights**: Automated detection of spending anomalies and personalized financial advice.

### 💳 Transaction Management
- **Comprehensive Tracking**: Log income and expenses with categories, dates, and descriptions.
- **Receipt Uploads**: Attach images/PDFs to transactions for record-keeping.
- **Multi-Currency Support**: Track transactions in different currencies with automatic conversion estimates.

### 🏦 Bank Integration
- **Statement Import**: Upload **PDF** or **CSV** bank statements.
- **Auto-Categorization**: Intelligent mapping of bank description patterns to your categories.
- **Duplicate Detection**: Smart logic prevents double-entry of transactions.

### 📉 Reports & Export
- **Monthly Reports**: Detailed month-over-month comparison.
- **Category Analysis**: Deep dive into where your money goes.
- **Export Options**: Download reports as **CSV** or **PDF** for offline analysis.

### 🔔 Smart Notifications
- **Budget Alerts**: Email notifications when you exceed category budgets (Integrated with **SendGrid**).
- **Weekly Summaries**: Scheduled emails with your financial health summary.

### 🔒 Security & Auth
- **Google OAuth**: Fast and secure login with Google (via **Django Allauth**).
- **Role-Based Access**: Secure data isolation ensures users only see their own data.

---

## 🛠️ Tech Stack

| Component | Technology | Description |
|-----------|------------|-------------|
| **Backend** | Django 5.1 | Python Web Framework |
| **Language** | Python 3.12 | Core logic and scripting |
| **Database** | PostgreSQL 17 | Relational Data Storage |
| **Frontend** | HTML5, CSS3, JS | Custom Dark Theme UI |
| **Visualization** | Chart.js | Interactive Graphs |
| **AI Module** | DeepSeek (OpenRouter) | LLM for Insights |
| **Authentication** | Django Allauth | Google OAuth2 & Local Auth |
| **Email** | SendGrid | Transactional Emails |
| **PDF Generation** | WeasyPrint | Report Exporting |
| **Data Analysis** | Pandas | Bank Statement Parsing |

---

## 📂 Project Structure

```bash
finance_tracker/
├── apps/
│   ├── accounts/       # User profile & authentication
│   ├── transactions/   # Core transaction logic
│   ├── budgets/        # Budgeting & alerts
│   ├── reports/        # Analytics & PDF/CSV export
│   ├── ai_features/    # Chatbot & Insights
│   ├── bank_import/    # Statement parsing engine
│   ├── categories/     # Category management
│   └── notifications/  # Email & system notifications
├── templates/          # HTML Templates (Tailwind-style)
├── static/             # CSS, JS, Images
├── media/              # User uploads (Receipts)
└── manage.py           # Django CLI
```

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.10+
- PostgreSQL
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/SatyamSingh-Git/FJ-BE-R2-Satyam-Singh-NIT-Delhi.git
cd FJ-BE-R2-Satyam-Singh-NIT-Delhi
```

### 2. Create Virtual Environment
```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file in the root directory with the following variables:
```env
DEBUG=True
SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://postgres:password@localhost:5432/finance_tracker
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
OPENROUTER_API_KEY=your_deepseek_api_key
SENDGRID_API_KEY=your_sendgrid_key
email_host_user=your_email
email_host_password=your_app_password
```

### 5. Database Setup
```bash
# Create database
createdb -U postgres finance_tracker

# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser
```

### 6. Run the Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000` to access the application.

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
