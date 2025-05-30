from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_restx import Api, Resource, fields, abort
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import abort

"""
This file contains the Flask app configuration and API endpoints.
It also includes authentication and database models."""
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:123@localhost/GymMembershipSystem'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-change-this'  # Change this to a secure secret key
CORS(app)

authorizations = {
    'Bearer': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': "Type 'Bearer' followed by your token"
    }
}

db = SQLAlchemy(app)
migrate = Migrate(app, db)
api = Api(app, version='1.0', title='Gym Course Scheduling API',
          description='API for managing gym courses, rooms, users, and schedules',
          authorizations=authorizations, 
          )

# ------------ AUTHENTICATION DECORATOR ----------------

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Check for token in Authorization header
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]

        if not token:
            abort(401, 'Token is missing')

        if is_token_blacklisted(token):
            abort(401, 'Token is blacklisted')

        try:
            # Decode the token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])

            # Fetch the user from the database
            current_user = Users.query.get(data['ssn'])

            if not current_user:
                abort(401, 'User not found')

        except jwt.ExpiredSignatureError:
            abort(401, 'Token has expired')
        except jwt.InvalidTokenError:
            abort(401, 'Invalid token')

        # Pass the current_user to the next function
        return f(current_user, *args, **kwargs)

    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        # Debugging logs to help trace the issue
        print(f"DEBUG: Admin Check for User: {current_user}")
        print(f"DEBUG: User Type: {type(current_user)}")
        print(f"DEBUG: User Attributes: {dir(current_user)}")

        # Check if the user is an admin
        if not current_user or not hasattr(current_user, 'membershipType') or current_user.membershipType != 'ad':
            abort(403, 'Admin privileges required')

        # Proceed to the next function
        return f(current_user, *args, **kwargs)

    return decorated

# ------------Logout Mechanism Functions----------------
def blacklist_token(token):
    blacklisted_token = Blacklist(token=token)
    db.session.add(blacklisted_token)
    db.session.commit()

def is_token_blacklisted(token):
    blacklisted = Blacklist.query.filter_by(token=token).first()
    return bool(blacklisted)

# ------------ MODELS (Updated with password) ----------------

class Blacklist(db.Model):
    __tablename__ = 'Blacklist'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    token = db.Column(db.String(500), unique=True, nullable=False)
    blacklisted_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __init__(self, token):
        self.token = token

class Membership(db.Model):
    __tablename__ = 'Membership'
    sign = db.Column(db.String(2), primary_key=True)  # PRIMARY KEY
    fee = db.Column(db.Numeric(7, 2), nullable=False)  # Decimal(7,2)
    typeName = db.Column(db.String(10), nullable=False)
    plan = db.Column(db.String(8), nullable=False)

    def to_dict(self):
        return {
            'sign': self.sign,
            'fee': self.fee,
            'typeName': self.typeName,
            'plan': self.plan
        }

class Users(db.Model):
    __tablename__ = 'Users'
    SSN = db.Column(db.String(20), primary_key=True)
    firstName = db.Column(db.String(50), nullable=False)
    lastName = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)  # Added password field
    membershipType = db.Column(db.String(2), db.ForeignKey('Membership.sign'))
    membership = db.relationship('Membership', backref='users')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Phone(db.Model):
    __tablename__ = 'Phone'
    phone = db.Column(db.String(20), primary_key=True)
    userSSN = db.Column(db.String(20), db.ForeignKey('Users.SSN', ondelete='CASCADE'))
    user = db.relationship('Users', backref='phones')


class Instructors(db.Model):
    __tablename__ = 'Instructors'
    SSN = db.Column(db.String(20), primary_key=True)
    firstName = db.Column(db.String(50), nullable=False)
    lastName = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))


class Room(db.Model):
    __tablename__ = 'Room'
    ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    roomName = db.Column(db.String(20), nullable=False)


