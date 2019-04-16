from collections import OrderedDict
from pkg_resources import resource_filename as pkg_file
import gzip
import pandas as pd

hpa_data = pd.read_csv(pkg_file(__name__, 'data/genes/E-MTAB-2836-query-results.tpms.tsv.gz'),
                       sep='\t', comment='#', index_col=0).drop('Gene Name', axis=1)
def _converter(g):
    if 'PAR_Y' in g:
        return g
    else:
        return g.split('.')[0]
dice_data = pd.read_csv(pkg_file(__name__, 'data/genes/dice_tpm.tsv.gz'), sep='\t',
                      converters={0:_converter},
                      index_col=0)
_mmus_x = pd.read_csv(pkg_file(__name__, 'data/genes/Mus_musculus_RNA-Seq_read_counts_TPM_FPKM_GSE36026.tsv.gz'),
                  sep='\t', usecols=(3, 5, 11))
bgee_data = _mmus_x.pivot(index='Gene ID', columns='Anatomical entity name', values='TPM')

celltype_choices = {sp:OrderedDict() for sp in ('human', 'mouse')}
celltype_choices['human'].update([ ('DICE-'+c,  '(DICE-DB) '+c) for c in dice_data.columns ])
celltype_choices['human'].update([ ('HPA-'+tissue, '(HPA) '+tissue) for tissue in \
                                    hpa_data.columns ])
celltype_choices['mouse'].update([ ('Bgee-'+c, '(Bgee) '+c) for c in bgee_data.columns ])

