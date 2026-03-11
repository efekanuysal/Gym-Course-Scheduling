from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_restx import Api, Resource, fields, abort as api_abort
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:123@localhost/GymMembershipSystem'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
CORS(app)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

authorizations = {
    'Bearer': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization'
    }
}

api_blueprint = Blueprint('api_blueprint', __name__, url_prefix='/api/v1')
api = Api(api_blueprint, version='1.0', title='Gym Course Scheduling API', authorizations=authorizations, doc='/docs')
app.register_blueprint(api_blueprint)


def extract_token_from_header(headers):
    if 'Authorization' in headers:
        return headers['Authorization'].split(" ")[1]
    return None


def require_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = extract_token_from_header(request.headers)
        if not token:
            api_abort(401)

        if is_token_blacklisted(token):
            api_abort(401)

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = Users.query.get(data['ssn'])
            if not current_user:
                api_abort(401)
        except jwt.ExpiredSignatureError:
            api_abort(401)
        except jwt.InvalidTokenError:
            api_abort(401)

        return f(current_user, *args, **kwargs)

    return decorated


def require_admin(f):
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        if not current_user or not hasattr(current_user, 'membershipType') or current_user.membershipType != 'ad':
            api_abort(403)
        return f(current_user, *args, **kwargs)

    return decorated


def blacklist_token(token):
    blacklisted_token = Blacklist(token=token)
    db.session.add(blacklisted_token)
    db.session.commit()


def is_token_blacklisted(token):
    return bool(Blacklist.query.filter_by(token=token).first())


class Blacklist(db.Model):
    __tablename__ = 'Blacklist'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    token = db.Column(db.String(500), unique=True, nullable=False)
    blacklisted_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Membership(db.Model):
    __tablename__ = 'Membership'
    sign = db.Column(db.String(2), primary_key=True)
    fee = db.Column(db.Numeric(7, 2), nullable=False)
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
    password_hash = db.Column(db.String(255), nullable=False)
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


login_model = api.model('Login', {
    'SSN': fields.String(required=True),
    'password': fields.String(required=True)
})

register_model = api.model('Register', {
    'SSN': fields.String(required=True),
    'firstName': fields.String(required=True),
    'lastName': fields.String(required=True),
    'password': fields.String(required=True),
    'membershipType': fields.String()
})

membership_model = api.model('Membership', {
    'sign': fields.String(required=True, enum=['em', 'ea', 'rm', 'ra', 'am', 'aa', 'ad', 'in']),
    'fee': fields.Float(required=True),
    'typeName': fields.String(required=True),
    'plan': fields.String(required=True)
})

user_model = api.model('Users', {
    'SSN': fields.String(required=True),
    'firstName': fields.String(required=True),
    'lastName': fields.String(required=True),
    'membershipType': fields.String()
})

phone_model = api.model('Phone', {
    'phone': fields.String(required=True),
    'userSSN': fields.String()
})

instructor_model = api.model('Instructors', {
    'SSN': fields.String(required=True),
    'firstName': fields.String(required=True),
    'lastName': fields.String(required=True),
    'phone': fields.String()
})

room_model = api.model('Room', {
    'ID': fields.Integer(readOnly=True),
    'roomName': fields.String(required=True)
})

course_model = api.model('Course', {
    'courseName': fields.String(required=True),
    'capacity': fields.Integer(required=True),
    'isSpecial': fields.Boolean(required=True),
    'InstructorID': fields.String(required=True),
    'roomId': fields.Integer(required=True)
})

roomschedule_model = api.model('RoomSchedule', {
    'scheduleID': fields.Integer(readOnly=True),
    'roomId': fields.Integer(required=True),
    'scheduleDate': fields.Date(required=True),
    'scheduleTime': fields.String(required=True),
    'bookingType': fields.String(required=True, enum=['cleaning', 'class', 'private']),
    'userID': fields.String(),
    'courseName': fields.String(),
    'isBooked': fields.Boolean(required=True)
})

user_course_model = api.model('User_Course', {
    'courseName': fields.String(required=True),
    'userID': fields.String(required=True)
})

feedback_model = api.model('Feedback', {
    'feedBackNo': fields.Integer(readOnly=True),
    'roomId': fields.Integer(required=True),
    'userID': fields.String(required=True),
    'scheduleID': fields.Integer(required=True),
    'score': fields.Float(required=True),
    'comment': fields.String()
})


