FROM mysql:5.5 as mysql

FROM php:5-apache

ENV DEBIAN_FRONTEND=noninteractive

# install packages
RUN apt-get update && apt-get -qqy install \
    git libmcrypt-dev libxslt-dev libpng-dev libjpeg-dev libaio1


# install extensions
RUN docker-php-ext-install mbstring mcrypt mysqli xsl gd

# Apache; enables mod_rewrite
RUN a2enmod rewrite

# set root
ENV SCALAR_ROOT=/var/www/html

RUN git clone https://github.com/anvc/scalar.git /app

RUN git clone https://github.com/Michael628/scalar-book-transfer-tool.git /app/system/application/plugins/transfer

COPY php.ini /usr/local/etc/php/

COPY codeigniter.php /app

RUN chown www-data /app

RUN rm -rf $SCALAR_ROOT && ln -s /app $SCALAR_ROOT

# mysql install
RUN groupadd -r mysql && useradd -r -g mysql mysql

COPY --from=mysql /usr/local/bin/docker-entrypoint.sh /usr/local/bin/
COPY --from=mysql /usr/local/bin/gosu /usr/local/bin/
COPY --from=mysql /usr/local/mysql /usr/local/mysql
COPY --from=mysql /etc/mysql/ /etc/mysql/

# copy scalar_store.sql to initdb.d
RUN mkdir -p /docker-entrypoint-initdb.d/ && cp /app/system/application/config/scalar_store.sql /docker-entrypoint-initdb.d/

RUN mkdir -p /var/lib/mysql /var/run/mysqld \
    && chown -R mysql:mysql /var/lib/mysql /var/run/mysqld \
    && chmod 777 /var/run/mysqld

ENV PATH $PATH:/usr/local/mysql/bin:/usr/local/mysql/scripts

ENV SCALAR_DB_USERNAME=user
ENV SCALAR_DB_PASSWORD=password
ENV SCALAR_DB_DATABASE=scalar
ENV SCALAR_ENCRYPTION_KEY=eiy1ShahSiL4ohce2gei5Eiyiechae5j

ENV MYSQL_USER=user
ENV MYSQL_PASSWORD=password
ENV MYSQL_ROOT_PASSWORD=password
ENV MYSQL_DATABASE=scalar
ENV MYSQL_INITDB_SKIP_TZINFO=1

# run script
COPY run.sh /tmp/
COPY import.sh /tmp/
CMD /tmp/run.sh




