import os
from pkg_resources import resource_filename as pkg_file
import gzip
from collections import defaultdict, OrderedDict
import uuid
import re
import logging
import networkx as nx
import numpy as np
import pandas as pd
from time import sleep
from gonet.clry import celery_app
from gonet import settings
import genontol
from genontol.read import goa as read_goa
from genontol.ontol import GOntology
import pickle

def parse_protname(s):
    cbi = 0
    while (cbi<len(s)-1):
        obi = s.find('(', cbi)
        if obi == -1:
            return s.strip()
        else:
            cbi = s.find(')', obi)
            if s[cbi:].startswith(') (') or s[cbi:]==")":
                return s[:obi].strip()

def read_slim(filename, sep = '\t', skip_header=0, comment='#'):
    ret = []
    with open(filename, 'r') as infile:
        for i in range(skip_header):
            infile.readline()
        for line in infile.readlines():
            if line.startswith(comment):
                continue
            splitted = line.split(sep, 1)
            ret.append(splitted[0].rstrip())
    return ret

def series_to_dict_of_lists(s):
     ret = defaultdict(list)
     for i in s.iteritems():
          ret[i[0]].append(i[1])
     return dict(ret)

#* Uniprot to Ensembl conversion data
uniprot2ensembl, ensembl2chr = ({}, {})
for sp in ('human', 'mouse'):
    map_file = pkg_file(__name__, 'data/genes/'+sp.upper()+'_idmapping.EnsemblIDs.dat.gz')
    u2e = pd.read_csv(map_file, sep='\t', usecols=(0,2),
                      index_col=0, header=None)
    uniprot2ensembl[sp] = series_to_dict_of_lists(u2e[2])
    g2c = pd.read_csv(pkg_file(__name__, 'data/genes/'+sp+'_gene_chr.tsv.gz'),
                      sep='\t', index_col=0)
    ensembl2chr[sp] = g2c['Chromosome/scaffold name'].to_dict()

#* Additional mouse gene ID data
mrk_ensembl_df = pd.read_csv(pkg_file(__name__, 'data/genes/MRK_ENSEMBL.rpt.gz'),
                          sep='\t', usecols=(0,4,5), names=['mgi_id','chr','ensembl_id'])
mgi2ensembl = series_to_dict_of_lists(mrk_ensembl_df.set_index('mgi_id')['ensembl_id'])

mrk_swp_df = pd.read_csv(pkg_file(__name__, 'data/genes/MRK_SwissProt.rpt.gz'),
                          sep='\t', usecols=(0,5,6), names=['mgi_id','chr','uniprot_id'])
mgi2uniprot = series_to_dict_of_lists(mrk_swp_df.set_index('mgi_id')['uniprot_id'])
uniprot2mgi = series_to_dict_of_lists(mrk_swp_df.set_index('uniprot_id')['mgi_id'])

#* Read expression data
hpa_data = pd.read_csv(pkg_file(__name__, 'data/genes/E-MTAB-2836-query-results.tpms.tsv.gz'),
                       sep='\t', comment='#', index_col=0).drop('Gene Name', axis=1)
def _converter(g):
    if 'PAR_Y' in g:
        return g
    else:
        return g.split('.')[0]
dice_data = pd.read_csv(pkg_file(__name__, 'data/genes/r24tpm.tsv.gz'), sep='\t',
                      converters={0:_converter},
                      index_col=0)
_mmus_x = pd.read_csv(pkg_file(__name__, 'data/genes/Mus_musculus_RNA-Seq_read_counts_TPM_FPKM_GSE36026.tsv.gz'),
                  sep='\t', usecols=(3, 5, 11))
bgee_data = _mmus_x.pivot(index='Gene ID', columns='Anatomical entity name', values='TPM')

celltype_choices = {sp:OrderedDict() for sp in ('human', 'mouse')}
celltype_choices['human'].update( {'DICE-'+c : '(DICE-DB) '+c for c in dice_data.columns} )
celltype_choices['human'].update( {'HPA-'+tissue : '(HPA) '+tissue for tissue in \
                                   hpa_data.columns} )
