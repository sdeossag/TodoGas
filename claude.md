# TodoGas CMMS

Backend Django para un CMMS de gases medicinales.

## Stack
- Django 5.x + Django REST Framework
- PostgreSQL
- Celery + Redis
- WeasyPrint para PDFs
- Deploy en AWS

## Estructura de apps
users, assets, checklists, work_orders, maintenance,
evidence, inventory, audit, reports, notifications

## Reglas importantes
- ForeignKeys entre apps siempre con string: 'app.Modelo'
- UUIDs como primary key en todos los modelos
- on_delete=models.PROTECT siempre, nunca CASCADE
- AUTH_USER_MODEL = 'users.User'
- Los modelos estan en models_complete.py en la raiz