@app.route('/')
def home():
    if 'user_token' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login_view'))


@app.route('/login', methods=['GET', 'POST'], endpoint='login_view')
def login_view():
    if request.method == 'POST':
        ssn = request.form.get('ssn')
        password = request.form.get('password')
        user = Users.query.get(ssn)

        if not user or not user.check_password(password):
            flash('Invalid credentials', 'danger')
            return redirect(url_for('login_view'))

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


@app.route('/register', methods=['GET', 'POST'], endpoint='register_view')
def register_view():
    if request.method == 'POST':
        ssn = request.form.get('ssn')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        password = request.form.get('password')
        membership_type = request.form.get('membership_type')

        if Users.query.get(ssn):
            flash('User already exists', 'danger')
            return redirect(url_for('register_view'))

        if membership_type and not Membership.query.get(membership_type):
            flash('Invalid membership type', 'danger')
            return redirect(url_for('register_view'))

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
        return redirect(url_for('login_view'))

    memberships = Membership.query.filter(Membership.sign.notin_(['ad', 'in'])).all()
    return render_template('register.html', memberships=memberships)


@app.route('/dashboard')
def dashboard():
    if 'user_token' not in session:
        return redirect(url_for('login_view'))

    try:
        jwt.decode(session['user_token'], app.config['SECRET_KEY'], algorithms=['HS256'])
    except:
        session.clear()
        return redirect(url_for('login_view'))

    if session['user_type'] == 'ad':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('member_dashboard'))


@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_token' not in session or session['user_type'] != 'ad':
        return redirect(url_for('login_view'))
    return render_template('admin/dashboard.html')


@app.route('/member/dashboard')
def member_dashboard():
    if 'user_token' not in session:
        return redirect(url_for('login_view'))

    user_ssn = session['user_ssn']
    enrolled_courses = User_Course.query.filter_by(userID=user_ssn).all()
    bookings = RoomSchedule.query.filter_by(userID=user_ssn).all()

    return render_template('member/dashboard.html', enrolled_courses=enrolled_courses, bookings=bookings)


@app.route('/logout', endpoint='logout_view')
def logout_view():
    if 'user_token' in session:
        token = session['user_token']
        if not is_token_blacklisted(token):
            blacklist_token(token)
    session.clear()
    return redirect(url_for('login_view'))


@app.route('/admin/users')
def admin_users():
    if 'user_token' not in session or session['user_type'] != 'ad':
        return redirect(url_for('login_view'))
    users = Users.query.all()
    return render_template('admin/users.html', users=users)


@app.route('/admin/courses')
def admin_courses():
    if 'user_token' not in session or session['user_type'] != 'ad':
        return redirect(url_for('login_view'))
    courses = Course.query.all()
    instructors = Instructors.query.all()
    rooms = Room.query.all()
    return render_template('admin/courses.html', courses=courses, instructors=instructors, rooms=rooms)


@app.route('/admin/rooms')
def admin_rooms():
    if 'user_token' not in session or session['user_type'] != 'ad':
        return redirect(url_for('login_view'))
    rooms = Room.query.all()
    return render_template('admin/rooms.html', rooms=rooms)


@app.route('/admin/schedules')
def admin_schedules():
    if 'user_token' not in session or session['user_type'] != 'ad':
        return redirect(url_for('login_view'))
    schedules = RoomSchedule.query.all()
    courses = Course.query.all()
    users = Users.query.all()
    rooms = Room.query.all()
    return render_template('admin/schedules.html', schedules=schedules, courses=courses, users=users, rooms=rooms)


@app.route('/member/profile')
def member_profile():
    if 'user_token' not in session:
        return redirect(url_for('login_view'))
    user = Users.query.get(session['user_ssn'])
    phones = Phone.query.filter_by(userSSN=session['user_ssn']).all()
    return render_template('member/profile.html', user=user, phones=phones)


@app.route('/member/courses')
def member_courses():
    if 'user_token' not in session:
        return redirect(url_for('login_view'))
    all_courses = Course.query.all()
    enrolled_courses = User_Course.query.filter_by(userID=session['user_ssn']).all()
    enrolled_course_names = [ec.courseName for ec in enrolled_courses]
    return render_template('member/courses.html', courses=all_courses, enrolled_courses=enrolled_course_names)


