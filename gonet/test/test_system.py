from django.conf import settings
from django.test import TestCase
import pandas as pd
from pandas._libs.tslibs import parsing

class SystemTestCase(TestCase):

    def test_ontology_version(self):
        ver = parsing.parse_datetime_string(settings.ONTOLOGY_VERSION)
        t = pd.datetime(2019, 4, 16)
        self.assertGreater(ver, t)

    def test_human_annotation_version(self):
        ver = parsing.parse_datetime_string(settings.ANNOTATION_VERSION['human'])
        t = pd.datetime(2019, 4, 16)
        self.assertGreater(ver, t)

    def test_mouse_annotation_version(self):
        ver = parsing.parse_datetime_string(settings.ANNOTATION_VERSION['mouse'])
        t = pd.datetime(2019, 4, 16)
        self.assertGreater(ver, t)
        