class Course(db.Model):
    __tablename__ = 'Course'
    courseName = db.Column(db.String(20), primary_key=True)
    capacity = db.Column(db.Numeric(2), nullable=False)
    isSpecial = db.Column(db.Boolean, nullable=False)
    InstructorID = db.Column(db.String(20), db.ForeignKey('Instructors.SSN'), nullable=False)
    roomId = db.Column(db.Integer, db.ForeignKey('Room.ID'), nullable=False)
    instructor = db.relationship('Instructors', backref='courses')
    room = db.relationship('Room', backref='courses')


class RoomSchedule(db.Model):
    __tablename__ = 'RoomSchedule'
    scheduleID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    roomId = db.Column(db.Integer, db.ForeignKey('Room.ID', ondelete='CASCADE'), nullable=False)
    scheduleDate = db.Column(db.Date, nullable=False)
    scheduleTime = db.Column(db.Time, nullable=False)
    bookingType = db.Column(db.String(10), nullable=False)
    userID = db.Column(db.String(20), db.ForeignKey('Users.SSN', ondelete='CASCADE'))
    courseName = db.Column(db.String(20), db.ForeignKey('Course.courseName', ondelete='CASCADE'))
    isBooked = db.Column(db.Boolean, nullable=False)
    room = db.relationship('Room', backref='schedules')
    user = db.relationship('Users', backref='room_bookings')
    course = db.relationship('Course', backref='room_schedules')


class User_Course(db.Model):
    __tablename__ = 'User_Course'
    courseName = db.Column(db.String(20), db.ForeignKey('Course.courseName', ondelete='CASCADE'), primary_key=True)
    userID = db.Column(db.String(20), db.ForeignKey('Users.SSN', ondelete='CASCADE'), primary_key=True)
    user = db.relationship('Users', backref='enrolled_courses')
    course = db.relationship('Course', backref='enrolled_users')


class Feedback(db.Model):
    __tablename__ = 'Feedback'
    feedBackNo = db.Column(db.Integer, primary_key=True, autoincrement=True)
    roomId = db.Column(db.Integer, db.ForeignKey('Room.ID', ondelete='CASCADE'), nullable=False)
    userID = db.Column(db.String(20), db.ForeignKey('Users.SSN', ondelete='CASCADE'), nullable=False)
    scheduleID = db.Column(db.Integer, db.ForeignKey('RoomSchedule.scheduleID', ondelete='CASCADE'), nullable=False)
    score = db.Column(db.Numeric(2, 1), nullable=False)
    comment = db.Column(db.String(200))
    room = db.relationship('Room', backref='feedbacks')
    user = db.relationship('Users', backref='feedbacks')
    schedule = db.relationship('RoomSchedule', backref='feedbacks')


# ------------ SWAGGER MODELS (Updated) ----------------

# Auth models
login_model = api.model('Login', {
    'SSN': fields.String(required=True, description='User SSN'),
    'password': fields.String(required=True, description='User password')
})

register_model = api.model('Register', {
    'SSN': fields.String(required=True, description='Social Security Number'),
    'firstName': fields.String(required=True, description='First name'),
    'lastName': fields.String(required=True, description='Last name'),
    'password': fields.String(required=True, description='Password'),
    'membershipType': fields.String(description='Membership type sign')
})

membership_model = api.model('Membership', {
    'sign': fields.String(required=True, enum=['em', 'ea', 'rm', 'ra', 'am', 'aa', 'ad', 'in'], description='Membership signature'),
    'fee': fields.Float(required=True, description='Membership fee'),
    'typeName': fields.String(required=True, description='Type name (e.g., "economy")'),
    'plan': fields.String(required=True, description='Plan type (e.g., "monthly")')
})

user_model = api.model('Users', {
    'SSN': fields.String(required=True, description='Social Security Number'),
    'firstName': fields.String(required=True, description='First name'),
    'lastName': fields.String(required=True, description='Last name'),
    'membershipType': fields.String(description='Membership type sign')
})

phone_model = api.model('Phone', {
    'phone': fields.String(required=True, description='Phone number'),
    'userSSN': fields.String(description='User SSN')
})

instructor_model = api.model('Instructors', {
    'SSN': fields.String(required=True, description='Instructor SSN'),
    'firstName': fields.String(required=True, description='First name'),
    'lastName': fields.String(required=True, description='Last name'),
    'phone': fields.String(description='Phone number')
})