@app.route('/member/bookings')
def member_bookings():
    if 'user_token' not in session:
        return redirect(url_for('login_view'))
    bookings = RoomSchedule.query.filter_by(userID=session['user_ssn']).all()
    return render_template('member/bookings.html', bookings=bookings)


@app.route('/api/enroll_course', methods=['POST'])
def enroll_course():
    if 'user_token' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    course_name = request.json.get('course_name')
    user_id = session['user_ssn']
    existing = User_Course.query.filter_by(courseName=course_name, userID=user_id).first()

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

    if not all(key in data for key in ['room_id', 'date', 'time', 'booking_type']):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

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


@api.route('/auth/register', endpoint='api_register')
class RegisterAPI(Resource):
    @api.expect(register_model)
    def post(self):
        data = api.payload
        if Users.query.get(data['SSN']):
            api_abort(400)

        if data.get('membershipType') and not Membership.query.get(data['membershipType']):
            api_abort(400)

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


@api.route('/auth/login', endpoint='api_login')
class LoginAPI(Resource):
    @api.expect(login_model)
    def post(self):
        data = api.payload
        user = Users.query.get(data['SSN'])

        if not user or not user.check_password(data['password']):
            api_abort(401)

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


@api.route('/auth/logout', endpoint='api_logout')
class LogoutAPI(Resource):
    @api.doc(security='Bearer')
    @require_token
    def post(self, current_user):
        token = extract_token_from_header(request.headers)
        if is_token_blacklisted(token):
            api_abort(400)
        blacklist_token(token)
        return {'message': 'Successfully logged out'}, 200


@api.route('/memberships', endpoint='api_memberships')
class MembershipListAPI(Resource):
    @api.marshal_list_with(membership_model)
    def get(self):
        return Membership.query.all()

    @api.expect(membership_model)
    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def post(self, current_user):
        data = api.payload
        if Membership.query.get(data['sign']):
            api_abort(400)
        membership = Membership(**data)
        db.session.add(membership)
        db.session.commit()
        return {'message': 'Membership created'}, 201


@api.route('/memberships/<string:sign>', endpoint='api_membership_detail')
class MembershipResourceAPI(Resource):
    @api.marshal_with(membership_model)
    def get(self, sign):
        return Membership.query.get_or_404(sign)

    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def delete(self, current_user, sign):
        membership = Membership.query.get_or_404(sign)
        db.session.delete(membership)
        db.session.commit()
        return {'message': 'Membership deleted'}

    @api.expect(membership_model)
    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def put(self, current_user, sign):
        membership = Membership.query.get_or_404(sign)
        data = api.payload
        membership.fee = data.get('fee', membership.fee)
        membership.typeName = data.get('typeName', membership.typeName)
        membership.plan = data.get('plan', membership.plan)
        db.session.commit()
        return {'message': 'Membership updated'}


@api.route('/users', endpoint='api_users')
class UsersListAPI(Resource):
    @api.marshal_list_with(user_model)
    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def get(self, current_user):
        return Users.query.all()


@api.route('/users/<string:ssn>', endpoint='api_user_detail')
class UsersResourceAPI(Resource):
    @api.marshal_with(user_model)
    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def get(self, current_user, ssn):
        return Users.query.get_or_404(ssn)

    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def delete(self, current_user, ssn):
        user = Users.query.get_or_404(ssn)
        db.session.delete(user)
        db.session.commit()
        return {'message': 'User deleted'}

    @api.expect(user_model)
    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def put(self, current_user, ssn):
        user = Users.query.get_or_404(ssn)
        data = api.payload
        user.firstName = data.get('firstName', user.firstName)
        user.lastName = data.get('lastName', user.lastName)
        if 'membershipType' in data:
            if data['membershipType'] and not Membership.query.get(data['membershipType']):
                api_abort(400)
            user.membershipType = data['membershipType']
        db.session.commit()
        return {'message': 'User updated'}


@api.route('/phones', endpoint='api_phones')
class PhoneListAPI(Resource):
    @api.marshal_list_with(phone_model)
    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def get(self, current_user):
        return Phone.query.all()

    @api.expect(phone_model)
    @api.doc(security='Bearer')
    @require_token
    def post(self, current_user):
        data = api.payload
        if Phone.query.get(data['phone']):
            api_abort(400)
        if data.get('userSSN') and not Users.query.get(data['userSSN']):
            api_abort(400)
        phone = Phone(**data)
        db.session.add(phone)
        db.session.commit()
        return {'message': 'Phone created'}, 201


