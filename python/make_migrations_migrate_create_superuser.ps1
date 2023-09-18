.\venv\Scripts\python.exe .\manage.py makemigrations
.\venv\Scripts\python.exe .\manage.py migrate
$Env:DJANGO_SUPERUSER_PASSWORD = '123456789'
.\venv\Scripts\python.exe .\manage.py createsuperuser --no-input --username=root --email=test@test.test