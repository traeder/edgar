import re

item_regex = r'ITEM\s*\d+[A-Z]?\s?\.'
space_regex = r'\s+'
item_title_regex = r"(?<!IN\s)(?<!SEE\s)(?<!WITH\s)(?<!UNDER\s)ITEM\s*\d+[A-Z]?\s?\.[ \t\r\f\vA-Z']*"

class SectionParseError(ValueError):
    pass


def extract_sections(filing):
    txt = filing.text()
    matches = re.finditer(item_title_regex, txt.upper().replace("’", "'").replace("‘", "'").replace("’", "'"))
    start = False
    sxns = []
    toc = []
    startix = None
    
    # skip item 1 in the TOC
    toc.append(next(matches).group(0))
    for match in matches:
        # find item 1 again to start the search
        if re.search(r'ITEM\s1\.', match.group(0)) is not None:
            start = True
        elif start is False:
            toc.append(match.group(0))
        if start is True:
            if startix is not None:
                endix = match.span()[0]
                sxns.append(txt[startix:endix])
            startix = match.span()[0]
    sxns.append(txt[startix:])
    return sxns, toc

def get_section_title(s):
    clean_s = re.sub(space_regex, '', s.upper())
    match = re.match(item_regex, clean_s)
    if match is None:
        print(f"no title match for {s[:30]}")
        return ""
    title = match.group(0)
    return title

def match_section_titles(s1, s2):
    return get_section_title(s1) == get_section_title(s2)

def merge_ooo_sections(sxns, toc):
    ret = []
    tocix = 0
    sxnix = 0
    while sxnix < len(sxns):
        if match_section_titles(sxns[sxnix], toc[tocix]):
            ret.append(sxns[sxnix])
            sxnix += 1
            tocix += 1
        else:
            ret[-1] += sxns[sxnix]
            sxnix += 1
    return ret

def clean_print_sections(arr):
    s = [str((i, arr[i][:30])) for i in range(len(arr))]
    print("\n".join(s))

def validate_sections(sxns, toc):
    sxn_summary = [str((i, sxns[i][:30])) for i in range(len(sxns))]
    toc_summary = [str((i, toc[i][:30])) for i in range(len(toc))]
    if len(sxns) != len(toc):
        raise SectionParseError(f"length of sections ({len(sxns)} not equal length of toc {len(toc)}\n\n{"\n".join(sxn_summary)}\n\n{"\n".join(toc_summary)}.")
    for i in range(len(sxns)):
        if not match_section_titles(sxns[i], toc[i]):
            raise SectionParseError(f"section label mismatch at index {i} (first 30 chars shown) {sxn_summary[i]} != {toc_summary[i]}.")
    return True

def filing_to_json(company, filing):
    sections, toc = extract_sections(filing)
    merged = merge_ooo_sections(sections, toc)
    validate_sections(merged, toc)
    ret = {
        'filing_id': filing.accession_no,
        'company_name': filing.company,
        'ticker': company.ticker_display,
        'cik': filing.cik,
        'sic': company.sic,
        'industry': company.industry,
        'filing_type': filing.form,
        'filing_date': f'{filing.filing_date:%Y-%m-%d}',
        'period_end_date': filing.period_of_report
    }
    for section in merged:
        title = get_section_title(section)
        label = re.sub(r'\s+', ' ', title.lower()).replace('.', '')
        print(title, label)
        ret[label] = section
    return ret