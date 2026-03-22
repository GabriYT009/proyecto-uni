How to run this project on another Windows machine

1) Copy the `django_app` folder to the other computer (keep the `cliente` folder alongside it that contains `solucionarteBD.sql`).

2) Open PowerShell and change to the `django_app` folder.

3) Create a virtual environment and install dependencies (recommended):

    .\setup_portable.ps1 -CreateVenv -InstallReqs

4) Import the SQL dump into `db.sqlite3` (if you want the exact DB state):

    .\setup_portable.ps1 -ImportSQL

   This will look for `..\cliente\solucionarteBD.sql` relative to the `django_app` folder. If you placed it elsewhere, run the import script directly:

    .\.venv\Scripts\python.exe .\scripts\import_sql.py ..\cliente\solucionarteBD.sql

5) Run the development server:

    .\setup_portable.ps1 -RunServer

Notes
- Ensure Python 3.10+ is installed on the target machine and available via `python` in PATH.
- The `requirements.txt` includes Django 5.2.8; add any other packages your environment needs.
- If you prefer manual steps: create venv, activate it, `pip install -r requirements.txt`, then import SQL and run `python manage.py runserver`.