room_model = api.model('Room', {
    'ID': fields.Integer(readOnly=True, description='Room ID'),
    'roomName': fields.String(required=True, description='Room name')
})

course_model = api.model('Course', {
    'courseName': fields.String(required=True, description='Course name'),
    'capacity': fields.Integer(required=True, description='Course capacity'),
    'isSpecial': fields.Boolean(required=True, description='Is special course'),
    'InstructorID': fields.String(required=True, description='Instructor SSN'),
    'roomId': fields.Integer(required=True, description='Room ID')
})

roomschedule_model = api.model('RoomSchedule', {
    'scheduleID': fields.Integer(readOnly=True),
    'roomId': fields.Integer(required=True),
    'scheduleDate': fields.Date(required=True),
    'scheduleTime': fields.String(required=True),  # Time field as string
    'bookingType': fields.String(required=True, enum=['cleaning', 'class', 'private']),
    'userID': fields.String(description='User SSN for private bookings'),
    'courseName': fields.String(description='Course name for class bookings'),
    'isBooked': fields.Boolean(required=True)
})

user_course_model = api.model('User_Course', {
    'courseName': fields.String(required=True),
    'userID': fields.String(required=True, description='User SSN')
})

feedback_model = api.model('Feedback', {
    'feedBackNo': fields.Integer(readOnly=True),
    'roomId': fields.Integer(required=True),
    'userID': fields.String(required=True, description='User SSN'),
    'scheduleID': fields.Integer(required=True),
    'score': fields.Float(required=True, description='Rating score'),
    'comment': fields.String(description='Feedback comment')
})


# ------------ AUTHENTICATION ENDPOINTS ----------------

# ------------ WEB ROUTES ----------------

