import io
import time
import logging
from django.test import TransactionTestCase
from django.test import Client
from django.db import models, connection
from django import urls
from pkg_resources import resource_filename as pkg_file
import json
import logging
from .models import GOnetSubmission
from gonet.exceptions import InputValidationError
import networkx as nx
import numpy as np
import pandas as pd
from . import cyjs

log = logging.getLogger(__name__)

sbmsn_param = {'submit': 'Submit', 'organism':'human',
               'namespace':'biological_process', 'bg_type':'all',
               'analysis_type':'enrich', 'output_type':'graph',
               'csv_separator':'\t', 'qvalue':0.05}

c = Client()
class GOnetEnrichmentTestCase(TransactionTestCase):

    def test_GO_enrichment_default(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist2.tsv'), 'r').read()
        req = dict(sbmsn_param, **{'paste_data':input_lines})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')

        self.assertIn('GO:0006334', set(sn.enrich_res_df.query('q<0.05')['term']))
        net_dict = json.loads(sn.network)
        G_case = cyjs.cyjs2nx(net_dict)

        # Test CSV response
        csv_resp = c.get(urls.reverse('GOnet-csv-res', args=(str(sn.id),)))
        b = io.StringIO(); b.write(csv_resp.content.decode()); b.seek(0)
        res = pd.read_csv(b, sep=',', index_col=0)
        self.assertEqual(res.index[0], 1)
        self.assertListEqual(list(res.columns), ['GO_term_ID', 'GO_term_def', 'P',
                                                 'P_FDR_adj', 'NofGenes', 'Genes'])
        res.set_index('GO_term_ID', inplace=True)
        self.assertEqual(res.index.name, 'GO_term_ID')
        self.assertIn('GO:0006334', set(res.index))
        self.assertEqual(res.loc['GO:2000520', 'Genes'], "CCR7|HAVCR2")

        # Test TXT response
        txt_resp = c.get(urls.reverse('GOnet-txt-res', args=(str(sn.id),)))
        b = io.StringIO()
        b.write(txt_resp.content.decode())
        b.seek(0)
        enrichterms = []
        for line in b:
            enrichterms.append(line.split()[0])
        self.assertIn('GO:0006334', set(enrichterms))

        # Test specific terms
        t_edge_name = 'GO:0006334 (interacts with) HIST2H2BC'
        e = list(filter(lambda e: e['data']['name']==t_edge_name,
                           net_dict['elements']['edges']))[0]
        self.assertDictEqual(e['data']['specific_terms'],
                             {'GO:0006334': {'refs': ['PMID:21873635'],
                             'specific_term_name': 'nucleosome assembly'}})
        # Test relation
        # "histone H3-K27 trimethylation" is_a "histone H3-K27 methylation"
        t_edge_name = 'GO:0070734 (interacts with) GO:0098532'
        e = list(filter(lambda e: e['data']['name']==t_edge_name,
                           net_dict['elements']['edges']))[0]
        self.assertEqual(e['data']['relation'], 'is_a')

        # Test node ABCB1
        n = list(filter(lambda n: n['data']['nodesymbol']=='ABCB1', net_dict['elements']['nodes']))[0]
        #self.assertAlmostEqual(n['data']['val'], 0.60217044443096)
        self.assertAlmostEqual(n['data']['expr:user_supplied'], 0.6021704444)
        self.assertEqual(n['data']['ensembl_id'], 'ENSG00000085563')

        # Test node GO:0098532 (histone H3-K27 trimethylation)
        n = list(filter(lambda n: n['data']['id']=='GO:0098532', net_dict['elements']['nodes']))[0]
        self.assertAlmostEqual(n['data']['P'], 8.57800000e-07)
        self.assertAlmostEqual(n['data']['Padj'], 0.0030845372)

        # Test resolved attribute
        n = list(filter(lambda e: e['data']['nodesymbol']=='LPPR2', net_dict['elements']['nodes']))[0]
        self.assertEqual(n['data']['uniprot_id'], 'Q96GM1')
        self.assertEqual(n['data']['ensembl_id'], 'ENSG00000105520')
        self.assertEqual(n['data']['desc'], 'Phospholipid phosphatase-related protein type 2')

        n = list(filter(lambda e: e['data']['nodesymbol']=='LTC4S', net_dict['elements']['nodes']))[0]
        self.assertEqual(n['data']['uniprot_id'], 'Q16873')
        self.assertEqual(n['data']['ensembl_id'], 'ENSG00000213316')

        #Check expression values (protein atlas)
        resp = c.get(urls.reverse('GOnet-get-expression',
                                  kwargs={'jobid':str(sn.id), 'celltype':'HPA-adipose tissue'}))
        expr_vals = json.loads(resp.content.decode())
        self.assertEqual(expr_vals['O14503'], 170.0)

        #Check expression values (DICE-DB)
        resp = c.get(urls.reverse('GOnet-get-expression',
                                  kwargs={'jobid':str(sn.id), 'celltype':'DICE-THSTAR'}))
        expr_vals = json.loads(resp.content.decode())
        self.assertAlmostEqual(expr_vals['P10721'], 9.893615)

        #Test id mapping response
        idmap_resp = c.get(urls.reverse('GOnet-input-idmap', args=(str(sn.id),)))
        b = io.StringIO(); b.write(idmap_resp.content.decode()); b.seek(0)
        res = pd.read_csv(b, sep='\t', index_col=0)
        self.assertEqual(res.loc['HIST1H2AM', 'Notes'], 'same as HIST1H2AG')

    def test_GO_enrichment_nothing_enriched(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist5.txt'), 'r').read()
        req = dict(sbmsn_param, **{'paste_data':input_lines})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')

        # Test CSV response
        csv_resp = c.get(urls.reverse('GOnet-csv-res', args=(str(sn.id),)))
        self.assertEqual(',GO_term_ID,GO_term_def,P,P_FDR_adj,NofGenes,Genes', csv_resp.content.decode().strip())

        # Test TXT response
        txt_resp = c.get(urls.reverse('GOnet-txt-res', args=(str(sn.id),)))
        self.assertContains(txt_resp, 'GO_term_def')

    def test_GO_enrichment_mouse_genes(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist7.txt'), 'r').read()
        req = dict(sbmsn_param, **{'paste_data':input_lines,
                                   'organism':'mouse'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')

        pval = sn.enrich_res_df.query('term=="GO:0006950"')['p'].values[0]
        self.assertAlmostEqual(pval, 2.27e-08)

        #Check expression values
        resp = c.get(urls.reverse('GOnet-get-expression',
                                  kwargs={'jobid':str(sn.id), 'celltype':'Bgee-spleen'}))
        expr_vals = json.loads(resp.content.decode())
        self.assertEqual(expr_vals['MGI:107654'], 2.560124)

        #Test id mapping response
        idmap_resp = c.get(urls.reverse('GOnet-input-idmap', args=(str(sn.id),)))
        b = io.StringIO(); b.write(idmap_resp.content.decode()); b.seek(0)
        res = pd.read_csv(b, sep='\t', index_col=0)
        self.assertEqual(res.loc['Ifngr2', 'Ensembl_ID'], 'ENSMUSG00000022965')
        self.assertEqual(res.loc['Calca', 'Uniprot_ID'], 'P70160')
        self.assertEqual(res.loc['Ifngr2', 'Description'], 'interferon gamma receptor 2')
        

    def test_GO_enrichment_qval01_celcomp(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist2.tsv'), 'r').read()
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'qvalue':0.01,
                                   'namespace':'cellular_component'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        net_dict = json.loads(sn.network)
        G = cyjs.cyjs2nx(net_dict)
        enriched = set(filter(lambda n: n.startswith('GO:'), G.nodes()))
        self.assertSetEqual(enriched, set(['GO:0000786', 'GO:0044815', 'GO:0032993',
                                           'GO:0000790', 'GO:0000785']))

class GOnetEnrichmentWBgTestCase(TransactionTestCase):
    def test_GO_enrichment_list3_qval0001_CD8bg(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist3.csv'), 'r').read()
        bg_file = open(pkg_file(__name__, 'data/tests/CD8_cells_background_TPM10.lst'), 'r')
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'bg_type':'custom',
                                   'bg_file':bg_file, 'qvalue':0.0001,
                                   'csv_separator':','})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')

        #check enriched terms
        enriched = set(sn.enrich_res_df.query('q<0.0001')['term'])
        self.assertIn('GO:0002376', enriched) # Immune system process
 
    def test_GO_enrichment_list3_predefined_BG(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist3.csv'), 'r').read()
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'bg_type': 'predef',
                                   'bg_cell' : 'DICE-any', 'qvalue':0.01,
                                   'csv_separator':','})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')

        #check enriched terms
        enriched = set(sn.enrich_res_df.query('q<0.01')['term'])
        self.assertIn('GO:0002376', enriched) # Immune system process

    def test_GO_enrichment_list3_HPA_bonemarrow_BG(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist3.csv'), 'r').read()
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'bg_type': 'predef',
                                   'bg_cell' : 'HPA-bone marrow', 'qvalue':0.01,
                                   'csv_separator':','})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')

        #check enriched terms
        enriched = set(sn.enrich_res_df.query('q<0.01')['term'])
        self.assertIn('GO:0002376', enriched)
        
    def test_GO_enrichment_list7_mouse_predefined_BG(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist7.txt'), 'r').read()
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'organism':'mouse',
                                   'bg_type': 'predef',
                                   'bg_cell' : 'Bgee-any', 'qvalue':0.01,
                                   'csv_separator':','})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        enriched = set(sn.enrich_res_df.query('q<0.01')['term'])
        self.assertIn('GO:0050789', enriched)

    def test_GO_enrichment_list7_mouse_fibroblast_BG(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist7.txt'), 'r').read()
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'organism':'mouse',
                                   'bg_type': 'predef',
                                   'bg_cell' : 'Bgee-fibroblast', 'qvalue':0.01,
                                   'csv_separator':','})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        enriched = set(sn.enrich_res_df.query('q<0.01')['term'])
        self.assertGreater(len(enriched), 0)
        
    def test_GO_enrich_genelist6_long(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist6.tsv'), 'r').read()
        bg_file = open(pkg_file(__name__, 'data/tests/DPOS_Mgate_Tcells_background_TPM1.lst'), 'r')
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'bg_type':'custom',
                                   'bg_file':bg_file, 'qvalue':0.0001})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        self.assertEqual(resp.status_code, 200)

