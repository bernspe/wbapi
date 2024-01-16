#!/bin/bash
echo "ACtivating Environment"
source activate dockerenv
echo "Analyzing environment"
python --version
echo "Working directory"
pwd
echo "Environment"
conda env list
echo "Collectstatic"
python manage.py collectstatic --no-input
python manage.py makemigrations
python manage.py migrate
python manage.py initadmin
python manage.py gen_groups
python manage.py createapplication --client-id $1 --client-secret $2 --skip-authorization --name WBAPIAuth confidential password
export PATH=/opt/conda/envs/dockerenv/lib/python3.11/site-packages:$PATH
echo PATH
gunicorn --bind 0.0.0.0:8002 wbapi.wsgi:application