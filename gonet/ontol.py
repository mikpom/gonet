from pkg_resources import resource_filename as pkg_file
from collections import defaultdict
import uuid
import pandas as pd
from time import sleep
from .clry import celery_app
from .expression import hpa_data, bgee_data, dice_data
from .geneid import uni2ens, mgi2ens
import genontol
from genontol.read import goa as read_goa
from genontol.ontol import GOntology

# Slims
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
goslim_immunol = read_slim(pkg_file(__name__, 'data/GO/goslim_immunology.lst'), sep='\t')
goslim_generic = GOntology.from_obo(pkg_file(__name__, 'data/GO/goslim_generic.obo.gz'))

# Read GAF annotation files
gaf = {}
gaf_ids = {}

# Dictionary mapping primary ID to GO terms
# structure is sp -> ID -> {set of GO terms}
id2go = {sp:defaultdict(set) for sp in ('human', 'mouse')}
for sp, gaf_file in [('human', 'goa_human.gaf.gz'),
                     ('mouse', 'gene_association.mgi.gz')]:
    gaf_file = pkg_file(__name__, 'data/GO/'+gaf_file)
    gaf[sp] = genontol.read.goa(gaf_file, experimental=False)
    gaf_ids[sp] = set(gaf[sp].db_object_id) # Dictionary of known IDs
    gaf[sp].set_index(['db_object_id', 'go_id'], drop=False, inplace=True)
    for v in gaf[sp][['db_object_id', 'go_id']].itertuples():
        id2go[sp][v.db_object_id].add(v.go_id)

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
                for uid, ensids in uni2ens[sp].items():
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
                for mgi_id, ensids in mgi2ens.items():
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

def get_domain_subgraph(O, domain):
    items = filter(lambda i: i[1]['namespace']==domain, O.G.nodes.items())
    nodes = [i[0] for i in items]
    subgraph = O.G.subgraph(nodes)
    return subgraph

def slimterms(slimname, domain):
    if slimname=='goslim_immunol':
        slimterms = goslim_immunol
    elif slimname == 'goslim_generic':
        slimterms = list(filter(lambda t: O.get_attr(t,'namespace')==domain,
                                goslim_generic.G.nodes()))
        slimterms.remove(O.roots[domain])
    else:
         print('Unknown slim name')
    return slimterms