class GeneNamesResolutionTest(TransactionTestCase):
    def test_resolution(self):
        # CMKBR7 is synonym of CCR7
        # Q9Y5X4 is PNR
        input_lines = '\n'.join(["PNR", "KIAA0457", "ELDF10", "CCR7", "AIM",
                                 "Q9Y5X4", "CMKBR7", "O14804", "P28068", "FOO"])
        req = dict(sbmsn_param, **{'paste_data':input_lines})
        URL = urls.reverse('GOnet-submit-form')
        resp = c.post(URL, req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        res_d = sn.parsed_data['submit_name'].to_dict()
        self.assertDictEqual(res_d, {'O75787': 'ELDF10', 'P32248': 'CCR7',
                                     'Q9NRI5': 'KIAA0457', 'Q9Y5X4': 'PNR',
                                     '_00000': 'Q9Y5X4', '_00001': 'CMKBR7',
                                     'O14804' :'O14804', 'P28068':'P28068',
                                     'P26358' : 'AIM', '_00002':'FOO'})
        self.assertEqual(sn.parsed_data.loc['_00000', 'duplicate_of'], 'Q9Y5X4')

        #Test id mapping response
        idmap_resp = c.get(urls.reverse('GOnet-input-idmap', args=(str(sn.id),)))
        b = io.StringIO(); b.write(idmap_resp.content.decode()); b.seek(0)
        res = pd.read_csv(b, sep='\t', index_col=0)
        self.assertEqual(res.loc['CMKBR7', 'Notes'], 'same as CCR7')
        self.assertEqual(res.loc['Q9Y5X4', 'Notes'], 'same as PNR')
        self.assertEqual(res.loc['AIM', 'Description'], 'DNA (cytosine-5)-methyltransferase 1')
        self.assertIn('ambiguous', res.loc['PNR', 'Notes'])
        self.assertIn('not recognized', res.loc['FOO', 'Notes'])

        #Test tricky Ensembl IDs
        self.assertEqual(res.loc['P28068', 'Ensembl_ID'], 'ENSG00000242574')

        # Check graph attributes
        G = cyjs.cyjs2nx(json.loads(sn.network))
        self.assertEqual(G.node['_00002']['data']['identified'], False)
        self.assertEqual(G.node['P32248']['data']['identified'], True)
        self.assertEqual(G.node['Q9Y5X4']['data']['ambiguous'], True)

    def test_resolution_accidental_space(self):
        
        input_lines = '\n'.join(["BLK", "GAS6", "CD1C ", "SEPT4"])
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'goslim_immunol'})
        URL = urls.reverse('GOnet-submit-form')
        resp = c.post(URL, req, follow=True)
        self.assertEqual(resp.status_code, 200)
        sn = GOnetSubmission.objects.latest('submit_time')
        idmap_resp = c.get(urls.reverse('GOnet-input-idmap', args=(str(sn.id),)))
        b = io.StringIO(); b.write(idmap_resp.content.decode()); b.seek(0)
        res = pd.read_csv(b, sep='\t', index_col=0)
        self.assertEqual(res.loc['CD1C', 'Uniprot_ID'], 'P29017')

    def test_resolution_mouse_Uniprot_IDs_wrong_species(self):
        genelist9 = pd.read_csv(pkg_file(__name__, 'data/tests/genelist9.tsv'), sep='\t')
        input_lines = '\n'.join(genelist9[genelist9.Uniprot_ID != 'None']['Uniprot_ID'])
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'goslim_immunol', 'output_type':'csv'})
        URL = urls.reverse('GOnet-submit-form')
        resp = c.post(URL, req, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'None of the genes submitted')

    def test_resolution_mouse_Uniprot_IDs(self):
        genelist9 = pd.read_csv(pkg_file(__name__, 'data/tests/genelist9.tsv'), sep='\t')
        genelist9 = genelist9[genelist9.Uniprot_ID != 'None']
        input_lines = '\n'.join(genelist9['Uniprot_ID'])
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'analysis_type':'annot',
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