@api.route('/phones/<string:phone_number>', endpoint='api_phone_detail')
class PhoneResourceAPI(Resource):
    @api.marshal_with(phone_model)
    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def get(self, current_user, phone_number):
        return Phone.query.get_or_404(phone_number)

    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def delete(self, current_user, phone_number):
        phone = Phone.query.get_or_404(phone_number)
        db.session.delete(phone)
        db.session.commit()
        return {'message': 'Phone deleted'}


@api.route('/instructors', endpoint='api_instructors')
class InstructorsListAPI(Resource):
    @api.marshal_list_with(instructor_model)
    def get(self):
        return Instructors.query.all()

    @api.expect(instructor_model)
    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def post(self, current_user):
        data = api.payload
        if Instructors.query.get(data['SSN']):
            api_abort(400)
        instructor = Instructors(**data)
        db.session.add(instructor)
        db.session.commit()
        return {'message': 'Instructor created'}, 201


@api.route('/instructors/<string:ssn>', endpoint='api_instructor_detail')
class InstructorsResourceAPI(Resource):
    @api.marshal_with(instructor_model)
    def get(self, ssn):
        return Instructors.query.get_or_404(ssn)

    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def delete(self, current_user, ssn):
        instructor = Instructors.query.get_or_404(ssn)
        db.session.delete(instructor)
        db.session.commit()
        return {'message': 'Instructor deleted'}

    @api.expect(instructor_model)
    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def put(self, current_user, ssn):
        instructor = Instructors.query.get_or_404(ssn)
        data = api.payload
        instructor.firstName = data.get('firstName', instructor.firstName)
        instructor.lastName = data.get('lastName', instructor.lastName)
        instructor.phone = data.get('phone', instructor.phone)
        db.session.commit()
        return {'message': 'Instructor updated'}


@api.route('/rooms', endpoint='api_rooms')
class RoomListAPI(Resource):
    @api.marshal_list_with(room_model)
    def get(self):
        return Room.query.all()

    @api.expect(room_model)
    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def post(self, current_user):
        data = api.payload
        room = Room(roomName=data['roomName'])
        db.session.add(room)
        db.session.commit()
        return {'message': 'Room created'}, 201


@api.route('/rooms/<int:room_id>', endpoint='api_room_detail')
class RoomResourceAPI(Resource):
    @api.marshal_with(room_model)
    def get(self, room_id):
        return Room.query.get_or_404(room_id)

    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def delete(self, current_user, room_id):
        room = Room.query.get_or_404(room_id)
        db.session.delete(room)
        db.session.commit()
        return {'message': 'Room deleted'}

    @api.expect(room_model)
    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def put(self, current_user, room_id):
        room = Room.query.get_or_404(room_id)
        data = api.payload
        room.roomName = data.get('roomName', room.roomName)
        db.session.commit()
        return {'message': 'Room updated'}


@api.route('/courses', endpoint='api_courses')
class CourseListAPI(Resource):
    @api.marshal_list_with(course_model)
    def get(self):
        return Course.query.all()

    @api.expect(course_model)
    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def post(self, current_user):
        data = api.payload
        if Course.query.get(data['courseName']):
            api_abort(400)
        if not Instructors.query.get(data['InstructorID']):
            api_abort(400)
        if not Room.query.get(data['roomId']):
            api_abort(400)

        course = Course(**data)
        db.session.add(course)
        db.session.commit()
        return {'message': 'Course created'}, 201


@api.route('/courses/<string:course_name>', endpoint='api_course_detail')
class CourseResourceAPI(Resource):
    @api.marshal_with(course_model)
    def get(self, course_name):
        return Course.query.get_or_404(course_name)

    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def delete(self, current_user, course_name):
        course = Course.query.get_or_404(course_name)
        db.session.delete(course)
        db.session.commit()
        return {'message': 'Course deleted'}

    @api.expect(course_model)
    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def put(self, current_user, course_name):
        course = Course.query.get_or_404(course_name)
        data = api.payload
        course.capacity = data.get('capacity', course.capacity)
        course.isSpecial = data.get('isSpecial', course.isSpecial)

        if 'InstructorID' in data:
            if not Instructors.query.get(data['InstructorID']):
                api_abort(400)
            course.InstructorID = data['InstructorID']

        if 'roomId' in data:
            if not Room.query.get(data['roomId']):
                api_abort(400)
            course.roomId = data['roomId']

        db.session.commit()
        return {'message': 'Course updated'}


