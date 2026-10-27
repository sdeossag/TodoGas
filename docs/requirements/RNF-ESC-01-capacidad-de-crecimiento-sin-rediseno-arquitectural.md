---
id: RNF-ESC-01
issue: 72
titulo: "Capacidad de crecimiento sin rediseño arquitectural"
tipo: non-functional
prioridad: should-have
modulo: escalabilidad
estado: OPEN
etiquetas: ['priority: should-have', 'type: non-functional', 'mod: escalabilidad']
---

# RNF-ESC-01 - Capacidad de crecimiento sin rediseño arquitectural

### RNF-ESC-01: Capacidad de crecimiento sin rediseño arquitectural
**Prioridad:** S

**Descripción:**
El sistema debe poder soportar un crecimiento de hasta 3 veces el volumen inicial sin requerir cambios arquitecturales mayores, solo ajustes de infraestructura (scaling vertical u horizontal).

**Criterios de aceptación:**
- El diseño del modelo de datos en PostgreSQL soporta sin migración estructural: hasta **15,000 activos** (3.8× el volumen inicial), hasta **500 hospitales**, hasta **30 técnicos**, y hasta **5,000 OTs por mes**.
- El API de Django está diseñado para **escalado horizontal**: múltiples instancias del servidor pueden correr en paralelo detrás de un Application Load Balancer (ALB) sin estado compartido entre instancias (las sesiones/tokens son stateless con JWT; el estado de las tareas Celery está en Redis).
- Los workers de **Celery** pueden escalar horizontalmente añadiendo más instancias sin cambios de código. La cola de tareas en Redis soporta múltiples workers consumiendo de la misma cola.
- Los tiempos de respuesta del API (RNF-REN-01) se mantienen dentro de los objetivos con **50 usuarios concurrentes** (escenario de crecimiento al doble) sin cambios de código, solo escalando la instancia RDS y añadiendo una segunda instancia del API.
- El almacenamiento en S3 es elástico por naturaleza; no hay límite de capacidad que requiera planeación.

---

---

**Metadatos de importacion**
- Tipo: `Requisito no funcional`
- Fase: `2`
- Repositorio destino: `sdeossag/TodoGas`
- Categoria: `ESC - Escalabilidad`
- Prioridad: `S`
- Fuente: `CMMS Gases Medicinales - Fase 2: Requisitos No Funcionales`

**Implementación (revisión del 2026-10-27):**
- [x] Modelo de datos con UUID e índices para 15.000 activos — UUID como clave primaria e índices
- [x] API sin estado y escalable detrás del ALB — JWT sin estado, servicio ECS, caché en Redis
- [x] Workers de Celery escalables — Servicio de worker aparte sobre SQS o Redis
- [ ] Tiempos con 50 usuarios concurrentes — Sin prueba de carga
- [x] S3 elástico

Commits: 45090aa
Archivos: `infra/terraform/ecs.tf`, `infra/terraform/sqs.tf`, `backend/config/settings/production.py`
