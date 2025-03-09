import pysolr
import json
import requests

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
        }
        ] + [
            {"name": f"item{c}", "type": "text_sec", "indexed": True, "stored": True}
            for c in ['1', '1A', '1B', '1C', 2, 3, 4, 5, 6, 7, '7A', 8, 9, '9A', '9B', '9C', 10, 11, 12, 13, 14, 15, 16]
        ]
    }
    
    # Send field type definitions
    response = requests.post(schema_url, json=field_types)
    
    # Send field definitions
    response = requests.post(schema_url, json=fields)
    
    return response.json()

def summarize_with_claude(text):
    msg = f"The following is text from a company's SEC filing.  Act as a financial analyst and summarize the most important elements with bullet points: <text>{text}</text>"
    return send_message_to_claude(msg, max_tokens=50_000, api_key=claude_api_key)


# Example of indexing a SEC filing
def index_filing(company, filing, raise_errors=True):
    try:
        j = filing_to_json(company, filing)
        for s in ['1', '1a', '7a']:
            j[f'item{s}_summary'] = summarize_with_claude(j[f'item{s}'])
        solr.add([j], commit=True, overwrite=True)
    except Exception as e:
        print(e)
        if raise_errors:
            raise e

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