#!/usr/bin/env python
"""
Module: report_tags.py
Package: pbs.templatetags
Description: Give me some markup

"""
from __future__ import print_function, division, unicode_literals, absolute_import
### Imports
from django import template

### Constants
register = template.Library()
### Classes

### Functions
@register.simple_tag
def show_rows(row, user):
    key_order = [
        'burn_id',
        'name',
        'region',
        'district',
        'aerial_text',
        'area',
        'contentious_text',
        'approval_status_text',
        'read_by_text',
        'reviewed_by_text',
    ]
    field_tpl = """<td><div class="text-center {}">{}</div></td>"""
    row_fields = "".join(field_tpl.format(k, row[k]) for k in key_order)

    read_button = """
    <td><button type="button" class="read" prescription_id="{0}" user="{1}">
        Read
    </button></td>""".format(row['prescription_id'], user)
    reviewed_button = """
    <td><button type="button" class="reviewed" prescription_id={0} user="{1}">
        Approve
    </button></td>""".format(row['prescription_id'], user)
    row_str = """
    <tr id="{pid}">
    {rf} {reb} {rvb}
    </tr>
    """.format(pid=row['prescription_id'], rf=row_fields,
               reb=read_button, rvb=reviewed_button)
    return row_str
    # return "<h1>{}</h1>".format(row_fields)
### Tests

if __name__ == "__main__":

    print("Done __main__")
