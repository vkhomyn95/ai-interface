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
    negative = db.Column(db.Integer, default=0)
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


class Rights(db.Model):
    __tablename__ = "rights"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=True)
    permissions = db.Column(db.JSON, default=[], nullable=False)


class MLModel(db.Model):
    __tablename__ = 'ml_models'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    model_path = db.Column(db.String(512), nullable=False)  # шлях до .pth файлу
    indexer_path = db.Column(db.String(512), nullable=False)  # шлях до .pkl файлу
    num_classes = db.Column(db.Integer, default=3)
    input_shape = db.Column(db.JSON)  # {"channels": 1, "height": 128, "width": 431}
    version = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow(), nullable=True)
    updated_date = db.Column(db.DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow(), nullable=True)

    # Зв'язок з користувачами
    users = db.relationship('User', back_populates='ml_model')


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
    right_id = db.Column(db.Integer, db.ForeignKey('rights.id'))

    tariff = db.relationship('Tariff', uselist=False, back_populates="user")
    recognition = db.relationship('RecognitionConfiguration', uselist=False, back_populates="user")
    role = db.relationship('UserRole', back_populates='users')

    rights = db.relationship('Rights')

    ml_model_id = db.Column(db.Integer, db.ForeignKey('ml_models.id'), nullable=True)
    ml_model = db.relationship('MLModel', back_populates='users')

    @property
    def permissions(self):
        return self.rights.permissions if self.rights else []


# ALTER TABLE user ADD COLUMN right_id INTEGER;
# ALTER TABLE user ADD CONSTRAINT fk_user_rights FOREIGN KEY (right_id) REFERENCES rights(id);
