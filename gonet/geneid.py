import gzip
import re
from collections import defaultdict
from pkg_resources import resource_filename as pkg_file
import numpy as np
import pandas as pd
from .clry import celery_app
from .utils import to_dict_of_lists

print('Start reading gene mapping files...', end='', flush=True)
######################
# Reading Uniprot data
######################
uni2ens= {}
ens2uni = {'human':{}, 'mouse':{}}
for sp, fl in (('human', 'HUMAN_9606_idmapping.dat.EnsemblIDs.gz'),
               ('mouse', 'MOUSE_10090_idmapping.dat.EnsemblIDs.gz')):
    fl = pkg_file(__name__, 'data/genes/'+fl)
    uni_ens = pd.read_csv(fl, sep='\t', usecols=(0,2),
                              header=None, names=['uni', 'ens'])
    uni2ens[sp] = to_dict_of_lists(uni_ens.set_index('uni')['ens'])
    ens2uni[sp] = to_dict_of_lists(uni_ens.set_index('ens')['uni'])
    
    # for key, values in uni2ens[sp].items():
    #     for value in values:
    #         ens2uni[sp].setdefault(value, []).append(key)

##################
# Reading MGI data
##################
# MGI-Ensembl conversion
mgi_ens = pd.read_csv(pkg_file(__name__, 'data/genes/MRK_ENSEMBL.rpt.gz'),
                      sep='\t', usecols=(0,4,5),
                      names=['mgi_id', 'chr', 'ensembl_id'])
mgi2ens = to_dict_of_lists(mgi_ens.set_index('mgi_id')['ensembl_id'])
ens2mgi = to_dict_of_lists(mgi_ens.set_index('ensembl_id')['mgi_id'])

# MGI-Uniprot conversions
mgi_uni = pd.read_csv(pkg_file('gonet', 'data/genes/MRK_SwissProt.rpt.gz'),
                      sep='\t', usecols=(0,6), names=['mgi_id','uniprot_id'])
mgi2uni = {}
uni2mgi = defaultdict(set)
for tp in mgi_uni.itertuples():
    uniprotids = tp.uniprot_id.split(' ')
    mgi2uni[tp.mgi_id] = set(uniprotids)
    for uid in uniprotids:
        uni2mgi[uid].add(tp.mgi_id)

# Init Swissprot data and load Mouse
# Human is read later
swissprot = {'human':set(), 'mouse':set()}
fl = pkg_file(__name__, 'data/genes/mouse_swissprot.tsv.gz')
with gzip.open(fl, 'rt') as f:
    f.readline()
    for line in f:
        swissprot['mouse'].add(line.split()[0])

##############################
# Read chromosom ids for genes
##############################
ens2chr = {}
ens2chr['human'] = pd.read_csv(pkg_file(__name__, 'data/genes/human_gene_chr.tsv.gz'),
                      sep='\t', index_col=0)['Chromosome/scaffold name'].to_dict()
ens2chr['mouse'] = to_dict_of_lists(mgi_ens.set_index('mgi_id')['chr'])


#########################################################
# Reading synonyms and genenames data for Human and Mouse
#########################################################
def _parse_protname(s):
    cbi = 0
    while (cbi<len(s)-1):
        obi = s.find('(', cbi)
        if obi == -1:
            return s.strip()
        else:
            cbi = s.find(')', obi)
            if s[cbi:].startswith(') (') or s[cbi:]==")":
                return s[:obi].strip()

# dictionary mapping synonyms to primary IDs
syn2id  = {sp:defaultdict(set) for sp in ('human', 'mouse')}
# dictionary mapping primary name to primary IDs
primname2id = {sp:defaultdict(set) for sp in ('human', 'mouse')}
id2primname = {sp:{} for sp in ('human', 'mouse')}
# dictionary mapping Primary ID to description
id2desc = {sp:{} for sp in ('human', 'mouse')}

human_nm = pd.read_csv(pkg_file('gonet', 'data/genes/human_nameprim_def_syn.tsv.gz'),
                       usecols=(0,2,3,4,5), skiprows=1, sep='\t',
                       names=['uniprotid', 'prot_name', 'status', 'primname', 'synonyms'])

