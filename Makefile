venv: venv/touchfile

venv/touchfile: requirements.txt
	test -d venv || python -m venv venv
	. venv/bin/activate; pip install -Ur requirements.txt
	touch venv/touchfile

migrations: venv
	. venv/bin/activate; \
	python manage.py makemigrations; \
	python manage.py migrate

superuser: venv
	. venv/bin/activate; \
	export DJANGO_SUPERUSER_PASSWORD=123456789; \
	python manage.py createsuperuser --no-input --username=root --email=test@test.test

run: venv migrations superuser
	. venv/bin/activate; \
	python manage.py runserver

clean_migrations:
	rm db.sqlite3
	find ./smt_management_app/migrations -type f ! -name "__init__.py" -delete
	rm -r ./smt_management_app/__pycache__

clean: clean_migrations
	rm -rf venv
	find -iname "*.pyc" -delete