@api.route('/roomschedules', endpoint='api_roomschedules')
class RoomScheduleListAPI(Resource):
    @api.marshal_list_with(roomschedule_model)
    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def get(self, current_user):
        return RoomSchedule.query.all()

    @api.expect(roomschedule_model)
    @api.doc(security='Bearer')
    @require_token
    def post(self, current_user):
        data = api.payload
        if not Room.query.get(data['roomId']):
            api_abort(400)

        if data['bookingType'] == 'class' and not data.get('courseName'):
            api_abort(400)
        if data['bookingType'] == 'private' and not data.get('userID'):
            api_abort(400)
        if data['bookingType'] == 'class' and not Course.query.get(data['courseName']):
            api_abort(400)
        if data['bookingType'] == 'private' and not Users.query.get(data['userID']):
            api_abort(400)

        schedule = RoomSchedule(**data)
        db.session.add(schedule)
        db.session.commit()
        return {'message': 'Room schedule created'}, 201


@api.route('/roomschedules/<int:schedule_id>', endpoint='api_roomschedule_detail')
class RoomScheduleResourceAPI(Resource):
    @api.marshal_with(roomschedule_model)
    @api.doc(security='Bearer')
    @require_token
    def get(self, current_user, schedule_id):
        return RoomSchedule.query.get_or_404(schedule_id)

    @api.doc(security='Bearer')
    @require_token
    def delete(self, current_user, schedule_id):
        schedule = RoomSchedule.query.get_or_404(schedule_id)
        db.session.delete(schedule)
        db.session.commit()
        return {'message': 'Room schedule deleted'}


@api.route('/user_courses', endpoint='api_user_courses')
class UserCourseListAPI(Resource):
    @api.marshal_list_with(user_course_model)
    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def get(self, current_user):
        return User_Course.query.all()

    @api.expect(user_course_model)
    @api.doc(security='Bearer')
    @require_token
    def post(self, current_user):
        data = api.payload
        if not Course.query.get(data['courseName']):
            api_abort(400)
        if not Users.query.get(data['userID']):
            api_abort(400)

        existing = User_Course.query.filter_by(
            courseName=data['courseName'],
            userID=data['userID']
        ).first()
        if existing:
            api_abort(400)

        enrollment = User_Course(**data)
        db.session.add(enrollment)
        db.session.commit()
        return {'message': 'User enrolled in course'}, 201


@api.route('/user_courses/<string:course_name>/<string:user_id>', endpoint='api_user_course_detail')
class UserCourseResourceAPI(Resource):
    @api.doc(security='Bearer')
    @require_token
    def delete(self, current_user, course_name, user_id):
        enrollment = User_Course.query.filter_by(
            courseName=course_name,
            userID=user_id
        ).first_or_404()
        db.session.delete(enrollment)
        db.session.commit()
        return {'message': 'User removed from course'}


@api.route('/feedbacks', endpoint='api_feedbacks')
class FeedbackListAPI(Resource):
    @api.marshal_list_with(feedback_model)
    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def get(self, current_user):
        return Feedback.query.all()

    @api.expect(feedback_model)
    @api.doc(security='Bearer')
    @require_token
    def post(self, current_user):
        data = api.payload
        if not Room.query.get(data['roomId']):
            api_abort(400)
        if not Users.query.get(data['userID']):
            api_abort(400)
        if not RoomSchedule.query.get(data['scheduleID']):
            api_abort(400)

        feedback = Feedback(**data)
        db.session.add(feedback)
        db.session.commit()
        return {'message': 'Feedback created'}, 201


@api.route('/feedbacks/<int:feedback_id>', endpoint='api_feedback_detail')
class FeedbackResourceAPI(Resource):
    @api.marshal_with(feedback_model)
    @api.doc(security='Bearer')
    @require_token
    def get(self, current_user, feedback_id):
        return Feedback.query.get_or_404(feedback_id)

    @api.doc(security='Bearer')
    @require_token
    @require_admin
    def delete(self, current_user, feedback_id):
        feedback = Feedback.query.get_or_404(feedback_id)
        db.session.delete(feedback)
        db.session.commit()
        return {'message': 'Feedback deleted'}


