Remove-Item db.sqlite3
Remove-Item .\smt_management_app\migrations\* -Exclude *__init__* -Recurse
Remove-Item .\smt_management_app\__pycache__ -Recurse

.\venv\Scripts\python.exe .\manage.py makemigrations
.\venv\Scripts\python.exe .\manage.py migrate
$Env:DJANGO_SUPERUSER_PASSWORD = '123456789'
.\venv\Scripts\python.exe .\manage.py createsuperuser --no-input --username=root --email=test@test.test
.\venv\Scripts\python.exe .\manage.py runscript import_ATN_storage
cls
.\venv\Scripts\python.exe .\manage.py runserver