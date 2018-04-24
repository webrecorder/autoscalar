#!/bin/bash
mysql="mysql --user=user --password=password scalar"

while ! mysql --user=user --password=password -e"quit"; do
    echo "Waiting for mysql"
    sleep 1
done

email="scalar@example.com"
name="$1"

path="$2"

slug="$3"
title="$4"
subtitle="$5"
description="$6"

echo "insert into scalar_db_users(user_id, email, fullname, password) values(10, '$email', '$name', '')" | eval $mysql
echo "insert into scalar_db_books(book_id, title, subtitle, description, slug, url_is_public, display_in_index, is_featured) values(1, '$title', '$subtitle', '$description', '$slug', 1, 1, 1)"  | eval $mysql

echo "insert into scalar_db_user_books(user_id, book_id, relationship, list_in_index, whitelist) values(10, 1, 'author', 1, 1)" | $mysql

if [ "$path" != "/" ]; then
    rm /var/www/html
    mkdir -p /var/www/html/$(dirname $path)
    ln -s /app /var/www/html/$(dirname $path)/$(basename $path)
fi

