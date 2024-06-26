import json

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
from werkzeug.security import check_password_hash, generate_password_hash

from database import Database, User, Tariff, RecognitionConfiguration
from variables import Variables

app = Flask(__name__)

variables = Variables()

db = Database(
    variables.database_user,
    variables.database_password,
    variables.database_host,
    variables.database_port,
    variables.database_name
)

app.config['SECRET_KEY'] = variables.secret_key

"""
    Define auth routing controller
"""


@app.route("/", methods=["GET", "POST"])
@app.route("/login/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if not username or not password:
            flash("Invalid username or password")
            return redirect(url_for("login"))
        else:
            username = username.strip()
            password = password.strip()

        user = db.load_user_by_username(username, None)

        if user and check_password_hash(user['password'], password):
            session["user"] = user
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password")
    return render_template('login.html')


@app.route("/logout", methods=["GET"])
def logout():
    session.pop("user")
    return redirect(url_for('login'))


"""
    Define dashboard controller
"""


@app.route("/dashboard")
def dashboard():
    user = get_user()

    if user:
        if is_admin():
            user_id = request.args.get(
                'user_id',
                user["id"] if not "dashboard_filter" in session else session["dashboard_filter"],
                type=int
            )
        else:
            user_id = user["id"]

        session["dashboard_filter"] = user_id

        board = db.load_user_dashboard(user_id if is_admin() else user["id"])
        return render_template(
            'dashboard.html',
            users=db.load_simple_users() if is_admin() else [],
            dashboard={key: int(value) if value is not None else 0 for key, value in board.items()},
            role=user["role_name"],
            filter=session["dashboard_filter"],
            username=user["first_name"] + " " + user["last_name"]
        )
    else:
        return redirect(url_for("login"))


"""
    Define user routing controller
"""


@app.route('/users')
def users():
    current_user = session.get("user")

    if current_user:
        if current_user['role_name'] == 'admin':
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 10, type=int)
            offset = (page - 1) * limit

            users = db.load_users(limit, offset, current_user["id"])
            users_count = db.count_users()["count"]
            total_pages = 1 if users_count <= limit else (users_count + (limit - 1)) // limit

            # Determine the range of pages to display
            start_page = max(1, page - 2)
            end_page = min(total_pages, page + 2)

            # Render the template with the data
            return render_template(
                'users.html',
                users=users,
                total_pages=total_pages,
                page=page,
                start_page=start_page,
                end_page=end_page,
                role=current_user["role_name"],
                username=current_user["first_name"] + " " + current_user["last_name"]
            )
        else:
            return redirect(url_for("user", user_id=current_user["id"]))
    else:
        return redirect(url_for('login'))


@app.route('/profile', methods=['POST', 'GET'])
def profile():
    current_user = session.get("user")

    if current_user:
        user = db.load_user_by_id(int(current_user["id"]))
        if request.method == "GET":
            # Render the template with the data
            user["password"] = ""
            return render_template(
                'user.html',
                user=user,
                role=current_user["role_name"],
                username=current_user["first_name"] + " " + current_user["last_name"],
                is_profile=True
            )
        else:
            db.update_user(to_tariff_obj(request, user), to_recognition_obj(request), to_user_obj(request, user))

            return redirect(url_for('users'))
    else:
        return redirect(url_for('login'))


@app.route('/users/<user_id>', methods=['POST', 'GET'])
def user(user_id: int):
    current_user = session.get("user")

    if current_user:
        user = db.load_user_by_id(int(user_id))
        if request.method == "GET":
            # Render the template with the data
            user["password"] = ""
            return render_template(
                'user.html',
                user=user,
                role=current_user["role_name"],
                username=current_user["first_name"] + " " + current_user["last_name"]
            )
        else:
            db.update_user(to_tariff_obj(request, user), to_recognition_obj(request), to_user_obj(request, user))

            return redirect(url_for('users'))
    else:
        return redirect(url_for('login'))


@app.route('/create-user', methods=['POST', 'GET'])
def create_user():
    current_user = session.get("user")

    if current_user:
        if request.method == "GET":
            if is_admin():

                # Render the template with the data
                return render_template(
                    'user.html',
                    user={
                        "active": False,
                        "total": 0,
                        "used": 0,
                        "encoding": "slin",
                        "rate": 8000,
                        "interval_length": 2,
                        "predictions": 2,
                        "prediction_criteria": ""
                    },
                    role=current_user["role_name"],
                    username=current_user["first_name"] + " " + current_user["last_name"]
                )
            else:
                redirect(url_for('user', user_id=current_user["id"]))
        else:
            user = db.load_user_by_username(request.form["username"], request.form["email"])

            if user is not None:
                flash("User with username {} or email {} already exists".format(
                    request.form["username"], request.form["email"])
                )
                merged_dict = {}
                merged_dict.update(to_tariff_obj(request, user))
                merged_dict.update(to_recognition_obj(request))
                merged_dict.update(to_user_obj(request, user))
                return render_template(
                    'user.html',
                    user=merged_dict,
                    role=current_user["role_name"],
                    username=current_user["first_name"] + " " + current_user["last_name"]
                )
            else:
                db.insert_user(to_tariff_obj(request, user), to_recognition_obj(request), to_user_obj(request, user))

            return redirect(url_for('users'))
    else:
        return redirect(url_for('login'))


