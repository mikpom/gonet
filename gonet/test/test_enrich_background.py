import io
from django.test import TransactionTestCase
from django.test import Client
from django import urls
from pkg_resources import resource_filename as pkg_file
import json
from ..models import GOnetSubmission
import numpy as np
import pandas as pd
from gonet import cyjs
from . import job_req

c = Client()

class GOnetEnrichmentWBgTestCase(TransactionTestCase):
    def test_GO_enrichment_list3_qval0001_CD8bg(self):
        input_lines = open(pkg_file(__name__, 'data/genelist3.csv'), 'r').read()
        bg_file = open(pkg_file(__name__, 'data/CD8_cells_background_TPM10.lst'), 'r')
        req = dict(job_req, **{'paste_data':input_lines, 'bg_type':'custom',
                                   'bg_file':bg_file, 'qvalue':0.0001,
                                   'csv_separator':','})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')

        #check enriched terms
        enriched = set(sn.enrich_res_df.query('q<0.0001')['term'])
        self.assertIn('GO:0002376', enriched) # Immune system process
 
    def test_GO_enrichment_list3_predefined_BG(self):
        input_lines = open(pkg_file(__name__, 'data/genelist3.csv'), 'r').read()
        req = dict(job_req, **{'paste_data':input_lines, 'bg_type': 'predef',
                                   'bg_cell' : 'DICE-any', 'qvalue':0.01,
                                   'csv_separator':','})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')

        #check enriched terms
        enriched = set(sn.enrich_res_df.query('q<0.01')['term'])
        self.assertIn('GO:0002376', enriched) # Immune system process

    def test_GO_enrichment_list3_HPA_bonemarrow_BG(self):
        input_lines = open(pkg_file(__name__, 'data/genelist3.csv'), 'r').read()
        req = dict(job_req, **{'paste_data':input_lines, 'bg_type': 'predef',
                                   'bg_cell' : 'HPA-bone marrow', 'qvalue':0.01,
                                   'csv_separator':','})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')

        #check enriched terms
        enriched = set(sn.enrich_res_df.query('q<0.01')['term'])
        self.assertIn('GO:0002376', enriched)
        
    def test_GO_enrichment_list7_mouse_predefined_BG(self):
        input_lines = open(pkg_file(__name__, 'data/genelist7.txt'), 'r').read()
        req = dict(job_req, **{'paste_data':input_lines, 'organism':'mouse',
                                   'bg_type': 'predef',
                                   'bg_cell' : 'Bgee-any', 'qvalue':0.01,
                                   'csv_separator':','})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        enriched = set(sn.enrich_res_df.query('q<0.01')['term'])
        self.assertIn('GO:0050789', enriched)

    def test_GO_enrichment_list7_mouse_fibroblast_BG(self):
        input_lines = open(pkg_file(__name__, 'data/genelist7.txt'), 'r').read()
        req = dict(job_req, **{'paste_data':input_lines, 'organism':'mouse',
                                   'bg_type': 'predef',
                                   'bg_cell' : 'Bgee-fibroblast', 'qvalue':0.01,
                                   'csv_separator':','})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        enriched = set(sn.enrich_res_df.query('q<0.01')['term'])
        self.assertGreater(len(enriched), 0)
        
    def test_GO_enrich_genelist6_long(self):
        input_lines = open(pkg_file(__name__, 'data/genelist6.tsv'), 'r').read()
        bg_file = open(pkg_file(__name__, 'data/DPOS_Mgate_Tcells_background_TPM1.lst'), 'r')
        req = dict(job_req, **{'paste_data':input_lines, 'bg_type':'custom',
                                   'bg_file':bg_file, 'qvalue':0.0001})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        self.assertEqual(resp.status_code, 200)
