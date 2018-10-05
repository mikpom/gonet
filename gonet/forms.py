from django.forms import ModelForm
from .models import GOnetSubmission
from django.forms import CharField, ChoiceField, TypedChoiceField,\
                         Select as select_widget, \
                         RadioSelect, Textarea

class GOnetSubmitForm(ModelForm):
    qvalue = TypedChoiceField(widget=select_widget, required=False,
                              choices=GOnetSubmission.qval_choices,
                              coerce=float, empty_value=0)
    organism = ChoiceField(widget=RadioSelect, required=True,
                           choices=GOnetSubmission.organism_choices,
                           initial='human')
    analysis_type = ChoiceField(widget=RadioSelect, required=True,
                           choices=GOnetSubmission.analysis_choices,
                           initial='enrich')
    custom_terms = CharField(widget=Textarea(attrs={'cols':16}), required=False)

    bg_type = TypedChoiceField(widget=select_widget, required=False,
                               choices=GOnetSubmission.bgtype_choices,
                               empty_value='all')
    bg_cell = TypedChoiceField(widget=select_widget, required=False,
                               choices=GOnetSubmission.bg_choices)
    slim = TypedChoiceField(widget=select_widget, required=False,
                            choices=GOnetSubmission.slim_choices,
                            initial='goslim_generic')

    
    class Meta:
        model = GOnetSubmission
        fields = ['job_name', 'uploaded_file', 'paste_data', 'namespace',
                  'output_type', 'slim', 'csv_separator',
                  'bg_file']

