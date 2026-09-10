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

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
