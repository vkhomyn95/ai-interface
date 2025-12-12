import json
import logging
import os
import uuid
from datetime import datetime
from io import BytesIO

import pandas as pd
import pytz
from flask import Blueprint, request, flash, redirect, url_for, session, render_template, send_from_directory, send_file, g, abort, jsonify
from sqlalchemy.orm import class_mapper
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

from app.config import variables
from app.extensions import storage
from app.models import User, Tariff, RecognitionConfiguration, Rights, MLModel
from app.schemas import UserSchema
from app.extensions.permissions import PermissionTypes

bases = Blueprint("bases_blp", __name__, url_prefix="/")

def require_permission(permission_id):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user = get_user()
            permissions = user.get('rights', {}).get('permissions', [])
            if permission_id not in permissions:
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator


@bases.route("/", methods=["GET", "POST"])
@bases.route("/login/", methods=["GET", "POST"])
def login():
    """
    Handle the login page.

    GET:
        Renders the 'login.html' template to display the login form.

    POST:
        Processes the login form submission.
        - If the username or password is missing, flashes an error message and redirects to the login page.
        - Strips leading/trailing whitespace from the username and password.
        - Loads the user by username.
        - Checks the password hash against the provided password.
        - If the credentials are valid, sets the user session and redirects to the dashboard.
        - Otherwise, flashes an error message and re displays the login page.

    Templates:
        - login.html: The template for the login page.
        """
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if not username or not password:
            flash("Invalid username or password")
            return redirect(url_for("login"))
        else:
            username = username.strip()
            password = password.strip()

        current_user: User = storage.load_user_by_username(username, None)

        if current_user and check_password_hash(current_user.password, password):
            session["user"] = UserSchema().dump(current_user)
            return redirect(url_for("bases.bases_blp.dashboard"))
        else:
            flash("Invalid username or password")
    return render_template('login.html')


@bases.route("/logout", methods=["GET"])
def logout():
    """
    Handle user logout.

    GET:
        Logs out the current user by removing the 'user' key from the session.
        Redirects the user to the login page after logging out.

    Templates:
        - None: This endpoint does not render a template; it only performs a redirect.
    """
    session.pop("user")
    return redirect(url_for('bases.bases_blp.login'))


@bases.route("/dashboard", methods=["GET"])
def dashboard():
    """
    Renders the user dashboard.

    Returns:
        str: The rendered HTML of the dashboard page.
    """
    session_user = get_user()

    if not session_user:
        return redirect(url_for("bases.bases_blp.login"))

    reset = bool(request.args.get('reset', 0, type=int))
    dashboard_filter = session.get("dashboard_filter", {})
    if is_admin() or is_supervisor():
        user_id = request.args.get(
            'user_id',
            dashboard_filter.get("user_id", session_user["id"]) if not reset else '',
            type=int
        )
        time = request.args.get('datetime', '')
        date_time = dashboard_filter.get("datetime", '') if not reset and not time else time
    else:
        user_id = session_user["id"]
        time = request.args.get('datetime', '')
        date_time = dashboard_filter.get("datetime", '') if not reset and not time else time

    session["dashboard_filter"] = {"user_id": user_id, "datetime": date_time}
    board = storage.load_user_dashboard(user_id if is_admin() or is_supervisor() else session_user["id"], date_time)

    return render_template(
        'dashboard.html',
        users=storage.load_simple_users() if is_admin() or is_supervisor() else [],
        dashboard={} if board is None else {key: int(value) if value is not None else 0 for key, value in board.items()},
        filter=session.get("dashboard_filter", {}),
        current_user=session_user
    )


@bases.route('/profile', methods=['GET'])
@require_permission(PermissionTypes.TAB_PROFILE)
def profile():
    """
    Handle the login page.

    GET:
        Renders the 'user.html' template to display the profile form.

    POST:
        Processes the profile form submission.
        - If the username or password is missing, flashes an error message and redirects to the login page.
        - Strips leading/trailing whitespace from the username and password.
        - Loads the user by username.
        - Checks the password hash against the provided password.
        - If the credentials are valid, sets the user session and redirects to the dashboard.
        - Otherwise, flashes an error message and re displays the login page.

    Templates:
        - user.html: The template for the profile page.
        """
    session_user = get_user()

    if not session_user:
        return redirect(url_for("bases.bases_blp.login"))

    searched_user = storage.load_user_by_id(session_user["id"])
    searched_user.password = ""
    return render_template(
        'user.html',
        user=searched_user,
        rights=storage.load_simple_rights(),
        current_user=session_user,
        is_profile=True
    )


