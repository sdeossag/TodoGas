from django.contrib import admin

from .models import Asset, AssetCustomField, AssetCustomFieldValue, AssetNode, Hospital

admin.site.register(Hospital)
admin.site.register(AssetNode)
admin.site.register(Asset)
admin.site.register(AssetCustomField)
admin.site.register(AssetCustomFieldValue)
