from flask import render_template, url_for, flash, request, redirect, Blueprint, current_app, abort, jsonify
from flask_login import current_user, login_required
from companyblog import db
from companyblog.models import BlogPost, Comment, Reaction, User
from companyblog.blog_posts.forms import BlogPostForm, CommentForm
import os
import secrets
from werkzeug.utils import secure_filename

blog_posts = Blueprint('blog_posts', __name__)

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}  # Allowed image extensions

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file.save(os.path.join(upload_folder, filename))
        return filename
    return None

import os
import secrets
from flask import url_for, current_app
from werkzeug.utils import secure_filename

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/post_pics', picture_fn)
    
    # Tạo thư mục nếu chưa tồn tại
    os.makedirs(os.path.dirname(picture_path), exist_ok=True)
    
    form_picture.save(picture_path)
    return picture_fn

@blog_posts.route('/create', methods=['GET', 'POST'])
@login_required
def create_post():
    form = BlogPostForm()
    if form.validate_on_submit():
        if form.image.data:
            picture_file = save_picture(form.image.data)
            post = BlogPost(title=form.title.data, text=form.text.data, image_file=picture_file, user_id=current_user.id)
        else:
            post = BlogPost(title=form.title.data, text=form.text.data, user_id=current_user.id)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('blog_posts.view_post', blog_post_id=post.id))
    return render_template('create_post.html', title='New Post', form=form)

@blog_posts.route('/<int:blog_post_id>', methods=['GET', 'POST'])
def view_post(blog_post_id):
    blog_post = BlogPost.query.get_or_404(blog_post_id)
    form = CommentForm()
    if form.validate_on_submit():
        if current_user.is_authenticated:
            comment = Comment(body=form.body.data,
                              post_id=blog_post.id,
                              user_id=current_user.id)
            db.session.add(comment)
            db.session.commit()
            flash('Your comment has been added!', 'success')
            return redirect(url_for('blog_posts.view_post', blog_post_id=blog_post.id))
        else:
            flash('You need to be logged in to comment.', 'warning')
            return redirect(url_for('users.login'))

    reactions = Reaction.query.filter_by(post_id=blog_post.id).all()
    reaction_counts = {
        '👍': sum(1 for r in reactions if r.type == 'like'),
        '❤️': sum(1 for r in reactions if r.type == 'love'),
        '😂': sum(1 for r in reactions if r.type == 'haha'),
        '😮': sum(1 for r in reactions if r.type == 'wow'),
        '😢': sum(1 for r in reactions if r.type == 'sad'),
        '😡': sum(1 for r in reactions if r.type == 'angry'),
    }
    return render_template('blog_post.html', title=blog_post.title,
                           post=blog_post, form=form, reactions=reactions, reaction_counts=reaction_counts)

@blog_posts.route('/<int:blog_post_id>/react/<string:reaction_type>', methods=['POST'])
@login_required
def react_to_post(blog_post_id, reaction_type):
    blog_post = BlogPost.query.get_or_404(blog_post_id)
    existing_reaction = Reaction.query.filter_by(user=current_user, post=blog_post).first()
    
    if existing_reaction:
        if existing_reaction.type == reaction_type:
            db.session.delete(existing_reaction)
        else:
            existing_reaction.type = reaction_type
    else:
        new_reaction = Reaction(type=reaction_type, user=current_user, post=blog_post)
        db.session.add(new_reaction)
    
    db.session.commit()

    reactions = Reaction.query.filter_by(post_id=blog_post.id).all()
    reaction_counts = {
        'like': sum(1 for r in reactions if r.type == 'like'),
        'love': sum(1 for r in reactions if r.type == 'love'),
        'haha': sum(1 for r in reactions if r.type == 'haha'),
        'wow': sum(1 for r in reactions if r.type == 'wow'),
        'sad': sum(1 for r in reactions if r.type == 'sad'),
        'angry': sum(1 for r in reactions if r.type == 'angry'),
    }

    return jsonify({'status': 'success', 'count': reaction_counts})

@blog_posts.route("/<int:blog_post_id>/update", methods=['GET', 'POST'])
@login_required
def update(blog_post_id):
    blog_post = BlogPost.query.get_or_404(blog_post_id)
    if blog_post.user != current_user:
        abort(403)

    form = BlogPostForm()
    if form.validate_on_submit():
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, filename))
                image_file = filename
            else:
                image_file = blog_post.image_file
        else:
            image_file = blog_post.image_file

        blog_post.title = form.title.data
        blog_post.text = form.text.data
        db.session.commit()
        flash('Post Updated')
        return redirect(url_for('blog_posts.view_post', blog_post_id=blog_post.id))
    elif request.method == 'GET':
        form.title.data = blog_post.title
        form.text.data = blog_post.text
    return render_template('create_post.html', title='Update', form=form)

@blog_posts.route("/<int:blog_post_id>/delete", methods=['POST'])
@login_required
def delete_post(blog_post_id):
    blog_post = BlogPost.query.get_or_404(blog_post_id)
    if blog_post.user_id != current_user.id:
        abort(403)
    db.session.delete(blog_post)
    db.session.commit()
    flash('Post has been deleted')
    return redirect(url_for('core.index'))

@blog_posts.route('/post/<int:post_id>/add_reaction', methods=['POST'])
@login_required
def add_reaction(post_id):
    post = BlogPost.query.get_or_404(post_id)
    form = ReactionForm()
    if form.validate_on_submit():
        reaction = Reaction(type=form.reaction.data, user=current_user, post=post)
        db.session.add(reaction)
        db.session.commit()
        flash('Your reaction has been added!', 'success')
    return redirect(url_for('blog_posts.view_post', post_id=post.id))

    
@blog_posts.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post(post_id):
    post = Post.query.get_or_404(post_id)
    reactions = Reaction.query.filter_by(post_id=post.id).all()
    reaction_counts = {
        'like': sum(1 for r in reactions if r.type == 'like'),
        'love': sum(1 for r in reactions if r.type == 'love'),
        'haha': sum(1 for r in reactions if r.type == 'haha'),
        'wow': sum(1 for r in reactions if r.type == 'wow'),
        'sad': sum(1 for r in reactions if r.type == 'sad'),
        'angry': sum(1 for r in reactions if r.type == 'angry'),
    }
    return render_template('blog_post.html', post=post, reaction_counts=reaction_counts)