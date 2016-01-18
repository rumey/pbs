from django import template

register = template.Library()


@register.inclusion_tag('admin/prescription/regional_objectives.html',
                        takes_context=True)
def show_regional_objectives(context):
    return {
        'request': context.get('request'),
        'current': context.get('current'),
    }
