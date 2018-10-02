# Human Protein Atlas expression data
E-MTAB-2836-query-results.tpms.tsv	https://www.ebi.ac.uk/gxa/experiments-content/E-MTAB-2836/resources/ExperimentDownloadSupplier.RnaSeqBaseline/tpms.tsv

# Human and mouse Uniprot <-> Ensembl ID mapping 
HUMAN_idmapping.EnsemblIDs.dat	ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/by_organism/HUMAN_9606_idmapping.dat.gz
MOUSE_idmapping.EnsemblIDs.dat	ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/by_organism/MOUSE_10090_idmapping.dat.gz
# Both files are filtered using   awk '{if ($2=="Ensembl"){print}}' to get only Ensembl IDs

#Human gene name and synonym data
# Configured columns should be EntryEntry name, Protein names, Reviewed, Gene names (primary), Gene names (synonym)
human_nameprim_def_syn.tsv	https://www.uniprot.org/uniprot/

# MGI data (download page http://www.informatics.jax.org/downloads/reports/index.html)
MRK_ENSEMBL.rpt	http://www.informatics.jax.org/downloads/reports/MRK_ENSEMBL.rpt
MRK_List2.rpt	http://www.informatics.jax.org/downloads/reports/MRK_List2.rpt
MRK_SwissProt.rpt	http://www.informatics.jax.org/downloads/reports/MRK_SwissProt.rpt

# Mouse expression data
Mus_musculus_RNA-Seq_read_counts_TPM_FPKM_GSE36026.tsv	ftp://ftp.bgee.org/current/download/processed_expr_values/rna_seq/Mus_musculus/

# Mouse Swissprot Entries
Go to Uniprot, click Swissprot and choose minimal number of columns

