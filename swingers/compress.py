from compressor.js import JsCompressor as DefaultJsCompressor
from compressor.css import CssCompressor as DefaultCssCompressor
from compressor.parser.lxml import LxmlParser
from compressor.base import Compressor

#
# settings.py
#
# COMPRESS_JS_COMPRESSOR = '.compress.JsCssCompressor'
# COMPRESS_PARSER = '.compress.CompressParser'
#
# base.html
#
# <!doctype html>
# <html>
# <head>
#    {% compress js %}
#    ...
#    {% endcompress %}
# </head>
# </html>

import logging

logger = logging.getLogger("log." + __name__)


class CompressorMixin(Compressor):
    def split_contents(self):
        _split_contents = super(CompressorMixin, self).split_contents()
        for kind, value, basename, elem in _split_contents:
            if getattr(self, 'remove_elems', False):
                self.parser.elem_remove(elem)
        return _split_contents


class JsCompressor(CompressorMixin, DefaultJsCompressor):
    pass


class CssCompressor(CompressorMixin, DefaultCssCompressor):
    pass


class JsCssCompressor(Compressor):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.css_compressor = CssCompressor(*args, **kwargs)
        self.js_compressor = JsCompressor(*args, **kwargs)
        super(JsCssCompressor, self).__init__(*args, **kwargs)

    def output(self, mode='file', forced=False):
        self.css_compressor.remove_elems = True
        css_output = self.css_compressor.output(mode, forced)

        self.kwargs.update({
            'content': self.css_compressor.parser.get_processed_content()
        })
        self.js_compressor = JsCompressor(*self.args, **self.kwargs)
        self.js_compressor.remove_elems = True
        js_output = self.js_compressor.output(mode, forced)
        return (css_output + js_output +
                self.js_compressor.parser.get_processed_content())

    def split_contents(self):
        return (self.css_compressor.split_contents() +
                self.js_compressor.split_contents())


class CompressParser(LxmlParser):
    def js_elems(self):
        return self.tree.xpath("//script[not(@data-compress='false')]")

    def css_elems(self):
        return self.tree.xpath(
            '//link[re:test(@rel, "^stylesheet$", "i")]'
            '[not(@data-compress="false")]|style[not(@data-compress="false")]',
            namespaces={"re": "http://exslt.org/regular-expressions"})

    def get_processed_content(self):
        # remove <root> and </root>
        return self.tostring(self.tree, method='html')[6:-7]

    def elem_remove(self, elem):
        elem.getparent().remove(elem)