celltype_choices['mouse'].update({'Bgee-'+c : '(Bgee) '+c for c in bgee_data.columns})

#* Slims
goslim_generic = GOntology.from_obo(pkg_file(__name__, 'data/GO/goslim_generic.obo.gz'))
goslim_immunol = read_slim(pkg_file(__name__, 'data/GO/goslim_immunology.lst'), sep='\t')

#* Make ontology graph O and propagate necessary annotations
if settings.RECALCULATE:
    # Read mouse swissprot data from 
    swissprot = {'human':set(), 'mouse':set()}
    with gzip.open(pkg_file(__name__, 'data/genes/mouse_swissprot.tsv.gz'), 'rt') as f:
        f.readline()
        for line in f:
            swissprot['mouse'].add(line.split()[0])

    # Read GAF annotation files
    gaf = {}
    gaf_ids = {}

    # Dictionary mapping primary ID to GO terms
    # structure is sp -> ID -> {set of GO terms}
    id2go = {sp:defaultdict(set) for sp in ('human', 'mouse')}
    for sp, gaf_file in [('human', 'goa_human.gaf.gz'), ('mouse', 'gene_association.mgi.gz')]:
        gaf_file = pkg_file(__name__, 'data/GO/'+gaf_file)
        gaf[sp] = genontol.read.goa(gaf_file, experimental=False)
        gaf_ids[sp] = set(gaf[sp].db_object_id) # Dictionary of known IDs
        gaf[sp].set_index(['db_object_id', 'go_id'], drop=False, inplace=True)
        for v in gaf[sp][['db_object_id', 'go_id']].itertuples():
            id2go[sp][v.db_object_id].add(v.go_id)

    ###
    # Reading synonyms and genenames data for Human and Mouse
    ###
    # dictionary mapping synonyms to primary IDs
    syn2id  = {sp:defaultdict(set) for sp in ('human', 'mouse')}
    # dictionary mapping primary name to primary IDs
    gname2id = {sp:defaultdict(set) for sp in ('human', 'mouse')}
    # dictionary mapping Primary ID to description
    id2desc = {sp:{} for sp in ('human', 'mouse')}

    human_nm = pd.read_csv(pkg_file(__name__, 'data/genes/human_nameprim_def_syn.tsv.gz'),
                                 names=['uniprotid', 'entry_name', 'prot_name', 'status',
                                        'name_prim', 'synonyms', 'gene_names'],
                                 skiprows=1, sep='\t')
    for v in human_nm.itertuples():
        if not pd.isnull(v.synonyms):
            # synonyms can be of form H2AFP; H2AFC; H2AFD; H2AFI; H2AFN
            # or OLFMF OR1F10 OR1F4 OR1F5 OR1F6 OR1F7 OR1F8 OR1F9
            for s in re.split(r'[; ]+', v.synonyms):
                syn2id['human'][s].add(v.uniprotid)
        if v.status == 'reviewed':
            swissprot['human'].add(v.uniprotid)
        id2desc['human'][v.uniprotid] = parse_protname(v.prot_name)
        if not pd.isnull(v.name_prim):
            # e.g. HIST1H2AG; HIST1H2AI; HIST1H2AK; HIST1H2AL; HIST1H2AM ...
            for nm in re.split(r'[; ]+', v.name_prim):
                gname2id['human'][nm].add(v.uniprotid)

    mouse_nm = pd.read_csv(pkg_file(__name__, 'data/genes/MRK_List2.rpt.gz'), sep='\t',
                                 usecols=(0,6,8,11), names=['mgi_id','symbol','name','synonym'],
                                 skiprows=[0])
    mouse_nm.fillna('null', inplace=True)

    for t in mouse_nm.itertuples():
        gname2id['mouse'][t.symbol].add(t.mgi_id)
        if t.synonym != 'null':
            synonyms = t.synonym.split('|')
            for s in set(synonyms):
                syn2id['mouse'][s].add(t.mgi_id)
        id2desc['mouse'][t.mgi_id] = t.name
    
    # graph is directed from  specific term to less specific !!
    O = GOntology.from_obo(pkg_file(__name__, 'data/GO/go-basic.obo.gz'))
    bg = {'human':defaultdict(set), 'mouse':defaultdict(set)}
    specific_terms = {'human':defaultdict(set), 'mouse':defaultdict(set)}
    for sp in ('human', 'mouse'):
        for gene in gaf_ids[sp]:
            for goterm in id2go[sp][gene]:
                if O.has_term(goterm):
                    bg[sp][goterm].add(gene)
                    specific_terms[sp][goterm].add((gene, goterm))
        O.propagate(bg[sp], sp)
        O.propagate(specific_terms[sp], 'specific_terms')
    # Dictionary sp -> gene ID -> {set of terms}
    # here propagation is taken into account
    gene2allterms = {'human':defaultdict(set), 'mouse':defaultdict(set)}
    for term in O.all_terms():
        for sp in ('human', 'mouse'):
            for gene in O.get_attr(term, sp):
                gene2allterms[sp][gene].add(term)
    pickle.dump(id2go, open(pkg_file(__name__, 'data/pickles/id2go.pkl'), 'wb'))
    pickle.dump(id2desc, open(pkg_file(__name__, 'data/pickles/id2desc.pkl'), 'wb'))
    pickle.dump(gname2id, open(pkg_file(__name__, 'data/pickles/gname2id.pkl'), 'wb'))
    pickle.dump(syn2id, open(pkg_file(__name__, 'data/pickles/syn2id.pkl'), 'wb'))
    pickle.dump(O, open(pkg_file(__name__, 'data/pickles/O.pkl'), 'wb'))
    pickle.dump(gene2allterms, open(pkg_file(__name__, 'data/pickles/gene2allterms.pkl'), 'wb'))
    pickle.dump(gaf, open(pkg_file(__name__, 'data/pickles/gaf.pkl'), 'wb'))
    pickle.dump(swissprot, open(pkg_file(__name__, 'data/pickles/swissprot.pkl'), 'wb'))
