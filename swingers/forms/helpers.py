from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


class BaseFormHelper(FormHelper):
    """
    A crispy_forms FormHelper class consisting of Save and Cancel submit
    buttons.
    """
    def __init__(self, *args, **kwargs):
        super(BaseFormHelper, self).__init__(*args, **kwargs)
        self.form_class = 'form-horizontal'
        self.form_method = 'POST'
        self.help_text_inline = True
        save_button = Submit('save', 'Save')
        save_button.field_classes = 'btn-primary btn-large'
        self.add_input(save_button)
        cancel_button = Submit('cancel', 'Cancel')
        self.add_input(cancel_button)
