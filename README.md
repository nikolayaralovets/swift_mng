Web UI для администрирования Openstack Swift.

Установка.
1. Установить python 3.9, pip, git и др.:\
   dnf install python39\
   dnf module disable python36\
   dnf module disable python38\
   dnf install python39-pip git gcc python39-devel nginx openldap-devel
2. Установить PostgreSQL:\
   dnf install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm \
   dnf install postgresql14-devel postgresql14-server postgresql14-contrib\
   /usr/pgsql-14/bin/postgresql-14-setup initdb\
   systemctl start postgresql-14\
   systemctl enable postgresql-14
3. Создать пользователя и БД:\
   sudo -u postgres /usr/pgsql-14/bin/createuser -P swiftbilling\
   sudo -u postgres /usr/pgsql-14/bin/createdb -O swiftbilling swiftbilling
4. Установить django, uwsgi и др.:\
   pip3 install django  uritemplate uwsgi psycopg2 requests django-auth-ldap
5. Клонировать репозиторий в /opt:\
   cd /opt\
   git clone https://github.com/kozlovd/swiftbilling.git
6. В файле /opt/swiftbilling/swiftbilling/settings.py указать параметры подключения к БД
7. В файле /opt/swiftbilling/billing/settings.py задать параметры кластера swift
8. Скопировать конфигурационные файлы из misc:
   cp /opt/swiftbilling/misc/nginx_vserver.conf /etc/nginx/conf.d/swiftbilling.conf\
   cp -rf /opt/swiftbilling/misc/uwsgi /etc/\
   cp /opt/swiftbilling/misc/uwsgi.service /usr/lib/systemd/system/
9. Настройка пользователей:
   useradd -M -d /opt/swiftbilling -s /sbin/nologin uwsgi\
   groupadd django\
   usermod -aG django uwsgi\
   usermod -aG django nginx
10. Запуск:
   systemctl enable uwsgi nginx\
   systemctl start uwsgi nginx\
   cd /opt/swiftbilling\
   python3 manage.py createsuperuser\
   python3 manage.py migrate\
   chown -R uwsgi:django /opt/swiftbilling/
