from datetime import datetime

from app.config import variables
from app.extensions import db


class Tariff(db.Model):
    __tablename__ = "tariff"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow(), nullable=True)
    updated_date = db.Column(db.DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow(), nullable=True)
    active = db.Column(db.Boolean, default=False)
    total = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)

    user = db.relationship("User", back_populates="tariff")


class UserRole(db.Model):
    __tablename__ = "user_role"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=True)

    users = db.relationship('User', back_populates='role')


class RecognitionConfiguration(db.Model):
    __tablename__ = "recognition_configuration"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    encoding = db.Column(db.String(128))
    rate = db.Column(db.Integer, default=variables.audio_sample_rate)
    interval_length = db.Column(db.Integer, default=variables.audio_interval)
    predictions = db.Column(db.Integer, default=variables.max_predictions)
    prediction_criteria = db.Column(db.Text, default=variables.prediction_criteria)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)

    user = db.relationship('User', back_populates='recognition', uselist=False, foreign_keys=[user_id])


class Recognition(db.Model):
    __tablename__ = "recognition"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow(), nullable=True)
    final = db.Column(db.Boolean, default=True)
    request_uuid = db.Column(db.String(128), nullable=True)
    audio_uuid = db.Column(db.String(128), nullable=True)
    confidence = db.Column(db.Integer, nullable=True)
    prediction = db.Column(db.String(64), nullable=True)
    extension = db.Column(db.String(64), nullable=True)
    company_id = db.Column(db.Integer, nullable=True)
    campaign_id = db.Column(db.Integer, nullable=True)
    application_id = db.Column(db.Integer, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', uselist=False, lazy=True)


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow(), nullable=True)
    updated_date = db.Column(db.DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow(), nullable=True)
    first_name = db.Column(db.String(128), nullable=True)
    last_name = db.Column(db.String(128), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(128), nullable=True)
    username = db.Column(db.String(128), unique=True, nullable=True)
    password = db.Column(db.String(255), nullable=True)
    api_key = db.Column(db.String(255), nullable=True)
    uuid = db.Column(db.String(255), nullable=True)
    audience = db.Column(db.String(255), nullable=True)
    role_id = db.Column(db.Integer, db.ForeignKey('user_role.id'))

    tariff = db.relationship('Tariff', uselist=False, back_populates="user")
    recognition = db.relationship('RecognitionConfiguration', uselist=False, back_populates="user")
    role = db.relationship('UserRole', back_populates='users')

