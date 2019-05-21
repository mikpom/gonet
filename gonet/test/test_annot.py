import io
from django.test import TransactionTestCase
from django.test import Client
from django import urls
from pkg_resources import resource_filename as pkg_file
import json
from ..models import GOnetSubmission
from ..ontol import O
import numpy as np
import pandas as pd
from gonet import cyjs
from . import job_req

c = Client()
class GOnetAnnotTestCase(TransactionTestCase):
    def test_GO_annotate_genelist1(self):
        input_lines = open(pkg_file(__name__, 'data/genelist1.lst'), 'r').read()
        req = dict(job_req, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'goslim_immunol'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        net_dict = json.loads(sn.network)
        G = cyjs.cyjs2nx(net_dict)
        self.assertTrue(G.has_edge('GO:0042254', 'Q9HC36'))

    def test_genename_resolution(self):
        input_lines = open(pkg_file(__name__, 'data/genelist6.tsv'), 'r').read()
        req = dict(job_req, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'goslim_immunol'})

        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        self.assertEqual(sn.parsed_data.loc['P61160', 'submit_name'], 'ACTR2')

    def test_GO_annotate_genelist2(self):
        input_lines = open(pkg_file(__name__, 'data/genelist2.tsv'), 'r').read()
        input_data_df = pd.read_csv(pkg_file(__name__, 'data/genelist2.tsv'), sep='\t', header=None)
        req = dict(job_req, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'goslim_immunol'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertEqual(resp.status_code, 200)
        sn = GOnetSubmission.objects.latest('submit_time')
        net = json.loads(sn.network)
        G = cyjs.cyjs2nx(net)
        self.assertTrue(G.has_edge('GO:0007165', 'P29376'))

        # Test recognition of user-supplied contrast values
        gene_nodes = filter(lambda n: not n['data']['name'].startswith('GO:'),
                            net['elements']['nodes'])
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
        input_lines = open(pkg_file(__name__, 'data/genelist7.txt'), 'r').read()
        req = dict(job_req, **{'paste_data':input_lines, 'analysis_type':'annot',
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
        input_lines = open(pkg_file(__name__, 'data/genelist2.tsv'), 'r').read()
        req = dict(job_req, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'goslim_generic', 'namespace':'cellular_component'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        G = cyjs.cyjs2nx(json.loads(sn.network))
        self.assertTrue(G.has_edge('GO:0005886', 'P32248')) # CCR7 in plasma membrane

        self.assertEqual(len(G.node['O60282']['data']['slimterms']), 6)

        ids = list(filter(lambda n: G.node[n]['data']['nodesymbol']=='ZNF761', G.nodes()))
        self.assertEqual(len(ids), 1)
        znf_node = G.node[ids[0]]
        self.assertEqual(znf_node['data']['slimterms'], [])
        
    def test_GO_annotate_genelist8_large(self):
        
        input_lines = open(pkg_file(__name__, 'data/genelist8.tsv'), 'r').read().split('\n')
        input_str = '\n'.join(input_lines[:2500])
        req = dict(job_req, **{'paste_data':input_str, 'analysis_type':'annot',
                                   'slim':'goslim_generic'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sn = GOnetSubmission.objects.latest('submit_time')
        G = cyjs.cyjs2nx(json.loads(sn.network))
        self.assertEqual(G.node['Q8TCT6']['data']['nodesymbol'], 'SPPL3')

        #Check expression values (DICE-DB)
        resp = c.get(urls.reverse('GOnet-get-expression',
                                  kwargs={'jobid':str(sn.id), 'celltype':'DICE-CD4 T cell (stim)'}))
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
    # TODO: custom annotation and namespace relation
    def test_GO_annotate_genelist2(self):
        input_lines = open(pkg_file(__name__, 'data/genelist2.tsv'), 'r').read()
        custom_annotation = open(pkg_file(__name__, 'data/custom_annotation.txt'), 'r').read()
        req = dict(job_req, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'custom', 'custom_terms':custom_annotation})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertEqual(resp.status_code, 200)

        sn = GOnetSubmission.objects.latest('submit_time')
        net_dict = json.loads(sn.network)
        G = cyjs.cyjs2nx(net_dict)
        self.assertListEqual(list(G.predecessors('P29376')), ['GO:0071300'])
        self.assertListEqual(list(G.predecessors('Q5TBA9')), ['GO:0008150'])
        self.assertListEqual(list(G.predecessors('P16403')), ['GO:0065003'])

        # Test node GO:0071300 (cellular response to retinoic acid)
        n = list(filter(lambda n: n['data']['id']=='GO:0071300', net_dict['elements']['nodes']))[0]
        self.assertEqual(n['data']['tot_gn'], len(O.get_attr('GO:0071300', 'human')))
        
        # Test CSV response
        csv_resp = c.get(urls.reverse('GOnet-csv-res', args=(str(sn.id),)))
        b = io.StringIO(); b.write(csv_resp.content.decode()); b.seek(0)
        res = pd.read_csv(b, sep=',', index_col=1)
        self.assertIn('LTK', res.loc['GO:0032526', 'Genes'])
        
        # Test TXT response
        txt_resp = c.get(urls.reverse('GOnet-txt-res', args=(str(sn.id),)))
        b = io.StringIO()
        b.write(txt_resp.content.decode())
        b.seek(0)
        line_found = False
        for line in b:
            if line.strip().startswith('GO:0032526'):
                self.assertIn('LTK', line)
                line_found = True
                break
        self.assertTrue(line_found)

    # annotated vs terms enriched in genelist2.
    # graph should be consistent with enrichment results
    def test_GO_annotate_genelist2_vs_enriched(self):
        input_lines = open(pkg_file(__name__, 'data/genelist2.tsv'), 'r').read()
        req = dict(job_req, **{'paste_data':input_lines})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        
        enrich_job = GOnetSubmission.objects.latest('submit_time')
        df = enrich_job.enrich_res_df
        enriched_terms = df[df['q']<enrich_job.qvalue]['term']
        custom_annotation = '\n'.join(enriched_terms)
        req = dict(job_req, **{'paste_data':input_lines, 'analysis_type':'annot',
                                   'slim':'custom', 'custom_terms':custom_annotation})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        annot_job = GOnetSubmission.objects.latest('submit_time')
        
        G_enrich = cyjs.cyjs2nx(json.loads(enrich_job.network))
        G_annot = cyjs.cyjs2nx(json.loads(annot_job.network))

        self.assertSetEqual(set(G_enrich.nodes), set(G_annot.nodes))
        self.assertSetEqual(set(G_enrich.edges), set(G_annot.edges))
        
    def test_GO_annotate_invalid_term(self):
        input_lines = open(pkg_file(__name__, 'data/genelist2.tsv'), 'r').read()
        custom_annotation = open(pkg_file(__name__, 'data/custom_annotation.txt'), 'r').read()
        custom_annotation += 'GO:1234567'
        req = dict(job_req, **{'paste_data':input_lines, 'analysis_type':'annot',
                               'slim':'custom', 'custom_terms':custom_annotation})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        self.assertContains(resp, 'Some of the custom terms provided were not found')
        self.assertContains(resp, 'GO:1234567')