def is_admin_authenticated():
    return 'user_token' in session and session.get('user_type') == 'ad'


@app.route('/booking_admin', methods=['GET', 'POST'])
def manage_admin_bookings():
    if not is_admin_authenticated():
        return redirect(url_for('login_view'))

    if request.method == 'POST':
        return process_booking_creation(request.get_json())

    return render_booking_dashboard()


def process_booking_creation(payload):
    try:
        schedule_date = datetime.strptime(payload['scheduleDate'], '%Y-%m-%d').date()
        schedule_time = datetime.strptime(payload['scheduleTime'], '%H:%M').time()

        new_booking = RoomSchedule(
            roomId=payload['roomId'],
            scheduleDate=schedule_date,
            scheduleTime=schedule_time,
            bookingType=payload['bookingType'],
            courseName=payload['courseName'],
            isBooked=True
        )

        db.session.add(new_booking)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Booking confirmed'})

    except Exception as error:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(error)}), 400


def render_booking_dashboard():
    available_courses = [{'name': course.courseName} for course in Course.query.all()]
    available_rooms = [{'id': room.ID, 'name': room.roomName} for room in Room.query.all()]
    existing_schedules = [
        {
            'roomId': schedule.roomId,
            'scheduleDate': str(schedule.scheduleDate),
            'scheduleTime': str(schedule.scheduleTime)[:5]
        }
        for schedule in RoomSchedule.query.all()
    ]

    return render_template(
        'book_class_admin.html',
        courses=available_courses,
        rooms=available_rooms,
        roomSchedule=existing_schedules
    )


@app.route('/add_instructor', methods=['GET', 'POST'])
def register_new_instructor():
    if not is_admin_authenticated():
        return redirect(url_for('login_view'))

    if request.method == 'POST':
        create_instructor_record(request.form)
        return redirect(url_for('admin_users'))

    return render_template('add instructor.html')


def create_instructor_record(form_data):
    new_instructor = Instructors(
        SSN=form_data.get('ssn'),
        firstName=form_data.get('first_name'),
        lastName=form_data.get('last_name'),
        phone=form_data.get('phone')
    )
    db.session.add(new_instructor)
    db.session.commit()


@app.route('/add_class', methods=['GET', 'POST'])
def register_new_class():
    if not is_admin_authenticated():
        return redirect(url_for('login_view'))

    if request.method == 'POST':
        create_course_record(request.form)
        return redirect(url_for('admin_courses'))

    return render_template(
        'add Class.html',
        instructors=Instructors.query.all(),
        rooms=Room.query.all()
    )


def create_course_record(form_data):
    new_course = Course(
        courseName=form_data.get('course_name'),
        capacity=form_data.get('capacity'),
        isSpecial=form_data.get('is_special') == 'on',
        InstructorID=form_data.get('instructor_id'),
        roomId=form_data.get('room_id')
    )
    db.session.add(new_course)
    db.session.commit()


@app.route('/remove_member', methods=['GET', 'POST'])
def manage_member_deletion():
    if not is_admin_authenticated():
        return redirect(url_for('login_view'))

    if request.method == 'POST':
        delete_user_record(request.form.get('ssn'))
        return redirect(url_for('admin_users'))

    return render_template('remove_members.html', users=Users.query.all())


def delete_user_record(user_ssn):
    target_user = Users.query.get(user_ssn)
    if target_user:
        db.session.delete(target_user)
        db.session.commit()

def initialize_database():
    db.create_all()
    if not Membership.query.first():
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
            db.session.add(Membership(**membership_data))

    if not Room.query.first():
        default_rooms = [
            {'roomName': 'Gym Floor'},
            {'roomName': 'Yoga Studio'},
            {'roomName': 'Pilates Room'},
            {'roomName': 'Cardio Zone'},
            {'roomName': 'Weight Room'}
        ]
        for room_data in default_rooms:
            db.session.add(Room(**room_data))

    admin_ssn = "ADMIN123"
    if not Users.query.get(admin_ssn):
        admin_user = Users(SSN=admin_ssn, firstName="Admin", lastName="User", membershipType="ad")
        admin_user.set_password("admin123")
        db.session.add(admin_user)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()



if __name__ == '__main__':
    with app.app_context():
        initialize_database()
    app.run(debug=True, host='0.0.0.0', port=5001)