@app.route('/')
def home():
    if 'user_token' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        ssn = request.form.get('ssn')
        password = request.form.get('password')

        user = Users.query.get(ssn)
        if not user or not user.check_password(password):
            flash('Invalid credentials', 'danger')
            return redirect(url_for('login'))

        # Generate token
        token = jwt.encode({
            'ssn': user.SSN,
            'membershipType': user.membershipType,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')

        session['user_token'] = token
        session['user_ssn'] = user.SSN
        session['user_type'] = user.membershipType
        session['user_name'] = f"{user.firstName} {user.lastName}"

        return redirect(url_for('dashboard'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        ssn = request.form.get('ssn')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        password = request.form.get('password')
        membership_type = request.form.get('membership_type')

        if Users.query.get(ssn):
            flash('User already exists', 'danger')
            return redirect(url_for('register'))

        if membership_type and not Membership.query.get(membership_type):
            flash('Invalid membership type', 'danger')
            return redirect(url_for('register'))

        user = Users(
            SSN=ssn,
            firstName=first_name,
            lastName=last_name,
            membershipType=membership_type
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    memberships = Membership.query.filter(Membership.sign.notin_(['ad', 'in'])).all()
    return render_template('register.html', memberships=memberships)


@app.route('/dashboard')
def dashboard():
    if 'user_token' not in session:
        return redirect(url_for('login'))

    try:
        # Verify token
        jwt.decode(session['user_token'], app.config['SECRET_KEY'], algorithms=['HS256'])
    except:
        session.clear()
        return redirect(url_for('login'))

    user_type = session['user_type']

    if user_type == 'ad':
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('member_dashboard'))


@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_token' not in session or session['user_type'] != 'ad':
        return redirect(url_for('login'))

    return render_template('admin/dashboard.html')


@app.route('/member/dashboard')
def member_dashboard():
    if 'user_token' not in session:
        return redirect(url_for('login'))

    user_ssn = session['user_ssn']
    enrolled_courses = User_Course.query.filter_by(userID=user_ssn).all()
    bookings = RoomSchedule.query.filter_by(userID=user_ssn).all()

    return render_template('member/dashboard.html',
                           enrolled_courses=enrolled_courses,
                           bookings=bookings)


@app.route('/logout')
def logout():
    if 'user_token' in session:
        token = session['user_token']
        if not is_token_blacklisted(token):
            blacklist_token(token)
    session.clear()
    return redirect(url_for('login'))


# Admin Management Routes
@app.route('/admin/users')
def admin_users():
    if 'user_token' not in session or session['user_type'] != 'ad':
        return redirect(url_for('login'))

    users = Users.query.all()
    return render_template('admin/users.html', users=users)


@app.route('/admin/courses')
def admin_courses():
    if 'user_token' not in session or session['user_type'] != 'ad':
        return redirect(url_for('login'))

    courses = Course.query.all()
    instructors = Instructors.query.all()
    rooms = Room.query.all()
    return render_template('admin/courses.html',
                           courses=courses,
                           instructors=instructors,
                           rooms=rooms)


@app.route('/admin/rooms')
def admin_rooms():
    if 'user_token' not in session or session['user_type'] != 'ad':
        return redirect(url_for('login'))

    rooms = Room.query.all()
    return render_template('admin/rooms.html', rooms=rooms)


@app.route('/admin/schedules')
def admin_schedules():
    if 'user_token' not in session or session['user_type'] != 'ad':
        return redirect(url_for('login'))

    schedules = RoomSchedule.query.all()
    courses = Course.query.all()
    users = Users.query.all()
    rooms = Room.query.all()

    return render_template('admin/schedules.html',
                           schedules=schedules,
                           courses=courses,
                           users=users,
                           rooms=rooms)


# Member Routes
@app.route('/member/profile')
def member_profile():
    if 'user_token' not in session:
        return redirect(url_for('login'))

    user = Users.query.get(session['user_ssn'])
    phones = Phone.query.filter_by(userSSN=session['user_ssn']).all()

    return render_template('member/profile.html', user=user, phones=phones)


@app.route('/member/courses')
def member_courses():
    if 'user_token' not in session:
        return redirect(url_for('login'))

    all_courses = Course.query.all()
    enrolled_courses = User_Course.query.filter_by(userID=session['user_ssn']).all()
    enrolled_course_names = [ec.courseName for ec in enrolled_courses]

    return render_template('member/courses.html',
                           courses=all_courses,
                           enrolled_courses=enrolled_course_names)


@app.route('/member/bookings')
def member_bookings():
    if 'user_token' not in session:
        return redirect(url_for('login'))

    bookings = RoomSchedule.query.filter_by(userID=session['user_ssn']).all()
    return render_template('member/bookings.html', bookings=bookings)


# API AJAX Endpoints
@app.route('/api/enroll_course', methods=['POST'])
def enroll_course():
    if 'user_token' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    course_name = request.json.get('course_name')
    user_id = session['user_ssn']

    # Check if already enrolled
    existing = User_Course.query.filter_by(
        courseName=course_name,
        userID=user_id
    ).first()
    if existing:
        return jsonify({'success': False, 'message': 'Already enrolled'}), 400

    enrollment = User_Course(courseName=course_name, userID=user_id)
    db.session.add(enrollment)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Enrolled successfully'})


@app.route('/api/book_room', methods=['POST'])
def book_room():
    if 'user_token' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    data = request.json
    user_id = session['user_ssn']

    # Validate data
    if not all(key in data for key in ['room_id', 'date', 'time', 'booking_type']):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    # Create booking
    booking = RoomSchedule(
        roomId=data['room_id'],
        scheduleDate=datetime.strptime(data['date'], '%Y-%m-%d').date(),
        scheduleTime=datetime.strptime(data['time'], '%H:%M').time(),
        bookingType=data['booking_type'],
        userID=user_id,
        isBooked=True
    )

    db.session.add(booking)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Booking successful'})

@api.route('/auth/register')
class Register(Resource):
    @api.expect(register_model)
    def post(self):
        """Register a new user"""
        data = api.payload

        # Check if user already exists
        if Users.query.get(data['SSN']):
            abort(400, 'User already exists')

        # Check if membership type exists
        if data.get('membershipType') and not Membership.query.get(data['membershipType']):
            abort(400, 'Membership type not found')

        # Create new user
        user = Users(
            SSN=data['SSN'],
            firstName=data['firstName'],
            lastName=data['lastName'],
            membershipType=data.get('membershipType')
        )
        user.set_password(data['password'])

        db.session.add(user)
        db.session.commit()

        return {'message': 'User registered successfully'}, 201


@api.route('/auth/login')
class Login(Resource):
    @api.expect(login_model)
    def post(self):
        """Login user and get token"""
        data = api.payload

        user = Users.query.get(data['SSN'])
        if not user or not user.check_password(data['password']):
            abort(401, 'Invalid credentials')

        # Generate token
        token = jwt.encode({
            'ssn': user.SSN,
            'membershipType': user.membershipType,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')

        return {
            'token': token,
            'user': {
                'SSN': user.SSN,
                'firstName': user.firstName,
                'lastName': user.lastName,
                'membershipType': user.membershipType
            }
        }
@api.route('/auth/logout')
class Logout(Resource):
    @api.doc(security='Bearer')
    @token_required
    def post(self, current_user):
        """Logout user and blacklist the token"""
        # Extract the token from the Authorization header
        token = request.headers.get('Authorization').split(" ")[1]

        # Check if token is already blacklisted
        if is_token_blacklisted(token):
            abort(400, 'Token is already blacklisted')

        # Blacklist the token
        blacklist_token(token)
        return {'message': 'Successfully logged out'}, 200

# ------------ API ENDPOINTS (Updated with Authentication) -----------------

# -------- Membership Endpoints --------
@api.route('/memberships')
class MembershipList(Resource):
    @api.marshal_list_with(membership_model)
    def get(self):
        """Get all memberships"""
        return Membership.query.all()

    @api.expect(membership_model)
    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def post(self, current_user):
        """Create a new membership"""
        data = api.payload
        if Membership.query.get(data['sign']):
            abort(400, 'Membership already exists')
        membership = Membership(**data)
        db.session.add(membership)
        db.session.commit()
        return {'message': 'Membership created'}, 201


@api.route('/memberships/<string:sign>')
class MembershipResource(Resource):
    @api.marshal_with(membership_model)
    def get(self, sign):
        """Get membership by sign"""
        return Membership.query.get_or_404(sign)

    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def delete(self, current_user, sign):
        """Delete membership"""
        membership = Membership.query.get_or_404(sign)
        db.session.delete(membership)
        db.session.commit()
        return {'message': 'Membership deleted'}

    @api.expect(membership_model)
    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def put(self, current_user, sign):
        """Update membership"""
        membership = Membership.query.get_or_404(sign)
        data = api.payload
        membership.fee = data.get('fee', membership.fee)
        membership.typeName = data.get('typeName', membership.typeName)
        membership.plan = data.get('plan', membership.plan)
        db.session.commit()
        return {'message': 'Membership updated'}


# -------- User Endpoints --------
@api.route('/users')
class UsersList(Resource):
    @api.marshal_list_with(user_model)
    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def get(self, current_user):
        """Get all users"""
        return Users.query.all()


@api.route('/users/<string:ssn>')
class UsersResource(Resource):
    @api.marshal_with(user_model)
    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def get(self, current_user, ssn):
        """Get user by SSN"""
        user = Users.query.get_or_404(ssn)
        return user

    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def delete(self, current_user, ssn):
        """Delete user"""
        user = Users.query.get_or_404(ssn)
        db.session.delete(user)
        db.session.commit()
        return {'message': 'User deleted'}

    @api.expect(user_model)
    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def put(self, current_user, ssn):
        """Update user"""
        user = Users.query.get_or_404(ssn)
        data = api.payload
        user.firstName = data.get('firstName', user.firstName)
        user.lastName = data.get('lastName', user.lastName)
        if 'membershipType' in data:
            if data['membershipType'] and not Membership.query.get(data['membershipType']):
                abort(400, 'Membership type not found')
            user.membershipType = data['membershipType']
        db.session.commit()
        return {'message': 'User updated'}


# -------- Phone Endpoints --------
@api.route('/phones')
class PhoneList(Resource):
    @api.marshal_list_with(phone_model)
    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def get(self, current_user):
        """Get all phones"""
        return Phone.query.all()

    @api.expect(phone_model)
    @api.doc(security='Bearer')
    @token_required
    def post(self, current_user):
        """Create a new phone"""
        data = api.payload
        if Phone.query.get(data['phone']):
            abort(400, 'Phone number already exists')
        if data.get('userSSN') and not Users.query.get(data['userSSN']):
            abort(400, 'User not found')
        phone = Phone(**data)
        db.session.add(phone)
        db.session.commit()
        return {'message': 'Phone created'}, 201


@api.route('/phones/<string:phone_number>')
class PhoneResource(Resource):
    @api.marshal_with(phone_model)
    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def get(self, current_user, phone_number):
        """Get phone by number"""
        phone = Phone.query.get_or_404(phone_number)
        return phone

    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def delete(self, current_user, phone_number):
        """Delete phone"""
        phone = Phone.query.get_or_404(phone_number)
        db.session.delete(phone)
        db.session.commit()
        return {'message': 'Phone deleted'}


# -------- Instructor Endpoints --------
@api.route('/instructors')
class InstructorsList(Resource):
    @api.marshal_list_with(instructor_model)
    def get(self):
        """Get all instructors"""
        return Instructors.query.all()

    @api.expect(instructor_model)
    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def post(self, current_user):
        """Create a new instructor"""
        data = api.payload
        if Instructors.query.get(data['SSN']):
            abort(400, 'Instructor already exists')
        instructor = Instructors(**data)
        db.session.add(instructor)
        db.session.commit()
        return {'message': 'Instructor created'}, 201


@api.route('/instructors/<string:ssn>')
class InstructorsResource(Resource):
    @api.marshal_with(instructor_model)
    def get(self, ssn):
        """Get instructor by SSN"""
        instructor = Instructors.query.get_or_404(ssn)
        return instructor

    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def delete(self, current_user, ssn):
        """Delete instructor"""
        instructor = Instructors.query.get_or_404(ssn)
        db.session.delete(instructor)
        db.session.commit()
        return {'message': 'Instructor deleted'}

    @api.expect(instructor_model)
    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def put(self, current_user, ssn):
        """Update instructor"""
        instructor = Instructors.query.get_or_404(ssn)
        data = api.payload
        instructor.firstName = data.get('firstName', instructor.firstName)
        instructor.lastName = data.get('lastName', instructor.lastName)
        instructor.phone = data.get('phone', instructor.phone)
        db.session.commit()
        return {'message': 'Instructor updated'}


# -------- Room Endpoints --------
@api.route('/rooms')
class RoomList(Resource):
    @api.marshal_list_with(room_model)
    def get(self):
        """Get all rooms"""
        return Room.query.all()

    @api.expect(room_model)
    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def post(self, current_user):
        """Create a new room"""
        data = api.payload
        room = Room(roomName=data['roomName'])
        db.session.add(room)
        db.session.commit()
        return {'message': 'Room created'}, 201


@api.route('/rooms/<int:room_id>')
class RoomResource(Resource):
    @api.marshal_with(room_model)
    def get(self, room_id):
        """Get room by ID"""
        room = Room.query.get_or_404(room_id)
        return room

    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def delete(self, current_user, room_id):
        """Delete room"""
        room = Room.query.get_or_404(room_id)
        db.session.delete(room)
        db.session.commit()
        return {'message': 'Room deleted'}

    @api.expect(room_model)
    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def put(self, current_user, room_id):
        """Update room"""
        room = Room.query.get_or_404(room_id)
        data = api.payload
        room.roomName = data.get('roomName', room.roomName)
        db.session.commit()
        return {'message': 'Room updated'}


# -------- Course Endpoints --------
@api.route('/courses')
class CourseList(Resource):
    @api.marshal_list_with(course_model)
    def get(self):
        """Get all courses"""
        return Course.query.all()

    @api.expect(course_model)
    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def post(self, current_user):
        """Create a new course"""
        data = api.payload
        if Course.query.get(data['courseName']):
            abort(400, 'Course already exists')
        if not Instructors.query.get(data['InstructorID']):
            abort(400, 'Instructor not found')
        if not Room.query.get(data['roomId']):
            abort(400, 'Room not found')
        course = Course(**data)
        db.session.add(course)
        db.session.commit()
        return {'message': 'Course created'}, 201


@api.route('/courses/<string:course_name>')
class CourseResource(Resource):
    @api.marshal_with(course_model)
    def get(self, course_name):
        """Get course by name"""
        course = Course.query.get_or_404(course_name)
        return course

    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def delete(self, current_user, course_name):
        """Delete course"""
        course = Course.query.get_or_404(course_name)
        db.session.delete(course)
        db.session.commit()
        return {'message': 'Course deleted'}

    @api.expect(course_model)
    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def put(self, current_user, course_name):
        """Update course"""
        course = Course.query.get_or_404(course_name)
        data = api.payload
        course.capacity = data.get('capacity', course.capacity)
        course.isSpecial = data.get('isSpecial', course.isSpecial)
        if 'InstructorID' in data:
            if not Instructors.query.get(data['InstructorID']):
                abort(400, 'Instructor not found')
            course.InstructorID = data['InstructorID']
        if 'roomId' in data:
            if not Room.query.get(data['roomId']):
                abort(400, 'Room not found')
            course.roomId = data['roomId']
        db.session.commit()
        return {'message': 'Course updated'}


# -------- RoomSchedule Endpoints --------
@api.route('/roomschedules')
class RoomScheduleList(Resource):
    @api.marshal_list_with(roomschedule_model)
    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def get(self, current_user):
        """Get all room schedules"""
        return RoomSchedule.query.all()

    @api.expect(roomschedule_model)
    @api.doc(security='Bearer')
    @token_required
    def post(self, current_user):
        """Create a new room schedule"""
        data = api.payload
        if not Room.query.get(data['roomId']):
            abort(400, 'Room not found')

        # Validate booking type constraints
        if data['bookingType'] == 'class' and not data.get('courseName'):
            abort(400, 'Course name required for class booking')
        if data['bookingType'] == 'private' and not data.get('userID'):
            abort(400, 'User ID required for private booking')
        if data['bookingType'] == 'class' and not Course.query.get(data['courseName']):
            abort(400, 'Course not found')
        if data['bookingType'] == 'private' and not Users.query.get(data['userID']):
            abort(400, 'User not found')

        schedule = RoomSchedule(**data)
        db.session.add(schedule)
        db.session.commit()
        return {'message': 'Room schedule created'}, 201


@api.route('/roomschedules/<int:schedule_id>')
class RoomScheduleResource(Resource):
    @api.marshal_with(roomschedule_model)
    @api.doc(security='Bearer')
    @token_required
    def get(self, current_user, schedule_id):
        """Get room schedule by ID"""
        schedule = RoomSchedule.query.get_or_404(schedule_id)
        return schedule

    @api.doc(security='Bearer')
    @token_required
    def delete(self, current_user, schedule_id):
        """Delete room schedule"""
        schedule = RoomSchedule.query.get_or_404(schedule_id)
        db.session.delete(schedule)
        db.session.commit()
        return {'message': 'Room schedule deleted'}


# -------- User_Course Endpoints --------
@api.route('/user_courses')
class UserCourseList(Resource):
    @api.marshal_list_with(user_course_model)
    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def get(self, current_user):
        """Get all user course enrollments"""
        return User_Course.query.all()

    @api.expect(user_course_model)
    @api.doc(security='Bearer')
    @token_required
    def post(self, current_user):
        """Enroll user in course"""
        data = api.payload
        if not Course.query.get(data['courseName']):
            abort(400, 'Course not found')
        if not Users.query.get(data['userID']):
            abort(400, 'User not found')

        # Check if already enrolled
        existing = User_Course.query.filter_by(
            courseName=data['courseName'],
            userID=data['userID']
        ).first()
        if existing:
            abort(400, 'User already enrolled in this course')

        enrollment = User_Course(**data)
        db.session.add(enrollment)
        db.session.commit()
        return {'message': 'User enrolled in course'}, 201


@api.route('/user_courses/<string:course_name>/<string:user_id>')
class UserCourseResource(Resource):
    @api.doc(security='Bearer')
    @token_required
    def delete(self, current_user, course_name, user_id):
        """Remove user from course"""
        enrollment = User_Course.query.filter_by(
            courseName=course_name,
            userID=user_id
        ).first_or_404()
        db.session.delete(enrollment)
        db.session.commit()
        return {'message': 'User removed from course'}


# -------- Feedback Endpoints --------
@api.route('/feedbacks')
class FeedbackList(Resource):
    @api.marshal_list_with(feedback_model)
    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def get(self, current_user):
        """Get all feedback"""
        return Feedback.query.all()

    @api.expect(feedback_model)
    @api.doc(security='Bearer')
    @token_required
    def post(self, current_user):
        """Create feedback"""
        data = api.payload
        if not Room.query.get(data['roomId']):
            abort(400, 'Room not found')
        if not Users.query.get(data['userID']):
            abort(400, 'User not found')
        if not RoomSchedule.query.get(data['scheduleID']):
            abort(400, 'Schedule not found')

        feedback = Feedback(**data)
        db.session.add(feedback)
        db.session.commit()
        return {'message': 'Feedback created'}, 201


@api.route('/feedbacks/<int:feedback_id>')
class FeedbackResource(Resource):
    @api.marshal_with(feedback_model)
    @api.doc(security='Bearer')
    @token_required
    def get(self, current_user, feedback_id):
        """Get feedback by ID"""
        feedback = Feedback.query.get_or_404(feedback_id)
        return feedback

    @api.doc(security='Bearer')
    @token_required
    @admin_required
    def delete(self, current_user, feedback_id):
        """Delete feedback"""
        feedback = Feedback.query.get_or_404(feedback_id)
        db.session.delete(feedback)
        db.session.commit()
        return {'message': 'Feedback deleted'}


# ------------ MAIN APPLICATION ----------------

if __name__ == '__main__':
    with app.app_context():
        #db.drop_all()
        # Create all tables if they don't exist
        db.create_all()

        # Check if tables are empty before populating them
        if not Membership.query.first():
            # Create default memberships if they don't exist
            default_memberships = [
                {'sign': 'em', 'fee': 350.00, 'typeName': 'economy', 'plan': 'monthly'},
                {'sign': 'ea', 'fee': 4200.00, 'typeName': 'economy', 'plan': 'annual'},
                {'sign': 'rm', 'fee': 600.00, 'typeName': 'regular', 'plan': 'monthly'},
                {'sign': 'ra', 'fee': 7200.00, 'typeName': 'regular', 'plan': 'annual'},
                {'sign': 'am', 'fee': 900.00, 'typeName': 'advanced', 'plan': 'monthly'},
                {'sign': 'aa', 'fee': 9900.00, 'typeName': 'advanced', 'plan': 'annual'},
                {"sign": "ad", "fee": 0, "typeName": "admin", "plan": "none"},
                {"sign": "in", "fee": 0, "typeName": "instructor", "plan": "none"}
            ]

            for membership_data in default_memberships:
                membership = Membership(**membership_data)
                db.session.add(membership)

            print("Default memberships created.")

        if not Room.query.first():
            # Create default rooms if they don't exist
            default_rooms = [
                {'roomName': 'Gym Floor'},
                {'roomName': 'Yoga Studio'},
                {'roomName': 'Pilates Room'},
                {'roomName': 'Cardio Zone'},
                {'roomName': 'Weight Room'}
            ]

            for room_data in default_rooms:
                room = Room(**room_data)
                db.session.add(room)

            print("Default rooms created.")

        # Create a default admin user if it doesn't exist
        admin_ssn = "ADMIN123"
        if not Users.query.get(admin_ssn):
            admin_user = Users(
                SSN=admin_ssn,
                firstName="Admin",
                lastName="User",
                membershipType="ad"
            )
            admin_user.set_password("admin123")
            db.session.add(admin_user)
            print("Default admin user created - SSN: ADMIN123, Password: admin123")

        try:
            db.session.commit()
            print("Database initialized successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error initializing database: {e}")

    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5001)