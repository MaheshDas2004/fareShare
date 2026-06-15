
# 📊 FareShare

A Django-based expense sharing application that allows users to create groups, split expenses, manage settlements, and import bulk expenses via CSV with smart anomaly detection.

---

## 🚀 Features

* 👥 Group-based expense management
* 💸 Expense splitting (equal, shares, percentage)
* 🔄 Settlement tracking between users
* 📥 CSV bulk import system
* ⚠️ Smart anomaly detection with transparent reporting
* 📊 Import preview + user approval workflow

---

## 📂 Project Structure

```text
fareshare/
│
├── authentication/        # Authentication system
├── groups/          # Group & membership management
├── expenses/        # Expense tracking & splitting
├── settlements/     # Debt settlement tracking
├── common/          # Shared services (e.g. balance calculation)
├── importer/          # CSV import engine
|── config/          # Django settings & URLs
├── templates/       # UI templates
├── static/          # CSS/JS files
└── manage.py
```

---

## ⚙️ Setup Instructions

### 1️⃣ Clone Repository

```bash
git clone https://github.com/MaheshDas2004/fareShare.git
cd fareshare
```

---

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

---

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4️⃣ Configure Environment Variables

Create `.env` file:

```env
DB_NAME=fareshare_db
DB_USER=postgres
DB_PASSWORD="your-db-password"
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=your-django-secret-key
DEBUG=True
```

---

###change DB settings in `config/settings.py` to do local development with 
PostgreSQL:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    }
}
```

### 5️⃣ Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

---

### 6️⃣ Create Superuser

```bash
python manage.py createsuperuser
```

---

### 7️⃣ Run Server

```bash
python manage.py runserver
```

Open in browser:

```
http://127.0.0.1:8000/
```

---

## 📥 CSV Import Feature

### 🔄 Flow

```
Upload CSV
   ↓
Parse rows
   ↓
Detect anomalies
   ↓
Apply rules (skip / convert / modify)
   ↓
Generate report
   ↓
User approval
   ↓
Save to database
```

---

## ⚠️ Supported Anomalies & Policies

| Issue                    | Policy                         |
| ------------------------ | ------------------------------ |
| Duplicate expense        | Skip duplicate entry           |
| Missing paid_by          | Skip row                       |
| Missing currency         | Default INR                    |
| Zero amount              | Skip row                       |
| Negative amount          | Convert to refund              |
| Settlement text detected | Convert to settlement          |
| Invalid date format      | Best-effort parsing            |
| Member not in group      | Ignore invalid member in split |

---

## 🧾 Example CSV

```csv
description,amount,paid_by,currency
Dinner,500,Rohan,INR
Swiggy,0,Aisha,INR
Rent,,Rohan,INR
Rohan paid Aisha back,1000,Rohan,INR
```

---

## 📊 Import Report Example

```
✔ 2 expenses imported
⚠ 2 rows skipped

Details:
- Row 2 skipped (zero amount)
- Row 3 skipped (missing amount)
```

---

## 🧠 Design Philosophy

* No crashes during import
* No silent assumptions
* Every anomaly is visible to the user
* Rule-based validation before saving data

---

## 🔮 Future Improvements

* Real-time CSV validation UI
* Advanced duplicate detection
* Support for more complex split types (e.g. adjustments, multi-level splits and simplify debts)
* activity logging

---

## 👨‍💻 Author

**FareShare** — A Django-based expense sharing system with smart CSV import and transparent validation pipeline.

---

