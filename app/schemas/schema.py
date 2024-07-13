from marshmallow import fields

from app.extensions import ma, db
from app.models import Tariff, UserRole, RecognitionConfiguration, User


class TariffSchema(ma.SQLAlchemyAutoSchema):

    class Meta:
        model = Tariff
        load_instance = True
        # include_relationships = True
        # sqla_session = db.session
        exclude = ("total",)
        sqla_session = db.session

    id = fields.Int(allow_none=True)
    created_date = fields.Str()
    updated_date = fields.Str()
    active = fields.Bool()
    total = fields.Int()


class UserRoleSchema(ma.SQLAlchemyAutoSchema):

    class Meta:
        model = UserRole
        load_instance = True
        sqla_session = db.session

    id = fields.Int(allow_none=True)
    name = fields.Str()


class RecognitionConfigurationSchema(ma.SQLAlchemyAutoSchema):

    class Meta:
        model = RecognitionConfiguration
        load_instance = True
        sqla_session = db.session

    id = fields.Int()
    encoding = fields.Str(allow_none=True)
    rate = fields.Int()
    interval_length = fields.Int()
    predictions = fields.Int()
    prediction_criteria = fields.Str()


class RecognitionSchema(ma.SQLAlchemyAutoSchema):
    id = fields.Int(allow_none=True)
    created_date = fields.Str()
    final = fields.Bool()
    request_uuid = fields.Str()
    audio_uuid = fields.Str()
    confidence = fields.Int()
    prediction = fields.Str()
    extension = fields.Str()
    company_id = fields.Int()
    campaign_id = fields.Int()
    application_id = fields.Int()


class UserSchema(ma.SQLAlchemyAutoSchema):

    class Meta:
        model = User
        load_instance = True
        include_relationships = True
        sqla_session = db.session

    tariff = fields.Nested(TariffSchema)
    recognition = fields.Nested(RecognitionConfigurationSchema)
    role = fields.Nested(UserRoleSchema)


class UserAPISchema(ma.SQLAlchemyAutoSchema):

    class Meta:
        model = User
        load_instance = True
        include_relationships = True
        sqla_session = db.session

    tariff = fields.Nested(TariffSchema)
    recognition = fields.Nested(RecognitionConfigurationSchema)
    role = fields.Nested(UserRoleSchema)