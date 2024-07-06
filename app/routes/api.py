from flask import Blueprint, request
from werkzeug.security import generate_password_hash

from app.config import variables
from app.extensions import storage
from app.models import User, Tariff, RecognitionConfiguration
from app.schemas import UserSchema
from app.schemas.schema import UserAPISchema

apis = Blueprint("apis_blp", __name__, url_prefix="/user")


@apis.get("/<uuid>")
def get_user(uuid: str):
    access_token = request.args.get('access_token')
    if not access_token or access_token == "":
        return {"success": False, "data": "Invalid access token"}

    if not uuid or uuid == "":
        return {"success": False, "data": "Invalid UUID"}

    if access_token != variables.license_server_access_token:
        return {"success": False, "data": "Invalid access token"}

    user = storage.load_user_by_uuid(uuid)

    return {"success": True, "data": UserAPISchema(exclude=("recognition", "role", "password")).dump(user)}


@apis.post("")
def create_user():
    access_token = request.args.get('access_token')
    if not access_token or access_token == "":
        return {"success": False, "data": "Invalid access token"}

    if access_token != variables.license_server_access_token:
        return {"success": False, "data": "Invalid access token"}

    if "uuid" not in request.json:
        return {"success": False, "data": "Missing uuid"}

    user = storage.load_user_by_uuid(request.json["uuid"])

    if user is not None:
        return {"success": False, "data": "User already exists"}

    if "password" not in request.json:
        return {"success": False, "data": "Missing password"}

    if "username" not in request.json:
        return {"success": False, "data": "Missing username"}

    user = storage.load_user_by_username(request.json["username"], request.json["email"])
    if user is not None:
        return {"success": False, "data": "User already exists with defined email or username"}

    user_schema = UserAPISchema(exclude=("id", "tariff", "role", "recognition")).load(request.json)
    user_schema.role_id = 2
    user_schema.password = generate_password_hash(request.json["password"])
    user_schema.tariff = Tariff()
    user_schema.recognition = RecognitionConfiguration(
        rate=variables.audio_sample_rate,
        interval_length=variables.audio_interval,
        predictions=variables.max_predictions,
        prediction_criteria=variables.prediction_criteria
    )

    inserted_user = storage.insert_user(user_schema)

    return {"success": True, "data": UserAPISchema(exclude=("recognition", "role", "password")).dump(inserted_user)}


@apis.post("/<uuid>/license")
def increment_user_license(uuid: str):
    access_token = request.args.get('access_token')
    if not access_token or access_token == "":
        return {"success": False, "data": "Invalid access token"}

    if not uuid or uuid == "":
        return {"success": False, "data": "Invalid UUID"}

    if access_token != variables.license_server_access_token:
        return {"success": False, "data": "Invalid access token"}

    license_count = request.args.get('count')

    if not license_count or license_count == "0":
        return {"success": False, "data": "Invalid license count, should be greater than 0"}

    user = storage.load_user_by_uuid(uuid)

    if not user:
        return {"success": False, "data": "User does not exist with requested uuid"}

    storage.increment_user_tariff(user.tariff.id, int(license_count))

    return {"success": True, "data": "Successfully incremented user tariff"}
