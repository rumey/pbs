from django.contrib import admin

from swingers.admin import RelatedFieldAdmin
from swingers.tests.models import Duck, ParentDuck


class ParentDuckAdmin(RelatedFieldAdmin):
    pass


class DuckAdmin(admin.ModelAdmin):
    pass


class ParentDuckAdmin2(admin.ModelAdmin):
    search_fields = ('name',)


admin.site.register(Duck, DuckAdmin)
admin.site.register(ParentDuck, ParentDuckAdmin2)
