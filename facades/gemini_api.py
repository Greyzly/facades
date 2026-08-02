import requests
import time
import json
import logging

def ask_gemini_with_fallback(prompt: str, api_key: str) -> str:
    """
    Queries the Gemini API using the Streaming endpoint (Server-Sent Events).
    Receives text in parts to avoid connection timeouts, while still auto-continuing 
    if the model hits its maximum token output limit.
    """

    models = [
        # The newest release (includes a Free Tier)
        "gemini-3.5-flash",
        
        # 3.x Family (GA and Previews)
        # "gemini-3-flash",
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite",          # Note: This went GA in May 2026, no '-preview' needed
        "gemini-3.1-flash-lite-preview",
        
        # Your original 2.5 list
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ]
    
    headers = {
        "Content-Type": "application/json"
    }
    
    conversation_contents = [{"role": "user", "parts": [{"text": prompt}]}]
    full_response = ""
    
    max_retries = 3
    backoff_factor = 2
    max_continuations = 10 
    continuation_count = 0

    for model in models:
        # CHANGED: Using streamGenerateContent with alt=sse
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={api_key}"
        model_failed = False
        
        while True:
            payload = {
                "contents": conversation_contents,
                "generationConfig": {
                    "maxOutputTokens": 65536
                }
            }
            
            success = False
            turn_text = ""
            finish_reason = "STOP"
            
            for attempt in range(max_retries):
                try:
                    # CHANGED: stream=True tells requests to read the connection as it arrives
                    response = requests.post(url, headers=headers, json=payload, timeout=30, stream=True)
                    
                    if response.status_code == 200:
                        success = True
                        
                        # Process the Server-Sent Events (SSE) stream line-by-line
                        for line in response.iter_lines():
                            if line:
                                decoded_line = line.decode('utf-8')
                                
                                # SSE chunks start with "data: "
                                if decoded_line.startswith("data: "):
                                    data_str = decoded_line[6:]
                                    
                                    # The stream ends with a [DONE] flag
                                    if data_str == "[DONE]":
                                        continue
                                        
                                    try:
                                        chunk_data = json.loads(data_str)
                                        candidate = chunk_data['candidates'][0]
                                        
                                        # Safely extract text from the current chunk
                                        parts = candidate.get('content', {}).get('parts', [])
                                        chunk_text = "".join([part['text'] for part in parts if 'text' in part])
                                        turn_text += chunk_text
                                        
                                        # The finish reason is usually only attached to the very last chunk
                                        if 'finishReason' in candidate:
                                            finish_reason = candidate['finishReason']
                                            
                                    except (json.JSONDecodeError, KeyError, IndexError):
                                        # Ignore structural/safety chunks that don't contain text parts
                                        continue
                        break # Successfully read the stream, break retry loop
                        
                    elif response.status_code in [429, 403]:
                        logging.warning(f"[{model}] Quota exceeded (429) or invalid API key (403).")
                        model_failed = True
                        break 
                        
                    elif response.status_code >= 500:
                        logging.warning(f"[{model}] Server error ({response.status_code}). Retrying {attempt + 1}/{max_retries}...")
                        time.sleep(backoff_factor ** attempt)
                        continue
                        
                    else:
                        logging.error(f"[{model}] Fatal error ({response.status_code}): {response.text}")
                        return None
                        
                except requests.exceptions.RequestException as e:
                    # Network/Timeout Errors
                    logging.warning(f"[{model}] Network/Stream error: {e}. Retrying {attempt + 1}/{max_retries}...")
                    time.sleep(backoff_factor ** attempt)
                    continue
            
            # If model failed or max retries reached, exit this model's while loop to fallback
            if model_failed or not success:
                break
            
            full_response += turn_text
            
            # If the stream finished because it hit the token limit, trigger a continuation
            if finish_reason == "MAX_TOKENS" and continuation_count < max_continuations:
                continuation_count += 1
                logging.info(f"[{model}] Hit MAX_TOKENS limit. Requesting continuous flow chunk {continuation_count}...")
                
                conversation_contents.append({"role": "model", "parts": [{"text": turn_text}]})
                conversation_contents.append({
                    "role": "user", 
                    "parts": [{"text": "Continue your response exactly where you left off. Do not repeat anything you already wrote, and do not add conversational introduction filler. Just seamlessly continue."}]
                })
                continue 
            else:
                return full_response
                
        logging.info(f"--- Exhausted options or switched from {model}, moving down the list. ---")

    logging.error("All available free models failed or exhausted their quota.")
    return full_response if full_response else None

# --- Usage Example ---
if __name__ == "__main__":
    API_KEY = "KEY_HERE"
    PROMPT = "PROMPT_HERE"
    
    result = ask_gemini_with_fallback(PROMPT, API_KEY)
    print("\nFinal Output:\n")
    print(result)