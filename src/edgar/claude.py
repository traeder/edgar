import requests
import os
import json

def send_message_to_claude(prompt, model="claude-3-7-sonnet-20250219", max_tokens=1000):
    """
    Send a message to Claude API and get the response
    
    Args:
        prompt (str): The message to send to Claude
        model (str): The Claude model to use
        max_tokens (int): Maximum tokens in the response
        
    Returns:
        str: Claude's response text
    """
    # Get API key from environment variable
    api_key = os.environ["CLAUDE_API_KEY"]

    # API endpoint
    url = "https://api.anthropic.com/v1/messages"
    
    # Headers
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    # Request body
    data = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    # Make the request
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    # Check for errors
    if response.status_code != 200:
        raise Exception(f"API request failed with status code {response.status_code}: {response.text}")
    
    # Parse the response
    result = response.json()
    
    # Extract the content from Claude's response
    return result["content"][0]["text"]