@bases.route('/users', methods=["GET"])
@require_permission(PermissionTypes.TAB_USERS)
def users():
    """
    Handles the user management page for administrators.

    Returns:
        str: The rendered HTML of the user management page if the user is an admin.
             Redirects to the login page if no user is in session.
             Redirects to the user's personal page if the user is not an admin.
    """
    session_user = get_user()

    if not session_user:
        return redirect(url_for("bases.bases_blp.login"))

    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    offset = (page - 1) * limit

    searched_users = storage.load_users(limit, offset, session_user["id"])
    users_count = storage.count_users()
    total_pages = 1 if users_count <= limit else (users_count + (limit - 1)) // limit

    # Render the template with the data
    return render_template(
        'users.html',
        users=searched_users,
        total_pages=total_pages,
        page=page,
        start_page=max(1, page - 2),
        end_page=min(total_pages, page + 2),
        current_user=session_user
    )


@bases.route('/users/<user_id>', methods=['POST', 'GET'])
@require_permission(PermissionTypes.USERS_EDIT)
def user(user_id: int):
    """
    Handle the user's profile display and update.

    GET:
        - Retrieves the user data for the given user_id.
        - Renders the 'user.html' template with the user data and the current session user.

    POST:
        - Updates the user data based on the form submission.
        - Updates related objects (Tariff, RecognitionConfiguration).
        - Redirects to the 'users' page.

    Args:
        user_id (int): The ID of the user to be retrieved and updated.

    Returns:
        - A rendered template for GET requests.
        - A redirect to the 'users' page for POST requests.
    """
    session_user = session.get("user")

    if not session_user:
        return redirect(url_for("bases.bases_blp.login"))

    searched_user = storage.load_user_by_id(int(user_id))
    if request.method == "GET":
        if not is_admin() or is_supervisor():
            return redirect(url_for("bases.bases_blp.profile"))

        searched_user.password = ""
        return render_template(
            'user.html',
            user=searched_user,
            rights=storage.load_simple_rights(),
            ml_models=storage.get_active_models(),
            current_user=session_user
        )
    else:
        if is_supervisor():
            return redirect(url_for('bases.bases_blp.users'))
        if is_admin() or searched_user.id == session_user["id"]:
            ml_model_id = request.form.get('ml_model_id')
            searched_user.ml_model_id = int(ml_model_id) if ml_model_id else None

            update_user(request, searched_user)
            storage.update_user(searched_user)
            if is_admin():
                return redirect(url_for('bases.bases_blp.users'))
            else:
                return redirect(url_for("bases.bases_blp.dashboard"))
        else:
            return redirect(url_for("bases.bases_blp.profile"))


@bases.route('/create-user', methods=['POST', 'GET'])
@require_permission(PermissionTypes.USERS_CREATE)
def create_user():
    """
    Handle the creation of a new user.

    GET:
        - Renders the 'user.html' template with a blank user form for admin users.

    POST:
        - Creates a new user based on the form submission.
        - Checks for existing users with the same username or email.
        - If the user exists, flashes a message and re-renders the form.
        - If the user does not exist, inserts the new user and redirects to the 'users' page.

    Returns:
        - A rendered template for GET requests.
        - A redirect to the 'users' page for POST requests.
    """
    session_user = get_user()

    if not session_user:
        return redirect(url_for("bases.bases_blp.login"))

    if request.method == "GET":
        return render_template(
            'user.html',
            user=UserSchema().dump(
                User(
                    role_id=2,
                    tariff=Tariff(),
                    recognition=RecognitionConfiguration()
                )
            ),
            rights=storage.load_simple_rights(),
            ml_models=storage.get_active_models(),
            current_user=session_user
        )

    if request.method == "POST":
        if is_supervisor():
            return redirect(url_for('bases.bases_blp.users'))

        searched_user = storage.load_user_by_username(request.form.get("username"), request.form.get("email"))
        if searched_user:
            flash("User with username {} or email {} already exists".format(
                request.form["username"], request.form["email"])
            )
            new_user = User(
                role_id=2,
                tariff=Tariff(),
                recognition=RecognitionConfiguration()
            )
            update_user(request, new_user)
            return render_template(
                'user.html',
                user=new_user,
                rights=storage.load_simple_rights(),
                ml_models=storage.get_active_models(),
                current_user=session_user
            )
        else:
            new_user = User(
                role_id=2,
                tariff=Tariff(),
                recognition=RecognitionConfiguration()
            )
            ml_model_id = request.form.get('ml_model_id')
            new_user.ml_model_id = int(ml_model_id) if ml_model_id else None

            update_user(request, new_user)
            storage.insert_user(new_user)
            return redirect(url_for('bases.bases_blp.users'))
    else:
        redirect(url_for('bases.bases_blp.user', user_id=session_user["id"]))


