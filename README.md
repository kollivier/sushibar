Sushi bar
=========
The place where all the sushi chefs hang out.


TODO:

  - Look into celery beat for long term replacement to crontab setup
    http://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html

  - Add reasonable timeouts to all Studio-backend related requests (to avoid waiting
    on non-existent studio servers.)



Features
--------
  - Dashboard to monitor chefs' progress, logs, and run history
  - Remote control of a chefs started with the `--daemon` flag



Deploy to prod
--------------
Assuming your local repository has latest code + credentials + docker installed:

    # setup access to remote docker daemon
    eval $(docker-machine env gcpsushibarhost)    # this will set 4 env vars in current shell

    docker-compose -f production.yml  build
    docker-compose -f production.yml  up -d
    docker ps




Settings
--------
  - Use `config/settings/base.py` for common settings
  - Use `config/settings/local.py` for local development settings (default option when running `./manage.py`).
  - Use `config/settings/production.py` for added prod security restrictions.
    Credentials will be `source`d from the file `.prodenv`.



Localhost provision
-------------------
You'll need to install Python3, Postgres DB, and redis on your machine.


Code:

    virtualenv -p python3  venv
    source venv/bin/activate
    pip install -r requirements/local.txt
    ./manage.py makemigrations

Create DB for local development (assuming Postgres is running on localhost):

    createdb sushibar

Migrate models

    ./manage.py migrate

For convenience there you can load an predefined admin user fixture using

    ./manage.py loaddata sushibar/users/fixtures/admin_user.json

Then you can login with username `admin` and password `admin123`.
Alternatively, you can create a new admin account using:

    ./manage.py createsuperuser



Run in development
------------------
You'll need four separate tabs to run the four services needed for `sushibar`:

    pg_ctl ... start                        # to start postgres
    redis-server ...                        # run redis
    celery -A sushibar worker -l info       # run celery worker
    ./manage.py runserver                   # run django (wsgi+asgi)


Running tests
-------------

    ./manage.py test runs   # test sushibar api
    ./manage.py test        # all tests



Clean-slate restart
-------------------
This will drop all the data in the DB and restart:

    dropdb sushibar
    createdb sushibar
    rm -rf runs/migrations/0*.py
    ./manage.py makemigrations
    ./manage.py migrate
    ./manage.py loaddata sushibar/users/fixtures/admin_user.json




Production setup
----------------
Before we set this up as a kubernetes, we can test all the dockerization using
the tools `docker-machine` and `docker-compose`.

    # 1. setup env vars that proxy local docker commands to the docker host `gcpsushibarhost`
    eval $(docker-machine env gcpsushibarhost)

    # 2. create network
    docker network create nginx-proxy

    # 3. start all containers
    docker-compose -f production.yml up -d

    # check what's running
    docker ps

    # View nginx+django logs (like tail -f)
    docker-compose -f production.yml  logs -f nginx django-wsgi

Possibly use https://github.com/kubernetes-incubator/kompose to generate the
Kubernetes config from `production.yml` when it's done.




Update production server
------------------------
To deploy new code after updating the local repository, run the following steps:

    # setup access to remote docker daemon
    eval $(docker-machine env gcpsushibarhost)    # this will set 4 env vars in current shell

    # rebuild
    docker-compose -f production.yml  build

    # update running containers
    docker-compose -f production.yml  up -d

    # check containers are running OK
    docker ps

TODO: research what `--no-deps` flag does and if it's better.





Debugging production setup
--------------------------

See what's going on:

    docker ps                                   # running containers
    docker ps -a                                # running and stopped containers
    docker logs django-asgi                     # see latest logs from the ASGI container
    docker-compose -f production.yml  logs      # see latest logs from all containers


Run bash inside container, while allocating a tty and using interactive mode:

    docker exec -ti nginx  /bin/bash

See current production nginx config:

    docker exec nginx   cat /etc/nginx/conf.d/default.conf


Show all the network info

    docker network ls
    docker network ls -q | xargs docker network inspect

Show intenral IPs

    docker inspect -f '{{.Name}} - {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker ps -aq)
        /nginx-gen - 172.18.0.8
        /letsencrypt-nginx-proxy-companion - 172.18.0.9
        /django-wsgi - 172.18.0.7
        /nginx - 172.18.0.6
        /asgi-worker - 172.18.0.5
        /django-asgi - 172.18.0.4
        /sushibar-postgres - 172.18.0.3
        /sushibar_redis_1 - 172.18.0.2



Volumes check

    docker volume ls
    docker volume rm <volume id>



Running DB backups
------------------

    docker exec -ti sushibar-postgres /usr/local/bin/backup
    # watch and record DB_backup_filename
    docker cp sushibar-postgres:/backups/{{DB_backup_filename}} ~/Desktop/


Connecting to docker machine
----------------------------

    ssh -i ~/.docker/machine/machines/gcpsushibarhost/id_rsa  35.185.105.222


Restart from scratch
--------------------

    # bring containers down and make sure volumes are deleted
    docker-compose -f production.yml  down -v

    # cleanup images
    docker images
    docker-compose -f production.yml  rm
    docker rmi -f sample-api sample-website jwilder/docker-gen mhart/alpine-node \
                  jrcs/letsencrypt-nginx-proxy-companion nginx sushibar_nginx-gen
    docker images

    # rebuild
    docker-compose -f production.yml  build --no-cache

    docker-compose -f production.yml  up  # prints combined strout from all containers
