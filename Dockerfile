FROM framenetbrasil/php-fpm:8.5

ARG WWWGROUP=1000
ARG WWWUSER=1000
ARG PROD=

RUN addgroup -g $WWWGROUP www \
    && adduser -s /bin/sh -D -G www -u $WWWUSER sail \
    && mkdir /var/log/laravel \
    && touch /var/log/laravel/laravel.log \
    && chown -R sail:www /var/log/laravel

USER sail
WORKDIR /www

COPY --from=composer:latest /usr/bin/composer /usr/local/bin/composer

RUN if [ -n "$PROD" ]; then composer install --no-dev --optimize-autoloader; fi