@bases.route('/rights', methods=["GET"])
@require_permission(PermissionTypes.TAB_USERS_RIGHTS)
def rights():
    """
    Handles the user management page for administrators.

    Returns:
        str: The rendered HTML of the user management page if the user is an admin.
             Redirects to the login page if no user is in session.
             Redirects to the user's personal page if the user is not an admin.
    """
    session_user = get_user()

    if not session_user:
        return redirect(url_for("bases.bases_blp.login"))

    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    offset = (page - 1) * limit

    searched_rights = storage.load_rights(limit, offset)
    rights_count = storage.count_rights()
    total_pages = 1 if rights_count <= limit else (rights_count + (limit - 1)) // limit

    # Render the template with the data
    return render_template(
        'rights.html',
        rights=searched_rights,
        total_pages=total_pages,
        page=page,
        start_page=max(1, page - 2),
        end_page=min(total_pages, page + 2),
        current_user=session_user
    )


@bases.route('/update-rights/<right_id>', methods=['POST'])
@require_permission(PermissionTypes.TAB_USERS_RIGHTS)
def update_rights(right_id):
    if is_supervisor():
        return redirect(url_for('bases.bases_blp.rights'))

    permission = storage.load_right_by_id(right_id)
    update_right(request, permission)
    storage.update_right(permission)
    return redirect(url_for('bases.bases_blp.rights'))


@bases.route('/create-right', methods=['POST'])
@require_permission(PermissionTypes.TAB_USERS_RIGHTS)
def create_right():
    session_user = get_user()

    if not session_user:
        return redirect(url_for("bases.bases_blp.login"))

    if is_supervisor():
        return redirect(url_for('bases.bases_blp.rights'))

    if request.method == "POST":
        new_right = storage.insert_new_right(request.form.get('name'))
        logging.info(f'== Request create rights {new_right} by user {get_user()["id"]}')

        return redirect(url_for('bases.bases_blp.rights'))
    else:
        return redirect(url_for('bases.bases_blp.rights'))


@bases.route('/models', methods=["GET"])
@require_permission(PermissionTypes.TAB_ML_MODELS)
def models():
    """
    Handles the ML models list page.
    """
    session_user = get_user()

    if not session_user:
        return redirect(url_for("bases.bases_blp.login"))

    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    offset = (page - 1) * limit

    models = storage.load_models(limit, offset)
    count = storage.count_models()
    total_pages = 1 if count <= limit else (count + (limit - 1)) // limit

    return render_template(
        'models.html',
        models=models,
        total_pages=total_pages,
        page=page,
        start_page=max(1, page - 2),
        end_page=min(total_pages, page + 2),
        current_user=session_user
    )


