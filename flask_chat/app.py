from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, leave_room, emit
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = "supersecret123"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///chat.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ---------------- DB MODEL ----------------
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(50), nullable=False)
    room = db.Column(db.String(50), nullable=False)
    text = db.Column(db.Text, nullable=False)
    time = db.Column(db.String(20), nullable=False)

with app.app_context():
    db.create_all()

# ---------------- ROUTES ----------------
@app.route("/")
def login():
    return render_template("login.html")

@app.route("/join", methods=["POST"])
def join():
    username = request.form.get("username", "").strip()
    room = request.form.get("room", "").strip()

    if not username or not room:
        return redirect(url_for("login"))

    session["username"] = username
    session["room"] = room
    return redirect(url_for("chat"))

@app.route("/chat")
def chat():
    if "username" not in session or "room" not in session:
        return redirect(url_for("login"))

    # Load old messages from DB
    old_msgs = Message.query.filter_by(room=session["room"]).all()
    return render_template("chat.html",
                           username=session["username"],
                           room=session["room"],
                           old_msgs=old_msgs)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- SOCKET.IO EVENTS ----------------
@socketio.on("join_room")
def handle_join(data):
    username = data["username"]
    room = data["room"]

    join_room(room)

    emit("status", {"msg": f"✅ {username} joined room '{room}'"}, room=room)


@socketio.on("send_message")
def handle_message(data):
    sender = data["sender"]
    room = data["room"]
    text = data["text"]

    timestamp = datetime.now().strftime("%H:%M")

    # Save in DB
    msg = Message(sender=sender, room=room, text=text, time=timestamp)
    db.session.add(msg)
    db.session.commit()

    # Send to all users in room
    emit("new_message", {
        "sender": sender,
        "room": room,
        "text": text,
        "time": timestamp
    }, room=room)


@socketio.on("leave_room")
def handle_leave(data):
    username = data["username"]
    room = data["room"]

    leave_room(room)
    emit("status", {"msg": f"❌ {username} left room '{room}'"}, room=room)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)

