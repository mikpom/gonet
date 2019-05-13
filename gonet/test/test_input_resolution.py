import io
from django.test import TransactionTestCase
from django.test import Client
from django import urls
from pkg_resources import resource_filename as pkg_file
import json
from ..models import GOnetSubmission
import pandas as pd
from gonet import cyjs
from . import job_req

c = Client()
class GeneNamesResolutionTest(TransactionTestCase):
    def test_resolution(self):
        # CMKBR7 is synonym of CCR7
        # O14804 is PNR
        input_lines = '\n'.join(["PNR", "KIAA0457", "ELDF10", "CCR7", "AIM",
                                 "O14804", "CMKBR7", "Q9UNH8", "P28068", "FOO"])
        req = dict(job_req, **{'paste_data':input_lines})
        URL = urls.reverse('GOnet-submit-form')
        resp = c.post(URL, req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        res_d = sn.parsed_data['submit_name'].to_dict()
        self.assertDictEqual(res_d, {'O75787': 'ELDF10', 'P32248': 'CCR7',
                                     'Q9NRI5': 'KIAA0457', 'O14804': 'PNR',
                                     '_00000': 'O14804', '_00001': 'CMKBR7',
                                     'Q9UNH8' :'Q9UNH8', 'P28068':'P28068',
                                     'P26358' : 'AIM', '_00002':'FOO'})
        self.assertEqual(sn.parsed_data.loc['_00000', 'duplicate_of'], 'O14804')

        #Test id mapping response
        idmap_resp = c.get(urls.reverse('GOnet-input-idmap', args=(str(sn.id),)))
        b = io.StringIO(); b.write(idmap_resp.content.decode()); b.seek(0)
        res = pd.read_csv(b, sep='\t', index_col=0)
        self.assertEqual(res.loc['CMKBR7', 'Notes'], 'same as CCR7')
        self.assertEqual(res.loc['O14804', 'Notes'], 'same as PNR')
        self.assertEqual(res.loc['AIM', 'Description'], 'DNA (cytosine-5)-methyltransferase 1')
        self.assertIn('ambiguous', res.loc['PNR', 'Notes'])
        self.assertIn('not recognized', res.loc['FOO', 'Notes'])

        #Test tricky Ensembl IDs
        self.assertEqual(res.loc['P28068', 'Ensembl_ID'], 'ENSG00000242574')

        # Check graph attributes
        G = cyjs.cyjs2nx(json.loads(sn.network))
        self.assertEqual(G.node['_00002']['data']['identified'], False)
        self.assertEqual(G.node['P32248']['data']['identified'], True)
        self.assertEqual(G.node['O14804']['data']['ambiguous'], True)

    def test_resolution_mouse_Uniprot_IDs_wrong_species(self):
        genelist9 = pd.read_csv(pkg_file(__name__, 'data/genelist9.tsv'), sep='\t')
        input_lines = '\n'.join(genelist9[genelist9.Uniprot_ID != 'None']['Uniprot_ID'])
        req = dict(job_req, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'goslim_immunol', 'output_type':'csv'})
        URL = urls.reverse('GOnet-submit-form')
        resp = c.post(URL, req, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'None of the genes submitted')

    def test_resolution_mouse_Uniprot_IDs(self):
        genelist9 = pd.read_csv(pkg_file(__name__, 'data/genelist9.tsv'), sep='\t')
        genelist9 = genelist9[genelist9.Uniprot_ID != 'None']
        input_lines = '\n'.join(genelist9['Uniprot_ID'])
        req = dict(job_req, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'goslim_immunol', 'output_type':'csv',
                                   'organism':'mouse'})
        URL = urls.reverse('GOnet-submit-form')
        resp = c.post(URL, req, follow=True)
        self.assertEqual(resp.status_code, 200)
        sn = GOnetSubmission.objects.latest('submit_time')
        idmap_resp = c.get(urls.reverse('GOnet-input-idmap', args=(str(sn.id),)))
        b = io.StringIO(); b.write(idmap_resp.content.decode()); b.seek(0)
        res = pd.read_csv(b, sep='\t', index_col=0)
        for tup in genelist9.itertuples():
            if tup.MGI_ID=='MGI:2151253':
                continue
            self.assertEqual(res.loc[tup.Uniprot_ID, 'MGI_ID'], tup.MGI_ID)

    def test_resolution_error(self):
        # H7C0C1 throwing an error
        input_lines = 'H7C0C1'
        req = dict(job_req, **{'paste_data':input_lines})
        URL = urls.reverse('GOnet-submit-form')
        resp = c.post(URL, req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        res_d = sn.parsed_data['submit_name'].to_dict()
        self.assertDictEqual(res_d, {'H7C0C1': 'H7C0C1'})