@bases.route('/models/create', methods=['GET', 'POST'])
@require_permission(PermissionTypes.ML_MODEL_CREATE)
def create_ml_model():
    """
    Create new ML model.
    """
    session_user = get_user()

    if not session_user:
        return redirect(url_for("bases.bases_blp.login"))

    if request.method == "POST":
        try:
            # Parse input_shape from JSON string
            input_shape_str = request.form.get('input_shape', '{}')
            input_shape = json.loads(input_shape_str) if input_shape_str else {}

            new_model = MLModel(
                name=request.form.get('name'),
                description=request.form.get('description'),
                model_path=request.form.get('model_path'),
                indexer_path=request.form.get('indexer_path'),
                num_classes=int(request.form.get('num_classes', 3)),
                input_shape=input_shape,
                version=request.form.get('version'),
                is_active=request.form.get('is_active') == 'True'
            )

            storage.insert_ml_model(new_model)
            logging.info(f'== Created ML model {new_model.name} by user {session_user["id"]}')
            flash('ML модель успішно створена', 'success')

            return redirect(url_for('bases.bases_blp.models'))
        except Exception as e:
            logging.error(f'Error creating ML model: {str(e)}')
            flash('Помилка при створенні ML моделі', 'error')
            return redirect(url_for('bases.bases_blp.create_ml_model'))

    model = MLModel()
    return render_template(
        'model.html',
        model=model,
        current_user=session_user
    )


@bases.route('/models/<int:model_id>', methods=['GET', 'POST'])
@require_permission(PermissionTypes.ML_MODEL_EDIT)
def edit_ml_model(model_id):
    """
    Edit existing ML model.
    """
    session_user = get_user()

    if not session_user:
        return redirect(url_for("bases.bases_blp.login"))

    model = storage.load_model_by_id(model_id)

    if not model:
        flash('ML модель не знайдено', 'error')
        return redirect(url_for('bases.bases_blp.models'))

    if request.method == "POST":
        try:
            # Parse input_shape from JSON string
            input_shape_str = request.form.get('input_shape', '{}')
            input_shape = json.loads(input_shape_str) if input_shape_str else {}

            model.name = request.form.get('name')
            model.description = request.form.get('description')
            model.model_path = request.form.get('model_path')
            model.indexer_path = request.form.get('indexer_path')
            model.num_classes = int(request.form.get('num_classes', 3))
            model.input_shape = input_shape
            model.version = request.form.get('version')
            model.is_active = request.form.get('is_active') == 'True'
            model.updated_date = datetime.utcnow()

            storage.update_ml_model(model)
            logging.info(f'== Updated ML model {model.name} by user {session_user["id"]}')
            flash('ML модель успішно оновлена', 'success')

            return redirect(url_for('bases.bases_blp.models'))
        except Exception as e:
            logging.error(f'Error updating ML model: {str(e)}')
            flash('Помилка при оновленні ML моделі', 'error')

    return render_template(
        'model.html',
        model=model,
        current_user=session_user
    )


@bases.route('/models/<int:model_id>/delete', methods=['POST'])
@require_permission(PermissionTypes.ML_MODEL_DELETE)
def delete_ml_model(model_id):
    """
    Delete ML model.
    """
    session_user = get_user()

    if not session_user:
        return redirect(url_for("bases.bases_blp.login"))

    try:
        model = storage.load_model_by_id(model_id)

        if not model:
            flash('ML модель не знайдено', 'error')
            return redirect(url_for('bases.bases_blp.models'))

        # Check if any users are using this model
        users_count = storage.count_users_by_model_id(model_id)
        if users_count > 0:
            flash(f'Не можна видалити модель, оскільки вона використовується {users_count} користувачами', 'error')
            return redirect(url_for('bases.bases_blp.models'))

        # 1. Спочатку видаляємо запис з БД
        storage.delete_ml_model(model)

        # 2. Видаляємо фізичні файли
        try:
            # Формуємо повні шляхи до файлів
            full_model_path = os.path.join(variables.ml_models_dir, model.model_path)
            # Якщо у вас indexer_path може бути None, додайте перевірку: if model.indexer_path: ...
            full_indexer_path = os.path.join(variables.ml_models_dir, model.indexer_path)

            # Видаляємо основний файл моделі (.pth)
            if os.path.exists(full_model_path):
                os.remove(full_model_path)
                logging.info(f"File deleted: {full_model_path}")
            else:
                logging.warning(f"File not found during deletion: {full_model_path}")

            # Видаляємо файл мапінгу (.json або .pkl)
            if os.path.exists(full_indexer_path):
                os.remove(full_indexer_path)
                logging.info(f"File deleted: {full_indexer_path}")

        except Exception as file_error:
            # Логуємо помилку файлової системи, але не перериваємо редірект користувача
            logging.error(f"Error deleting physical files for model {model.name}: {file_error}")

        logging.info(f'== Deleted ML model {model.name} by user {session_user["id"]}')
        flash('ML модель успішно видалена', 'success')

    except Exception as e:
        logging.error(f'Error deleting ML model: {str(e)}')
        flash('Помилка при видаленні ML моделі', 'error')

    return redirect(url_for('bases.bases_blp.models'))


