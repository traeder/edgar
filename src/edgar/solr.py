import pysolr
import json
import requests
import subprocess

# Connect to Solr
solr = pysolr.Solr('http://localhost:8983/solr/sec_filings/', always_commit=True)

# First, create the collection (if it doesn't exist yet)
# This uses the Solr Collections API
def create_core():
    collection_url = 'http://localhost:8983/solr/admin/cores'
    params = {
        'action': 'CREATE',
        'name': 'sec_filings',
        'instanceDir': 'sec_filings'
    }
    response = requests.get(collection_url, params=params)
    return response.json()

# Define schema using Schema API
def define_schema():
    schema_url = 'http://localhost:8983/solr/sec_filings/schema'
    
    # Define field types
    field_types = {
        "add-field-type": [
            {
                "name": "text_sec",
                "class": "solr.TextField",
                "positionIncrementGap": "100",
                "analyzer": {
                    "tokenizer": {"class": "solr.StandardTokenizerFactory"},
                    "filters": [
                        {"class": "solr.LowerCaseFilterFactory"},
                        {"class": "solr.EnglishPossessiveFilterFactory"},
                        {"class": "solr.EnglishMinimalStemFilterFactory"}
                    ]
                }
            },
            {
                "name": "company_name",
                "class": "solr.TextField",
                "analyzer": {
                    "tokenizer": {"class": "solr.KeywordTokenizerFactory"},
                    "filters": [{"class": "solr.LowerCaseFilterFactory"}]
                }
            }
        ]
    }
    
    # Define fields for each section
    fields = {
        "add-field": [
            {"name": "filing_id", "type": "string", "indexed": True, "stored": True},
            {"name": "company_name", "type": "company_name", "indexed": True, "stored": True},
            {"name": "ticker", "type": "string", "indexed": True, "stored": True},
            {"name": "cik", "type": "string", "indexed": True, "stored": True},
            {"name": "sic", "type": "string", "indexed": True, "stored": True},
            {"name": "industry", "type": "string", "indexed": True, "stored": True},
            {"name": "filing_type", "type": "string", "indexed": True, "stored": True},
            {"name": "filing_date", "type": "pdate", "indexed": True, "stored": True},
            {"name": "period_end_date", "type": "pdate", "indexed": True, "stored": True},
            {
            "name": "all_text",
            "type": "text_sec",
            "indexed": True,
            "stored": False,
            "multiValued": True
        },
        {
            "name": "all_summaries",
            "type": "text_sec",
            "indexed": True,
            "stored": False,
            "multiValued": True
        }] + [
            {"name": f"item{c}", "type": "text_sec", "indexed": True, "stored": True}
            for c in ['1', '1A', '1B', '1C', 2, 3, 4, 5, 6, 7, '7A', 8, 9, '9A', '9B', '9C', 10, 11, 12, 13, 14, 15, 16]
        ]
        + [
            {"name": f"item{c}_summary", "type": "text_sec", "indexed": True, "stored": True}
            for c in ['1', '1A', '1B', '1C', 2, 3, 4, 5, 6, 7, '7A', 8, 9, '9A', '9B', '9C', 10, 11, 12, 13, 14, 15, 16]
        ]
    }

    copy_fields = {
        "add-copy-field": [
            {"source": f['name'], "dest": ["all_text"]}
            for f in fields['add-field'] if f['name'].startswith('item') and not f['name'].endswith('summary')
        ] + [
            {"source": f['name'], "dest": ["all_summaries"]}
            for f in fields['add-field'] if f['name'].endswith('summary')
        ]
    }
    
    # Send field type definitions
    response = requests.post(schema_url, json=field_types)
    
    # Send field definitions
    response = requests.post(schema_url, json=fields)

    # Set unique key
    unique_key = {
        "set-unique-key": "filing_id"
    }
    response = requests.post(schema_url, json=unique_key)

    # don't need this yet
    #response = requests.post(schema_url, json=copy_fields)

    
    return response.json()

def reload_core():
    core_url = 'http://localhost:8983/solr/admin/cores'
    params = {'action': 'RELOAD', 'core': 'sec_filings'}
    response = requests.get(core_url, params=params)
    return response.json()

def delete_core():
    solr_admin_url = 'http://localhost:8983/solr/admin'
    delete_url = f"{solr_admin_url}/cores"
    params = {
        'action': 'UNLOAD',
        'core': 'sec_filings',
        'deleteIndex': 'true',
        'deleteDataDir': 'true',
        'deleteInstanceDir': 'true'
    }
    
    response = requests.get(delete_url, params=params)
    print(f"Core deletion response: {response.json()}")
    return response.json()

def recreate_db():
    delete_core()
    subprocess.run(['mkdir', '-p', '/Users/troyraeder/Downloads/solr/solr-9.8.0/server/solr/sec_filings/conf'])
    p = subprocess.run(
        'cp -r /Users/troyraeder/Downloads/solr/solr-9.8.0/server/solr/configsets/_default/conf/* /Users/troyraeder/Downloads/solr/solr-9.8.0/server/solr/sec_filings/conf'
        ,shell=True)
    print(p)
    create_core()
    define_schema()