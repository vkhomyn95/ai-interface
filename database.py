import datetime
import logging
import re
import sys

import mariadb
from mariadb import OperationalError, ProgrammingError


class Database:
    """
        Singleton class of the logger system that will handle the logging system.
    ...

    Attributes
    ----------
    _database_instance: VoicemailRecognitionDatabase
        Represents the current running instance of VoicemailRecognitionDatabase,
        this will only be created once (by default set to None).

    """

    _database_instance = None

    @staticmethod
    def instance():
        """
            Obtains instance of VoicemailRecognitionDatabase.
        """

        return Database._database_instance

    def __init__(self, _user: str, _password: str, _host: str, _port: int, _database: str) -> None:
        """
            Default constructor.
        """

        if Database._database_instance is None:
            try:
                conn = mariadb.connect(
                    user=_user,
                    password=_password,
                    host=_host,
                    port=_port,
                    database=_database,
                    autocommit=True,
                    reconnect=True
                )
                Database._database_instance = self
            except mariadb.Error as e:
                logging.error(f'  >> Error connecting to MariaDB Platform: {e}')
                sys.exit(1)
            conn.auto_reconnect = True
            self.conn = conn
            self.cur = conn.cursor(dictionary=True)

            # Run migrations
            self.exec_migrations("db.sql")

        else:
            raise Exception("{}: Cannot construct, an instance is already running.".format(__file__))

    def exec_migrations(self, sql_file):
        logging.info(f'  >> Executing SQL script file: {sql_file}')
        statement = ""

        for line in open(sql_file):
            if re.match(r'--', line):  # ignore sql comment lines
                continue
            if not re.search(r';$', line):  # keep appending lines that don't end in ';'
                statement = statement + line
            else:  # when you get a line ending in ';' then exec statement and reset for next statement
                statement = statement + line
                logging.debug(f'  >> Executing SQL statement:\n {statement}')
                try:
                    self.cur.execute(statement)
                except (OperationalError, ProgrammingError) as e:
                    logging.warning(f'  >> MySQLError during execute statement: {e.args}')
                statement = ""

    def insert_user(
            self,
            tariff: object,
            recognition: object,
            user: object
    ):
        if not 'total' in tariff:
            tariff['total'] = 0

        current_date = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')

        self.cur.execute(
            f'INSERT into tariff (created_date, updated_date, active, total, used) '
            f'VALUES (?, ?, ?, ?, ?)',
            (current_date, current_date, tariff["active"], tariff["total"], tariff["used"])
        )

        tariff_id = self.cur.lastrowid

        self.cur.execute(
            f'INSERT into recognition_configuration (encoding, rate, interim, interval_length, predictions, prediction_criteria) '
            f'VALUES (?, ?, ?, ?, ?, ?)',
            (
                recognition["encoding"],
                recognition["rate"],
                recognition["interim"],
                recognition["interval_length"],
                recognition["predictions"],
                recognition["prediction_criteria"]
            )
        )

        recognition_id = self.cur.lastrowid

        self.cur.execute(
            f'INSERT into user (created_date, updated_date, username, password, first_name, last_name, email, phone, api_key, audience, tariff_id, recognition_id, role_id) '
            f'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                current_date,
                current_date,
                user["username"],
                user["password"],
                user["first_name"],
                user["last_name"],
                user["email"],
                user["phone"],
                user["api_key"],
                user["audience"],
                tariff_id,
                recognition_id,
                user["role_id"]
            )
        )
        return self.cur.lastrowid

    def update_user(
            self,
            tariff: object,
            recognition: object,
            user: object
    ):
        current_date = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')

        sql_query = """
            UPDATE user
            SET
                first_name = ?,
                last_name = ?,
                username = ?,
                password = ?,
                api_key = ?,
                email = ?,
                phone = ?,
                audience = ?,
                updated_date = ?
            WHERE
                id = ?
        """

        tariff_query = """
            UPDATE tariff
            SET
                active = ?,
                total = ?,
                used = ?
            WHERE
                id = ?
        """

        recognition_query = """
            UPDATE recognition_configuration
            SET
                encoding = ?,
                rate = ?,
                interim = ?,
                interval_length = ?,
                predictions = ?,
                prediction_criteria = ?
            WHERE
                id = ?
        """

        # Execute user update
        self.cur.execute(sql_query, (
            user["first_name"],
            user["last_name"],
            user["username"],
            user["password"],
            user["api_key"],
            user["email"],
            user["phone"],
            user["audience"],
            current_date,
            user["id"]
        ))

        # Execute tariff update
        self.cur.execute(tariff_query, (
            tariff["active"],
            tariff["total"] if tariff["total"] else 0,
            tariff["used"] if tariff["used"] else 0,
            user["tariff_id"]
        ))

        # Execute recognition configuration update
        self.cur.execute(recognition_query, (
            recognition["encoding"],
            recognition["rate"],
            recognition["interim"],
            recognition["interval_length"],
            recognition["predictions"],
            recognition["prediction_criteria"],
            user["recognition_id"]
        ))

        return self.cur.lastrowid

    def load_user_by_username(self, username: str):
        try:
            self.cur.execute(
                f'SELECT u.id as id, '
                f'u.first_name as first_name,'
                f' u.last_name as last_name,'
                f' u.username as username,'
                f' u.password as password,'
                f' u.role_id as role_id,'
                f' r.name as role_name from user u left join user_role r on r.id=u.role_id where u.username=?',
                (username,)
            )
            return self.cur.fetchone()
        except mariadb.InterfaceError as e:
            logging.error(f'  >> Error connecting to MariaDB Platform: {e}')
            self.conn.reconnect()
            return self.load_user_by_username(username)

    def load_users(self, limit: int, offset: int):
        try:
            self.cur.execute(
                f'SELECT u.id as id, '
                f'u.created_date as created_date,'
                f' u.first_name as first_name,'
                f' u.last_name as last_name,'
                f' u.username as username,'
                f' u.password as password,'
                f' u.api_key as api_key,'
                f' u.email as email,'
                f' u.phone as phone,'
                f' u.audience as audience,'
                f' u.role_id as role_id,'
                f' u.recognition_id as recognition_id,'
                f' t.id as tariff_id,'
                f' t.active as active,'
                f' t.total as total,'
                f' t.used as used'
                f' from user u left join tariff t on t.id=u.tariff_id limit {limit} offset {offset}',
                (limit, offset, )
            )
            return self.cur.fetchall()
        except mariadb.InterfaceError as e:
            logging.error(f'  >> Error connecting to MariaDB Platform: {e}')
            self.conn.reconnect()
            return self.load_users(limit, offset)

    def load_simple_users(self):
        try:
            self.cur.execute(
                f'SELECT * from user',
                ()
            )
            return self.cur.fetchall()
        except mariadb.InterfaceError as e:
            logging.error(f'  >> Error connecting to MariaDB Platform: {e}')
            self.conn.reconnect()
            return self.load_simple_users()

    def load_user_by_id(self, user_id: int):
        try:
            self.cur.execute(
                f'SELECT u.id as id, '
                f'u.first_name as first_name,'
                f' u.last_name as last_name,'
                f' u.username as username,'
                f' u.password as password,'
                f' u.api_key as api_key,'
                f' u.email as email,'
                f' u.phone as phone,'
                f' u.audience as audience,'
                f' u.role_id as role_id,'
                f' u.recognition_id as recognition_id,'
                f' r.name as role_name,'
                f' t.id as tariff_id,'
                f' t.active as active,'
                f' t.total as total,'
                f' t.used as used,'
                f' rc.encoding as encoding,'
                f' rc.rate as rate,'
                f' rc.interim as interim,'
                f' rc.interval_length as interval_length,'
                f' rc.predictions as predictions,'
                f' rc.prediction_criteria as prediction_criteria'
                f' from user u left join user_role r on r.id=u.role_id left join tariff t on t.id=u.tariff_id '
                f' left join recognition_configuration rc on rc.id=u.recognition_id '
                f'where u.id=?',
                (user_id,)
            )
            return self.cur.fetchone()
        except mariadb.InterfaceError as e:
            logging.error(f'  >> Error connecting to MariaDB Platform: {e}')
            self.conn.reconnect()
            return self.load_user_by_id(user_id)

    def load_user_dashboard(self, user_id: int):
        try:
            self.cur.execute(
                f'SELECT '
                f'SUM(CASE WHEN DATE(created_date) = CURDATE() THEN 1 ELSE 0 END) AS today_total, '
                f'SUM(CASE WHEN DATE(created_date) = CURDATE() AND prediction = \'voicemail\' THEN 1 ELSE 0 END) AS today_voicemail, '
                f'SUM(CASE WHEN DATE(created_date) = CURDATE() AND prediction <> \'voicemail\' THEN 1 ELSE 0 END) AS today_human, '
                f'SUM(CASE WHEN created_date >= CURDATE() - INTERVAL 6 DAY THEN 1 ELSE 0 END) AS week_total, '
                f'SUM(CASE WHEN created_date >= CURDATE() - INTERVAL 6 DAY AND prediction = \'voicemail\' THEN 1 ELSE 0 END) AS week_voicemail, '
                f'SUM(CASE WHEN created_date >= CURDATE() - INTERVAL 6 DAY AND prediction <> \'voicemail\' THEN 1 ELSE 0 END) AS week_human, '
                f'SUM(CASE WHEN created_date >= LAST_DAY(CURDATE()) + INTERVAL 1 DAY - INTERVAL 1 MONTH THEN 1 ELSE 0 END) AS month_total, '
                f'SUM(CASE WHEN created_date >= LAST_DAY(CURDATE()) + INTERVAL 1 DAY - INTERVAL 1 MONTH AND prediction = \'voicemail\' THEN 1 ELSE 0 END) AS month_voicemail, '
                f'SUM(CASE WHEN created_date >= LAST_DAY(CURDATE()) + INTERVAL 1 DAY - INTERVAL 1 MONTH AND prediction <> \'voicemail\' THEN 1 ELSE 0 END) AS month_human '
                f'FROM recognition WHERE created_date >= LAST_DAY(CURDATE()) + INTERVAL 1 DAY - INTERVAL 1 MONTH and final=true AND user_id=?',
                (user_id,)
            )
            return self.cur.fetchone()
        except mariadb.InterfaceError as e:
            logging.error(f'  >> Error connecting to MariaDB Platform: {e}')
            self.conn.reconnect()
            return self.load_user_dashboard(user_id)

    def count_users(self):
        try:
            self.cur.execute(f'SELECT count(*) as count from user', ())
            return self.cur.fetchone()
        except mariadb.InterfaceError as e:
            logging.error(f'  >> Error connecting to MariaDB Platform: {e}')
            self.conn.reconnect()
            return self.count_users()

    def load_user_by_api_key(self, api_key: str):
        try:
            self.cur.execute(
                f'SELECT * from user u left join tariff t on t.id=u.tariff_id where u.api_key=?',
                (api_key,)
            )
            return self.cur.fetchone()
        except mariadb.InterfaceError as e:
            logging.error(f'  >> Error connecting to MariaDB Platform: {e}')
            self.conn.reconnect()
            return self.load_user_by_id(api_key)

    def load_recognitions(self, user_id: int, request_uuid: str, extension: str, limit: int, offset: int):
        try:
            query = f'SELECT * from recognition'
            if user_id:
                query += f' where user_id={user_id}'
            if request_uuid:
                if not user_id:
                    query += f' where request_uuid={request_uuid}'
                else:
                    query += f' and request_uuid={request_uuid}'
            if extension:
                if not user_id and not request_uuid:
                    query += f' where extension="{extension}"'
                else:
                    query += f' and extension="{extension}"'
            query += f' order by id desc limit {limit} offset {offset}'
            self.cur.execute(
                query,
                (limit, offset, )
            )
            return self.cur.fetchall()
        except mariadb.InterfaceError as e:
            logging.error(f'  >> Error connecting to MariaDB Platform: {e}')
            self.conn.reconnect()
            return self.load_recognitions(user_id, request_uuid, extension, limit, offset)

    def load_recognitions_related_to_user(self, user_id: int, request_uuid: str, extension: str, limit: int, offset: int):
        try:
            query = f'SELECT * from recognition where user_id={user_id}'
            if request_uuid:
                query += f' and request_uuid="{request_uuid}"'
            if extension:
                query += f' and extension={extension}'
            query += f' order by id desc limit {limit} offset {offset}'
            print(query)
            self.cur.execute(
                query,
                (user_id, limit, offset, )
            )
            return self.cur.fetchall()
        except mariadb.InterfaceError as e:
            logging.error(f'  >> Error connecting to MariaDB Platform: {e}')
            self.conn.reconnect()
            return self.load_recognitions_related_to_user(limit, request_uuid, extension, offset)

    def load_related_recognitions(self, request_uuid):
        try:
            self.cur.execute(f'SELECT * from recognition where request_uuid=?', (request_uuid,))
            return self.cur.fetchall()
        except mariadb.InterfaceError as e:
            logging.error(f'  >> Error connecting to MariaDB Platform: {e}')
            self.conn.reconnect()
            return self.load_related_recognitions(request_uuid)

    def load_recognition_by_id(self, recognition_id: int):
        try:
            self.cur.execute(
                f'SELECT * from recognition r left join user u on r.user_id=u.id where r.id=? ',
                (recognition_id,)
            )
            return self.cur.fetchone()
        except mariadb.InterfaceError as e:
            logging.error(f'  >> Error connecting to MariaDB Platform: {e}')
            self.conn.reconnect()
            return self.load_recognition_by_id(recognition_id)

    def load_recognition_by_id_related_to_user(self, recognition_id: int, user_id: int):
        try:
            self.cur.execute(
                f'SELECT * from recognition r left join user u on r.user_id=u.id where r.id=? and r.user_id=? ',
                (recognition_id, user_id, )
            )
            return self.cur.fetchone()
        except mariadb.InterfaceError as e:
            logging.error(f'  >> Error connecting to MariaDB Platform: {e}')
            self.conn.reconnect()
            return self.load_recognition_by_id_related_to_user(recognition_id, user_id)

    def count_recognitions(self, user_id: int, request_uuid: str, extension: str,):
        try:
            query = f'SELECT count(*) as count from recognition'
            if user_id:
                query += f' where user_id={user_id}'
            if request_uuid:
                if not user_id:
                    query += f' where request_uuid="{request_uuid}"'
                else:
                    query += f' and request_uuid="{request_uuid}"'
            if extension:
                if not user_id and not request_uuid:
                    query += f' where extension="{extension}"'
                else:
                    query += f' and extension="{extension}"'
            self.cur.execute(query, ())
            return self.cur.fetchone()
        except mariadb.InterfaceError as e:
            logging.error(f'  >> Error connecting to MariaDB Platform: {e}')
            self.conn.reconnect()
            return self.count_recognitions(user_id, request_uuid, extension)

    def increment_tariff(self, tariff_id, audio_size):
        try:
            self.cur.execute(
                f'UPDATE tariff SET request_size = request_size + 1, audio_size = audio_size + ?  where id = ?',
                (audio_size,  tariff_id,)
            )
        except mariadb.InterfaceError as e:
            logging.error(f'  >> Error connecting to MariaDB Platform: {e}')
            self.conn.reconnect()
            return self.increment_tariff(tariff_id, audio_size)