@bases.route('/models/upload', methods=['POST'])
@require_permission(PermissionTypes.ML_MODEL_CREATE)
def upload_ml_file():
    """
    Upload model files (.pth / .json).
    """
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'Файл не надіслано'}), 400

    # Перевірка формату
    allowed = {'pth', 'json'}
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in allowed:
        return jsonify({'error': 'Дозволені лише .pth та .json'}), 400

    # UUID filename
    file_uuid = f"{uuid.uuid4()}.{ext}"

    # Куди зберігати
    folder = variables.ml_models_dir
    os.makedirs(folder, exist_ok=True)

    save_path = os.path.join(folder, file_uuid)
    file.save(save_path)

    return jsonify({
        'uuid': file_uuid,
        'path': save_path,
        'ext': ext
    })


@bases.route('/recognitions')
@require_permission(PermissionTypes.TAB_RECOGNITIONS)
def recognitions():
    """
    Handle the display of recognitions.

    - Retrieves and paginates recognitions based on user role and query parameters.
    - Renders the 'recognitions.html' template with the recognition data.

    Query Parameters:
        - page (int): The page number for pagination (default is 1).
        - limit (int): The number of recognitions per page (default is 10).
        - campaign_id (str): Filter by campaign ID.
        - request_uuid (str): Filter by request UUID.
        - extension (str): Filter by file extension.

    Returns:
        - A rendered template with the recognitions data.
        - A redirect to the 'login' page if the user is not authenticated.
    """
    session_user = get_user()

    if not session_user:
        return redirect(url_for("bases.bases_blp.login"))

    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    offset = (page - 1) * limit

    reset = bool(request.args.get('reset', 0, type=int))

    datetime = request.args.get('datetime', '', type=str).strip()
    campaign = request.args.get('campaign_id', '', type=str).strip()
    uuid = request.args.get('request_uuid', '', type=str).strip()
    request_extension = request.args.get('extension', '', type=str).strip()
    request_prediction = request.args.get('prediction', '', type=str).strip()

    recognition_filter = session.get("recognition_filter", {})
    if not isinstance(recognition_filter, dict):
        recognition_filter = {}

    if is_admin() or is_supervisor():
        user_id = request.args.get(
            'user_id',
            recognition_filter.get("user_id", session_user["id"]) if not reset else '',
            type=int
        )
    else:
        user_id = session_user["id"]

    campaign_id = campaign if campaign or reset else recognition_filter.get("campaign_id", '')
    date_time = datetime if datetime or reset else recognition_filter.get("datetime", '')
    request_uuid = uuid if uuid or reset else recognition_filter.get("request_uuid", '')
    extension = request_extension if request_extension or reset else recognition_filter.get("extension", '')
    prediction = request_prediction if request_prediction or reset else recognition_filter.get("prediction", '')

    session["recognition_filter"] = {
        "user_id": user_id,
        "campaign_id": campaign_id,
        "request_uuid": request_uuid,
        "extension": request_extension,
        "datetime": date_time,
        "prediction": prediction
    }

    searched_recognitions = storage.load_recognitions(user_id, date_time, campaign_id, request_uuid, extension, prediction, limit, offset)

    recognitions_count = storage.count_recognitions(user_id, date_time, campaign_id, request_uuid, extension, prediction)

    total_pages = 1 if recognitions_count <= limit else (recognitions_count + (limit - 1)) // limit

    return render_template(
        'recognitions.html',
        recognitions=searched_recognitions,
        total_pages=total_pages,
        page=page,
        start_page=max(1, page - 2),
        end_page=min(total_pages, page + 2),
        users=storage.load_simple_users() if is_admin() or is_supervisor() else [],
        filter=session.get("recognition_filter", {}),
        current_user=session_user
    )