else:
    O = pickle.load(open(pkg_file(__name__, 'data/pickles/O.pkl'), 'rb'))
    gene2allterms = pickle.load(open(pkg_file(__name__, 'data/pickles/gene2allterms.pkl'), 'rb'))
    gname2id = pickle.load(open(pkg_file(__name__, 'data/pickles/gname2id.pkl'), 'rb'))
    syn2id = pickle.load(open(pkg_file(__name__, 'data/pickles/syn2id.pkl'), 'rb'))
    id2go = pickle.load(open(pkg_file(__name__, 'data/pickles/id2go.pkl'), 'rb'))
    id2desc = pickle.load(open(pkg_file(__name__, 'data/pickles/id2desc.pkl'), 'rb'))
    gaf = pickle.load(open(pkg_file(__name__, 'data/pickles/gaf.pkl'), 'rb'))
    swissprot = pickle.load(open(pkg_file(__name__, 'data/pickles/swissprot.pkl'), 'rb'))
    gaf_ids = {sp:set(gaf[sp].db_object_id) for sp in gaf}

def get_slim(slimname, domain):
    if slimname=='goslim_immunol':
        slimterms = goslim_immunol
    elif slimname == 'goslim_generic':
        slimterms = list(filter(lambda t: O.get_attr(t,'namespace')==domain,
                                goslim_generic.G.nodes()))
        slimterms.remove(O.roots[domain])
    else:
         print('Unknown slim name')
    return slimterms

#* synonyms func
def _get_n_terms(sp):
    def __get_n_terms(uniprotid):
        try:
            n = len(id2go[sp][uniprotid])
            return n, uniprotid
        except KeyError:
            return 0, uniprotid
    return __get_n_terms

reg_chr = list(map(str, range(22))) + ['X', 'Y', 'MT']
def _get_ensembl_ids(geneid, sp):
    if sp == 'human':
        try:
            ensemblids = uniprot2ensembl[sp][geneid]
            on_reg_chr = list(filter(lambda i: ensembl2chr[sp][i] in reg_chr, ensemblids))
            if len(on_reg_chr) > 0:
                return on_reg_chr[0]
            else:
                return ensemblids[0]
        except KeyError:
            return None
    else:
        try:
            return mgi2ensembl[geneid][0]
        except KeyError:
            return None
    
