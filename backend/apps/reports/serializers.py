from django.core.files.storage import default_storage
from rest_framework import serializers

from .models import GeneratedReport, ReportSendLog


def _storage_url(path):
    if not path:
        return None
    if path.startswith("http"):
        return path
    return default_storage.url(path)


class ReportSendLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportSendLog
        fields = [
            "id", "recipient_email", "recipient_name",
            "sent_at", "was_successful", "error_message",
        ]


class WorkOrderMinSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    wo_number = serializers.IntegerField()


class GeneratedReportSerializer(serializers.ModelSerializer):
    work_order = WorkOrderMinSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    send_logs = ReportSendLogSerializer(many=True, read_only=True)

    class Meta:
        model = GeneratedReport
        fields = [
            "id", "work_order", "report_type", "title",
            "file_url", "file_hash", "generated_at", "send_logs",
        ]

    def get_file_url(self, obj):
        return _storage_url(obj.file_url)
