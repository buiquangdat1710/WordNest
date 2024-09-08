from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, FileField, HiddenField
from wtforms.validators import DataRequired
from flask_wtf.file import FileAllowed

class BlogPostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    text = TextAreaField('Content', validators=[DataRequired()])
    image = FileField('Update Blog Image', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Post')

class CommentForm(FlaskForm):
    body = TextAreaField('Comment', validators=[DataRequired()])
    submit = SubmitField('Post')

class ReactionForm(FlaskForm):
    reaction = HiddenField('Reaction', validators=[DataRequired()])