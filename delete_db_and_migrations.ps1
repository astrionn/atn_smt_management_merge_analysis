Remove-Item db.sqlite3
Remove-Item .\smt_management_app\migrations\* -Exclude *__init__* -Recurse
Remove-Item .\smt_management_app\__pycache__ -Recurse