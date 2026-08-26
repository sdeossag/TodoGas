from django.contrib import admin

from .models import (
    ChecklistField,
    ChecklistFieldResponse,
    ChecklistResponse,
    ChecklistTemplate,
    ChecklistTemplateVersion,
)

admin.site.register(ChecklistTemplate)
admin.site.register(ChecklistTemplateVersion)
admin.site.register(ChecklistField)
admin.site.register(ChecklistResponse)
admin.site.register(ChecklistFieldResponse)
