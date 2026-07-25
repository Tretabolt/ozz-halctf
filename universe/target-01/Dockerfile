FROM php:7.4-apache

RUN apt-get update && apt-get install -y sqlite3 libsqlite3-dev \
    && docker-php-ext-install sqlite3 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /var/secret /var/www/html

COPY app/ /var/www/html/

RUN chown -R www-data:www-data /var/www/html /var/secret
RUN chmod 755 /var/secret
RUN echo '<?php phpinfo(); ?>' > /var/www/html/info.php

EXPOSE 80
CMD ["apache2-foreground"]