_defaults = {'gn_with_go': 0, 'gn_in_swp' : 0, 'identified' : False, 'prim_ids':0,
             'syn_with_go' : 0, 'syn_in_swp' : 0, 'submit_name':'', 'ensembl_id':None,
             'uniprot_id':None, 'mgi_id' : None, 'desc':None}

_dtypes = {'gn_with_go': np.int8, 'gn_in_swp' : np.int8, 'identified' : np.bool_,
             'prim_ids':np.int8, 'syn_with_go' : np.int8, 'syn_in_swp' : np.int8,
             'submit_name':'object', 'ensembl_id':'object', 'uniprot_id':'object',
             'mgi_id' : 'object', 'desc':'object', 'FC':np.float_}

# Outline of resolve_geneid algorithm
# if uniprot_id supplied:
#     return 
# else:
#     if resolvable_symbol:
#         if in swp :
#             return with max GO terms
#         elif with GO:
#             return the first
#     if was not resolve to swp or with GO:    
#         if resolvable with synomyms:
#              if syn in swp:
#                   return with max GO
#              elif syn with GO:
#                   return first
# 
# 
def resolve_geneid(geneid, sp):
    ret = {k:v for k,v in _defaults.items()}
    # valid Uniprot ID supplied for human
    if (sp=='human') and ((geneid in uniprot2ensembl[sp]) or gaf[sp].index.contains(geneid)):
        prim_id = geneid
        ret['identified'] = True
        ret['prim_ids'] = 1
        ret['uniprot_id'] = geneid
        if gaf[sp].index.contains(geneid):
            ret['gn_with_go'] = 1
        if geneid in swissprot[sp]:
            ret['gn_in_swp'] = 1
    # valid Uniprot ID supplied for mouse
    elif (sp=='mouse') and ((geneid in uniprot2ensembl[sp]) or (geneid in uniprot2mgi)):
        if geneid in uniprot2mgi:
            prim_ids = uniprot2mgi[geneid]
            prim_id = max(uniprot2mgi[geneid], key=_get_n_terms(sp))
            ret['identified'] = True
        ret['uniprot_id'] = geneid
        if geneid in swissprot[sp]:
            ret['gn_in_swp'] = 1
    # valid MGI ID supplied for mouse
    elif (sp=='mouse') and ((geneid in mgi2uniprot) or (gaf[sp].index.contains(geneid))):
        ret['identified'] = True
        prim_id = geneid
        if gaf[sp].index.contains(geneid):
            ret['gn_with_go'] = 1
    else:
        if geneid in gname2id[sp]:
             prim_ids = gname2id[sp][geneid]
             ret['prim_ids'] = len(prim_ids)
             gn_with_go = list(filter(lambda i: i in gaf_ids[sp], prim_ids))
             ret['gn_with_go'] = len(gn_with_go)
             gn_in_swp = list(filter(lambda i: i in swissprot[sp], prim_ids))
             ret['gn_in_swp'] = len(gn_in_swp)
              
             if len(gn_in_swp) > 0:
                  # If found in swissprot then pick one with the most GO terms
                  prim_id = max(gn_in_swp, key=_get_n_terms(sp))
                  ret['identified'] = True
             else:
                  # If not found in swissprot but still a uniprot ID identified
                  # then use the first one of those
                  if len(gn_with_go)>0:
                       prim_id = gn_with_go[0]
                       ret['identified'] = True
        # Even if genes were identified but they were not from swissprot
        # or had zero GO term do another attempt with synonyms
        if (ret['gn_in_swp']==0) and (ret['gn_with_go']==0):
            if geneid in syn2id[sp]:
                 synonyms = syn2id[sp][geneid]
                 syn_in_swp = list(filter(lambda i: i in swissprot[sp], synonyms))
                 ret['syn_in_swp'] = len(syn_in_swp)
                 syn_with_go = list(filter(lambda i: i in gaf_ids[sp], synonyms))
                 ret['syn_with_go'] = len(syn_with_go)
                 if len(syn_in_swp) > 0:
                      prim_id = max(syn_in_swp, key=_get_n_terms(sp))
                      ret['identified'] = True
                 else:
                      if len(syn_with_go)>0:
                           prim_id = syn_with_go[0]
                           ret['identified'] = True
    if ret['identified']:
        ret['ensembl_id'] = _get_ensembl_ids(prim_id, sp=sp)
        if sp=='mouse':
            if not ret['uniprot_id']:
                try:
                    ret['uniprot_id'] = mgi2uniprot[prim_id][0].split(' ')[0]
                except KeyError:
                    ret['uniprot_id'] = None
            ret['mgi_id'] = prim_id
            ret['desc'] = id2desc[sp][ret['mgi_id']]
        else:
            ret['uniprot_id'] = prim_id
            ret['desc'] = id2desc[sp][ret['uniprot_id']]
    return ret

