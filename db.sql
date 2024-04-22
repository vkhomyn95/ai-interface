-- Create table tariff if does not exists
    CREATE TABLE IF NOT EXISTS `tariff` (
        `id` int(11) NOT NULL AUTO_INCREMENT,
        `created_date` datetime DEFAULT NULL,
        `updated_date` datetime DEFAULT NULL,
        `active` bit(1) DEFAULT 0,
        `total` int(11) DEFAULT 0,
        `used` int(11) DEFAULT 0,
        PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Create table user role if does not exists
    CREATE TABLE IF NOT EXISTS `user_role` (
        `id` int(11) NOT NULL AUTO_INCREMENT,
        `name` varchar(128) DEFAULT NULL,
        PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Insert user role if not exists
    INSERT INTO user_role (name) SELECT * FROM (SELECT 'admin') as admin WHERE NOT EXISTS(
        SELECT name FROM user_role WHERE name = 'admin'
    ) limit 1;
    INSERT INTO user_role (name) SELECT * FROM (SELECT 'guest') as admin WHERE NOT EXISTS(
        SELECT name FROM user_role WHERE name = 'guest'
    ) limit 1;

-- Create table recognition config if does not exists
    CREATE TABLE IF NOT EXISTS `recognition_configuration` (
        `id` int(11) NOT NULL AUTO_INCREMENT,
        `encoding` varchar(128) DEFAULT 'slin',
        `rate` int(11) NOT NULL,
        `interval_length` int(11) NOT NULL,
        `predictions` int(11) NOT NULL,
        `prediction_criteria` text DEFAULT NULL,
        PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Create table user if does not exists
    CREATE TABLE IF NOT EXISTS `user` (
        `id` int(11) NOT NULL AUTO_INCREMENT,
        `created_date` datetime DEFAULT NULL,
        `updated_date` datetime DEFAULT NULL,
        `first_name` varchar(128) DEFAULT NULL,
        `last_name` varchar(128) DEFAULT NULL,
        `email` varchar(255) DEFAULT NULL,
        `phone` varchar(128) DEFAULT NULL,
        `username` varchar(128) DEFAULT NULL,
        `api_key` varchar(255) DEFAULT NULL,
        `voiptime_api_key` varchar(255) DEFAULT NULL,
        `password` varchar(255) DEFAULT NULL,
        `audience` varchar(255) DEFAULT NULL,
        `tariff_id` int(11) DEFAULT NULL,
        `role_id` int(11) DEFAULT 2,
        `recognition_id` int(11) DEFAULT 0,
        PRIMARY KEY (`id`),
        KEY `fk_user_tariff` (`tariff_id`),
        KEY `fk_user_role` (`role_id`),
        KEY `fk_recognition_configuration` (`recognition_id`),
        CONSTRAINT `fk_user_tariff` FOREIGN KEY (`tariff_id`) REFERENCES `tariff` (`id`),
        CONSTRAINT `fk_user_role` FOREIGN KEY (`role_id`) REFERENCES `user_role` (`id`),
        CONSTRAINT `fk_recognition_configuration` FOREIGN KEY (`recognition_id`) REFERENCES `recognition_configuration` (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Create table recognition if does not exists
    CREATE TABLE IF NOT EXISTS `recognition` (
        `id` int(11) NOT NULL AUTO_INCREMENT,
        `created_date` datetime(3) DEFAULT NULL,
        `final` bit(1) NOT NULL,
        `request_uuid` varchar(128) DEFAULT NULL,
        `audio_uuid` varchar(128) DEFAULT NULL,
        `confidence` int(11) NOT NULL,
        `prediction` varchar(64) DEFAULT NULL,
        `extension` varchar(64) DEFAULT NULL,
        `company_id` int(11) DEFAULT NULL,
        `campaign_id` int(11) DEFAULT NULL,
        `application_id` int(11) DEFAULT NULL,
        `user_id` int(11) DEFAULT NULL,
        PRIMARY KEY (`id`),
        KEY `fk_recognition_user` (`user_id`),
        CONSTRAINT `fk_recognition_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Create table tariff trigger to reset value every month of 1th
CREATE EVENT IF NOT EXISTS reset_column_monthly
ON SCHEDULE EVERY 1 MONTH
STARTS CONCAT(DATE_FORMAT(CURRENT_TIMESTAMP, '%Y-%m-01'), ' 00:00:00')
DO
    UPDATE tariff SET used = 0;