@app.route('/api/user/<uuid>', methods=['POST', 'GET', 'PUT'])
def api_user(uuid: str):
    access_token = request.args.get('access_token')
    if access_token and access_token != variables.license_server_access_token:
        return {
            "success": False,
            "data": "Invalid access token"
        }

    if request.method == "GET":
        if uuid is not None and uuid != '':
            searched_user = db.load_user_by_uuid(uuid)
            if searched_user is not None:
                return {
                    "success": True,
                    "data": User(
                        id=searched_user["id"],
                        created_date=searched_user["created_date"],
                        updated_date=searched_user["updated_date"],
                        first_name=searched_user["first_name"],
                        last_name=searched_user["last_name"],
                        email=searched_user["email"],
                        phone=searched_user["phone"],
                        username=searched_user["username"],
                        api_key=searched_user["api_key"],
                        audience=searched_user["audience"],
                        tariff=Tariff(
                            searched_user["tariff_id"],
                            searched_user["created_date"],
                            searched_user["updated_date"],
                            byte_to_bool(searched_user["active"]),
                            searched_user["total"],
                            searched_user["used"]
                        ),
                        configuration=RecognitionConfiguration(
                            searched_user["recognition_id"],
                            searched_user["encoding"],
                            searched_user["rate"],
                            searched_user["interval_length"],
                            searched_user["predictions"],
                            searched_user["prediction_criteria"]
                        )
                    )
                }
            else:
                return {
                    "success": False,
                    "data": None
                }

    if request.method == "PUT":
        if uuid is not None and uuid != '':
            searched_user = db.load_user_by_uuid(uuid)
            if searched_user is not None:
                tariff = request.json["tariff"]
                configuration = request.json["configuration"]
                user_obj = request.json
                user_obj["tariff_id"] = tariff["id"]
                user_obj["recognition_id"] = configuration["id"]
                user_obj["password"] = searched_user["password"]
                db.update_user(tariff, configuration, user_obj)
                return {
                    "success": True,
                    "data": "Ok"
                }
            else:
                return {
                    "success": False,
                    "data": "Not valid request body. Invalid user id."
                }
        else:
            return {
                "success": False,
                "data": "Not valid request body. Invalid user id."
            }

    if request.method == "POST":
        if uuid is not None and uuid != '':
            searched_user = db.load_user_by_username(request.json["username"], request.json["email"])
            if searched_user is None:
                tariff = request.json["tariff"]
                configuration = request.json["configuration"]
                user_obj = request.json
                user_obj["password"] = generate_password_hash(request.json["password"])
                user_obj["uuid"] = uuid
                u_id = db.insert_user(tariff, configuration, user_obj)
                return {
                    "success": True,
                    "data": u_id
                }
            else:
                return {
                    "success": False,
                    "data": "User with username or email already exists."
                }
        else:
            return {
                "success": False,
                "data": "Not valid request body. Invalid user uuid."
            }


"""
    Define user recognition controller
"""


@app.route('/recognitions')
def recognitions():
    current_user = session.get("user")

    if current_user:

        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        offset = (page - 1) * limit

        campaign_id = request.args.get('campaign_id', '', type=str).strip()
        request_uuid = request.args.get('request_uuid', '', type=str).strip()
        extension = request.args.get('extension', '', type=str).strip()

        if current_user["role_name"] == "admin":
            user_id = request.args.get('user_id', '', type=str).strip()
            recognitions = db.load_recognitions(user_id, campaign_id, request_uuid, extension, limit, offset)
        else:
            user_id = current_user["id"]
            recognitions = db.load_recognitions_related_to_user(user_id, campaign_id, request_uuid, extension, limit, offset)

        recognitions_count = db.count_recognitions(user_id, campaign_id, request_uuid, extension)["count"]

        total_pages = 1 if recognitions_count <= limit else (recognitions_count + (limit - 1)) // limit

        # Determine the range of pages to display
        start_page = max(1, page - 2)
        end_page = min(total_pages, page + 2)

        # Render the template with the data
        return render_template(
            'recognitions.html',
            recognitions=recognitions,
            total_pages=total_pages,
            page=page,
            start_page=start_page,
            end_page=end_page,
            role=current_user["role_name"],
            users=db.load_simple_users() if current_user["role_name"] == "admin" else [],
            username=current_user["first_name"] + " " + current_user["last_name"],
            filter={
                "user_id": user_id,
                "campaign_id": campaign_id,
                "request_uuid": request_uuid,
                "extension": extension,
            }
        )
    else:
        return redirect(url_for('login'))


