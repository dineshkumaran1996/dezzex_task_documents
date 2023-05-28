from flask import *
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.config['SECRET_KEY'] = '123456789'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable modification tracking
db = SQLAlchemy(app)
socketio = SocketIO(app)

room1='employee'
room2='employer'
# Database models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False  )
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('messages', lazy=True))

# Routes
@app.route('/')
def home():
    if 'username' in session:
        messages = Message.query.join(User).all()
        return render_template('message.html',msg=messages)
    return render_template('login.html')


@app.route('/signup_page')
def signup_page():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup():
    username = request.form['username']
    password = request.form['password']
    confirm_password=request.form['confirm_password']
    if password==confirm_password:
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('home'))
    else:
        return jsonify({'message':'passwrod mismatch'})
        


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username, password=password).first()
    if user:
        session['username'] = username
        return redirect(url_for('home'))
    
    return jsonify({'message': 'Invalid credentials'})

@app.route('/logout', methods=['GET'])
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/api/messages', methods=['GET'])
def get_messages():
    if 'username' in session:
        messages = Message.query.join(User).all()
        return jsonify({'messages': [{'content': msg.content, 'username': msg.user.username} for msg in messages]})
    return jsonify({'message': 'Unauthorized'}), 401

@app.route('/api/messages', methods=['POST'])
def create_message():
    if 'username' in session:
        content = request.form['content']
        user = User.query.filter_by(username=session['username']).first()
        message = Message(content=content, user=user )
        db.session.add(message)
        db.session.commit()
        messages = Message.query.join(User).all()
        
        return render_template('message.html',msg=messages)
    return jsonify({'message': 'Unauthorized'}), 401

# WebSocket events
@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    emit('status', {'message': 'User has entered the room.'}, room=room)

@socketio.on('leave')
def on_leave(data):
    room = data['room']
    leave_room(room)
    emit('status', {'message': 'User has left the room.'}, room=room)

@socketio.on('message')
def handle_message(data):
    content = data['content']
    user = User.query.filter_by(username=session['username']).first()
    message = Message(content=content, user=user)
    db.session.add(message)
    db.session.commit()
    print('received message: ' + message)
    emit('message', {'content': content, 'username': user.username}, broadcast=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app)
