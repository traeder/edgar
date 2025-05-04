import requests
import os
import json

def summarize_with_claude(text):
    msg = f"The following is text from a company's SEC filing.  Act as a financial analyst and summarize the most important elements with bullet points: <text>{text}</text>"
    return send_message_to_claude(msg, max_tokens=50_000, api_key=claude_api_key)

def get_filters_from_claude(user_query):
    today = pd.Timestamp('now')
    oya = today - pd.DateOffset(years=1)

    msg = f"""You are an expert system designed to extract key filtering information from user queries about SEC filings.
Analyze the user's query and extract the following information, returning it as a JSON object:
- "company_names": A list of names of companies mentioned by the user. 
- "tickers": A list of tickers for the companies mentioned by the user, if you know them.
- "sic_codes" a list of sic codes for industries mentioned by the user.
- "sections" a list of 10-K section identifiers potentially relevant to the user's query if you can determine this.  It's ok to speculate here because I'll pull multiple documents.  Use only the item number (i.e. "Item 7")
- "filing_start_date" the first date of documents potentially relevant to the question.  For questions that appear to ask about the present, you can set this to {oya:%Y-%m-%d}.
- "filing_end_date" the last date of the documents potentially relevant to the question. For questions that appear to ask about the present, you can set this to {today:%Y-%m-%d}.

If any piece of information is not present in the query, use a null value for that key in the JSON.  Return only the JSON.  Do not return any explanation.

User Query: "{user_query}"

JSON Output: """
    
    return send_message_to_claude(system_prompt='', user_prompt=msg, max_tokens=50_000, api_key=claude_api_key)

def answer_with_claude(question, max_results=10):
    filters_text = get_filters_from_claude(question)
    filters_text = filters_text.replace("```json", "").replace("```", "")
    print(filters_text)
    filters_json = json.loads(filters_text)
    query = build_query_from_filters(filters_json, question, max_results=max_results)
    print(query)
    results = solr.search(**query)
    ctx = get_context_from_results(results)

    return ask_claude(question, ctx)

def ask_claude(question, ctx):
    system_msg = f"""You are a specialized financial analyst AI. Your task is to analyze SEC filings and answer the user's question with a structured report that includes precise citations.

**Instructions:**
1. **Analyze the Context:** Carefully examine the user's question and all provided context passages from SEC filings.
2. **Structure Your Answer as a Report:** 
   - Begin with a concise executive summary that directly answers the question
   - Follow with detailed supporting analysis
   - Use clear headings to organize your response
3. **Answer from Context Only:** Base your analysis exclusively on the provided passages. Do not introduce external knowledge or speculation.
4. **Provide Precise Citations:** For every claim or data point in your answer:
   - Include the exact source (filing_id, company name, filing date if available)
   - Quote the relevant text directly when appropriate
   - Format citations as [Company Name (filing_id), Section/Page if available]
5. **Present Data Effectively:** When relevant, summarize numerical data in tables for clarity
6. **Compare Across Companies:** When the question involves multiple companies, organize your analysis to facilitate comparison
7. **If Unanswerable:** If the context lacks information to answer the question properly, state this clearly and explain what specific information would be needed.
"""
    user_msg = f"""    
**Context Passages:**
{ctx}

**User Question:**
{question}

**Analysis Report:**
    """

    return send_message_to_claude(system_msg, user_msg, max_tokens=50_000, api_key=claude_api_key)

def build_one_query(name, options):
    return f"{name}:({' OR '.join(map(str, options))})"

def build_many_queries(options_dict):
    return [build_one_query(k, v) for k, v in options_dict.items()]

def build_query_from_filters(filters_json, question, max_results=10):
    query = {}
    options_dict = {'ticker': filters_json.get('tickers'),
                    'sic': filters_json.get('sic_codes')
                   }
    if filters_json['filing_start_date'] is not None:
        fsd_ = pd.Timestamp(filters_json['filing_start_date'])
        fsd = f"{fsd_:%Y-%m-%d}T00:00:00Z"
        fed_ = pd.Timestamp(filters_json.get('filing_end_date', 'now'))
        fed = f"{fed_:%Y-%m-%d}T00:00:00Z"
        options_dict['filing_date'] = [f'[{fsd} TO {fed}]']
    options_dict = {k: v for k, v in options_dict.items() if v is not None and v != []}
    items = filters_json.get('sections', 'item1,item1a,item7,item7a,item8')
    items = ','.join(items).lower().replace(' ', '')
    clean_question = re.sub(r'[^a-z0-9 ]', '', question.lower())
    
    query['q'] = "{!edismax qf=\"all_text^3 item1^3 item7^3 company_name^2 ticker^1.5 industry^1\" pf=\"all_text^5 item1^5 item7^5\" mm=2 tie=0.1}" + f'({clean_question})'
    query["fq"] = build_many_queries(options_dict)
    query['fl'] = f"company_name,filing_type,period_end_date,{items}",
    query["sort"] = "period_end_date desc",
    query["rows"] = max_results
    return query
    
def get_context_from_results(results):
    return json.dumps(results.docs)