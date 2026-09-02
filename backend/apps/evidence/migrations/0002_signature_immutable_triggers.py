"""
Inalterabilidad de las firmas a nivel de base de datos.

El docstring de Signature dice "Inmutable", pero nada lo hacia cumplir. Una
firma es lo que convierte el acta en un documento con valor probatorio bajo la
Ley 527 de 1999 (RNF-COM-03, RF-FD-03): si el par firma/hash se puede
reescribir, la firma no certifica nada.

Photo no lleva trigger: la galeria admite anadir y quitar fotos mientras la OT
esta abierta (RF-OT-05 permite hasta 20), y una vez cerrada ya lo cubren el
guard de estado terminal de WorkOrderViewSet y el hash de contenido, que
incluye el file_hash de cada foto.

TRUNCATE no se bloquea con trigger: es un privilegio otorgable aparte en
PostgreSQL, asi que le corresponde un REVOKE TRUNCATE al rol de aplicacion.
Bloquearlo por trigger alcanzaria tambien al propietario de la tabla y rompe
flujos legitimos (el flush de la base de pruebas, cargas de mantenimiento).
Ver la nota sobre separacion de roles en la migracion 0002 de audit.
"""

from django.db import migrations

FORWARD = """
CREATE OR REPLACE FUNCTION evidence_signature_block_write()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'evidence_signature es inmutable: % denegado sobre la firma %',
        TG_OP, OLD.id
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_evidence_signature_no_update ON evidence_signature;
CREATE TRIGGER trg_evidence_signature_no_update
    BEFORE UPDATE ON evidence_signature
    FOR EACH ROW EXECUTE FUNCTION evidence_signature_block_write();

DROP TRIGGER IF EXISTS trg_evidence_signature_no_delete ON evidence_signature;
CREATE TRIGGER trg_evidence_signature_no_delete
    BEFORE DELETE ON evidence_signature
    FOR EACH ROW EXECUTE FUNCTION evidence_signature_block_write();
"""

REVERSE = """
DROP TRIGGER IF EXISTS trg_evidence_signature_no_update ON evidence_signature;
DROP TRIGGER IF EXISTS trg_evidence_signature_no_delete ON evidence_signature;
DROP FUNCTION IF EXISTS evidence_signature_block_write();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("evidence", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE),
    ]