# Creating ad-hoc set of Uniprot IDs from this file
uniprot_ids2 = {'human':set(), 'mouse':set()}
for v in human_nm.itertuples():
    if not pd.isnull(v.synonyms):
        # synonyms can be of form H2AFP; H2AFC; H2AFD; H2AFI; H2AFN
        # or OLFMF OR1F10 OR1F4 OR1F5 OR1F6 OR1F7 OR1F8 OR1F9
        for s in re.split(r'[; ]+', v.synonyms):
            syn2id['human'][s].add(v.uniprotid)
    if v.status == 'reviewed':
        swissprot['human'].add(v.uniprotid)
    id2desc['human'][v.uniprotid] = _parse_protname(v.prot_name)
    if not pd.isnull(v.primname):
        # e.g. HIST1H2AG; HIST1H2AI; HIST1H2AK; HIST1H2AL; HIST1H2AM ...
        for ind, nm in enumerate(v.primname.split('; ')):
            primname2id['human'][nm].add(v.uniprotid)
            if ind == 0:
                id2primname['human'][v.uniprotid] = nm
            # Adding this Uniprot ID to ad-hoc dictionary
            uniprot_ids2['human'].add(v.uniprotid)

mouse_nm = pd.read_csv(pkg_file('gonet', 'data/genes/MRK_List2.rpt.gz'), sep='\t',
                             usecols=(0,6,8,11), names=['mgi_id','symbol','name','synonym'],
                             skiprows=[0])
mouse_nm.fillna('null', inplace=True)
id2primname['mouse'] = mouse_nm[['mgi_id','symbol']].set_index('mgi_id')['symbol']\
                                                          .to_dict()

for t in mouse_nm.itertuples():
    primname2id['mouse'][t.symbol].add(t.mgi_id)
    if t.synonym != 'null':
        synonyms = t.synonym.split('|')
        for s in synonyms:
            syn2id['mouse'][s].add(t.mgi_id)
    id2desc['mouse'][t.mgi_id] = t.name

print('done', flush=True)    

##################################
# Functions for resolving gene IDs
##################################
_defaults = {'gn_in_swp' : 0, 'identified' : False, 'prim_ids':0,
             'syn_in_swp' : 0, 'submit_name':'', 'pref_name':'',
             'ensembl_id':None,
             'uniprot_id':None, 'mgi_id' : None, 'desc':None}

_dtypes = {'gn_in_swp' : np.int8, 'identified' : np.bool_,
           'prim_ids':np.int8, 'syn_in_swp' : np.int8,
           'submit_name':'object', 'ensembl_id':'object',
           'uniprot_id':'object', 'mgi_id' : 'object', 'desc':'object',
           'val':np.float_}

def resolve_geneid(geneid, sp):
    ret = {k:v for k,v in _defaults.items()}
    # valid Uniprot ID supplied for human
    if (sp=='human') and \
                     (geneid in uni2ens[sp] or geneid in uniprot_ids2[sp]):
        prim_id = geneid
        ret['identified'] = True
        ret['prim_ids'] = 1
        ret['uniprot_id'] = geneid
        if geneid in swissprot[sp]:
            ret['gn_in_swp'] = 1
    # valid Uniprot ID supplied for mouse
    elif (sp=='mouse') and ((geneid in uni2ens[sp]) or (geneid in uni2mgi)):
        if geneid in uni2mgi:
            prim_ids = uni2mgi[geneid]
            prim_id = list(uni2mgi[geneid])[0]
            ret['identified'] = True
        ret['uniprot_id'] = geneid
        if geneid in swissprot[sp]:
            ret['gn_in_swp'] = 1
    # valid MGI ID supplied for mouse
    elif (sp=='mouse') and (geneid in mgi2uni):
        ret['identified'] = True
        prim_id = geneid
    else:
        prim_ids = None
        gn_in_swp = None
        synonyms = None
        syn_in_swp = None
        if geneid in primname2id[sp]:
            prim_ids = sorted(primname2id[sp][geneid])
            ret['prim_ids'] = len(prim_ids)
            gn_in_swp = list(filter(lambda i: i in swissprot[sp], prim_ids))
            ret['gn_in_swp'] = len(gn_in_swp)
        if geneid in syn2id[sp]:
            synonyms = sorted(syn2id[sp][geneid])
            syn_in_swp = list(filter(lambda i: i in swissprot[sp], synonyms))
            ret['syn_in_swp'] = len(syn_in_swp)

        # Priority is for primary names in Swissprot
        if gn_in_swp and len(gn_in_swp) > 0:
            prim_id = gn_in_swp[0]
            ret['identified'] = True
        # Then synonyms in Swissprot
        elif syn_in_swp and len(syn_in_swp) > 0:
            prim_id = syn_in_swp[0]
            ret['identified'] = True
        # Then primary IDs not in Swissprot
        elif prim_ids and len(prim_ids) > 0:
            prim_id = prim_ids[0]
            ret['identified'] = True
        # Then synonym IDs not in Swissprot
        elif synonyms and len(synonyms) > 0:
            prim_id = synonyms[0]
            ret['identified'] = True

    # If we have primary ID then look for other IDs
    if ret['identified']:
        ret['ensembl_id'] = _get_ensembl_ids(prim_id, sp=sp)
        ret['primname'] = id2primname[sp][prim_id]
        if sp=='mouse':
            if not ret['uniprot_id']:
                try:
                    ret['uniprot_id'] = sorted(mgi2uni[prim_id])[0]
                except KeyError:
                    ret['uniprot_id'] = None
            ret['mgi_id'] = prim_id
            ret['desc'] = id2desc[sp][ret['mgi_id']]
        else:
            ret['uniprot_id'] = prim_id
            ret['desc'] = id2desc[sp][ret['uniprot_id']]
    return ret

