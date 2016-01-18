from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.template import RequestContext
from django.template.loader import render_to_string

from reversion.admin import VersionAdmin
from guardian.admin import GuardedModelAdmin

from swingers.sauth.models import Job, ApplicationLink, Token


class AuditAdmin(VersionAdmin, GuardedModelAdmin, ModelAdmin):
    search_fields = ['id', 'creator__username', 'modifier__username',
                     'creator__email', 'modifier__email']
    list_display = ['__unicode__', 'creator', 'modifier', 'created',
                    'modified']
    raw_id_fields = ['creator', 'modifier']
    change_list_template = None

    def get_list_display(self, request):
        list_display = list(self.list_display)
        for index, field_name in enumerate(list_display):
            field = getattr(self.model, field_name, None)
            if hasattr(field, "related"):
                list_display.remove(field_name)
                list_display.insert(
                    index, self.display_add_link(request, field.related))
        return list_display

    def display_add_link(self, request, related):
        def inner(obj):
            opts = related.model._meta
            kwargs = {related.field.name: obj}
            count = related.model._default_manager.filter(**kwargs).count()
            context = {
                'related': related,
                'obj': obj,
                'opts': opts,
                'count': count
            }
            return render_to_string(
                'admin/change_list_links.html',
                RequestContext(request, context)
            )
        inner.allow_tags = True
        inner.short_description = related.opts.verbose_name_plural.title()
        return inner


admin.site.register(Job)
admin.site.register(ApplicationLink)
admin.site.register(Token)