@celery_app.task
def resolve_genenames_df(dfjs, sp='human', jobid=None):
    df = pd.read_json(dfjs, dtype=_dtypes)
    _df_d = defaultdict(dict)
    c_n = 0
    duplicates = {}
    for t in df.itertuples():
        genename, val = t.submit_name, t.val 
        d = resolve_geneid(genename, sp=sp)
        prim_id = d['uniprot_id'] if sp=='human' else d['mgi_id']
        if  d['identified']:
            if not prim_id in _df_d:
                gene_id = prim_id
            else:
                gene_id = '_{:05d}'.format(c_n)
                c_n += 1
                duplicates[gene_id] = prim_id
        else:
            gene_id = '_{:05d}'.format(c_n)
            c_n += 1
        _df_d[gene_id].update(d)
        _df_d[gene_id]['val'] = val
        _df_d[gene_id]['submit_name'] = genename
        
    for gene_id in _df_d:
        if gene_id in duplicates:
            _df_d[gene_id]['duplicate_of'] = duplicates[gene_id]
        else:
            _df_d[gene_id]['duplicate_of'] = ''
    ret = pd.DataFrame.from_dict(_df_d, orient='index')
    #print('from resolve_genenames_df', type(ret.loc['Q16873', 'mgi_id']))
    return ret.to_json()

def _resolve_genenames_df(df, sp, jobid=None):
    dfjs = df.to_json()
    return pd.read_json(resolve_genenames_df(dfjs, sp, jobid=jobid), dtypes=_dtypes)

#* Celery analyze func
@celery_app.task
def compute_enrichment(genes, namespace, sp, bg_type, jobid=None, 
                       bg_genes=None, bg_id=None, min_category_size=2,
                       max_category_size=10000, max_category_depth=10):
    
    kwargs = { 'max_category_size':max_category_size,
               'max_category_depth':max_category_depth,
               'min_category_size':min_category_size }
    
    if bg_type == 'all':
         res = O.get_enrichment(genes, sp, namespace, **kwargs)
    else:
        if bg_type == 'predef':
            if sp=='human':
                if bg_genes == 'DICE-any':
                    bg_ens = set(dice_data[(dice_data>1).any(axis=1)].index)
                elif bg_genes.startswith('DICE-'):
                    c = bg_genes[5:]
                    bg_ens = set(dice_data[dice_data[c]>1].index)
                elif bg_genes == 'HPA-any':
                    bg_ens = set(hpa_data[(hpa_data>1).any(axis=1)].index)
                elif bg_genes.startswith('HPA-'):
                    c = bg_genes[4:]
                    bg_ens = set(hpa_data[hpa_data[c]>1].index)
                bg_uniprot = list()
                for uid, ensids in uniprot2ensembl[sp].items():
                    for ensid in ensids:
                        if ensid in bg_ens:
                            bg_uniprot.append(uid)
                bg_final = list(set(bg_uniprot).union(set(genes)))
            elif sp=='mouse':
                if bg_genes == 'Bgee-any':
                    bg_ens = set(bgee_data[(bgee_data>1).any(axis=1)].index)
                elif bg_genes.startswith('Bgee-'):
                    c = bg_genes[5:]
                    bg_ens = set(bgee_data[bgee_data[c]>1].index)
                bg_mgi = list()
                for mgi_id, ensids in mgi2ensembl.items():
                    for ensid in ensids:
                        if ensid in bg_ens:
                            bg_mgi.append(mgi_id)
                bg_final = list(set(bg_mgi).union(set(genes)))
        elif bg_type == 'custom':
            bg_final = list(set(bg_genes).union(set(genes)))
        bg_attr = bg_id if not bg_id is None else str(uuid.uuid1())
        bg_dict = defaultdict(set)
        for gene in bg_final:
            try:
                goterms = id2go[sp][gene]
                for goterm in goterms:
                    bg_dict[goterm].add(gene)
            except KeyError:
                continue
        O.propagate(bg_dict, bg_attr)
        res = O.get_enrichment(genes, bg_attr, namespace, **kwargs)
        O.del_attr(bg_attr)
    return res.to_json()

