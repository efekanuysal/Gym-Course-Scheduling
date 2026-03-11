Gym Course Scheduling System
A scalable, modern web application and RESTful API designed to manage gym operations, including memberships, course scheduling, room allocations, and instructor assignments. The system is built using Python and leverages a robust relational database schema to ensure data integrity and optimized querying.

Architecture & Design
The system employs a hybrid architecture, providing both server-side rendered views for end-users and a fully documented REST API for potential decoupled client applications.

Role-Based Access Control (RBAC): Distinct access levels and dashboards for Administrators, Instructors, and standard Members.

Stateless API Authentication: Implements secure JSON Web Tokens (JWT) for the API namespace, complete with token blacklisting capabilities for secure logouts.

Modular Routing: Utilizes Flask Blueprints to isolate the API (/api/v1) from the frontend rendering routes.

Libraries and Modules
The project relies on the following core libraries and modules to ensure modularity and performance:

Flask (2.3.2): The core WSGI web application framework.

Flask-SQLAlchemy (3.1.1): An extension providing SQLAlchemy ORM integration for structural, object-oriented database interactions.

Flask-Migrate (4.0.5): Handles SQLAlchemy database migrations for schema version control.

Flask-RESTX: Utilized to build the structured REST API and automatically generate Swagger UI documentation.

PyJWT: Generates and decodes JSON Web Tokens for stateless API authentication and authorization.

psycopg2-binary: The PostgreSQL database adapter for Python.

Flask-CORS: Manages Cross-Origin Resource Sharing, enabling secure API consumption from diverse client origins.

python-dotenv (1.0.1): Loads environment variables for secure configuration management.

Werkzeug: Utilized specifically for secure password hashing (generate_password_hash, check_password_hash).

datetime & functools: Standard Python modules used for token expiration logic and authentication decorators.

Installation & Setup
Prerequisites:

Python 3.10+

PostgreSQL server

1. Clone the repository and navigate to the root directory

2. Install dependencies

Bash
pip install -r requirements.txt
3. Configure the Database
Create a PostgreSQL database named GymMembershipSystem. Ensure your local PostgreSQL server is running and accessible via the credentials specified in the application configuration (postgresql://postgres:123@localhost/GymMembershipSystem).

4. Run the Application

Bash
python app.py
The application will automatically initialize the database schema, seed default rooms, and create foundational membership plans upon startup.

Default Credentials
An initial administrative account is automatically generated during the first startup:

SSN (Username): ADMIN123

Password: admin123

API Documentation
The RESTful API endpoints are thoroughly documented and can be interacted with directly via the integrated Swagger UI. Once the server is running, navigate to:
http://localhost:5001/api/v1/docs
