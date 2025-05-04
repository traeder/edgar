import re

def filing_to_json(company, filing):
    raw_filing = filing._filing
    ret = {
        'filing_id': raw_filing.accession_no,
        'company_name': raw_filing.company,
        'ticker': company.tickers[0],
        'cik': raw_filing.cik,
        'sic': company.sic,
        'industry': company.industry,
        'filing_type': raw_filing.form,
        'filing_date': f'{raw_filing.filing_date:%Y-%m-%d}',
        'period_end_date': raw_filing.period_of_report
    }
    for item in filing.items:
        label = re.sub(r'\s+', '', item.lower()).replace('.', '')
        ret[label] = filing[item]
    return ret

    def index_filing(company, filing, raise_errors=True, summaries=False):
    try:
        j = filing_to_json(company, filing)
        sxns = ['1', '1a', '7', '7a'] if '10-K' in filing.form else ['1a', '2']
        if summaries:
            for s in sxns:
                key = f'item{s}'
                if key in j:
                    j[f'{key}_summary'] = summarize_with_claude(j[key])
        solr.add([j], commit=True, overwrite=True)
    except Exception as e:
        print(e)
        if raise_errors:
            raise e
        else:
            return None
    return j

def index_lots_of_filings(company, form, start_date, end_date, raise_errors=True, summaries=False):
    ret = []
    filings = company.get_filings(form=form, filing_date=f"{start_date}:{end_date}")
    for filing in tqdm(filings):
        indexed_filing = index_filing(company, filing.obj(), summaries=summaries, raise_errors=raise_errors)
        ret.append(indexed_filing)
        if summaries:
            time.sleep(30)
    return ret