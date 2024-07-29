import logging
from datetime import datetime, timedelta

from marshmallow import ValidationError
from sqlalchemy import func, case, update
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

    @staticmethod
    def load_user_dashboard(user_id):
        try:
            today = datetime.utcnow().date()
            last_week = today - timedelta(days=6)
            first_day_of_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)

            query = db.session.query(
                func.sum(
                    case(
                        (func.date(Recognition.created_date) == today, 1),
                        else_=0
                    )
                ).label('today_total'),
                func.sum(
                    case(
                        (func.date(Recognition.created_date) == today, case(
                            (Recognition.prediction == 'voicemail', 1),
                            else_=0
                        )),
                        else_=0
                    )
                ).label('today_voicemail'),
                func.sum(
                    case(
                        (func.date(Recognition.created_date) == today, case(
                            (Recognition.prediction != 'voicemail', 1),
                            else_=0
                        )),
                        else_=0
                    )
                ).label('today_human'),
                func.sum(
                    case(
                        (Recognition.created_date >= last_week, 1),
                        else_=0
                    )
                ).label('week_total'),
                func.sum(
                    case(
                        (Recognition.created_date >= last_week, case(
                            (Recognition.prediction == 'voicemail', 1),
                            else_=0
                        )),
                        else_=0
                    )
                ).label('week_voicemail'),
                func.sum(
                    case(
                        (Recognition.created_date >= last_week, case(
                            (Recognition.prediction != 'voicemail', 1),
                            else_=0
                        )),
                        else_=0
                    )
                ).label('week_human'),
                func.sum(
                    case(
                        (Recognition.created_date >= first_day_of_month, 1),
                        else_=0
                    )
                ).label('month_total'),
                func.sum(
                    case(
                        (Recognition.created_date >= first_day_of_month, case(
                            (Recognition.prediction == 'voicemail', 1),
                            else_=0
                        )),
                        else_=0
                    )
                ).label('month_voicemail'),
                func.sum(
                    case(
                        (Recognition.created_date >= first_day_of_month, case(
                            (Recognition.prediction != 'voicemail', 1),
                            else_=0
                        )),
                        else_=0
                    )
                ).label('month_human')
            ).filter(
                Recognition.created_date >= first_day_of_month,
                Recognition.final == True,
                Recognition.user_id == user_id
            ).first()

            return {
                'today_total': query.today_total,
                'today_voicemail': query.today_voicemail,
                'today_human': query.today_human,
                'week_total': query.week_total,
                'week_voicemail': query.week_voicemail,
                'week_human': query.week_human,
                'month_total': query.month_total,
                'month_voicemail': query.month_voicemail,
                'month_human': query.month_human
            }
        except Exception as e:
            logging.error(f'  >> Error during query dashboard: {e}')
            db.session.rollback()
            return None

    @staticmethod
    def load_recognitions(
            user_id: int,
            campaign_id: int,
            request_uuid: str,
            extension: str,
            limit: int,
            offset: int
    ):
        try:
            query = db.session.query(Recognition).filter(Recognition.final == True)

            if user_id:
                query = query.filter(Recognition.user_id == user_id)
            if campaign_id:
                query = query.filter(Recognition.campaign_id == campaign_id)
            if request_uuid:
                query = query.filter(Recognition.request_uuid == request_uuid)
            if extension:
                query = query.filter(Recognition.extension == extension)

            recognitions = query.order_by(Recognition.id.desc()).limit(limit).offset(offset).all()
            return recognitions
        except Exception as e:
            logging.error(f'  >> Error: {e}')
            db.session.rollback()
            return None

    @staticmethod
    def load_recognitions_related_to_user(
            user_id: int,
            campaign_id: int,
            request_uuid: str,
            extension: str,
            limit: int,
            offset: int
    ):
        try:
            query = db.session.query(Recognition).filter(Recognition.user_id == user_id, Recognition.final == True)

            if campaign_id:
                query = query.filter(Recognition.campaign_id == campaign_id)
            if request_uuid:
                query = query.filter(Recognition.request_uuid == request_uuid)
            if extension:
                query = query.filter(Recognition.extension == extension)

            recognitions = query.order_by(Recognition.id.desc()).limit(limit).offset(offset).all()
            return recognitions
        except Exception as e:
            logging.error(f'  >> Error: {e}')
            db.session.rollback()
            return None

    @staticmethod
    def load_related_recognitions(request_uuid: str):
        try:
            recognitions = db.session.query(Recognition).filter(Recognition.request_uuid == request_uuid).all()
            return recognitions
        except Exception as e:
            logging.error(f'  >> Error: {e}')
            db.session.rollback()
            return None

    @staticmethod
    def load_recognition_by_id(recognition_id: int):
        try:
            return db.session.query(Recognition).filter(Recognition.id == recognition_id).first()
        except Exception as e:
            logging.error(f'  >> Error during query: {e}')
            db.session.rollback()
            return None

    @staticmethod
    def load_recognition_by_id_related_to_user(recognition_id: int, user_id: int):
        try:
            recognition = db.session.query(Recognition).join(User, Recognition.user_id == User.id).filter(
                Recognition.id == recognition_id,
                Recognition.user_id == user_id
            ).first()
            return recognition
        except Exception as e:
            logging.error(f'  >> Error: {e}')
            db.session.rollback()
            return None

    @staticmethod
    def count_recognitions(user_id: int, campaign_id: int, request_uuid: str, extension: str):
        try:
            query = db.session.query(func.count(Recognition.id)).filter(Recognition.final == True)

            if user_id:
                query = query.filter(Recognition.user_id == user_id)
            if campaign_id:
                query = query.filter(Recognition.campaign_id == campaign_id)
            if request_uuid:
                query = query.filter(Recognition.request_uuid == request_uuid)
            if extension:
                query = query.filter(Recognition.extension == extension)

            return query.scalar()
        except Exception as e:
            logging.error(f'  >> Error: {e}')
            db.session.rollback()
            return 0

    @staticmethod
    def increment_user_tariff(tariff_id: int, count: int):
        try:
            tariff = db.session.query(Tariff).filter_by(id=tariff_id).one()
            tariff.total += count
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
