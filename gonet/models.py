import os
import uuid
import io
import time
import logging
import json
import networkx as nx
from django.db import models
from django.utils import timezone
import pandas as pd
pd.set_option('display.width', 240)
from gonet.exceptions import DataNotProvidedError, InputValidationError
from gonet.fields import DataFrameField
from .ontol import O, hpa_data, dice_data, bgee_data, \
    prepare_enrich_res_txt as enrich_txt, \
    prepare_annot_res_txt as annot_txt, \
    prepare_enrich_res_csv as enrich_csv, \
    prepare_annot_res_csv as annot_csv
from . import ontol, graph
from gonet.utils import thread_func, process_signature

log = logging.getLogger(__name__)

def _pprint_successors(ret, format_func, G, node, indent=1):
    for s in G.successors(node):
        ret.append(format_func(s, indent))
        _pprint_successors(ret, format_func, G, s, indent=indent+1)


class GOnetJobStatus(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rdy = models.BooleanField(default=True)
    err = models.CharField(max_length=1000, default='')

class GOnetSubmission(models.Model):
    sep_choices = (('\t', '{tab}'), (',', '{,}'), ('\s+', 'Any whitespace'))
    organism_choices = (('human', 'Human'), ('mouse', 'Mouse'))
    analysis_choices = (('enrich', 'GO term enrichment'), ('annot', 'GO term annotation'))
    output_choices = (('graph', 'Interactive Graph'), ('txt', 'Hierarchical TXT'), ('csv', 'CSV'))
    slim_choices = (('goslim_generic', 'Generic GO slim'), ('goslim_immunol', 'GO slim for immunology'),
                    ('custom', 'Custom GO terms'))
    namespace_choices = (('biological_process', 'biological_process'),
                         ('molecular_function', 'molecular_function'),
                         ('cellular_component', 'cellular_component'))
    qval_choices = ((0.05, '* ('+chr(8804)+' 0.05)'),
                    (0.01, '** ('+chr(8804)+' 0.01)'),
                    (0.001, '*** ('+chr(8804)+' 0.001)'),
                    (0.0001, '**** ('+chr(8804)+' 0.0001)'))
    bg_choices = (('DICE-any', 'Any DICE-DB celltype'),) \
                 + (('HPA-any', 'Any HPA celltype'),) \
                 + tuple(ontol.celltype_choices['human'].items()) \
                 + (('Bgee-any', 'Any Bgee celltype'),) \
                 + tuple(ontol.celltype_choices['mouse'].items())
    bgtype_choices = (('all', 'all annotated genes'),
                      ('custom', 'custom gene list'),
                      ('predef', 'predefined backgrounds'))


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submit_time = models.DateTimeField('Submission time', default=timezone.localtime)
    uploaded_file = models.FileField(upload_to=os.path.join('csv/'), default='', blank=True)
    file_uploaded = models.BooleanField(default=True)
    paste_data = models.TextField(default='', blank=True)
    parsed_data = DataFrameField()
    cli_addr = models.CharField(max_length = 20, default = '0.0.0.0')
    csv_separator = models.CharField(max_length=10, default='comma', choices=sep_choices)
    job_name = models.CharField(max_length=40, default='', blank=True)
    organism = models.CharField(max_length=10, default='human', choices=organism_choices)
    qvalue = models.FloatField(default=0.05)
    network = models.TextField(default='{}', blank=True)
    namespace = models.CharField(max_length=20, default='biological_process',
                                 choices=namespace_choices, blank=True)
    analysis_type = models.CharField(max_length=12, default='enrich', choices=analysis_choices)
    output_type = models.CharField(max_length=12, default='graph', choices=output_choices)
    slim = models.CharField(max_length=20, default='goslim_generic', choices=slim_choices, blank=True)
    bg_type = models.CharField(max_length=20, default='all', choices=bgtype_choices, blank=True)
    bg_file = models.FileField(upload_to=os.path.join('csv/'), default='', blank=True)
    bg_genes = DataFrameField(default='', blank=True)
    bg_cell = models.CharField(max_length=20, default='DICE-any', choices=bg_choices, blank=True)
    custom_terms = models.TextField(default='', blank=True)
    parsed_custom_terms = DataFrameField(default='', blank=True)
    enrich_res_df = DataFrameField(default='')
    res_txt = models.TextField(default='', blank=True)
    res_csv = models.TextField(default='', blank=True)
    
    def __repr__(self):
        return '<Submission on ' + str(timezone.localtime(self.submit_time)) + \
               ' from ' + str(self.cli_addr) + '>'

    @classmethod
    def create(cls, cln_data, genelist_file=None, bg_file=None, cli='127.0.0.1'):
        if bg_file:
            if len(bg_file.read()) == 0:
                raise DataNotProvidedError('Background file provided is empty')
            bg_file.seek(0)
        submsn = cls(job_name=cln_data['job_name'], organism=cln_data['organism'],
                     paste_data=cln_data['paste_data'], namespace=cln_data['namespace'],
                     analysis_type=cln_data['analysis_type'], output_type=cln_data['output_type'],
                     slim=cln_data['slim'], csv_separator=cln_data['csv_separator'],
                     uploaded_file=genelist_file, bg_type=cln_data['bg_type'],bg_file=bg_file,
                     bg_cell=cln_data['bg_cell'], custom_terms=cln_data['custom_terms'],
                     qvalue=cln_data['qvalue'], cli_addr=cli)
        if ((not submsn.uploaded_file) and (submsn.paste_data=='')):
            raise DataNotProvidedError('File with gene list should be uploaded ' \
                                        + 'or text with data pasted in the corresponding section\n')
        if ((submsn.analysis_type=="annot") and \
            (submsn.slim=="custom") and (submsn.custom_terms=='')):
                        raise DataNotProvidedError('Custom GO terms option specified ' \
                                        + 'but corresponding text field is empty\n')
        elif (submsn.uploaded_file):
            submsn.file_uploaded = True
        elif (submsn.paste_data != ''):
            submsn.file_uploaded = False
        submsn.save()
        return submsn

    @thread_func
    def run_pre_analysis(self):
        jobid=str(self.id)
        log.info('Starting pre analysis...', extra={'jobid':jobid})
        job_status = GOnetJobStatus.objects.get(pk=self.id)
        colnames = ['submit_name', 'val']
        if (self.file_uploaded):
            stream = self.uploaded_file
        else:
            stream = io.StringIO(self.paste_data)

        # Check for multiple separators
        ln = stream.readline()
        if len(ln.split(self.csv_separator))>2:
            log.info('Got multiple separators on the first line. ',
                     extra={'jobid':jobid})
            job_status.err += ';too_many_seps'
            job_status.rdy = True
            job_status.save()
            return

        stream.seek(0)
        # Read using Pandas
        self.parsed_data = pd.read_csv(stream, sep=self.csv_separator, names=colnames)
        
        if (len(self.parsed_data)>20000):
            job_status.err += ';too_many_entries'
            log.info('Too many entries. Got '\
                     +str(len(self.parsed_data)), extra={'jobid':jobid})
            job_status.rdy = True
            job_status.save()
            return
        elif (len(self.parsed_data)>3000) and (self.output_type=='graph'):
            job_status.err += 'too_many_entries_for_graph'
            log.info('Too many entries for graph output. Got '\
                     +str(len(self.parsed_data)), extra={'jobid':jobid})
            job_status.rdy = True
            job_status.save()
            return
        self.parsed_data['submit_name'] = self.parsed_data['submit_name'].str.strip()
        self.parsed_data.fillna({'FC':0.0}, inplace=True)
        s = ontol.resolve_genenames_df.signature(args=(self.parsed_data.to_json(), self.organism),
                                                 kwargs={'jobid':jobid})
        r = process_signature(s)
        parsed_data = pd.read_json(r, dtype=ontol._dtypes)
        self.parsed_data = parsed_data
        #print('from run_pre_analysis', type(parsed_data.loc['Q16873', 'mgi_id']))
        if self.parsed_data['identified'].sum() == 0.0:
            job_status.err += 'genes_not_recognized'
            self.save()
            job_status.rdy = True
            log.info('W: None of the genes submitted identified', extra={'jobid':jobid})
            job_status.save()
            return

        if self.bg_file:
            if not self.bg_type == 'custom':
                log.warn('W: Background file submitted but bg_type is '\
                         +str(self.bg_type)+'. Proceeding as if bg_type was custom.',
                         extra={'jobid':jobid})

            
            if self.analysis_type == 'enrich':
                self.bg_genes = pd.read_csv(self.bg_file,
                                   names=colnames)
                s = ontol.resolve_genenames_df.signature(args=(self.bg_genes.to_json(),
                                                         self.organism), kwargs={'jobid':jobid})
                bg_genes = pd.read_json(process_signature(s))
                self.bg_genes = bg_genes
                if self.bg_genes['identified'].sum() == 0.0:
                    job_status.err += 'genes_not_recognized'
                    self.save()
                    job_status.rdy = True
                    job_status.save()
                    log.info('None of the genes in background file identified',
                             extra={'jobid':jobid})
                    return
            else:
                log.warn('W: Background file submitted but analysis type is not "enrich"'\
                         +' so skipping background file parsing.')
        if self.slim=='custom':
            if self.analysis_type == 'annot':
                self.parsed_custom_terms = pd.read_csv(io.StringIO(self.custom_terms),
                                                       names=['termid'])
                invalid_term = []
                for t in self.parsed_custom_terms.itertuples():
                    if not O.has_term(t.termid):
                        invalid_term.append(True)
                    else:
                        invalid_term.append(False)
                self.parsed_custom_terms['invalid'] = invalid_term
                if sum(invalid_term)>0:
                    self.save()
                    job_status.err += 'invalid_GO_terms'
                    log.info('Invalid custom GO terms encountered', extra={'jobid':jobid})
                    job_status.rdy = True
                    job_status.save()
                    return
            else:
                log.warn('W: Custom GO terms submitted but analysis type is not "annot"'\
                         +' so proceeding without custom terms parsing.')    
        log.info('pre_analysis done', extra={'jobid':jobid})
        #print('from run_pre_analysis', type(self.parsed_data.loc['Q16873', 'mgi_id']))
        self.run_analysis()

    @thread_func
    def run_analysis(self):
        jobid=str(self.id)
        log.info('Starting run_analysis...', extra={'jobid':jobid})
        if self.analysis_type=='enrich':
            args = (list(self.parsed_data.index), self.namespace,
                    self.organism, self.bg_type)
            if self.bg_type == 'all':
                kwargs = {}
            elif self.bg_type == 'custom':
                kwargs = {'bg_genes':
                          list(self.bg_genes.index.union(self.parsed_data.index)),
                          'bg_id' : jobid}
            elif self.bg_type == 'predef':
                kwargs = {'bg_genes':self.bg_cell, 'bg_id' : jobid}
            kwargs.update({'jobid':jobid})
            s = ontol.compute_enrichment.signature(args=args, kwargs=kwargs)
            self.enrich_res_df = pd.read_json(process_signature(s))\
                                   .dropna().query('p<0.1')
            if (self.output_type=="txt"):
                self.get_enrich_res_txt()
            elif (self.output_type=="csv"):
                self.get_enrich_res_csv()
            elif (self.output_type == "graph"):
                #print('from run_analysis', type(self.parsed_data.loc['Q16873', 'mgi_id']))
                args = (self.enrich_res_df.to_json(), self.qvalue,
                        self.parsed_data.to_json(), self.namespace, self.organism)
                s = graph.build_enrich_GOnet.signature(args=args, kwargs={'jobid':jobid})
                self.network = process_signature(s)
        elif self.analysis_type=='annot':
            if self.slim == 'custom':
                slim = list(self.parsed_custom_terms['termid'])
            else:
                slim = self.slim
            if (self.output_type=="txt"):
                self.get_annot_res_txt()
            elif (self.output_type=="csv"):
                self.get_annot_res_csv()
            elif (self.output_type=="graph"):
                s = graph.build_slim_GOnet.signature(args=(self.parsed_data.to_json(),
                                                           slim, self.namespace, self.organism),
                                                     kwargs={'jobid':jobid})
                self.network = process_signature(s)
        self.save()
        job_status = GOnetJobStatus.objects.get(pk=self.id)
        job_status.rdy = True
        job_status.save()
        log.info('run_analysis done', extra={'jobid':jobid})

    def get_id_map(self):
        s = ontol.prepare_id_map_txt.signature(args=(self.parsed_data.to_json(),),
                                               kwargs={'sp':self.organism,
                                                       'jobid':str(self.id)})
        r = process_signature(s)
        return r        

    def get_expr_json(self, celltype):
        if celltype.startswith('DICE-'):
            _cltype = celltype[5:]
            df = dice_data
        elif celltype.startswith('HPA-'):
            _cltype = celltype[4:]
            df = hpa_data
        elif celltype.startswith('Bgee-'):
            _cltype = celltype[5:]
            df = bgee_data
        id2ensembl = self.parsed_data['ensembl_id'].to_dict()
        valid_ids = set(id2ensembl.values()).intersection(df.index)
        if len(valid_ids) > 0:
            e = df.loc[valid_ids, _cltype].to_dict()
        else:
            e = {}
        expr = {}
        for i in id2ensembl:
            expr[i] = e.get(id2ensembl[i], float('nan'))
        return json.dumps(expr)

    def get_annot_res_csv(self):
        args, kwargs = ((self.parsed_data.to_json(), self.slim,
                         self.namespace, self.organism),
                        {'jobid':str(self.id)})
        s = annot_csv.signature(args=args, kwargs=kwargs)
        r = process_signature(s)

        df = pd.read_json(r, orient='split')
        b = io.StringIO()
        df.to_csv(b, sep=',', float_format='%.3E')
        b.seek(0)
        self.res_csv = b.read()
        self.save()

    def get_annot_res_txt(self):
        s = annot_txt.signature(args=(self.parsed_data.to_json(), self.slim,
                                      self.namespace, self.organism),
                                kwargs={'jobid':str(self.id)})
        r = process_signature(s)
        self.res_txt = r
        self.save()

    def get_enrich_res_csv(self):
        args, kwargs = ((self.parsed_data.to_json(), self.enrich_res_df.to_json(),
                         self.qvalue, self.organism), {'jobid':str(self.id)})
        s = enrich_csv.signature(args=args, kwargs=kwargs)
        r = process_signature(s)
        df = pd.read_json(r, orient='split')
        b = io.StringIO()
        df.to_csv(b, sep=',', float_format='%.3E')
        b.seek(0)
        self.res_csv = b.read()
        self.save()

    def get_enrich_res_txt(self):
        s = enrich_txt.signature(args=(self.parsed_data.to_json(), self.enrich_res_df.to_json(),
                                       self.qvalue, self.organism),
                                kwargs={'jobid':str(self.id)})
        r = process_signature(s)
        self.res_txt = r
        self.save()