@bases.route('/recognitions-export')
@require_permission(PermissionTypes.RECOGNITIONS_EXPORT)
def recognitions_export():
    """
    Handle the recognitions export.

    - Retrieves the recognition by ID.
    - For admins, retrieves related recognitions and calculates average confidence.
    - For regular users, retrieves only the recognitions related to the user.
    - Renders the 'recognition.html' template with the recognition and related data.

    Returns:
        - A rendered template with the recognition data.
        - A redirect to the 'login' page if the user is not authenticated.
    """
    session_user = get_user()

    if not session_user:
        return redirect(url_for("bases.bases_blp.login"))

    # Get query parameters
    datetime = request.args.get('datetime', '', type=str).strip()
    campaign_id = request.args.get('campaign_id', '', type=str).strip()
    request_uuid = request.args.get('request_uuid', '', type=str).strip()
    extension = request.args.get('extension', '', type=str).strip()
    prediction = request.args.get('prediction', '', type=str).strip()
    client_timezone = request.args.get('client_timezone', 'UTC', type=str).strip()

    if is_admin() or is_supervisor():
        user_id = request.args.get('user_id', '', type=str).strip()
        recognitions = storage.load_recognitions(
            user_id, datetime, campaign_id, request_uuid, extension, prediction, None, None
        )
    else:
        user_id = session_user["id"]
        recognitions = storage.load_recognitions_related_to_user(
            user_id, datetime, campaign_id, request_uuid, extension, prediction, None, None
        )

    if not recognitions:
        flash("Recognitions does not found")
        return redirect(url_for("bases.bases_blp.recognitions"))

    def convert_to_client_timezone(utc_dt, client_timezone):
        """Converts a UTC datetime object to a client's timezone."""
        timezone = pytz.timezone(client_timezone)  # Create a timezone object
        local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(timezone)
        return local_dt.strftime('%Y-%m-%d %H:%M:%S')

    data = [
        {
            "ID": rec.id,
            "Created Date": convert_to_client_timezone(rec.created_date, client_timezone) if rec.created_date else "",
            "Final": rec.final,
            "Request UUID": rec.request_uuid,
            "Audio UUID": rec.audio_uuid,
            "Confidence": rec.confidence,
            "Prediction": rec.prediction,
            "Extension": rec.extension,
            "Company ID": rec.company_id,
            "Campaign ID": rec.campaign_id,
            "Application ID": rec.application_id,
            "User ID": rec.user_id,
        }
        for rec in recognitions
    ]

    df = pd.DataFrame(data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Recognitions")

    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="recognitions.xlsx"
    )


@bases.route('/recognitions/<recognition_id>')
def recognition(recognition_id: int):
    """
    Handle the display of a single recognition and its related recognitions.

    - Retrieves the recognition by ID.
    - For admins, retrieves related recognitions and calculates average confidence.
    - For regular users, retrieves only the recognitions related to the user.
    - Renders the 'recognition.html' template with the recognition and related data.

    Args:
        recognition_id (int): The ID of the recognition to be retrieved.

    Returns:
        - A rendered template with the recognition data.
        - A redirect to the 'login' page if the user is not authenticated.
    """
    session_user = get_user()

    if not session_user:
        return redirect(url_for("bases.bases_blp.login"))

    related_recognitions = []

    if is_admin() or is_supervisor():
        searched_recognition = storage.load_recognition_by_id(recognition_id)
        if searched_recognition is not None:
            related_recognitions = storage.load_related_recognitions(searched_recognition.request_uuid)
            k = 0
            l = 0
            r = ''
            for r in related_recognitions:
                if r.prediction != "ring":
                    k += r.confidence
                    l += 1
                if r.final:
                    r = r.prediction
            if len(related_recognitions) > 0:
                if l != 0:
                    searched_recognition.confidence = k / l
                searched_recognition.prediction = r
    else:
        searched_recognition = storage.load_recognition_by_id_related_to_user(recognition_id, session_user["id"])
        if searched_recognition is not None:
            related_recognitions = storage.load_related_recognitions(searched_recognition.request_uuid)
            k = 0
            l = 0
            r = ''
            for r in related_recognitions:
                if r.prediction != "ring":
                    k += r.confidence
                    l += 1
                if r.final:
                    r = r.prediction
            if len(related_recognitions) > 0:
                if l != 0:
                    recognition.confidence = k / l
                recognition.prediction = r
    # Render the template with the data
    return render_template(
        'recognition.html',
        recognition=searched_recognition,
        related_recognitions=related_recognitions,
        current_user=session_user
    )


