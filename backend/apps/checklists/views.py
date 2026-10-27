from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.ip import client_ip
from apps.audit.models import AuditLog
from apps.users import scope
from apps.users.models import User
from apps.users import permisos
from apps.users.permissions import IsAdminOrSupOrTec, TienePermiso
from apps.work_orders.device_time import device_time

from .models import ChecklistResponse, ChecklistTemplate, ChecklistTemplateVersion
from .serializers import (
    ChecklistFieldResponseCreateSerializer,
    ChecklistFieldResponseSerializer,
    ChecklistResponseCreateSerializer,
    ChecklistResponseSerializer,
    ChecklistTemplateCreateUpdateSerializer,
    ChecklistTemplateDetailSerializer,
    ChecklistTemplateListSerializer,
    ChecklistTemplateVersionSerializer,
    ChecklistVersionCreateSerializer,
)
from .validators import validate_field_value


class ChecklistTemplateViewSet(viewsets.ModelViewSet):
    queryset = ChecklistTemplate.objects.prefetch_related("versions__fields").all()

    def get_queryset(self):
        qs = ChecklistTemplate.objects.prefetch_related("versions__fields").all()
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ("true", "1"))
        return qs

    def get_permissions(self):
        # Las plantillas son del trabajo interno: el hospital ve el checklist
        # respondido en su OT, no el catalogo.
        if self.action in ("list", "retrieve"):
            return [IsAdminOrSupOrTec()]
        return [TienePermiso("checklists.gestionar")()]

    def get_serializer_class(self):
        if self.action == "list":
            return ChecklistTemplateListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ChecklistTemplateCreateUpdateSerializer
        return ChecklistTemplateDetailSerializer

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=["post"], url_path="publish-version")
    def publish_version(self, request, pk=None):
        template = self.get_object()
        serializer = ChecklistVersionCreateSerializer(
            data=request.data,
            context={"template": template, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        version = serializer.save()
        return Response(
            ChecklistTemplateVersionSerializer(version).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="set-current")
    def set_current(self, request, pk=None):
        template = self.get_object()
        version_id = request.data.get("version_id")
        if not version_id:
            return Response(
                {"detail": "Se requiere 'version_id'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        version = get_object_or_404(ChecklistTemplateVersion, pk=version_id, template=template)
        with transaction.atomic():
            ChecklistTemplateVersion.objects.filter(template=template, is_current=True).update(is_current=False)
            version.is_current = True
            version.save()
        return Response(ChecklistTemplateVersionSerializer(version).data)


class ChecklistResponseViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        # Leer: todos, cada uno dentro de lo suyo (get_queryset). Escribir
        # (crear, responder, cambiar tomas, cerrar): nunca una cuenta de
        # hospital. Antes submit-field le respondia 200 a un cliente sobre el
        # checklist abierto de otro hospital.
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAdminOrSupOrTec()]

    def get_serializer_class(self):
        if self.action == "create":
            return ChecklistResponseCreateSerializer
        return ChecklistResponseSerializer

    def get_queryset(self):
        user = self.request.user
        qs = ChecklistResponse.objects.select_related(
            "version", "completed_by", "task__work_order"
        ).prefetch_related("field_responses__field")
        if user.role == User.Role.TEC and not permisos.ve_ots_en_alcance(user):
            return qs.filter(task__work_order__assigned_to=user)
        if user.role == User.Role.CLI:
            # Como sus OTs: solo lo finalizado, dentro de su alcance.
            qs = qs.filter(task__work_order__status="COMPLETED")
        return scope.work_orders(qs, user, prefix="task__work_order__")

    def _solo_quien_ejecuta(self, request, response):
        """
        Un tecnico con permisos de gestion ve los checklists de su alcance para
        revisarlos, pero responder y cerrar sigue siendo de quien tiene la OT
        (admin y supervisor, como hoy, pueden ademas con las ajenas).
        """
        if request.user.role == User.Role.TEC and response.task.work_order.assigned_to_id != request.user.id:
            return Response(
                {"detail": "Solo quien tiene asignada la OT llena su checklist."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    # Mientras la OT esta programada o en curso el checklist se llena y se
    # corrige (revision del 2026-10-23: "si uno se equivoco, no se puede volver
    # a corregir"). En revision lo corrige quien revisa (correct-field) y,
    # devuelta a en curso, el tecnico vuelve a editar.
    _ESTADOS_EDITABLES = ("PENDING", "IN_PROGRESS")

    def _ot_no_editable(self, response):
        if response.task.work_order.status in self._ESTADOS_EDITABLES:
            return None
        return Response(
            {
                "detail": "La OT ya no está en curso: el checklist no admite cambios. "
                          "Si hay que corregir algo, que la devuelvan a en curso.",
                "code": "ot_no_editable",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    @staticmethod
    def _reabrir(response):
        """Un cambio deja el checklist por cerrar de nuevo."""
        if response.completed_at or response.completed_by_id:
            response.completed_at = None
            response.completed_by = None
            response.save(update_fields=["completed_at", "completed_by"])

    @staticmethod
    def _quitar_pendientes_de(response, field, repeticion):
        """Responder el item (o algo de su bloque) lo saca de los pendientes."""
        grupo = field.group if field.group in response.version.repeatable_groups else ""
        restantes = [
            p for p in response.pendientes
            if not (
                (p.get("field") and str(p["field"]) == str(field.id)
                 and p.get("repetition", 0) == repeticion)
                or (not p.get("field") and grupo and p.get("group") == grupo
                    and p.get("repetition") == repeticion)
            )
        ]
        if len(restantes) != len(response.pendientes):
            response.pendientes = restantes
            response.save(update_fields=["pendientes"])

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=["post"], url_path="submit-field")
    def submit_field(self, request, pk=None):
        response = self.get_object()
        if (bloqueo := self._solo_quien_ejecuta(request, response)) is not None:
            return bloqueo
        if (bloqueo := self._ot_no_editable(response)) is not None:
            return bloqueo

        serializer = ChecklistFieldResponseCreateSerializer(
            data=request.data,
            context={"response": response, "request": request},
        )
        serializer.is_valid(raise_exception=True)

        field = serializer.validated_data["field"]
        value = serializer.validated_data.get("value", "")
        repeticion = serializer.validated_data.get("repetition", 0)
        try:
            extra = validate_field_value(field, value)
        except ValueError as e:
            return Response({"value": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        previa = response.field_responses.filter(field=field, repetition=repeticion).first()
        notas = serializer.validated_data.get("notes", "")
        cambio = previa is None or previa.value != value or previa.notes != notas

        field_response = serializer.save()
        field_response._out_of_range = extra.get("out_of_range", False)
        # El checklist se crea vacio al programar la tarea: empieza de verdad
        # con la primera respuesta.
        if response.started_at is None:
            response.started_at = timezone.now()
            response.save(update_fields=["started_at"])
        self._quitar_pendientes_de(response, field, repeticion)
        if cambio:
            self._reabrir(response)

        return Response(ChecklistFieldResponseSerializer(field_response).data)

    @action(detail=True, methods=["post"], url_path="correct-field")
    def correct_field(self, request, pk=None):
        """
        Un administrador o supervisor corrige una respuesta de una OT en
        revision, antes de aprobarla (decision del 2026-10-01). Antes solo podia
        devolverla al tecnico. La respuesta conserva la hora del tecnico, queda
        marcada "Corregido por" y el valor anterior va a la auditoria; el acta
        sale con el valor final.
        """
        if not permisos.puede(request.user, "ot.revisar"):
            return Response(status=status.HTTP_403_FORBIDDEN)
        response = self.get_object()
        if response.task.work_order.status != "IN_REVIEW":
            return Response(
                {"detail": "Solo se corrige una OT en revisión. En proceso la llena quien la ejecuta."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ChecklistFieldResponseCreateSerializer(
            data=request.data,
            context={"response": response, "request": request, "corrector": request.user},
        )
        serializer.is_valid(raise_exception=True)
        field = serializer.validated_data["field"]
        value = serializer.validated_data.get("value", "")
        repeticion = serializer.validated_data.get("repetition", 0)
        try:
            extra = validate_field_value(field, value)
        except ValueError as e:
            return Response({"value": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        previa = response.field_responses.filter(field=field, repetition=repeticion).first()
        notas = serializer.validated_data.get("notes", previa.notes if previa else "")
        if previa is not None and previa.value == value and previa.notes == notas:
            return Response(ChecklistFieldResponseSerializer(previa).data)

        serializer.validated_data["notes"] = notas
        field_response = serializer.save()
        field_response._out_of_range = extra.get("out_of_range", False)
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.UPDATE,
            entity_type="ChecklistFieldResponse",
            entity_id=field_response.id,
            changes={
                "correccion": True,
                "work_order": str(response.task.work_order_id),
                "field": field.label,
                "repetition": repeticion,
                "value": {"from": previa.value if previa else None, "to": value},
                "notes": {"from": previa.notes if previa else None, "to": notas},
            },
            ip_address=client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        return Response(ChecklistFieldResponseSerializer(field_response).data)

    @action(detail=True, methods=["post"], url_path="block-count")
    def block_count(self, request, pk=None):
        """
        El tecnico encontro otra cantidad de tomas que la del plan. El checklist
        queda con la real; la diferencia la ve el administrador en la OT.
        """
        response = self.get_object()
        if (bloqueo := self._solo_quien_ejecuta(request, response)) is not None:
            return bloqueo
        if (bloqueo := self._ot_no_editable(response)) is not None:
            return bloqueo
        grupo = request.data.get("group", "")
        if grupo not in response.version.repeatable_groups:
            return Response(
                {"group": f"«{grupo}» no es un grupo que se repita en este checklist."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            cuantas = int(request.data.get("count"))
        except (TypeError, ValueError):
            cuantas = 0
        if cuantas < 1:
            return Response(
                {"count": "Tiene que haber al menos una."}, status=status.HTTP_400_BAD_REQUEST
            )
        # Solo se quitan tomas vacias: bajar la cantidad no borra respuestas.
        mayor = max(
            (fr.repetition for fr in response.field_responses.all() if fr.field.group == grupo),
            default=0,
        )
        if cuantas < mayor:
            return Response(
                {"count": f"La {grupo.lower()} {mayor} tiene respuestas; no se puede quitar."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if cuantas != response.count_for(grupo):
            self._reabrir(response)
        response.block_counts = {**response.block_counts, grupo: cuantas}
        # Un pendiente de una toma que ya no existe se va con ella.
        response.pendientes = [
            p for p in response.pendientes
            if not (p.get("group") == grupo and (p.get("repetition") or 0) > cuantas)
        ]
        response.save(update_fields=["block_counts", "pendientes"])
        return Response(ChecklistResponseSerializer(response).data)

    @action(detail=True, methods=["post"], url_path="pending")
    def set_pending(self, request, pk=None):
        """
        Deja como "Pendiente - no se pudo revisar" un campo o un bloque
        repetible completo (p. ej. el cubiculo 7, aislado por aerosoles), con
        su motivo. Recibe la lista completa de pendientes: reenviarla es
        idempotente, como lo necesita la cola sin red. Responder el item
        despues lo quita solo.
        """
        response = self.get_object()
        if (bloqueo := self._solo_quien_ejecuta(request, response)) is not None:
            return bloqueo
        if (bloqueo := self._ot_no_editable(response)) is not None:
            return bloqueo
        entrada = request.data.get("pendientes")
        if not isinstance(entrada, list):
            return Response({"pendientes": "Manda la lista de pendientes."},
                            status=status.HTTP_400_BAD_REQUEST)

        campos = {str(f.id): f for f in response.version.fields.all()}
        repetibles = response.version.repeatable_groups
        respondidas = {
            (str(fid), rep)
            for fid, rep in response.field_responses.values_list("field_id", "repetition")
        }
        previos = {
            (str(p.get("field") or ""), p.get("group", ""), p.get("repetition", 0)): p
            for p in response.pendientes
        }
        nuevos, vistos = [], set()
        for item in entrada:
            if not isinstance(item, dict):
                return Response({"pendientes": "Pendiente inválido."}, status=status.HTTP_400_BAD_REQUEST)
            motivo = str(item.get("reason") or "").strip()
            if not motivo:
                return Response({"reason": "Di por qué quedó pendiente."}, status=status.HTTP_400_BAD_REQUEST)
            if len(motivo) > 200:
                return Response({"reason": "El motivo es muy largo (máximo 200 letras)."},
                                status=status.HTTP_400_BAD_REQUEST)
            try:
                rep = int(item.get("repetition") or 0)
            except (TypeError, ValueError):
                return Response({"repetition": "Número de repetición inválido."},
                                status=status.HTTP_400_BAD_REQUEST)
            campo_id = str(item.get("field") or "")
            if campo_id:
                campo = campos.get(campo_id)
                if campo is None:
                    return Response({"field": "El campo no pertenece a este checklist."},
                                    status=status.HTTP_400_BAD_REQUEST)
                grupo = campo.group if campo.group in repetibles else ""
                if grupo:
                    if not 1 <= rep <= response.count_for(grupo):
                        return Response({"repetition": f"«{grupo}» va de 1 a {response.count_for(grupo)}."},
                                        status=status.HTTP_400_BAD_REQUEST)
                elif rep != 0:
                    return Response({"repetition": f"«{campo.label}» no se repite."},
                                    status=status.HTTP_400_BAD_REQUEST)
                if (campo_id, rep) in respondidas:
                    continue  # ya tiene respuesta: no esta pendiente
                grupo_p = ""
            else:
                grupo_p = str(item.get("group") or "")
                if grupo_p not in repetibles:
                    return Response({"group": f"«{grupo_p}» no es un grupo que se repita en este checklist."},
                                    status=status.HTTP_400_BAD_REQUEST)
                if not 1 <= rep <= response.count_for(grupo_p):
                    return Response({"repetition": f"«{grupo_p}» va de 1 a {response.count_for(grupo_p)}."},
                                    status=status.HTTP_400_BAD_REQUEST)
            clave = (campo_id, grupo_p, rep)
            if clave in vistos:
                continue
            vistos.add(clave)
            previo = previos.get(clave)
            if previo is not None:
                nuevos.append({**previo, "reason": motivo})
                continue
            cuando = item.get("marked_at")
            cuando = parse_datetime(cuando) if isinstance(cuando, str) else None
            nuevos.append({
                "field": campo_id or None,
                "group": grupo_p,
                "repetition": rep,
                "reason": motivo,
                "marked_at": device_time(cuando, response.task.work_order).isoformat(),
                "marked_by": str(request.user.id),
            })

        response.pendientes = nuevos
        response.save(update_fields=["pendientes"])
        if nuevos:
            self._reabrir(response)
        return Response(ChecklistResponseSerializer(response).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        response = self.get_object()
        if (bloqueo := self._solo_quien_ejecuta(request, response)) is not None:
            return bloqueo
        if response.completed_at:
            return Response(
                {"detail": "El checklist ya está completado.", "code": "checklist_completed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Un pendiente es lo que no se pudo revisar: mientras siga ahi el
        # checklist no esta completo.
        if response.pendientes:
            return Response(
                {"detail": "Hay pendientes por resolver: " + "; ".join(response.pendientes_texto()) + "."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Un obligatorio de un grupo repetible lo es en cada toma, no solo en
        # la primera (en Fracttal solo la primera toma tenia obligatorios).
        answered = set(response.field_responses.values_list("field_id", "repetition"))
        unanswered = [
            f"{field.group} {n}: {field.label}" if n else field.label
            for field, n in response.slots()
            if field.is_required and (field.id, n) not in answered
        ]

        if unanswered:
            return Response(
                {"detail": f"Campos requeridos sin responder: {', '.join(unanswered)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Cerrado sin red, llega la hora en que el tecnico lo cerro en el telefono.
        cuando = request.data.get("completed_at")
        cuando = parse_datetime(cuando) if isinstance(cuando, str) else None
        response.completed_at = device_time(cuando, response.task.work_order)
        response.completed_by = request.user
        response.save()

        return Response(ChecklistResponseSerializer(response).data)
