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
class DefaultTestCase(TransactionTestCase):

    def test_GO_enrichment_default(self):
        input_lines = open(pkg_file(__name__, 'data/genelist2.tsv'), 'r').read()
        req = dict(job_req, **{'paste_data':input_lines})
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
        t_edge_name = 'GO:0006334 (interacts with) HIST1H2BC'
        e = list(filter(lambda e: e['data']['name']==t_edge_name,
                           net_dict['elements']['edges']))[0]
        self.assertDictEqual(e['data']['specific_terms'],
                             {'GO:0006334': {'refs': ['PMID:422550', 'PMID:9119399'],
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
        self.assertLess(n['data']['P'], 8.0e-07)
        # Should be rather significant
        self.assertLess(n['data']['Padj'], 0.01)
        self.assertEqual(n['data']['tot_gn'], 6)

        # Test resolved attribute
        n = list(filter(lambda e: e['data']['nodesymbol']=='LPPR2', net_dict['elements']['nodes']))[0]
        self.assertEqual(n['data']['uniprot_id'], 'Q96GM1')
        self.assertEqual(n['data']['ensembl_id'], 'ENSG00000105520')
        self.assertEqual(n['data']['desc'], 'Phospholipid phosphatase-related protein type 2')
        self.assertEqual(n['data']['primname'], 'PLPPR2')

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
                                  kwargs={'jobid':str(sn.id), 'celltype':'DICE-Th1Th17'}))
        expr_vals = json.loads(resp.content.decode())
        self.assertAlmostEqual(expr_vals['P10721'], 9.893615)

        #Test id mapping response
        idmap_resp = c.get(urls.reverse('GOnet-input-idmap', args=(str(sn.id),)))
        b = io.StringIO(); b.write(idmap_resp.content.decode()); b.seek(0)
        res = pd.read_csv(b, sep='\t', index_col=0)
        self.assertEqual(res.loc['HIST1H2AM', 'Notes'], 'same as HIST1H2AG')
        self.assertEqual(res.loc['LPPR2', 'Preferred_name'], 'PLPPR2')

    def test_uploading_file(self):
        with open(pkg_file(__name__, 'data/genelist2.tsv'), 'r') as fh:
            req = dict(job_req, **{'uploaded_file':fh})
            resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
            sn = GOnetSubmission.objects.latest('submit_time')
            self.assertIn('GO:0006334', set(sn.enrich_res_df.query('q<0.05')['term']))

    def test_GO_enrichment_nothing_enriched(self):
        input_lines = open(pkg_file(__name__, 'data/genelist5.txt'), 'r').read()
        req = dict(job_req, **{'paste_data':input_lines})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')

        # Test CSV response
        csv_resp = c.get(urls.reverse('GOnet-csv-res', args=(str(sn.id),)))
        self.assertEqual(',GO_term_ID,GO_term_def,P,P_FDR_adj,NofGenes,Genes', csv_resp.content.decode().strip())

        # Test TXT response
        txt_resp = c.get(urls.reverse('GOnet-txt-res', args=(str(sn.id),)))
        self.assertContains(txt_resp, 'GO_term_def')

    def test_GO_enrichment_mouse_genes(self):
        input_lines = open(pkg_file(__name__, 'data/genelist7.txt'), 'r').read()
        req = dict(job_req, **{'paste_data':input_lines,
                                   'organism':'mouse'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')

        pval = sn.enrich_res_df.query('term=="GO:0006950"')['p'].values[0]
        # was 1.109e-07
        self.assertLess(pval, 1e-06)

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
        input_lines = open(pkg_file(__name__, 'data/genelist2.tsv'), 'r').read()
        req = dict(job_req, **{'paste_data':input_lines, 'qvalue':0.01,
                                   'namespace':'cellular_component'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        net_dict = json.loads(sn.network)
        G = cyjs.cyjs2nx(net_dict)
        enriched = set(filter(lambda n: n.startswith('GO:'), G.nodes()))
        for term in ['GO:0000786', 'GO:0044815', 'GO:0032993', 'GO:0000785']:
            self.assertIn(term, enriched)

    def test_genelist12(self):
        input_lines = open(pkg_file(__name__, 'data/genelist12.lst'), 'r').read()
        req = dict(job_req, **{'paste_data':input_lines})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        self.assertGreater(sn.enrich_res_df.shape[0], 1)
