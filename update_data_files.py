from pkg_resources import resource_filename as pkg_file
from urllib.request import urlretrieve
import gzip
import os
import shutil

tmp_filename = pkg_file('gonet', 'tmp')

# ##
# ## Ontology files
# ##
ontol_files = {'go-basic': 'http://purl.obolibrary.org/obo/go/go-basic.obo',
               'goslim_generic' : 'http://current.geneontology.org/ontology/subsets/goslim_generic.obo'}

for fl, url in ontol_files.items():
    
    print('Updating {:s} ontology...'.format(fl))

    basename = os.path.basename(url)
    dest_file = pkg_file('gonet', 'data/GO/{:s}.gz'.format(basename))

    # # Backing up
    # print('Backing up old file {:s} -> {:s}.bak'.format(dest_file, dest_file))
    # shutil.move(dest_file, dest_file+'.bak')

    # retrive and write gzipped version
    print('Fetching from {:s}'.format(url))
    with gzip.open(dest_file, 'w') as out:
        urlretrieve(url, filename=tmp_filename)
        with open(tmp_filename, 'rb') as tmp:
            out.write(tmp.read())


# ##
# ## Annotation files
# ##
annot_files = {'human':'http://geneontology.org/gene-associations/goa_human.gaf.gz',
               'mouse':'http://geneontology.org/gene-associations/gene_association.mgi.gz'}

for sp, url in annot_files.items():
    print('Updating {:s} annotation file...'.format(sp))

    basename = os.path.basename(url)
    dest_file = pkg_file('gonet', 'data/GO/{:s}'.format(basename))

    # # Backing up
    # print('Backing up old file {:s} -> {:s}.bak'.format(dest_file, dest_file))
    # shutil.move(dest_file, dest_file+'.bak')

    # Retrieving
    print('Fetching from {:s}'.format(url))    
    urlretrieve(url, filename=dest_file)


##
## Uniprot -> Ensembl ID mappings
##
map_files = {'human':'HUMAN_9606_idmapping.dat.gz',
             'mouse':'MOUSE_10090_idmapping.dat.gz'}

base_url = 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/by_organism'
for sp, fl in map_files.items():
    print('Updating {:s} Uniprot -> Ensembl mapping file...'.format(sp))

    basename = os.path.splitext(fl)[0]+'.EnsemblIDs.gz'
    dest_file = pkg_file('gonet', 'data/genes/{:s}'.format(basename))
    url = os.path.join(base_url, fl)

    # # Backing up
    # if os.path.isfile(dest_file):
    #     print('Backing up old file {:s} -> {:s}.bak'.format(dest_file, dest_file))
    #     shutil.move(dest_file, dest_file+'.bak')

    print('Retrieving...', end='', flush=True)
    urlretrieve(url, filename=tmp_filename)
    print('done')

    # Read, filter and write
    with gzip.open(tmp_filename, 'rt') as tmp:
        with gzip.open(dest_file, 'wt') as dest:
            for line in tmp:
                #print('>'+line.split()[1]+'>')
                if line.split()[1] == 'Ensembl':
                    dest.write(line)


##
## Human gene names and synonyms
##

print('Updating human gene names and synonyms...')

dest_file = pkg_file('gonet', 'data/genes/human_nameprim_def_syn.tsv.gz')

# Backing up
# print('Backing up old file {:s} -> {:s}.bak'.format(dest_file, dest_file))
# shutil.move(dest_file, dest_file+'.bak')

# retrive and write gzipped version
print('Fetching from Uniprot...', end='', flush=True)
url = 'https://www.uniprot.org/uniprot/?query=organism:9606'+\
      '&columns=id,entry_name,protein_names,reviewed,genes(PREFERRED),genes(ALTERNATIVE)&format=tab'
urlretrieve(url, filename=tmp_filename)
print('done')

with gzip.open(dest_file, 'w') as out:
    with open(tmp_filename, 'rb') as tmp:
        out.write(tmp.read())

##
## Mouse Swissprot entries
##
print('Updating mouse Swissprot names...')

dest_file = pkg_file('gonet', 'data/genes/mouse_swissprot.tsv.gz')

# Backing up
# print('Backing up old file {:s} -> {:s}.bak'.format(dest_file, dest_file))
# shutil.move(dest_file, dest_file+'.bak')

# retrieve and write gzipped version
print('Fetching from Uniprot...', end='', flush=True)
url = 'https://www.uniprot.org/uniprot/?query=organism:10090+AND+reviewed:yes'\
       +'&format=tab&columns=id,entry_name'
urlretrieve(url, filename=tmp_filename)
print('done')

with gzip.open(dest_file, 'w') as out:
    with open(tmp_filename, 'rb') as tmp:
        out.write(tmp.read())
        

##
## Mouse data from MGI
##

mgi_files = ['MRK_ENSEMBL.rpt', 'MRK_List2.rpt', 'MRK_SwissProt.rpt']
base_url = 'http://www.informatics.jax.org/downloads/reports'

for fl in mgi_files:
    print('Updating {:s} ...'.format(fl))

    url = os.path.join(base_url, fl)
    dest_file = pkg_file('gonet', 'data/genes/{:s}.gz'.format(fl))

    # Backing up
    # print('Backing up old file {:s} -> {:s}.bak'.format(dest_file, dest_file))
    # shutil.move(dest_file, dest_file+'.bak')

    # Fetch
    print('Fetching from {:s} ...'.format(url), end='', flush=True)
    urlretrieve(url, filename=tmp_filename)
    print('done')

    # Write gzipped file
    with gzip.open(dest_file, 'w') as out:
        with open(tmp_filename, 'rb') as tmp:
            out.write(tmp.read())

os.remove(tmp_filename)            
