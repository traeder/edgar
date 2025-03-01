import requests
import os
import time
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import logging
import xml.etree.ElementTree as ET
import re


logging.basicConfig(level=logging.INFO)

class EdgarDownloader:
    def __init__(self, user_agent):
        """
        Initialize the SEC EDGAR downloader
        
        Args:
            user_agent (str): Email address or name for SEC request headers
        """
        self.headers = {
            'User-Agent': user_agent
        }
        self.base_url = "https://www.sec.gov/Archives"
        self.edgar_url = "https://www.sec.gov/cgi-bin/browse-edgar"
        # Rate limiting to comply with SEC guidelines (10 requests per second)
        self.request_delay = 0.1
        
    def _make_request(self, url, params=None):
        """Make an HTTP request with rate limiting"""
        time.sleep(self.request_delay)
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code != 200:
            raise Exception(f"Request failed with status code {response.status_code}")
        return response
    
    def get_company_filings(self, ticker, filing_type, count=10):
        """
        Get a list of filings for a particular company
        
        Args:
            ticker (str): Company ticker symbol
            filing_type (str): Type of filing (10-K, 10-Q, 8-K, etc)
            count (int): Number of filings to retrieve
            
        Returns:
            List of dictionaries with filing information
        """
        params = {
            'action': 'getcompany',
            'owner': 'exclude',
            'output': 'xml',
            'CIK': ticker,
            'type': filing_type,
            'count': count
        }
        
        response = self._make_request(f"{self.edgar_url}", params=params)
        #print(response.content)
        # Parse the XML
        root = ET.fromstring(response.content)
    
        # Find all filing elements and extract their HREF values
        filing_hrefs = []
        
        # Navigate to filings in the results section
        filings = root.findall('.//filing')
        
        infos = []
        for filing in filings:
            filing_info = {
                'href': filing.find('filingHREF').text.strip(),
                'type': filing.find('type').text.strip(),
                'filing_date': filing.find('dateFiled').text.strip()
            }
            filing_info['filing_accession_number'] = filing_info['href'].split('/')[-2]
            
            infos.append(filing_info)
            print(filing_info)

        return infos
    
    def download_filing(self, filing, save_path):
        """
        Download a specific filing document by accession number
        
        Args:
            accession_number (str): SEC accession number for the filing
            save_path (str): Directory to save the downloaded filing
            
        Returns:
            Path to the saved filing
        """        
        # Get the index page for this filing
        index_url = filing['href']
        accession_number = filing['filing_accession_number']
        print(index_url)
        response = self._make_request(index_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the filing document link (usually the 10-K, 10-Q, etc. report)
        table = soup.find('table', summary='Document Format Files')
        if not table:
            raise Exception("Could not find document table in index page")
        
        # Look for the primary document (typically has the same name as the filing type)
        filing_link = None
        for row in table.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 3:
                doc_type = cells[0].text.strip()
                if doc_type in ['10-K', '10-Q', '8-K', 'DEF 14A'] or 'htm' in doc_type.lower():
                    filing_link = cells[2].find('a')['href']
                    break
        
        if not filing_link:
            # Fall back to the first .htm file
            for row in table.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 3 and cells[2].find('a') and cells[2].find('a')['href'].endswith(('.htm', '.html')):
                    filing_link = cells[2].find('a')['href']
                    break
                    
        if not filing_link:
            raise Exception("Could not find filing document link")
        
        # Download the actual filing document
        filing_url = f"https://www.sec.gov{filing_link}"
        filing_response = self._make_request(filing_url)
        
        # Create save directory if it doesn't exist
        os.makedirs(save_path, exist_ok=True)
        
        # Extract filing type and date from accession number for filename
        date_part = accession_number.split('-')[0]
        year = date_part[0:4]
        month = date_part[4:6]
        day = date_part[6:8]
        
        # Save the filing
        filename = f"{accession_number}.html"
        file_path = os.path.join(save_path, filename)
        
        with open(file_path, 'wb') as f:
            f.write(filing_response.content)
            
        return file_path

    def download_multiple_filings(self, ticker, filing_type, count=5, save_dir="filings"):
        """
        Download multiple filings for a company
        
        Args:
            ticker (str): Company ticker symbol
            filing_type (str): Type of filing (10-K, 10-Q, 8-K, etc)
            count (int): Number of filings to retrieve
            save_dir (str): Directory to save downloaded filings
            
        Returns:
            DataFrame with information about downloaded filings
        """
        # Get list of filings
        filings = self.get_company_filings(ticker, filing_type, count)
        
        # Create company-specific directory
        company_dir = os.path.join(save_dir, ticker)
        os.makedirs(company_dir, exist_ok=True)
        
        results = []
        
        for filing in filings:
            file_path = self.download_filing(filing, company_dir)
            
            filing['local_path'] = file_path
            filing['download_status'] = 'Success'
            print(f"Downloaded {filing_type} for {ticker} filed on {filing['filing_date']}")
            results.append(filing)
            
        # Create a summary DataFrame
        df = pd.DataFrame(results)
        
        # Save summary to CSV
        summary_path = os.path.join(save_dir, f"{ticker}_{filing_type}_filings.csv")
        df.to_csv(summary_path, index=False)
        
        return df

# Example usage
if __name__ == "__main__":
    # Initialize downloader with your email as the user agent (SEC requirement)
    downloader = EdgarDownloader(user_agent="your_email@example.com")
    
    # Download most recent 10-K filings for Apple
    apple_filings = downloader.download_multiple_filings("AAPL", "10-K", count=3, save_dir="sec_filings")
    
    # Download most recent 10-Q filings for Tesla
    #tesla_filings = downloader.download_multiple_filings("TSLA", "10-Q", count=3, save_dir="sec_filings")
    
    print("Download complete!")