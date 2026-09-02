"""
Inalterabilidad del log de auditoria a nivel de base de datos.

AuditLog.save() y delete() ya levantaban excepcion, pero esa garantia vive solo
en el ORM y se elude sin esfuerzo:

    AuditLog.objects.filter(...).update(...)   # no pasa por save()
    AuditLog.objects.filter(...).delete()      # no pasa por delete()

y cualquier sesion de psql la ignora por completo. RNF-COM-01 y RNF-COM-04
piden poder demostrar ante INVIMA que el registro no fue alterado, asi que la
regla tiene que estar donde vive el dato, no en la capa que da la casualidad de
estar usandolo.

Los triggers aplican a TODOS los roles, incluido el propietario de la tabla.
Un superusuario de PostgreSQL puede desactivarlos (ALTER TABLE ... DISABLE
TRIGGER), y eso es inevitable: la defensa contra un superusuario es operativa
(no repartir esas credenciales), no declarativa. Lo que esto cierra es la via
accidental y la via de una cuenta de aplicacion comprometida.

PENDIENTE, separacion de roles. Hoy Django se conecta con el propietario de
las tablas, que puede desactivar sus propios triggers. Lo correcto son dos
roles: uno propietario para migraciones y otro de aplicacion con permisos
recortados, y sobre ese segundo:

    REVOKE UPDATE, DELETE, TRUNCATE ON audit_auditlog FROM <rol_app>;
    REVOKE UPDATE, DELETE, TRUNCATE ON evidence_signature FROM <rol_app>;

TRUNCATE se cubre ahi y no con un trigger: es un privilegio otorgable aparte,
y bloquearlo por trigger alcanzaria tambien al propietario, rompiendo el flush
de la base de pruebas y las cargas de mantenimiento. Sin ese segundo rol, esta
migracion es la mitad de la proteccion, no la proteccion entera.
"""

from django.db import migrations

FORWARD = """
CREATE OR REPLACE FUNCTION audit_auditlog_block_write()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'audit_auditlog es append-only: % denegado sobre la fila %',
        TG_OP, OLD.id
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_auditlog_no_update ON audit_auditlog;
CREATE TRIGGER trg_audit_auditlog_no_update
    BEFORE UPDATE ON audit_auditlog
    FOR EACH ROW EXECUTE FUNCTION audit_auditlog_block_write();

DROP TRIGGER IF EXISTS trg_audit_auditlog_no_delete ON audit_auditlog;
CREATE TRIGGER trg_audit_auditlog_no_delete
    BEFORE DELETE ON audit_auditlog
    FOR EACH ROW EXECUTE FUNCTION audit_auditlog_block_write();

"""

REVERSE = """
DROP TRIGGER IF EXISTS trg_audit_auditlog_no_update ON audit_auditlog;
DROP TRIGGER IF EXISTS trg_audit_auditlog_no_delete ON audit_auditlog;
DROP FUNCTION IF EXISTS audit_auditlog_block_write();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("audit", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE),
    ]
