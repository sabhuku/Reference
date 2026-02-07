from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Optional, Length, Regexp, URL, Email, EqualTo

class ReferenceForm(FlaskForm):
    title = StringField('Title', validators=[
        DataRequired(message="Title is required"),
        Length(min=1, max=500, message="Title must be between 1 and 500 characters")
    ])
    authors = StringField(
        'Authors (comma-separated, e.g. "Smith, J., Doe, A.")',
        validators=[
            Optional(),
            Length(max=1000, message="Authors field is too long (max 1000 characters)")
        ]
    )
    year = StringField('Year', validators=[
        Optional(),
        Regexp(r'^\d{4}$', message="Year must be 4 digits (e.g., 2023)")
    ])
    volume = StringField('Volume', validators=[
        Optional(),
        Length(max=20, message="Volume is too long (max 20 characters)")
    ])
    issue = StringField('Issue', validators=[
        Optional(),
        Length(max=20, message="Issue is too long (max 20 characters)")
    ])
    pages = StringField('Pages', validators=[
        Optional(),
        Regexp(r'^[\d\-–\s]+$', message="Pages must be numbers or ranges (e.g., 25-30)")
    ])
    pub_type = SelectField('Type', choices=[
        ('book', 'Book'), 
        ('journal-article', 'Journal Article'),
        ('proceedings-article', 'Proceedings Article'),
        ('web', 'Web Page'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    journal = StringField('Journal / Publisher', validators=[
        Optional(),
        Length(max=300, message="Journal name is too long (max 300 characters)")
    ])
    publisher = StringField('Publisher (for books)', validators=[
        Optional(),
        Length(max=200, message="Publisher name is too long (max 200 characters)")
    ])
    doi = StringField('DOI', validators=[
        Optional(),
        Regexp(
            r'^10\.\d{4,9}/[\S]+$',
            message="Invalid DOI format (should start with 10., e.g., 10.1234/example)"
        )
    ])
    url = StringField('URL', validators=[
        Optional(),
        URL(message="Invalid URL format (e.g., https://example.com)")
    ])
    access_date = StringField('Access Date (e.g., 5 February 2026)', validators=[Optional()])
    submit = SubmitField('Save Reference')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Log In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')
