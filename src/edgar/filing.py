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