@celery_app.task
def resolve_genes(dfjs, sp='human', jobid=None):
    df = pd.read_json(dfjs, dtype=_dtypes)
    _df_d = defaultdict(dict)
    cnt = 0
    duplicates = {}
    for t in df.itertuples():
        genename, val = t.submit_name, t.val 
        d = resolve_geneid(genename, sp=sp)
        prim_id = d['uniprot_id'] if sp=='human' else d['mgi_id']
        if  d['identified']:
            if not prim_id in _df_d:
                gid = prim_id
            else:
                gid = '_{:05d}'.format(cnt)
                cnt += 1
                duplicates[gid] = prim_id
        else:
            gid = '_{:05d}'.format(cnt)
            cnt += 1
        _df_d[gid].update(d)
        _df_d[gid]['val'] = val
        _df_d[gid]['submit_name'] = genename

    for gid in _df_d:
        if gid in duplicates:
            _df_d[gid]['duplicate_of'] = duplicates[gid]
        else:
            _df_d[gid]['duplicate_of'] = ''
    ret = pd.DataFrame.from_dict(_df_d, orient='index')
    return ret.to_json()

@celery_app.task
def id_map_txt(dfjs, sp='human', jobid=None):
    df = pd.read_json(dfjs)
    df.sort_values('submit_name', inplace=True)
    if sp=='human':
        txt = 'Name\tPreferred_name\tUniprot_ID\tEnsembl_ID\tDescription\tNotes\n'
    elif sp=='mouse':
        txt = 'Name\tPreferred_name\tMGI_ID\tUniprot_ID\tEnsembl_ID\tDescription\tNotes\n'
    for t in df.itertuples():
        warn = []
        if t.duplicate_of != '':
            warn.append('same as '+df.loc[t.duplicate_of, 'submit_name'])
        if t.gn_in_swp > 1 or t.syn_in_swp > 1:
            warn.append('ambiguous')
        if not t.identified:
            warn.append('not recognized')
        notes = '; '.join(warn)
        if sp=='human':
            txt += '\t'.join(map(str, [t.submit_name, t.primname, t.uniprot_id,
                                       t.ensembl_id, t.desc, notes]))+'\n'
        elif sp=='mouse':
            txt += '\t'.join(map(str, [t.submit_name, t.primname, t.mgi_id,
                                       t.uniprot_id, t.ensembl_id, t.desc, notes]))+'\n'
    return txt

reg_chr = list(map(str, range(22))) + ['X', 'Y', 'MT']
def _get_ensembl_ids(geneid, sp):
    if sp == 'human':
        try:
            ensemblids = uni2ens[sp][geneid]
            on_reg_chr = list(filter(lambda i: ens2chr[sp][i] in reg_chr, ensemblids))
            if len(on_reg_chr) > 0:
                return on_reg_chr[0]
            elif len(ensemblids)>0:
                return ensemblids[0]
            else:
                return None
        except KeyError:
            return None
    else:
        try:
            return mgi2ens[geneid][0]
        except KeyError:
            return None

def _get_n_terms(sp):
    def __get_n_terms(uniprotid):
        try:
            n = len(id2go[sp][uniprotid])
            return n, uniprotid
        except KeyError:
            return 0, uniprotid
    return __get_n_terms