@celery_app.task
def prepare_id_map_txt(dfjs, sp='human', jobid=None):
    df = pd.read_json(dfjs)
    df.sort_values('submit_name', inplace=True)
    if sp=='human':
        txt = 'genename\tUniprot_ID\tEnsembl_ID\tDescription\tNotes\n'
    elif sp=='mouse':
        txt = 'genename\tMGI_ID\tUniprot_ID\tEnsembl_ID\tDescription\tNotes\n'
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
            txt += '\t'.join(map(str, [t.submit_name, t.uniprot_id,
                                       t.ensembl_id, t.desc, notes]))+'\n'
        elif sp=='mouse':
            txt += '\t'.join(map(str, [t.submit_name, t.mgi_id, t.uniprot_id,
                                       t.ensembl_id, t.desc, notes]))+'\n'
    return txt


def _pprint_successors(ret, format_func, G, node, indent=1):
    for s in G.successors(node):
        ret.append(format_func(s, indent))
        _pprint_successors(ret, format_func, G, s, indent=indent+1)

@celery_app.task
def prepare_annot_res_txt(dfjs, slim, namespace, organism, jobid=None):
    _df = pd.read_json(dfjs)
    df = _df[_df['duplicate_of']=='']
    slimterms = get_slim(slim, namespace)
    def _format_term(t, indent):
        tname = O.get_attr(t, 'name')
        termgenes = []
        for gene in df.index:
            if gene in term_subgraph.node[t][organism]:
                termgenes.append(df.loc[gene, 'submit_name'])
        return '    '*max(indent, 0)+t, tname, \
                       ', '.join(termgenes)
    term_subgraph = O.G.subgraph(slimterms).reverse()
    res_txt_list = []
    for component in nx.connected_components(term_subgraph.to_undirected()):
        roots = filter(lambda n: term_subgraph.in_degree(n)==0,
                       term_subgraph.subgraph(component))
        for root in roots:
            res_txt_list.append(_format_term(root, 0))
            _pprint_successors(res_txt_list, _format_term, term_subgraph, root, indent=1)
    max_first = max([len(a[0]) for a in res_txt_list])
    res_txt = ('{:<'+str(max_first+2)+'}').format('GO_term_id') \
              +'{:<80}'.format('GO_term_def') \
              +'Genes\n'
    for vals in res_txt_list:
        if len(vals[1])>80:
            term_def = vals[1][:75]+'...'
        else:
            term_def = vals[1]
        res_txt += (('{:<'+str(max_first+2)+'}').format(vals[0]) \
                    +'{:<80.80}'.format(term_def) \
                    +vals[2])
        res_txt +='\n'
    return res_txt

