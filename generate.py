import sys
import re
import os
import traceback

import pyarrow.csv as csv
from jinja2 import Environment, FileSystemLoader, select_autoescape


def normalize_filename(fname):
    '''turn a language name into a pleasant-looking filename'''
    fname = fname.lower().replace(' ', '_').replace('(', '_').replace(')', '_')
    fname = fname.replace("'", '_').replace('"', '_')
    fname = re.sub(r'_+', '_', fname)
    return fname


def skip_comments(row):
    if row.text.startswith('#'):
        return 'skip'


def read_tsv_pa(fname, column_names, usecols=None):
    parse_options = csv.ParseOptions(
        delimiter='\t',
        invalid_row_handler=skip_comments,
    )
    convert_options = csv.ConvertOptions(
        include_columns=usecols,
    )
    read_options = csv.ReadOptions(
        column_names=column_names,
        skip_rows=1,
    )

    table = csv.read_csv(
        fname,
        parse_options=parse_options,
        convert_options=convert_options,
        read_options=read_options,
    )

    return table


env = Environment(
    loader=FileSystemLoader('./templates'),
    autoescape=select_autoescape(['html'])
)


language_type_map = {  # note the lower case
    #'A': 'ancient',  # seems to have been deprecated a while ago
    'C': 'constructed',
    'E': 'extinct',
    'H': 'historical',
    'L': 'living',
    'S': 'special',
}

extras = {
    # macrolanguages: if these are > 50mm speakers, label them big
    'ara': {'Id': 'ara', 'Names': [],        'noedit': True, 'big': True, 'comment': 'See Modern Standard Arabic, and many others'},
    'fas': {'Id': 'fas', 'Names': ['Farsi'], 'noedit': True, 'big': True, 'comment': 'See Iranian Persian, Dari, and Tajik'},
    'msa': {'Id': 'msa', 'Names': [],        'noedit': True, 'big': True, 'comment': 'See Indonesian, and 34 other languages with Malay in their name'},
    'zho': {'Id': 'zho', 'Names': [],        'noedit': True, 'big': True, 'comment': 'See Mandarin Chinese and the many other Chinese languages'},
    'lah': {'Id': 'lah', 'Names': [],        'noedit': True, 'big': True, 'comment': 'Macrolanguage. See Western Panjabi and [the list here](https://en.wikipedia.org/wiki/Lahnda)'},
    # macro not big
    'pus': {'Id': 'pus', 'Names': ['Pashto'], 'noedit': True, 'comment': 'See Northern, Southern, and Central Pashto'},  # 40mm speakers
    # not macro, still no edit
    'eng': {'Id': '', 'Names': [], 'noedit': True, 'comment': ''},
    'rus': {'Id': '', 'Names': [], 'noedit': True, 'comment': ''},
    'deu': {'Id': '', 'Names': [], 'noedit': True, 'comment': ''},
    'spa': {'Id': 'spa', 'Names': [], 'noedit': True, 'comment': 'We may eventually make a geographic breakdown'},
    'fra': {'Id': '', 'Names': [], 'noedit': True, 'comment': ''},
    # other
    'pnb': {'Id': 'pnb', 'Names': ['Lahndi'], 'comment': 'See also [the list here](https://en.wikipedia.org/wiki/Lahnda)'},
    'por': {'Id': 'por', 'Names': [], 'comment': 'Includes Brazil, we may break that out later'},
    #'': {'Id': '', 'Names': [], 'noedit': True, 'comment': ''},
}


basedir = '../web-languages'


def add_names(entry, names):
    Names = [entry['Ref_Name']] + entry.get('Extra_Names', [])
    for name in names:
        if not Names.count(name):
            if 'Extra_Names' not in entry:
                entry['Extra_Names'] = []
            entry['Extra_Names'].append(name)


