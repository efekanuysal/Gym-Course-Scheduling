# Gym Course Scheduling System

A scalable, modern web application and RESTful API designed to manage gym operations, including memberships, course scheduling, room allocations, and instructor assignments. Built with Python and a robust relational database schema to ensure data integrity and optimized querying.

---

## Architecture & Design

The system uses a hybrid architecture, providing both server-side rendered views for end-users and a fully documented REST API for decoupled client applications.

- **Role-Based Access Control (RBAC):** Distinct access levels and dashboards for Administrators, Instructors, and standard Members.
- **Stateless API Authentication:** Secure JSON Web Tokens (JWT) with token blacklisting for secure logouts.
- **Modular Routing:** Flask Blueprints isolate the API (`/api/v1`) from frontend rendering routes.

---

## Libraries & Dependencies

| Library | Version | Purpose |
|---|---|---|
| Flask | 2.3.2 | Core WSGI web application framework |
| Flask-SQLAlchemy | 3.1.1 | SQLAlchemy ORM integration |
| Flask-Migrate | 4.0.5 | Database schema version control |
| Flask-RESTX | latest | REST API structure + Swagger UI docs |
| PyJWT | latest | JWT generation and decoding |
| psycopg2-binary | latest | PostgreSQL database adapter |
| Flask-CORS | latest | Cross-Origin Resource Sharing |
| python-dotenv | 1.0.1 | Environment variable configuration |
| Werkzeug | latest | Secure password hashing |
| datetime & functools | stdlib | Token expiration and auth decorators |

---

## Installation & Setup

### Prerequisites

- Python 3.10+
- PostgreSQL server

### Steps

**1. Clone the repository and navigate to the root directory**

```bash
git clone <repository-url>
cd <project-directory>
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Configure the database**

Create a PostgreSQL database named `GymMembershipSystem` and ensure your local PostgreSQL server is running and accessible via:

```
postgresql://postgres:123@localhost/GymMembershipSystem
```

**4. Run the application**

```bash
python app.py
```

On first startup, the application will automatically:
- Initialize the database schema
- Seed default rooms
- Create foundational membership plans

---

## Default Credentials

An initial administrator account is created automatically on first startup:

| Field | Value |
|---|---|
| SSN (Username) | `ADMIN123` |
| Password | `admin123` |

> ⚠️ Change the default admin password after first login.

---

## API Documentation

The RESTful API is fully documented via an integrated Swagger UI. Once the server is running, navigate to:

```
http://localhost:5001/api/v1/docs
```
