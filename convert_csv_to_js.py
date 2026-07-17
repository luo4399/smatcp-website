#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert somatic_fil.csv to JavaScript data for index.html
"""

import csv
import json
from collections import defaultdict

def process_csv():
    # Read CSV file
    mutations = []
    genes_set = set()
    tissues_set = set()
    
    with open('somatic_fil.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mutations.append({
                'chromosome': row['Chromosome'],
                'position': int(row['Position']),
                'ref': row['Ref'],
                'alt': row['Alt'],
                'vaf': float(row['VAF']),
                'region': row['Region'],
                'gene': row['Gene'],
                'subtissue': row['Subtissue'],
                'mutation_type': row['Mutation_type']
            })
            
            # Collect unique genes and tissues
            if row['Gene'] and row['Gene'] != 'Unknown':
                genes_set.add(row['Gene'])
            tissues_set.add(row['Subtissue'])
    
    print(f"Total mutations: {len(mutations)}")
    print(f"Unique genes: {len(genes_set)}")
    print(f"Unique tissues: {len(tissues_set)}")
    
    return mutations, sorted(genes_set), sorted(tissues_set)

def generate_js_data(mutations, genes, tissues):
    """Generate JavaScript code for the data"""
    
    # Generate MOCK_DATA array
    js_code = "    // ===================== REAL DATA FROM CSV =====================\n"
    js_code += "    const MOCK_DATA = [\n"
    
    # Export top 5000 mutations (full dataset too large for browser)
    total = min(5000, len(mutations))
    for i in range(total):
        mut = mutations[i]
        gene_name = mut['gene'] if mut['gene'] != 'Unknown' else 'Unknown'

        js_code += "      {\n"
        js_code += f"        Chromosome: '{mut['chromosome']}',\n"
        js_code += f"        Position: {mut['position']},\n"
        js_code += f"        Ref: '{mut['ref']}',\n"
        js_code += f"        Alt: '{mut['alt']}',\n"
        js_code += f"        VAF: {mut['vaf']:.4f},\n"
        js_code += f"        Region: '{mut['region']}',\n"
        js_code += f"        Gene: '{gene_name}',\n"
        js_code += f"        Subtissue: '{mut['subtissue']}',\n"
        js_code += f"        Mutation_type: '{mut['mutation_type']}'\n"
        js_code += "      }" + ("," if i < total - 1 else "") + "\n"
    
    js_code += "    ];\n\n"
    
    # Generate GENES array from unique genes in data
    gene_list = []
    gene_positions = {}
    
    for mut in mutations:
        gene = mut['gene']
        if gene and gene != 'Unknown' and gene not in gene_positions:
            gene_positions[gene] = {
                'chr': mut['chromosome'],
                'pos': mut['position']
            }
    
    # Take top 50 most common genes
    gene_counts = defaultdict(int)
    for mut in mutations:
        if mut['gene'] and mut['gene'] != 'Unknown':
            gene_counts[mut['gene']] += 1
    
    top_genes = sorted(gene_counts.items(), key=lambda x: x[1], reverse=True)[:200]
    
    js_code += "    const GENES = [\n"
    for gene, count in top_genes:
        if gene in gene_positions:
            pos_info = gene_positions[gene]
            js_code += f"      {{ name: '{gene}', chr: '{pos_info['chr']}', start: {pos_info['pos']}, end: {pos_info['pos'] + 10000}, desc: '{gene} gene' }},\n"
    js_code += "    ];\n\n"
    
    # Generate TISSUES array
    tissue_mapping = {
        'Whole_Blood': {'name': 'Whole Blood', 'germ': 'Mesoderm', 'germClass': 'blood', 'icon': 'fa-droplet'},
        'Liver': {'name': 'Liver', 'germ': 'Endoderm', 'germClass': 'endo', 'icon': 'fa-liver'},
        'Gallbladder': {'name': 'Gallbladder', 'germ': 'Endoderm', 'germClass': 'endo', 'icon': 'fa-droplet'},
        'Pancreas_Head': {'name': 'Pancreas Head', 'germ': 'Endoderm', 'germClass': 'endo', 'icon': 'fa-disease'},
        'Muscle': {'name': 'Muscle', 'germ': 'Mesoderm', 'germClass': 'meso', 'icon': 'fa-dumbbell'},
        'Heart_Left_Atrium': {'name': 'Heart Left Atrium', 'germ': 'Mesoderm', 'germClass': 'meso', 'icon': 'fa-heart-pulse'},
        'Heart_Right_Atrium': {'name': 'Heart Right Atrium', 'germ': 'Mesoderm', 'germClass': 'meso', 'icon': 'fa-heart-pulse'},
        'Heart_Left_Ventricle': {'name': 'Heart Left Ventricle', 'germ': 'Mesoderm', 'germClass': 'meso', 'icon': 'fa-heart'},
        'Heart_Right_Ventricle': {'name': 'Heart Right Ventricle', 'germ': 'Mesoderm', 'germClass': 'meso', 'icon': 'fa-heart'},
        'Heart_Mitral_Valve': {'name': 'Heart Mitral Valve', 'germ': 'Mesoderm', 'germClass': 'meso', 'icon': 'fa-heart-circle-check'},
        'Heart_Tricuspid_Valve': {'name': 'Heart Tricuspid Valve', 'germ': 'Mesoderm', 'germClass': 'meso', 'icon': 'fa-heart-circle-plus'},
        'Adrenal_Gland': {'name': 'Adrenal Gland', 'germ': 'Ectoderm', 'germClass': 'ecto', 'icon': 'fa-kidney'},
        'Skin': {'name': 'Skin', 'germ': 'Ectoderm', 'germClass': 'ecto', 'icon': 'fa-hand-dots'},
    }
    
    js_code += "    const TISSUES = [\n"
    for tissue in sorted(tissues):
        if tissue in tissue_mapping:
            t = tissue_mapping[tissue]
            js_code += f"      {{ name: '{t['name']}', germ: '{t['germ']}', germClass: '{t['germClass']}', icon: '{t['icon']}' }},\n"
    js_code += "    ];\n"
    
    return js_code

if __name__ == '__main__':
    mutations, genes, tissues = process_csv()
    js_code = generate_js_data(mutations, genes, tissues)
    
    # Write to output file
    with open('data_output.js', 'w', encoding='utf-8') as f:
        f.write(js_code)
    
    print("\nJavaScript code generated successfully!")
    print("Output saved to: data_output.js")