def main():
    column_names = ['Id', 'Part2b', 'Part2t', 'Part1', 'Scope', 'Language_Type', 'Ref_Name', 'Comment']
    usecols = None  # list of str
    table = read_tsv_pa('iso-639-3_Code_Tables_20240415/iso-639-3.tab', column_names=column_names, usecols=usecols)
    print('ISO-639-3 rows', table.num_rows)
    types = set(table['Language_Type'].to_pylist())

    column_names = ['Name', 'Code', 'Family', 'Script', 'doc_count', 'image_count', 'token_count']
    usecols = ['Name', 'Code', 'Script', 'doc_count']
    mOSCAR_table = read_tsv_pa('mOSCAR_table.tsv', column_names=column_names, usecols=usecols)
    print('mOSCAR rows', mOSCAR_table.num_rows)

    column_names = ['Id', 'Name', 'speakers']
    usecols = None
    wikipedia_size_table = read_tsv_pa('wikipedia_size.tsv', column_names=column_names, usecols=usecols)
    print('wikipedia_size rows', wikipedia_size_table.num_rows)

    column_names = ['wiki_code', 'iso_code', 'iso_name', 'wiki_name', 'wiki_local_name']
    usecols = None
    wikipedia_languages_table = read_tsv_pa('wikipedia_languages_all.tsv', column_names=column_names, usecols=usecols)
    print('wikipedia_language rows', wikipedia_languages_table.num_rows)

    # these are small so let's do it in python
    table_dicts = table.to_pylist()  # list of dictionaries
    mOSCAR_dicts = mOSCAR_table.to_pylist()
    wikipedia_size_dicts = wikipedia_size_table.to_pylist()
    wikipedia_languages_dicts = wikipedia_languages_table.to_pylist()

    assert len(table_dicts) == len(set(x['Id'] for x in table_dicts)), 'check that ISO 639 Ids are unique'
    assert len(table_dicts) == len(set(x['Ref_Name'] for x in table_dicts)), 'check that ISO 639 Ref_Names are unique'

    # split Code into a useful Id and ISO standard script name
    # scrpt https://en.wikipedia.org/wiki/ISO_15924
    for d in mOSCAR_dicts:
        d['Id'], d['scrpt'] = d['Code'].split('_')

    # start the main table
    ids = {}
    for d in table_dicts:
        Id = d['Id']
        ids[Id] = d

    # add in info from mOSCAR
    for d in mOSCAR_dicts:
        if d['Id'] == 'ajp':
            # special fixup (2023): ajp (South) -> apc (formerly North) and the ref_name is Levantine Arabic
            # the ref_name for ajp is alreay set to Levantine Arabic at this point
            # by NOT changing the 'Name', both North and South will be Extra_Names
            d['Id'] = 'apc'
        Id = d['Id']
        if Id not in ids:
            print(f'warning: mOSCAR Id {Id} not in table, skipping')
            continue
        entry = ids[Id]
        for name in ('Extra_Names', 'Scripts', 'scrpts'):
            if name not in entry:
                entry[name] = []
        if entry['Ref_Name'] != d['Name']:
            entry['Extra_Names'].append(d['Name'])

        for name in ('Script', 'scrpt'):
            entry[name+'s'].append(d[name])
            if len(entry[name+'s']) > 1:
                # zho really is 2; apc is 2 Arabics; eventually belarusian will have 2
                entry[name+'s'] = list(set(entry[name+'s']))
        if 'mOSCAR_doc_count' not in entry:
            entry['mOSCAR_doc_count'] = 0
        entry['mOSCAR_doc_count'] += d['doc_count']

    # wikipedia_size_table Id Name speakers -- these are all big
    for d in wikipedia_size_dicts:
        Id = d['Id']
        if Id not in ids:
            print(f'warning: wikipedia_size Id {Id} not in table, skipping')
            continue
        entry = ids[Id]
        entry['big'] = True
        if d['Name']:
            add_names(entry, [d['Name']])

    # wikipedia_languages wiki_code and maybe names
    # 'wiki_code', 'iso_code', 'iso_name', 'wiki_name', 'wiki_local_name'
    for d in wikipedia_languages_dicts:
        Id = d['iso_code']
        if Id not in ids:
            print(f'warning: wikipedia_languages Id {Id} not in table, skipping')
            continue
        entry = ids[Id]
        entry['wiki_code'] = d['wiki_code'] # XXX only allows one. Belarusian has 2.
        names = [x for x in [d['wiki_name'], d['wiki_local_name']] if x]
        if names:
            add_names(entry, names)

    # add in extras
    for Id, d in extras.items():
        if Id not in ids:
            # eventually we will use this to add new entries, but not yet (e.g. Taiwanese)
            print(f'warning: extras Id {Id} not in table')
            continue
        entry = ids[Id]
        if d['Names']:
            add_names(entry, d['Names'])
        for field in ('noedit', 'big', 'comment'):
            if field in d:
                entry[field] = d[field]

    # zip the scripts
    for k, v in ids.items():
        if 'Scripts' in v:  # means scrpts should also be present
            v['script_zip'] = zip(v['Scripts'], v['scrpts'])

    for type_ in types:
        os.makedirs(basedir.rstrip('/') + '/' + language_type_map[type_], exist_ok=True)

    for k, v in ids.items():
        fname = normalize_filename(v['Ref_Name']) + '.md'
        v['fname'] = fname
        fname = basedir.rstrip('/') + '/' + language_type_map[v['Language_Type']] + '/' + fname

        template = env.get_template('ref_name.template')
        with open(fname, 'w') as f:
            try:
                f.write(template.render(**v)+'\n')
            except Exception as e:
                print('got exception {} processing {}, skipping'.format(str(e), d), file=sys.stderr)
                print(traceback.format_exc())

    for type_ in types:
        print('type_', type_)
        type_list_big = []
        type_list = []
        for v in ids.values():
            if v['Language_Type'] == type_:
                if v.get('big'):
                    type_list_big.append(v)
                else:
                    type_list.append(v)
        if type_list_big:
            type_list_big = sorted(type_list_big, key=lambda k: k['Ref_Name'])
        type_list = sorted(type_list, key=lambda k: k['Ref_Name'])

        type_name = language_type_map[type_]
        template = env.get_template('type.template')

        fname = basedir.rstrip('/') + '/' + type_name + '/README.md'
        top = False
        subdir = type_name + '/'
        with open(fname, 'w') as f:
            try:
                f.write(template.render(
                    type_name=type_name, top=top, subdir=subdir, type_list_big=type_list_big, type_list=type_list
                )+'\n')
            except Exception as e:
                print('got exception {} processing {}, skipping'.format(str(e), d), file=sys.stderr)
                print(traceback.format_exc())
        if os.path.getsize(fname) > 500 * 1024:
            raise ValueError(f'{fname} is too big for github to display')

        if type_ != 'L':
            continue

        # top level README
        fname = basedir.rstrip('/') + '/' + '/README.md'
        top = True
        subdir = type_name + '/'
        with open(fname, 'w') as f:
            try:
                f.write(template.render(
                    type_name=type_name, top=top, subdir=subdir, type_list_big=type_list_big, type_list=type_list
                )+'\n')
            except Exception as e:
                print('got exception {} processing {}, skipping'.format(str(e), d), file=sys.stderr)
                print(traceback.format_exc())

        if os.path.getsize(fname) > 500 * 1024:
            raise ValueError(f'{fname} is too big for github to display')


if __name__ == '__main__':
    main()
