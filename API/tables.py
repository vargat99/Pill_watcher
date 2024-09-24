DB_NAME = 'Spencer2'

TABLES = {}
# Create the users table
TABLES['users'] = (
    "CREATE TABLE `users` ("
    "  `id` INT NOT NULL AUTO_INCREMENT,"
    "  `username` VARCHAR(255) NOT NULL,"
    "  `email` VARCHAR(255) NOT NULL,"
    "  `password` VARCHAR(255) NOT NULL,"
    "  `created_at` DATETIME NOT NULL,"
    "  PRIMARY KEY (`id`)"
    ") ENGINE=InnoDB")

# Create the pictures table
TABLES['pictures'] = (
    "CREATE TABLE `pictures` ("
    "  `id` INT NOT NULL AUTO_INCREMENT,"
    "  `picture_name` VARCHAR(255) NOT NULL,"
    "  `device_id` INT NOT NULL,"
    "  `encoder_position` INT NOT NULL,"
    "  `timestamp` DATETIME NOT NULL,"
    "  PRIMARY KEY (`id`)"
    ") ENGINE=InnoDB")

# Create the device table
TABLES['devices'] = (
    "CREATE TABLE `devices` ("
    "  `id` INT NOT NULL AUTO_INCREMENT,"
    "  `hostname` VARCHAR(50),"
    "  `shown_name` VARCHAR(50),"
    "  `sw_version` VARCHAR(50),"
    "  PRIMARY KEY (`id`),"
    "  FOREIGN KEY (`id`) REFERENCES pictures(`device_id`)"
    ") ENGINE=InnoDB")

# Create the connection table
TABLES['connections'] = (
    "CREATE TABLE `connection` ("
    "  `id` INT NOT NULL AUTO_INCREMENT,"
    "  `user_id` INT,"
    "  `device_id` INT,"
    "  PRIMARY KEY (`id`),"
    "  FOREIGN KEY (`user_id`) REFERENCES users(`id`),"
    "  FOREIGN KEY (`device_id`) REFERENCES devices(`id`)"
    ") ENGINE=InnoDB")