@app.route('/recognitions/<recognition_id>')
def recognition(recognition_id: int):
    current_user = session.get("user")

    if current_user:
        related_recognitions = []

        if is_admin():
            recognition = db.load_recognition_by_id(recognition_id)
            if recognition is not None:
                related_recognitions = db.load_related_recognitions(recognition["request_uuid"])
                k = 0
                l = 0
                r = ''
                for r in related_recognitions:
                    if r["prediction"] != "ring":
                        k += r["confidence"]
                        l += 1
                    if r["final"]:
                        r = r["prediction"]
                if len(related_recognitions) > 0:
                    if l != 0:
                        recognition["confidence"] = k / l
                    recognition["prediction"] = r
        else:
            recognition = db.load_recognition_by_id_related_to_user(recognition_id, current_user["id"])
            if recognition is not None:
                related_recognitions = db.load_related_recognitions(recognition["request_uuid"])
                k = 0
                l = 0
                r = ''
                for r in related_recognitions:
                    if r["prediction"] != "ring":
                        k += r["confidence"]
                        l += 1
                    if r["final"]:
                        r = r["prediction"]
                if len(related_recognitions) > 0:
                    if l != 0:
                        recognition["confidence"] = k / l
                    recognition["prediction"] = r
        # Render the template with the data
        return render_template(
            'recognition.html',
            recognition=recognition,
            related_recognitions=related_recognitions,
            role=current_user["role_name"],
            username=current_user["first_name"] + " " + current_user["last_name"]
        )
    else:
        return redirect(url_for('login'))


@app.route('/audio/<path:filename>')
def serve_audio(filename):
    current_user = session.get("user")

    if current_user:
        if filename != 'None':
            if not filename.endswith('.wav'):
                filename = filename + '.wav'
            return send_from_directory(variables.audio_dir, filename)
        return ''
    else:
        return redirect(url_for('login'))


"""
    Define a custom Jinja filter to transform bytes to boolean
"""


@app.template_filter('byte_to_bool')
def byte_to_bool(value):
    if value == "b'\\x00'":
        return False
    if value == "b'\\x01'":
        return True
    if value is None:
        return False
    if value == 'True':
        return True
    if value == 'False':
        return False
    if not value:
        return False
    if value == True:
        return True
    return bool(int.from_bytes(value, byteorder='big'))


@app.template_filter('obj_to_str')
def obj_to_str(value):
    return str(value)


@app.template_filter('str_to_int')
def str_to_int(value):
    if value is not None:
        return int(value)
    else:
        return None


@app.template_filter('calculate_avg_prediction_confidence')
def calculate_avg_prediction_confidence(arr):
    if len(arr) == 0:
        return 0
    total = sum(obj["confidence"] for obj in arr)
    return total / len(arr)


@app.template_filter('calculate_prediction_result')
def calculate_prediction_result(arr):
    for o in arr:
        if byte_to_bool(o["final"]):
            return o["prediction"]
    return "Not predicted"


def to_tariff_obj(request, user):
    return {
        "active": byte_to_bool(request.form.get("active")),
        "total": request.form.get("total") if get_user()["role_name"] == "admin" else user["total"],
        "used": request.form.get("used") if get_user()["role_name"] == "admin" else user["used"]
    }


def to_recognition_obj(request):
    return {
        "encoding": request.form.get("encoding"),
        "rate": request.form.get("rate"),
        "interval_length": request.form.get("interval_length"),
        "predictions": request.form.get("predictions"),
        "prediction_criteria": parse_criteria(request.form)
    }


def to_user_obj(request, user):
    # check if update form
    if user:
        if request.form.get("password") != "":
            password = generate_password_hash(request.form.get("password"))
        else:
            password = user["password"]
    else:
        password = generate_password_hash(request.form.get("password"))

    return {
        "id": request.form.get("id"),
        "username": request.form.get("username") if not user else user["username"],
        "password": password,
        "first_name": request.form.get("first_name"),
        "last_name": request.form.get("last_name"),
        "email": request.form.get("email"),
        "phone": request.form.get("phone"),
        "api_key": request.form.get("api_key"),
        "audience": request.form.get("audience"),
        "tariff_id": request.form.get("tariff_id"),
        "recognition_id": request.form.get("recognition_id"),
        "role_id": 2
    }


def parse_criteria(form):
    return json.dumps({key: form.get(key) for key in form.keys() if '_interval_' in key or 'result' in key})


def get_user():
    return session.get("user")


def is_admin():
    if session["user"]['role_name'] == 'admin':
        return True


if __name__ == '__main__':
    app.run(debug=True, host=variables.app_host, port=variables.app_port)
