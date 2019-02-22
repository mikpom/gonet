import os
import uuid
import io
import re
import logging
import traceback
import json
from django.db import models
from django.utils import timezone
from django.conf import settings
import numpy as np
import pandas as pd
from .exceptions import *
from .fields import DataFrameField, JSONField
from .geneid import resolve_genes, id_map_txt, _dtypes
from .expression import hpa_data, dice_data, \
    bgee_data, celltype_choices
from .ontol import O, compute_enrichment
from .export import enrich_txt, annot_txt, \
    enrich_csv, annot_csv
from .graph import build_enrich_GOnet, build_slim_GOnet
from .utils import thread_func, process_signature

log = logging.getLogger(__name__)

class GOnetJobStatus(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rdy = models.BooleanField(default=True)
    err = JSONField()

class GOnetSubmission(models.Model):
    sep_choices = (('\t', '{tab}'), (',', '{,}'), ('\s+', 'Any whitespace'))
    organism_choices = (('human', 'Human'), ('mouse', 'Mouse'))
    analysis_choices = (('enrich', 'GO term enrichment'), ('annot', 'GO term annotation'))
    output_choices = (('graph', 'Interactive Graph'),
                      ('txt', 'Hierarchical TXT'),
                      ('csv', 'CSV'))
    slim_choices = (('goslim_generic', 'Generic GO slim'),
                    ('goslim_immunol', 'GO slim for immunology (experimental; process only)'),
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
                 + tuple(celltype_choices['human'].items()) \
                 + (('Bgee-any', 'Any Bgee celltype'),) \
                 + tuple(celltype_choices['mouse'].items())
    bgtype_choices = (('all', 'all annotated genes'),
                      ('custom', 'custom gene list'),
                      ('predef', 'predefined backgrounds'))


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submit_time = models.DateTimeField('Submission time', default=timezone.localtime)
    uploaded_file = models.FileField(upload_to=os.path.join('csv/'),
                                     default='', blank=True)
    file_uploaded = models.BooleanField(default=True)
    paste_data = models.TextField(default='', blank=True)
    parsed_data = DataFrameField()
    cli_addr = models.CharField(max_length = 20, default = '0.0.0.0')
    csv_separator = models.CharField(max_length=10, default='comma', choices=sep_choices)
    job_name = models.CharField(max_length=40, default='', blank=True)
    organism = models.CharField(max_length=10, default='human', choices=organism_choices)
    qvalue = models.FloatField(default=0.05)
    network = models.TextField(default='{}', blank=True)
    # namespace is not required because of annot analysis with custom terms
    namespace = models.CharField(max_length=20, default='biological_process',
                                 choices=namespace_choices, blank=True) 
    analysis_type = models.CharField(max_length=12, default='enrich',
                                     choices=analysis_choices)
    output_type = models.CharField(max_length=12, default='graph',
                                   choices=output_choices)
    slim = models.CharField(max_length=20, default='goslim_generic',
                            choices=slim_choices, blank=True)
    bg_type = models.CharField(max_length=20, default='all',
                               choices=bgtype_choices, blank=True)
    bg_file = models.FileField(upload_to=os.path.join('csv/'), default='', blank=True)
    bg_genes = DataFrameField(default='', blank=True)
    bg_cell = models.CharField(max_length=20, default='DICE-any',
                               choices=bg_choices, blank=True)
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
        kwargs = cln_data
        kwargs.update({'cli_addr':cli, 'bg_file':bg_file,
                       'uploaded_file':genelist_file})
        sn = cls(**kwargs)
        if ((not sn.uploaded_file) and (sn.paste_data=='')):
            msg = 'File with gene list should be uploaded ' \
                  + 'or text with data pasted in the corresponding section\n'
            raise DataNotProvidedError(msg)
        if ((sn.analysis_type=="annot") and \
            (sn.slim=="custom") and (sn.custom_terms=='')):
            msg = 'Custom GO terms option specified ' \
                                        + 'but corresponding text field is empty\n'
            raise DataNotProvidedError(msg)
        elif (sn.uploaded_file):
            sn.file_uploaded = True
        elif (sn.paste_data != ''):
            sn.file_uploaded = False
        sn.save()
        return sn

    @thread_func
    def run_pre_analysis(self):
        
        jobid=str(self.id)
        log.info('Starting pre analysis...', extra={'jobid':jobid})
        job_status = GOnetJobStatus.objects.get(pk=self.id)
        
        try:
            if (self.file_uploaded):
                stream = self.uploaded_file
                first_line = stream.readline().decode().strip('\r\n')
            else:
                stream = io.StringIO(self.paste_data)
                first_line = stream.readline().strip('\r\n')

            # Check for multiple separators
            if len(re.split(self.csv_separator, first_line))>2:
                log.info('Got multiple separators on the first line. ',
                         extra={'jobid':jobid})
                raise TooManySeparatorsError

            # Read using Pandas
            stream.seek(0)
            colnames = ['submit_name', 'val']
            convert_val = lambda v: np.float_(v) if v else np.nan
            self.parsed_data = pd.read_csv(stream, sep=self.csv_separator,
                                           names=colnames,
                                           converters={'submit_name':np.str_,
                                                       'val': convert_val})

            # Check size of the input
            if (len(self.parsed_data)>20000):
                log.info('Too many entries. Got '\
                         +str(len(self.parsed_data)), extra={'jobid':jobid})
                raise TooManyEntriesError
            elif (len(self.parsed_data)>3000) and (self.output_type=='graph'):
                log.info('Too many entries for graph output. Got '\
                         +str(len(self.parsed_data)), extra={'jobid':jobid})
                raise TooManyEntriesGraphError

            # Fix input
            self.parsed_data['submit_name'] = self.parsed_data['submit_name'].str.strip()
            self.parsed_data.fillna({'FC':0.0}, inplace=True)

            # Resolve gene IDs
            s = resolve_genes.signature(args=(self.parsed_data.to_json(), self.organism),
                                                     kwargs={'jobid':jobid})
            r = process_signature(s)
            parsed_data = pd.read_json(r, dtype=_dtypes)
            self.parsed_data = parsed_data

            # Check any genes were identification
            if self.parsed_data['identified'].sum() == 0.0:
                log.info('W: None of the genes submitted identified', extra={'jobid':jobid})
                raise GenesNotIdentifiedError

            # Check background gene identifiers if uploaded
            if self.analysis_type=='enrich' and self.bg_file:
                if self.bg_type != 'custom': # check for weird input
                    log.warn('W: Background file submitted but bg_type is '\
                             +str(self.bg_type)+'. Proceeding as if bg_type was custom.',
                             extra={'jobid':jobid})

                self.bg_genes = pd.read_csv(self.bg_file,
                                   names=colnames)
                s = resolve_genes.signature(args=(self.bg_genes.to_json(),
                                                         self.organism),
                                                   kwargs={'jobid':jobid})
                bg_genes = pd.read_json(process_signature(s))
                self.bg_genes = bg_genes

                # Check if any genes in background were identified
                if self.bg_genes['identified'].sum() == 0.0:
                    log.info('None of the genes in background file identified',
                             extra={'jobid':jobid})
                    raise BgGenesNotIdentifiedError

            # Check validity of custom GO terms if supplied
            if self.analysis_type == 'annot' and self.slim=='custom':
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
                    log.info('Invalid custom GO terms encountered', extra={'jobid':jobid})
                    raise InvalidGOTermError

            log.info('pre_analysis done', extra={'jobid':jobid})

        except InputValidationError as err:
            tb = traceback.format_tb(err.__traceback__)
            job_status.err[err.__class__.__name__] = tb
            job_status.rdy = True
            job_status.save()
            self.save()
            return

        except Exception as err:
            if settings.TESTING:
                raise err
            else:
                tb = traceback.format_tb(err.__traceback__)
                job_status.err[err.__class__.__name__] = tb
                job_status.rdy = True
                job_status.save()
                self.save()
                log.error('Unhandeled exception during pre_analysis\n'+str(tb),
                          extra={'jobid':jobid})
                return

        self.run_analysis()

    @thread_func
    def run_analysis(self):
        jobid=str(self.id)
        log.info('Starting run_analysis...', extra={'jobid':jobid})
        job_status = GOnetJobStatus.objects.get(pk=self.id)
        try:
            dat = self.parsed_data
            if self.analysis_type=='enrich':
                gn = dat[(dat.duplicate_of=='')&(dat.identified)].index
                args = (gn, self.namespace,
                        self.organism, self.bg_type)
                if self.bg_type == 'all':
                    kwargs = {}
                elif self.bg_type == 'custom':
                    kwargs = {'bg_genes':
                              list(self.bg_genes.index.union(dat.index)),
                              'bg_id' : jobid}
                elif self.bg_type == 'predef':
                    kwargs = {'bg_genes':self.bg_cell, 'bg_id' : jobid}
                kwargs.update({'jobid':jobid})
                s = compute_enrichment.signature(args=args, kwargs=kwargs)
                self.enrich_res_df = pd.read_json(process_signature(s))\
                                       .dropna().query('p<0.1')
                if (self.output_type=="txt"):
                    self.get_enrich_res_txt()
                elif (self.output_type=="csv"):
                    self.get_enrich_res_csv()
                elif (self.output_type == "graph"):
                    args = (self.enrich_res_df.to_json(), self.qvalue,
                            dat.to_json(), self.namespace, self.organism)
                    s = build_enrich_GOnet.signature(args=args, kwargs={'jobid':jobid})
                    self.network = process_signature(s)
            elif self.analysis_type=='annot':
                if self.slim == 'custom':
                    slim = list(self.parsed_custom_terms['termid'])
                else:
                    slim = self.slim
                    if slim == 'goslim_immunol':
                        self.namespace = 'biological_process'
                if (self.output_type=="txt"):
                    self.get_annot_res_txt()
                elif (self.output_type=="csv"):
                    self.get_annot_res_csv()
                elif (self.output_type=="graph"):
                    s = build_slim_GOnet.signature(args=(dat.to_json(),
                                                         slim, self.namespace, self.organism),
                                                   kwargs={'jobid':jobid})
                    self.network = process_signature(s)
            self.save()
            job_status.rdy = True
            job_status.save()
            log.info('run_analysis done', extra={'jobid':jobid})
        except Exception as err:
            if settings.TESTING:
                raise err
            else:
                tb = traceback.format_tb(err.__traceback__)
                job_status.err[err.__class__.__name__] = tb
                job_status.rdy = True
                job_status.save()
                self.save()
                log.error('Unhandeled exception during pre_analysis\n'+str(tb),
                          extra={'jobid':jobid})

                return

    def get_id_map(self):
        s = id_map_txt.signature(args=(self.parsed_data.to_json(),),
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
        s = enrich_txt.signature(args=(self.parsed_data.to_json(),
                                       self.enrich_res_df.to_json(),
                                       self.qvalue, self.organism),
                                kwargs={'jobid':str(self.id)})
        r = process_signature(s)
        self.res_txt = r
        self.save()


