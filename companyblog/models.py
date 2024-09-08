from companyblog import db, login_manager
from datetime import datetime
from werkzeug.security import generate_password_hash,check_password_hash
from flask_login import UserMixin
# By inheriting the UserMixin we get access to a lot of built-in attributes
# which we will be able to call in our views!
# is_authenticated()
# is_active()
# is_anonymous()
# get_id()


# The user_loader decorator allows flask-login to load the current user
# and grab their id.

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('users.id'))
)

friendships = db.Table('friendships',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('friend_id', db.Integer, db.ForeignKey('users.id'))
)

class FriendRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model, UserMixin):

    # Create a table in the db
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key = True)
    profile_image = db.Column(db.String(64), nullable=False, default='default_profile.png')
    email = db.Column(db.String(120), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    # This connects BlogPosts to a User Author.
    posts = db.relationship('BlogPost', back_populates='user', lazy=True)
    comments = db.relationship('Comment', back_populates='user', lazy='dynamic')
    reactions = db.relationship('Reaction', back_populates='user', lazy='dynamic')
    
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers_backref', lazy='dynamic'), lazy='dynamic')
    
    friends = db.relationship('User', secondary=friendships,
                              primaryjoin=(friendships.c.user_id == id),
                              secondaryjoin=(friendships.c.friend_id == id),
                              backref=db.backref('friends_backref', lazy='dynamic'), lazy='dynamic')

    notifications = db.relationship('Notification', backref='recipient', lazy='dynamic')
    last_notification_read_time = db.Column(db.DateTime)

    friend_requests_sent = db.relationship('FriendRequest',
                                           foreign_keys=[FriendRequest.sender_id],
                                           backref='sender', lazy='dynamic')
    friend_requests_received = db.relationship('FriendRequest',
                                               foreign_keys=[FriendRequest.recipient_id],
                                               backref='recipient', lazy='dynamic')

    def __init__(self, email, username):
        self.email = email
        self.username = username

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self,password):
        # https://stackoverflow.com/questions/23432478/flask-generate-password-hash-not-constant-output
        return check_password_hash(self.password_hash,password)

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def add_friend(self, user):
        if not self.is_friend(user):
            self.friends.append(user)
            user.friends.append(self)
            return self

    def remove_friend(self, user):
        if self.is_friend(user):
            self.friends.remove(user)
            user.friends.remove(self)

    def is_friend(self, user):
        return self.friends.filter(friendships.c.friend_id == user.id).count() > 0

    def send_friend_request(self, user):
        if not self.has_sent_friend_request(user) and not self.is_friend(user):
            friend_request = FriendRequest(sender=self, recipient=user)
            db.session.add(friend_request)
            return friend_request

    def accept_friend_request(self, user):
        friend_request = self.friend_requests_received.filter_by(sender=user).first()
        if friend_request:
            self.friends.append(user)
            user.friends.append(self)
            db.session.delete(friend_request)
            return True
        return False

    def has_sent_friend_request(self, user):
        return self.friend_requests_sent.filter_by(recipient=user).count() > 0

    def has_received_friend_request(self, user):
        return self.friend_requests_received.filter_by(sender=user).count() > 0

    def add_notification(self, message, notification_type, link=None):
        notification = Notification(user_id=self.id, message=message, type=notification_type, link=link)
        db.session.add(notification)
        return notification

    def new_notifications(self):
        last_read_time = self.last_notification_read_time or datetime(1900, 1, 1)
        return Notification.query.filter_by(user_id=self.id).filter(
            Notification.timestamp > last_read_time).count()

    def __repr__(self):
        return f"UserName: {self.username}"

class BlogPost(db.Model):
    __tablename__ = 'blog_posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    title = db.Column(db.String(140), nullable=False)
    text = db.Column(db.Text, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    comments = db.relationship('Comment', back_populates='post', lazy='dynamic')
    reactions = db.relationship('Reaction', back_populates='post', lazy='dynamic')
    user = db.relationship('User', back_populates='posts')

    def __init__(self, title, text, user_id, image_file=None):
        self.title = title
        self.text = text
        self.user_id = user_id
        self.image_file = image_file

    def __repr__(self):
        return f"Post Id: {self.id} --- Date: {self.date} --- Title: {self.title}"

    def get_reaction_count(self, reaction_type):
        return Reaction.query.filter_by(post_id=self.id, type=reaction_type).count()

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post = db.relationship('BlogPost', back_populates='comments')
    user = db.relationship('User', back_populates='comments')

class Reaction(db.Model):
    __tablename__ = 'reactions'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'), nullable=False)
    post = db.relationship('BlogPost', back_populates='reactions')
    user = db.relationship('User', back_populates='reactions')

    def __repr__(self):
        return f"Reaction('{self.type}', '{self.timestamp}')"

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(250), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    type = db.Column(db.String(20), nullable=False)  # 'friend_request', 'follow', 'comment', 'reaction'
    link = db.Column(db.String(250))

    def __init__(self, user_id, message, type, link=None):
        self.user_id = user_id
        self.message = message
        self.type = type
        self.link = link

    def __repr__(self):
        return f"Notification: {self.message}"


