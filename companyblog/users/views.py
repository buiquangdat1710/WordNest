from flask import render_template, url_for, flash, redirect, request, Blueprint
from flask_login import login_user, current_user, logout_user, login_required
from companyblog import db
from companyblog.models import User, BlogPost, Notification, FriendRequest
from companyblog.users.forms import RegistrationForm, LoginForm, UpdateUserForm
from companyblog.users.picture_handler import add_profile_pic
from datetime import datetime

users = Blueprint('users', __name__)

@users.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('core.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Thanks for registering! Now you can login!', 'success')
        return redirect(url_for('users.login'))
    return render_template('register.html', form=form)

@users.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('core.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('core.index'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)




@users.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('core.index'))


@users.route("/account", methods=['GET', 'POST'])
@login_required
def account():

    form = UpdateUserForm()

    if form.validate_on_submit():
        print(form)
        if form.picture.data:
            username = current_user.username
            pic = add_profile_pic(form.picture.data,username)
            current_user.profile_image = pic

        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('User Account Updated')
        return redirect(url_for('users.account'))

    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email

    profile_image = url_for('static', filename='profile_pics/' + current_user.profile_image)
    return render_template('account.html', profile_image=profile_image, form=form)


@users.route("/<username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    blog_posts = BlogPost.query.filter_by(user=user).order_by(BlogPost.date.desc()).paginate(page=page, per_page=5)
    return render_template('user_blog_posts.html', blog_posts=blog_posts, user=user)

@users.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('core.index'))
    if user == current_user:
        flash('You cannot follow yourself!')
        return redirect(url_for('users.user_posts', username=username))
    current_user.follow(user)
    db.session.commit()
    user.add_notification(f'{current_user.username} started following you.', 'follow', url_for('users.user_posts', username=current_user.username))
    db.session.commit()
    flash('You are now following {}!'.format(username))
    return redirect(url_for('users.user_posts', username=username))

@users.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('core.index'))
    if user == current_user:
        flash('You cannot unfollow yourself!')
        return redirect(url_for('users.user_posts', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You have unfollowed {}.'.format(username))
    return redirect(url_for('users.user_posts', username=username))

@users.route('/send_friend_request/<username>')
@login_required
def send_friend_request(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('core.index'))
    if user == current_user:
        flash('You cannot send a friend request to yourself!')
        return redirect(url_for('users.user_posts', username=username))
    if current_user.is_friend(user):
        flash('You are already friends with {}!'.format(username))
        return redirect(url_for('users.user_posts', username=username))
    if current_user.has_sent_friend_request(user):
        flash('You have already sent a friend request to {}!'.format(username))
        return redirect(url_for('users.user_posts', username=username))
    
    friend_request = current_user.send_friend_request(user)
    if friend_request:
        db.session.commit()
        user.add_notification(f'{current_user.username} sent you a friend request.', 'friend_request', url_for('users.user_posts', username=current_user.username))
        db.session.commit()
        flash('Friend request sent to {}!'.format(username))
    else:
        flash('Unable to send friend request.')
    return redirect(url_for('users.user_posts', username=username))

@users.route('/accept_friend_request/<username>')
@login_required
def accept_friend_request(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User not found.', 'error')
        return redirect(url_for('users.friend_requests'))
    
    friend_request = FriendRequest.query.filter_by(sender=user, recipient=current_user).first()
    if friend_request is None:
        flash('Friend request not found.', 'error')
        return redirect(url_for('users.friend_requests'))
    
    current_user.friends.append(user)
    user.friends.append(current_user)
    db.session.delete(friend_request)
    db.session.commit()
    flash(f'You are now friends with {username}.', 'success')
    return redirect(url_for('users.friend_requests'))

@users.route('/friends')
@login_required
def friends_list():
    friends = current_user.friends.all()
    return render_template('friends_list.html', friends=friends)

@users.route('/friend_requests')
@login_required
def friend_requests():
    incoming_requests = current_user.friend_requests_received.all()
    return render_template('friend_requests.html', incoming_requests=incoming_requests)

@users.route('/followers')
@login_required
def followers_list():
    followers = current_user.followers_backref.all()
    return render_template('followers_list.html', followers=followers)

@users.route('/following')
@login_required
def following_list():
    following = current_user.followed.all()
    return render_template('following_list.html', following=following)

@users.route('/notifications')
@login_required
def notifications():
    current_user.last_notification_read_time = datetime.utcnow()
    db.session.commit()
    page = request.args.get('page', 1, type=int)
    notifications = current_user.notifications.order_by(Notification.timestamp.desc()).paginate(page=page, per_page=10)
    return render_template('notifications.html', notifications=notifications)

@users.route('/notifications/unread_count')
@login_required
def unread_notifications_count():
    count = current_user.new_notifications()
    return jsonify({'count': count})

@users.route('/remove_friend/<username>')
@login_required
def remove_friend(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('users.friends_list'))
    if user == current_user:
        flash('You cannot remove yourself as a friend!')
        return redirect(url_for('users.friends_list'))
    
    current_user.remove_friend(user)
    db.session.commit()
    flash('You have removed {} from your friends.'.format(username))
    return redirect(url_for('users.friends_list'))

@users.route('/decline_friend_request/<username>')
@login_required
def decline_friend_request(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User not found.', 'error')
        return redirect(url_for('users.friend_requests'))
    
    friend_request = FriendRequest.query.filter_by(sender=user, recipient=current_user).first()
    if friend_request is None:
        flash('Friend request not found.', 'error')
        return redirect(url_for('users.friend_requests'))
    
    db.session.delete(friend_request)
    db.session.commit()
    flash(f'You declined the friend request from {username}.', 'success')
    return redirect(url_for('users.friend_requests'))