class GOnetSimpleTestCase(TransactionTestCase):
    def test_submitting(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist1.lst'), 'r').read()
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'goslim_immunol',
                                   'job_name':'test job name'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'test job name')

    def test_empty_submission(self):
        input_lines = ''
        req = dict(sbmsn_param, **{'paste_data':input_lines})
        resp = c.get(urls.reverse('GOnet-submit-form'))
        self.assertEqual(resp.status_code, 200)
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertContains(resp, 'File with gene list should be uploaded')

    def test_custom_annot_no_input(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist1.lst'), 'r').read()
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'custom'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertContains(resp, 'Custom GO terms option specified')


    def test_wrong_separator(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist4.txt'), 'r').read()
        req = dict(sbmsn_param, **{'paste_data':input_lines})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'None of the genes submitted')
        self.assertContains(resp, 'IGLV3-27        1.204029972')

    def test_wrong_species(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist7.txt'), 'r').read()
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'goslim_immunol', 'organism':'human'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'None of the genes submitted')

    def test_maximum_entries_graph_output(self):
        
        input_lines = open(pkg_file(__name__, 'data/tests/genelist8.tsv'), 'r').read().split('\n')
        input_str = '\n'.join(input_lines[:5000])
        req = dict(sbmsn_param, **{'paste_data':input_str, 'analysis_type':'annot',
                                   'slim':'goslim_generic'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertContains(resp, 'incompatible with output type &quot;Graph&quot')

    def test_too_many_entries(self):
        input_str = '\n'.join(['ABC']*21000)
        req = dict(sbmsn_param, **{'paste_data':input_str, 'analysis_type':'annot',
                                   'slim':'goslim_generic'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertContains(resp, 'Maximum number of entries is 20000.')

    def test_one_line_entries(self):
        input_str = 'TAF13, AFP, ELMO2, PITX3, FSHB, KCNJ6'
        req = dict(sbmsn_param, **{'paste_data':input_str, 'csv_separator':','})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertContains(resp, 'Multiple separators detected')
        
class GOnetAnnotTestCase(TransactionTestCase):
    def test_GO_annotate_genelist1(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist1.lst'), 'r').read()
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'goslim_immunol'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        net_dict = json.loads(sn.network)
        G = cyjs.cyjs2nx(net_dict)
        self.assertTrue(G.has_edge('GO:0042254', 'Q9HC36'))

    def test_genename_resolution(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist6.tsv'), 'r').read()
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'goslim_immunol'})

        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        self.assertEqual(sn.parsed_data.loc['P61160', 'submit_name'], 'ACTR2')

    def test_GO_annotate_genelist2(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist2.tsv'), 'r').read()
        input_data_df = pd.read_csv(pkg_file(__name__, 'data/tests/genelist2.tsv'), sep='\t', header=None)
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'goslim_immunol'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertEqual(resp.status_code, 200)
        sn = GOnetSubmission.objects.latest('submit_time')
        G = cyjs.cyjs2nx(json.loads(sn.network))
        self.assertTrue(G.has_edge('GO:0007165', 'P29376'))

        # Test recognition of user-supplied contrast values
        gene_nodes = filter(lambda n: not n['data']['name'].startswith('GO:'),
                            json.loads(sn.network)['elements']['nodes'])
        gene_nodes = list(gene_nodes)
        self.assertEqual(len(list(filter(lambda node: float(node['data']['expr:user_supplied'])>0,   gene_nodes))), \
                         np.sum(input_data_df[1]>0) - 1 ) #-1 for HIST1H2AM
        self.assertEqual(len(list(filter(lambda node: float(node['data']['expr:user_supplied'])<0, gene_nodes))), \
                         np.sum(input_data_df[1]<0))

        #Test CSV response
        csv_resp = c.get(urls.reverse('GOnet-csv-res', args=(str(sn.id), )))
        res = io.StringIO(); res.write(csv_resp.content.decode()); res.seek(0)
        res_df = pd.read_csv(res, sep=',', index_col=0)
        self.assertIn('GO:0007165', set(res_df['GO_term_ID']))
        self.assertEqual(res_df.index[0], 1)

        #Test TXT response
        txt_resp = c.get(urls.reverse('GOnet-txt-res', args=(str(sn.id), )))
        res = io.StringIO(); res.write(txt_resp.content.decode()); res.seek(0)
        goterms=set()
        for line in res:
            goterms.add(line.split()[0])
        self.assertIn('GO:0007165', goterms)

    def test_GO_annot_mouse_genes(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist7.txt'), 'r').read()
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'goslim_generic', 'organism':'mouse'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        net_dict = json.loads(sn.network)
        G = cyjs.cyjs2nx(net_dict)
        self.assertIn('GO:0006950', G.predecessors('MGI:1351618'))
        self.assertEqual(len(G.node['GO:0048856']['data']['xgenes']), 35)
        self.assertEqual(G.node['MGI:1351618']['data']['ensembl_id'], 'ENSMUSG00000014905')
        self.assertEqual(G.node['MGI:1351618']['data']['uniprot_id'], 'Q9QYI6')
        self.assertEqual(G.node['MGI:1351618']['data']['mgi_id'], 'MGI:1351618')
        self.assertEqual(G.node['MGI:1351618']['data']['desc'],
                         'DnaJ heat shock protein family (Hsp40) member B9')

    def test_GO_annot_goslim_generic(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist2.tsv'), 'r').read()
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'goslim_generic', 'namespace':'cellular_component'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        G = cyjs.cyjs2nx(json.loads(sn.network))
        self.assertTrue(G.has_edge('GO:0005886', 'P32248')) # CCR7 in plasma membrane
        
    def test_GO_annotate_genelist8_large(self):
        
        input_lines = open(pkg_file(__name__, 'data/tests/genelist8.tsv'), 'r').read().split('\n')
        input_str = '\n'.join(input_lines[:2500])
        req = dict(sbmsn_param, **{'paste_data':input_str, 'analysis_type':'annot',
                                   'slim':'goslim_generic'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        G = cyjs.cyjs2nx(json.loads(sn.network))
        self.assertEqual(G.node['Q8TCT6']['data']['nodesymbol'], 'SPPL3')

        #Check expression values (DICE-DB)
        resp = c.get(urls.reverse('GOnet-get-expression',
                                  kwargs={'jobid':str(sn.id), 'celltype':'DICE-CD4STIM'}))
        expr_vals = json.loads(resp.content.decode())
        self.assertAlmostEqual(expr_vals['A1XBS5'], 0.09010716525639434)

        # Test TXT response
        txt_resp = c.get(urls.reverse('GOnet-txt-res', args=(str(sn.id),)))
        b = io.StringIO()
        b.write(txt_resp.content.decode())
        b.seek(0)

        # Test CSV response
        csv_resp = c.get(urls.reverse('GOnet-csv-res', args=(str(sn.id),)))
        b = io.StringIO(); b.write(csv_resp.content.decode()); b.seek(0)
        res = pd.read_csv(b, sep=',', index_col=0)

class GOnetAnnotCustomAnnotationTestCase(TransactionTestCase):
    def test_GO_annotate_genelist2(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist2.tsv'), 'r').read()
        custom_annotation = open(pkg_file(__name__, 'data/tests/custom_annotation.txt'), 'r').read()
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'custom', 'custom_terms':custom_annotation})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertEqual(resp.status_code, 200)

        sn = GOnetSubmission.objects.latest('submit_time')
        net_dict = json.loads(sn.network)
        G = cyjs.cyjs2nx(net_dict)
        self.assertListEqual(list(G.predecessors('P29376')), ['GO:0071300'])
        self.assertListEqual(list(G.predecessors('Q5TBA9')), ['GO:0016043'])
        self.assertListEqual(list(G.predecessors('P16403')), ['GO:0065003'])

    # annotated vs terms enriched in genelist2.
    # graph should be consistent with enrichment results
    def test_GO_annotate_genelist2_vs_enriched(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist2.tsv'), 'r').read()
        req = dict(sbmsn_param, **{'paste_data':input_lines})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        
        enrich_job = GOnetSubmission.objects.latest('submit_time')
        df = enrich_job.enrich_res_df
        enriched_terms = df[df['q']<enrich_job.qvalue]['term']
        custom_annotation = '\n'.join(enriched_terms)
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'custom', 'custom_terms':custom_annotation})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        annot_job = GOnetSubmission.objects.latest('submit_time')
        
        G_enrich = cyjs.cyjs2nx(json.loads(enrich_job.network))
        G_annot = cyjs.cyjs2nx(json.loads(annot_job.network))

        self.assertSetEqual(set(G_enrich.nodes), set(G_annot.nodes))
        self.assertSetEqual(set(G_enrich.edges), set(G_annot.edges))
        
    def test_GO_annotate_invalid_term(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist2.tsv'), 'r').read()
        custom_annotation = open(pkg_file(__name__, 'data/tests/custom_annotation.txt'), 'r').read()
        custom_annotation += 'GO:1234567'
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'custom', 'custom_terms':custom_annotation})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertContains(resp, 'Some of the custom terms provided were not found')
        self.assertContains(resp, 'GO:1234567')

    def test_GO_annotate_goslim_generic_plus_root(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist2.tsv'), 'r').read()
        custom_annotation = open(pkg_file(__name__, 'data/tests/custom_annotation.txt'), 'r').read()
        custom_annotation += 'GO:1234567'
        req = dict(sbmsn_param, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'custom', 'custom_terms':custom_annotation})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertContains(resp, 'Some of the custom terms provided were not found')
        self.assertContains(resp, 'GO:1234567')
        