@bases.route('/audio/<path:created_date>/<path:filename>')
def serve_audio(created_date, filename):
    """
    Serve audio files to the user.

    - Checks if the user is authenticated.
    - Serves the audio file from the directory if the filename is valid.

    Args:
        filename (str): The name of the audio file to be served.

    Returns:
        - The audio file if the user is authenticated and the filename is valid.
        - An empty string if the filename is 'None'.
        - A redirect to the 'login' page if the user is not authenticated.
        :param filename:
        :param created_date:
    """
    current_user = session.get("user")
    if current_user:
        if filename != 'None':
            save_dir = None
            if not filename.endswith('.wav'):
                filename = filename + '.wav'
                year, month, day = created_date.split(' ')[0].split("-")
                save_dir = os.path.join(variables.audio_dir, year, month, day)
            else:
                year, month, day = created_date.split(' ')[0].split('-')
                save_dir = os.path.join(variables.audio_dir, year, month, day)
            return send_from_directory(save_dir, filename)
        return ''
    else:
        return redirect(url_for('bases.bases_blp.login'))


def update_user(r, u: User):
    history_change = {"before": object_to_dict(u)}
    u.first_name = r.form.get("first_name", u.first_name)
    u.last_name = r.form.get("last_name", u.last_name)
    u.email = r.form.get("email", u.email)
    u.phone = r.form.get("phone", u.phone)
    u.username = r.form.get("username", u.username)
    u.password = generate_password_hash(r.form.get("password")) if r.form.get("password") != "" else u.password
    u.api_key = r.form.get("api_key", u.api_key)
    u.audience = r.form.get("audience", u.audience)
    u.right_id = r.form.get("right_id", u.right_id)
    u.tariff.active = True if r.form.get("active", u.tariff.active) == "True" else False
    u.recognition.encoding = r.form.get("encoding", u.recognition.encoding)
    u.recognition.rate = r.form.get("rate", u.recognition.rate)
    u.recognition.interval_length = r.form.get("interval_length", u.recognition.interval_length)
    u.recognition.predictions = r.form.get("predictions", u.recognition.predictions)
    u.recognition.prediction_criteria = (json.dumps({key: r.form.get(key) for key in r.form.keys() if '_interval_' in key or 'result' in key}))
    history_change["after"] = object_to_dict(u)
    logging.info(f'== Request update client by user {get_user()["id"]} history: {history_change}')


def update_right(r, permission: Rights):
    history_change = {"before": object_to_dict(permission)}
    permission.name = r.form.get("name", permission.name)
    if(r.form.getlist("permissions")):
        permission.permissions = [int(pid) for pid in r.form.getlist("permissions")]
    history_change["after"] = object_to_dict(permission)
    logging.info(f'== Request update rights by user {get_user()["id"]} history: {history_change}')

def object_to_dict(obj, found=None):
    if found is None:
        found = set()
    mapper = class_mapper(obj.__class__)
    columns = [column.key for column in mapper.columns]
    get_key_value = lambda c: (c, getattr(obj, c).isoformat()) if isinstance(getattr(obj, c), datetime) else (
    c, getattr(obj, c))
    out = dict(map(get_key_value, columns))
    for name, relation in mapper.relationships.items():
        if relation not in found:
            found.add(relation)
            related_obj = getattr(obj, name)
            if related_obj is not None:
                if relation.uselist:
                    out[name] = [object_to_dict(child, found) for child in related_obj]
                else:
                    out[name] = object_to_dict(related_obj, found)
    return out


def get_user() -> dict:
    """Returns the current session user or None if not logged in."""
    return session.get("user")


def is_admin():
    """Returns True if the current session user is an admin."""
    user_data = get_user()
    return user_data["role"]["name"] == 'admin'

def is_supervisor():
    """Returns True if the current session user is an supervisor."""
    user_data = get_user()
    return user_data["role"]["name"] == 'supervisor'
