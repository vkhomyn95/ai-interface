import logging
from datetime import datetime, timedelta

from marshmallow import ValidationError
from sqlalchemy import func, case, update, and_
from werkzeug.security import generate_password_hash

from app.config import variables
from app.extensions import db
from app.models import User, RecognitionConfiguration, Tariff, Recognition, UserRole
from app.schemas.schema import UserSchema


class Database:
    """
        Singleton class of the logger system that will handle the logging system.

    """

    @staticmethod
    def insert_default_roles() -> None:
        try:
            # Insert default roles if they do not exist
            default_roles = ['admin', 'guest']
            for role_name in default_roles:
                if not db.session.query(UserRole).filter(UserRole.name == role_name).first():
                    role = UserRole(name=role_name)
                    db.session.add(role)
                    db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f">>>Error inserting default roles: {e}")

    @staticmethod
    def insert_default_user() -> dict:
        try:
            if not db.session.query(User).filter(User.username == "admin").first():
                default_user = User(
                    username="admin",
                    password=generate_password_hash(variables.USER_DEFAULT_PASSWORD),
                    first_name="Administrator",
                    last_name="VoIPTime",
                    email="support@voiptime.net",
                    role_id=1,
                    tariff=Tariff(),
                    recognition=RecognitionConfiguration()
                )
                db.session.add(default_user)
                db.session.commit()
                return UserSchema().dump(default_user)
        except Exception as e:
            db.session.rollback()
            print(f">>>Error inserting default user: {e}")

    @staticmethod
    def insert_user(user: User):
        try:
            db.session.add(user)
            db.session.commit()
            return user
        except ValidationError as ve:
            print(f">>>Validation error insert_user: {ve.messages}")
            db.session.rollback()
            return None
        except Exception as e:
            db.session.rollback()
            print(f">>>Error insert_user: {e}")
            return None

    @staticmethod
    def update_user(user: User):
        try:
            db.session.add(user)
            db.session.commit()

            return user
        except ValidationError as ve:
            print(f">>>Validation error update_user: {ve.messages}")
            db.session.rollback()
            return None
        except Exception as e:
            db.session.rollback()
            print(f">>>Error update_user: {e}")
            return None

    @staticmethod
    def load_user_by_username(username: str, email: str) -> UserSchema:
        try:
            return db.session.query(User).filter((User.username == username) | (User.email == email)).first()
        except Exception as e:
            logging.error(f'  >> Error during query: {e}')
            db.session.rollback()
            return None

    @staticmethod
    def load_users(limit: int, offset: int, current_user_id: int):
        try:
            return db.session.query(User).filter(User.id != current_user_id).limit(limit).offset(offset).all()
        except Exception as e:
            logging.error(f'  >> Error during query: {e}')
            db.session.rollback()
            return None

    @staticmethod
    def count_users():
        try:
            return db.session.query(User).count()
        except Exception as e:
            logging.error(f'  >> Error during query: {e}')
            db.session.rollback()
            return None

    @staticmethod
    def load_simple_users():
        try:
            return db.session.query(User).all()
        except Exception as e:
            logging.error(f'  >> Error during query: {e}')
            db.session.rollback()
            return None

    @staticmethod
    def load_user_by_id(user_id: int):
        try:
            return db.session.query(User).filter(User.id == user_id).first()
        except Exception as e:
            logging.error(f'  >> Error during query: {e}')
            db.session.rollback()
            return None

    @staticmethod
    def load_user_by_uuid(user_uud: str):
        try:
            return db.session.query(User).filter(User.uuid == user_uud).first()
        except Exception as e:
            logging.error(f'  >> Error during query: {e}')
            db.session.rollback()
            return None

    @staticmethod
    def load_user_by_api_key(api_key: str):
        try:
            return db.session.query(User).filter(User.api_key == api_key).first()
        except Exception as e:
            logging.error(f'  >> Error during query: {e}')
            db.session.rollback()
            return None

    def load_user_dashboard(self, user_id, date_time):
        try:
            now = datetime.utcnow()
            last_24_hours = now - timedelta(days=1)
            filter_condition = Recognition.created_date >= last_24_hours

            if date_time and date_time != '':
                date_f = date_time.split(" - ")
                if len(date_f) == 2:
                    start_date = datetime.strptime(date_f[0], '%Y-%m-%d %H:%M:%S')
                    end_date = datetime.strptime(date_f[1], '%Y-%m-%d %H:%M:%S')
                    filter_condition = and_(Recognition.created_date >= start_date, Recognition.created_date <= end_date)

            query = db.session.query(
                func.sum(
                    case(
                        (filter_condition, 1),
                        else_=0
                    )
                ).label('total'),
                func.sum(
                    case(
                        (and_(filter_condition, Recognition.prediction == 'voicemail'), 1),
                        else_=0
                    )
                ).label('voicemail'),
                func.sum(
                    case(
                        (and_(filter_condition, Recognition.prediction == 'human'), 1),
                        else_=0
                    )
                ).label('human'),
                func.sum(
                    case(
                        (and_(filter_condition, Recognition.prediction == 'not_predicted'), 1),
                        else_=0
                    )
                ).label('not_predicted'),
            ).filter(
                filter_condition,
                Recognition.final == True,
                Recognition.user_id == user_id
            )

            query = query.first()

            return {
                'total': query.total or 0,
                'voicemail': query.voicemail or 0,
                'human': query.human or 0,
                'not_predicted': query.not_predicted or 0,
            }
        except Exception as e:
            logging.error(f'  >> Error during query dashboard: {e}')
            db.session.rollback()
            return None

    @staticmethod
    def parse_date_time(query, date_time: str):
        if date_time and date_time != '':
            date_f = date_time.split(" - ")
            if len(date_f) == 2:
                return query.filter(
                    Recognition.created_date >= datetime.strptime(date_f[0], '%Y-%m-%d %H:%M:%S'),
                    Recognition.created_date <= datetime.strptime(date_f[1], '%Y-%m-%d %H:%M:%S')
                )
        return query

    def load_recognitions(
            self,
            user_id: int,
            date_time: str,
            campaign_id: int,
            request_uuid: str,
            extension: str,
            prediction: str,
            limit: int,
            offset: int
    ):
        try:
            query = db.session.query(Recognition).filter(Recognition.final == True)

            if user_id:
                query = query.filter(Recognition.user_id == user_id)

            query = self.parse_date_time(query, date_time)

            if campaign_id:
                query = query.filter(Recognition.campaign_id == campaign_id)
            if request_uuid:
                query = query.filter(Recognition.request_uuid == request_uuid)
            if extension:
                query = query.filter(Recognition.extension == extension)
            if prediction:
                query = query.filter(Recognition.prediction == prediction)

            recognitions = query.order_by(Recognition.id.desc()).limit(limit).offset(offset).all()

            return recognitions
        except Exception as e:
            logging.error(f'  >> Error: {e}')
            db.session.rollback()
            return None

    def load_recognitions_related_to_user(
            self,
            user_id: int,
            date_time: str,
            campaign_id: int,
            request_uuid: str,
            extension: str,
            prediction: str,
            limit: int,
            offset: int
    ):
        try:
            query = db.session.query(Recognition).filter(Recognition.user_id == user_id, Recognition.final == True)

            query = self.parse_date_time(query, date_time)

            if campaign_id:
                query = query.filter(Recognition.campaign_id == campaign_id)
            if request_uuid:
                query = query.filter(Recognition.request_uuid == request_uuid)
            if extension:
                query = query.filter(Recognition.extension == extension)
            if prediction:
                query = query.filter(Recognition.prediction == prediction)

            recognitions = query.order_by(Recognition.id.desc()).limit(limit).offset(offset).all()
            return recognitions
        except Exception as e:
            logging.error(f'  >> Error: {e}')
            db.session.rollback()
            return None

    @staticmethod
    def load_related_recognitions(request_uuid: str):
        try:
            return db.session.query(Recognition).filter(Recognition.request_uuid == request_uuid).all()
        except Exception as e:
            logging.error(f'  >> Error: {e}')
            db.session.rollback()
            return None

    @staticmethod
    def load_recognition_by_id(recognition_id: int):
        try:
            return db.session.query(Recognition).join(User, Recognition.user_id == User.id).filter(Recognition.id == recognition_id).first()
        except Exception as e:
            logging.error(f'  >> Error during query: {e}')
            db.session.rollback()
            return None

    @staticmethod
    def load_recognition_by_id_related_to_user(recognition_id: int, user_id: int):
        try:
            recognition = db.session.query(Recognition).filter(
                Recognition.id == recognition_id,
                Recognition.user_id == user_id
            ).first()
            return recognition
        except Exception as e:
            logging.error(f'  >> Error: {e}')
            db.session.rollback()
            return None

    def count_recognitions(self, user_id: int, date_time: str, campaign_id: int, request_uuid: str, extension: str, prediction: str):
        try:
            query = db.session.query(func.count(Recognition.id)).filter(Recognition.final == True)

            if user_id:
                query = query.filter(Recognition.user_id == user_id)

            query = self.parse_date_time(query, date_time)

            if campaign_id:
                query = query.filter(Recognition.campaign_id == campaign_id)
            if request_uuid:
                query = query.filter(Recognition.request_uuid == request_uuid)
            if extension:
                query = query.filter(Recognition.extension == extension)
            if prediction:
                query = query.filter(Recognition.prediction == prediction)

            return query.scalar()
        except Exception as e:
            logging.error(f'  >> Error: {e}')
            db.session.rollback()
            return 0

    @staticmethod
    def increment_user_tariff(tariff_id: int, count: int, negative_count: int):
        try:
            tariff = db.session.query(Tariff).filter_by(id=tariff_id).one()
            tariff.total += count
            tariff.negative = negative_count
            db.session.commit()

        except Exception as e:
            logging.error(f'  >> Error: {e}')
            db.session.rollback()
            return {"success": False, "data": str(e)}

    @staticmethod
    def activate_deactivate_user_tariff(tariff_id: int, active: int):
        try:
            tariff = db.session.query(Tariff).filter_by(id=tariff_id).one()
            tariff.active = active
            db.session.commit()

        except Exception as e:
            logging.error(f'  >> Error: {e}')
            db.session.rollback()
            return {"success": False, "data": str(e)}


storage = Database()
