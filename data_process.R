somatic <- fread("/media/london_A/kewei/2025.04.16_somatic/Project_SNV/2025.08.04_sSNV/data/summary/integrated_variants.csv")
head(somatic,20)
somatic[, mutation_type := ifelse(
  nchar(ref) == 1 & nchar(alt) == 1,
  "SNV",
  "INDEL"
)]


somatic_fil <- somatic %>% dplyr::select(
  Chromosome = chr, 
  Position = pos, 
  Ref = ref, 
  Alt = alt,
  VAF,
  Region = region,
  Gene = gene,
  Subtissue = subtissue,
  Mutation_type = mutation_type)

fwrite(somatic_fil,"/media/iceland/share/Datasets/Archives/luodl/somatic/somatic_fil.csv")
