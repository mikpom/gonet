from django.test import TransactionTestCase
from django import urls
from django.test import Client
from pkg_resources import resource_filename as pkg_file
from threading import Thread
import random
import logging
from time import sleep
from GOnet.models import process_signature
from GOnet import ontol
from .models import GOnetSubmission

log = logging.getLogger(__name__)


sbmsn_param = {'submit': 'Submit', 'organism':'human',
               'namespace':'biological_process', 'analysis_type':'enrich',
               'output_type':'graph', 'csv_separator':'\t', 'qvalue':0.05}

c = Client()

class GOnetStressTestCase(TransactionTestCase):
    def test_submission_with_bg(self):
        input_lines = open(pkg_file('GOnet', 'data/tests/genelist3.csv'), 'r').read()
        bg_file = open(pkg_file('GOnet', 'data/tests/CD8_cells_background_TPM10.lst'), 'r')
        request_data = {'submit': ['Submit'], 'paste_data': [input_lines],
                        'bg_file':[bg_file],
                        'namespace':['biological_process'], 'analysis_type':['enrich'],
                        'output_type':['graph'], 'csv_separator':[','], 'qvalue':[0.0001]}
        threads = []
        seen = set()
        for n in range(200):
            bg_file.seek(0)
            t = Thread(target=c.post, args=(urls.reverse('GOnet-submit-form'), request_data))
            t.daemon = True
            t.start()
            threads.append(t)
            sleep(random.random()*10)
            print('>!< Spamming task', len(threads))
            print('new vars', set(vars().keys()).difference(seen))
            seen = set(vars().keys())
        for t in threads:
            t.join()
        print('deleting threads')
        del threads
        print('sleeping......................................')
        sleep(100000000)

        
            
    def test_submission_default(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist6.tsv'), 'r').read()
        request_data = {'submit': ['Submit'], 'paste_data': [input_lines],
                        'namespace':['biological_process'], 'analysis_type':['enrich'],
                        'output_type':['graph'], 'csv_separator':['\t'], 'qvalue':[0.05]}
        threads = []
        for n in range(200):
            t = Thread(target=c.post, args=(urls.reverse('GOnet-submit-form'), request_data))
            t.daemon = True
            t.start()
            threads.append(t)
            sleep(random.random()*10)
            print('>!< Spamming task', len(threads))
        for t in threads:
            t.join()
            
        del threads
        print('sleeping......................................')
        sleep(100000000)

            
    def test_threading(self):
        def dotask(t):
            s = ontol.f.signature(args=(t,))
            r = process_signature(s)
            print(r+' is done')
        
        t = Thread(target=dotask, args=('T1',))
        t.daemon = True
        t.start()
#        t.join()

        t = Thread(target=dotask, args=('T1',))
        t.daemon = True
        t.start()
        t.join()
        
    def test_large_submission(self):
        input_lines = open(pkg_file(__name__, 'data/tests/genelist8.tsv'), 'r').read()
        _lines = '\n'.join(input_lines.split('\n')[:])
        
        req = dict(sbmsn_param, **{'paste_data':_lines,
                                   'analysis_type':'annot',
                                   'output_type':'csv',
                                   'slim':'goslim_immunol'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sO = GOnetSubmission.objects.latest('submit_time')
        print(sO.parsed_data)

    def test_GO_annotate_genelist8_large(self):
        
        input_lines = open(pkg_file(__name__, 'data/tests/genelist8.tsv'), 'r').read().split('\n')
        input_str = '\n'.join(input_lines[:3000])
        req = dict(sbmsn_param, **{'paste_data':input_str, 'analysis_type':'annot',
                                   'slim':'goslim_generic'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sO = GOnetSubmission.objects.latest('submit_time')


    def test_GO_annotate_genelist8_csv(self):
        
        input_lines = open(pkg_file(__name__, 'data/tests/genelist8.tsv'), 'r').read().split('\n')
        input_str = '\n'.join(input_lines)
        req = dict(sbmsn_param, **{'paste_data':input_str, 'analysis_type':'annot',
                                   'slim':'goslim_generic', 'output_type':'csv'})
        resp = c.post(urls.reverse('GOnet-submit-form'), req, follow=True)
        sO = GOnetSubmission.objects.latest('submit_time')
        