@celery_app.task
def prepare_enrich_res_txt(dfjs, enrichjs, qval, organism, jobid=None):
    _df = pd.read_json(dfjs)
    df = _df[_df['duplicate_of']=='']
    enrich_res = pd.read_json(enrichjs)
    by_term = enrich_res.groupby('term')
    def _format_term(t, indent):
        goterm = O.get_term(t)
        pval, qval = by_term.get_group(t)[['p', 'q']].values.flatten()
        term_genes = []
        for gene in _df.index:
            if gene in goterm.node[organism]:
                term_genes.append(df.loc[gene, 'submit_name'])
        return '    '*max(indent, 0)+t, goterm.name, pval, qval, ', '.join(sorted(term_genes))
    significant_terms = set(enrich_res[enrich_res['q']<qval]['term'])
    # subgraph is oriented from more general to more specific
    term_subgraph = O.G.subgraph(significant_terms).reverse()
    res_txt_list = []
    for component in nx.connected_components(term_subgraph.to_undirected()):
        roots = filter(lambda n: term_subgraph.in_degree(n)==0,
                       term_subgraph.subgraph(component))
        for root in roots:
            res_txt_list.append(_format_term(root, 0))
            _pprint_successors(res_txt_list, _format_term, term_subgraph, root, indent=1)
    if res_txt_list:
        max_first = max([len(a[0]) for a in res_txt_list])
    else:
        max_first = 20
    res_txt = ('{:<'+str(max_first+2)+'}').format('GO_term_id') \
              +'{:<80}'.format('GO_term_def') \
              +'{:<23}'.format('  P') \
              +'{:<23}'.format('  P_FDR_adjusted') \
              +'Genes\n'
    for vals in res_txt_list:
        if len(vals[1])>80:
            term_def = vals[1][:75]+'...'
        else:
            term_def = vals[1]
        res_txt += (('{:<'+str(max_first+2)+'}').format(vals[0]) \
                    +'{:<80.80}'.format(term_def) \
                    +'{:<23}'.format('  '+'{:.3E}'.format(vals[2]))
                    +'{:<23}'.format('  '+'{:.3E}'.format(vals[3])) \
                    +vals[4])
        res_txt +='\n'
    return res_txt

def get_summary_df(gene_data, terms, organism):
    """
    Collects information about terms specified in a form of a DataFrame
    """
    terms = list(terms)
    smry = pd.DataFrame(index=pd.Index(list(range(len(terms))), name='N'),
                        columns = ['GO_term_ID', 'GO_term_def', 'NofGenes', 'Genes'])
    df = gene_data[gene_data['duplicate_of']=='']
    for ind in range(len(terms)):
        termgenes = []
        term = terms[ind]
        t = O.get_term(term)
        xgenes = t.node[organism].intersection(df.index)
        termgenes = sorted(list(df.loc[xgenes, 'submit_name']))
        smry.loc[ind, ['GO_term_ID', 'GO_term_def', 'NofGenes', 'Genes']] = \
                      [term, t.name, len(termgenes), '|'.join(termgenes)]
    return smry

@celery_app.task
def prepare_enrich_res_csv(dfjs, enrichjs, qval, organism, jobid=None):
    df = pd.read_json(dfjs)
    enrich_df = pd.read_json(enrichjs)
    res_df = enrich_df[['term', 'p', 'q']]
    significant_terms = res_df[res_df['q']<qval]
    significant_terms = significant_terms.sort_values('p')
    smry = get_summary_df(df, significant_terms['term'], organism)
    smry['P_FDR_adj'] = significant_terms['q'].values
    smry['P'] = significant_terms['p'].values
    smry.sort_values('P', inplace=True)
    smry['asc_N'] = list(range(1, len(smry)+1))
    smry.set_index('asc_N', inplace=True)
    smry = smry[['GO_term_ID', 'GO_term_def', 'P', 'P_FDR_adj', 'NofGenes', 'Genes']]
    return smry.to_json(orient='split')

@celery_app.task
def prepare_annot_res_csv(dfjs, slim, namespace, organism, jobid=None):
    df = pd.read_json(dfjs)
    slimterms = get_slim(slim, namespace)
    smry = get_summary_df(df, slimterms, organism)
    smry.sort_values('NofGenes', ascending=False, inplace=True)
    smry['asc_N'] = list(range(1, len(smry)+1))
    smry.set_index('asc_N', inplace=True)
    return smry.to_json(orient='split')

def get_domain_subgraph(O, domain):
    items = filter(lambda i: i[1]['namespace']==domain, O.G.nodes.items())
    nodes = [i[0] for i in items]
    subgraph = O.G.subgraph(nodes)
    return subgraph
