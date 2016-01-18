from django.conf import settings

from htmlmin.middleware import (HtmlMinifyMiddleware as
                                DefaultHtmlMinifyMiddleware)
from compressor.templatetags.compress import OUTPUT_FILE, CompressorNode

import logging

logger = logging.getLogger("log." + __name__)


class HtmlMinifyMiddleware(DefaultHtmlMinifyMiddleware):
    def can_minify_response(self, request, response):
        # don't minify when debug_toolbar is shown
        DEBUG_TOOLBAR_CONFIG = getattr(settings, 'DEBUG_TOOLBAR_CONFIG', {})
        show_debug_toolbar = DEBUG_TOOLBAR_CONFIG.get('SHOW_TOOLBAR_CALLBACK',
                                                      lambda x: False)

        return (not show_debug_toolbar(request) and
                super(HtmlMinifyMiddleware, self).can_minify_response(
                    request, response))


class ProxyCompressorNode(CompressorNode):
    def __init__(self, request, response):
        self.response = response
        self.request = request
        self.kind = 'js'
        self.mode = OUTPUT_FILE
        self.name = None
        self.pre_html = response.content[:response.content.find('<html')]

    def get_original_content(self, context):
        return self.response.content[len(self.pre_html):]

    def debug_mode(self, context):
        # don't compress when debug_toolbar is shown
        DEBUG_TOOLBAR_CONFIG = getattr(settings, 'DEBUG_TOOLBAR_CONFIG', {})
        show_debug_toolbar = DEBUG_TOOLBAR_CONFIG.get('SHOW_TOOLBAR_CALLBACK',
                                                      lambda x: False)

        return (show_debug_toolbar(self.request) or
                super(ProxyCompressorNode, self).debug_mode(context))

    def render(self, context, forced=False):
        self.response.content = self.pre_html + super(ProxyCompressorNode,
                                                      self).render(context,
                                                                   forced)
        return self.response


class JsCssCompressMiddleware(object):
    def process_template_response(self, request, response):
        response.add_post_render_callback(
            lambda r: ProxyCompressorNode(request, response).render({})
        )
        return response
