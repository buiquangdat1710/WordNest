from flask import render_template, request, Blueprint, jsonify, url_for
from companyblog.models import BlogPost, User
from sqlalchemy import or_

core = Blueprint('core', __name__)

@core.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    blog_posts = BlogPost.query.order_by(BlogPost.date.desc()).paginate(page=page, per_page=10)
    return render_template('index.html', blog_posts=blog_posts)

@core.route('/info')
def info():
    return render_template('info.html')

@core.route('/search')
def search():
    query = request.args.get('query', '')
    posts = BlogPost.query.filter(or_(BlogPost.title.contains(query), BlogPost.text.contains(query))).all()
    users = User.query.filter(User.username.contains(query)).all()
    return render_template('search_results.html', query=query, posts=posts, users=users)

@core.route('/search_suggestions')
def search_suggestions():
    query = request.args.get('query', '')
    posts = BlogPost.query.filter(BlogPost.title.contains(query)).limit(5).all()
    users = User.query.filter(User.username.contains(query)).limit(5).all()
    suggestions = [
        {
            'type': 'post',
            'title': post.title,
            'id': post.id
        } for post in posts
    ] + [
        {
            'type': 'user',
            'username': user.username
        } for user in users
    ]
    return jsonify(suggestions)
