import json

from flask import Blueprint, request, flash, redirect, url_for, session, render_template, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash

from app.config import variables
from app.extensions import storage, db
from app.models import User, Tariff, RecognitionConfiguration, UserRole
from app.schemas import UserSchema

bases = Blueprint("bases_blp", __name__, url_prefix="/")


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

    if is_admin():
        if "dashboard_filter" not in session:
            user_id = request.args.get('user_id', session_user["id"], type=int)
        else:
            user_id = request.args.get('user_id', session["dashboard_filter"], type=int)
    else:
        user_id = session_user["id"]

    session["dashboard_filter"] = user_id

    board = storage.load_user_dashboard(user_id if is_admin() else session_user["id"])

    return render_template(
        'dashboard.html',
        users=storage.load_simple_users() if is_admin() else [],
        dashboard={key: int(value) if value is not None else 0 for key, value in board.items()},
        filter=session["dashboard_filter"],
        current_user=session_user
    )


@bases.route('/profile', methods=['GET'])
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
        current_user=session_user,
        is_profile=True
    )


@bases.route('/users', methods=["GET"])
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

    if is_admin():
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
    else:
        return redirect(url_for("bases.bases_blp.user", user_id=session_user["id"]))


@bases.route('/users/<user_id>', methods=['POST', 'GET'])
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
        if not is_admin():
            return redirect(url_for("bases.bases_blp.profile"))

        searched_user.password = ""
        return render_template(
            'user.html',
            user=searched_user,
            current_user=session_user
        )
    else:
        if is_admin() or searched_user.id == session_user["id"]:
            update_user(request, searched_user)
            storage.update_user(searched_user)
            if is_admin():
                return redirect(url_for('bases.bases_blp.users'))
            else:
                return redirect(url_for("bases.bases_blp.dashboard"))
        else:
            return redirect(url_for("bases.bases_blp.profile"))


@bases.route('/create-user', methods=['POST', 'GET'])
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

    if request.method == "GET" and is_admin():
        return render_template(
            'user.html',
            user=UserSchema().dump(
                User(
                    role_id=2,
                    tariff=Tariff(),
                    recognition=RecognitionConfiguration()
                )
            ),
            current_user=session_user
        )
    else:
        redirect(url_for('bases.bases_blp.user', user_id=session_user["id"]))

    if request.method == "POST" and is_admin():
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
                current_user=session_user
            )
        else:
            new_user = User(
                role_id=2,
                tariff=Tariff(),
                recognition=RecognitionConfiguration()
            )
            update_user(request, new_user)
            storage.insert_user(new_user)
            return redirect(url_for('bases.bases_blp.users'))
    else:
        redirect(url_for('bases.bases_blp.user', user_id=session_user["id"]))


@bases.route('/recognitions')
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

    campaign_id = request.args.get('campaign_id', '', type=str).strip()
    request_uuid = request.args.get('request_uuid', '', type=str).strip()
    extension = request.args.get('extension', '', type=str).strip()

    if is_admin():
        user_id = request.args.get('user_id', '', type=str).strip()
        searched_recognitions = storage.load_recognitions(
            user_id, campaign_id, request_uuid, extension, limit, offset)
    else:
        user_id = session_user["id"]
        searched_recognitions = storage.load_recognitions_related_to_user(
            user_id, campaign_id, request_uuid, extension, limit, offset)
    recognitions_count = storage.count_recognitions(user_id, campaign_id, request_uuid, extension)

    total_pages = 1 if recognitions_count <= limit else (recognitions_count + (limit - 1)) // limit

    return render_template(
        'recognitions.html',
        recognitions=searched_recognitions,
        total_pages=total_pages,
        page=page,
        start_page=max(1, page - 2),
        end_page=min(total_pages, page + 2),
        users=storage.load_simple_users() if is_admin() else [],
        filter={
            "user_id": user_id,
            "campaign_id": campaign_id,
            "request_uuid": request_uuid,
            "extension": extension,
        },
        current_user=session_user
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

    if is_admin():
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


@bases.route('/audio/<path:filename>')
def serve_audio(filename):
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
    """
    current_user = session.get("user")

    if current_user:
        if filename != 'None':
            if not filename.endswith('.wav'):
                filename = filename + '.wav'
            return send_from_directory(variables.audio_dir, filename)
        return ''
    else:
        return redirect(url_for('bases.bases_blp.login'))


def update_user(r, u: User):
    u.first_name = r.form.get("first_name", u.first_name)
    u.last_name = r.form.get("last_name", u.last_name)
    u.email = r.form.get("email", u.email)
    u.phone = r.form.get("phone", u.phone)
    u.username = r.form.get("username", u.username)
    if r.form.get("password") != "":
        u.password = generate_password_hash(r.form.get("password"))
    u.api_key = r.form.get("api_key", u.api_key)
    u.audience = r.form.get("audience", u.audience)
    u.tariff.active = True if r.form.get("active", u.tariff.active) == "True" else False
    u.recognition.encoding = r.form.get("encoding", u.recognition.encoding)
    u.recognition.rate = r.form.get("rate", u.recognition.rate)
    u.recognition.interval_length = r.form.get("interval_length", u.recognition.interval_length)
    u.recognition.predictions = r.form.get("predictions", u.recognition.predictions)
    u.recognition.prediction_criteria = (
        json.dumps({key: r.form.get(key) for key in r.form.keys() if '_interval_' in key or 'result' in key}))


def get_user() -> dict:
    """Returns the current session user or None if not logged in."""
    return session.get("user")


def is_admin():
    """Returns True if the current session user is an admin."""
    user_data = get_user()
    return user_data["role"]["name"] == 'admin'
