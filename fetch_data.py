import json
import time
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from categories_store import get_categories_by_label

API_URL = "https://terraria.wiki.gg/api.php"
HEADERS = {"User-Agent": "TerrariaLLMBuilder/1.0 (jacekloboda55@gmail.com)"}

BASE_DIR = Path(__file__).parent
OUTPUT_FILE = BASE_DIR / "wiki_data.jsonl"

def get_category_members(category_name: str) -> list[str]:
    members = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category_name}",
        "cmnamespace": 0,
        "cmlimit": 500,
        "format": "json"
    }

    while True:
        response = requests.get(API_URL, headers=HEADERS, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        for item in data.get("query", {}).get("categorymembers", []):
            members.append(item["title"])
        
        if "continue" in data:
            params.update(data["continue"])
            time.sleep(0.5)
        else:
            break
            
    return members

def get_clean_text(page_title: str) -> str:
    params = {
        "action": "parse",
        "page": page_title,
        "prop": "text",
        "format": "json",
        "redirects": 1 
    }
    
    try:
        response = requests.get(API_URL, headers=HEADERS, params=params, timeout=30)
        data = response.json()
        
        if "parse" in data and "text" in data["parse"]:
            html_content = data["parse"]["text"]["*"]
            soup = BeautifulSoup(html_content, "html.parser")
            
            for unwanted in soup(['script', 'style', 'sup', 'table']):
                unwanted.extract()
                
            unwanted_classes = [
                'navbox',          
                'mw-collapsible',  
                'infobox',         
                'toc',             
                'noprint',         
                'mw-editsection',  
                'box-bottom'       
            ]
            
            for cls in unwanted_classes:
                for element in soup.find_all(class_=cls):
                    element.extract() 
                    
            for edit_span in soup.find_all('span', class_='mw-editsection'):
                edit_span.extract()
                    
            text = soup.get_text(separator=" ", strip=True)
            return text
            
    except Exception as e:
        print(f"Error fetching text for {page_title}: {e}")
        
    return ""

def main() -> None:
    core_categories = get_categories_by_label("core")
    print(f"Core categories: {len(core_categories)}")
    
    if not core_categories:
        print("Error, no core categories found.")
        return

    visited_pages = set()
    
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        
        for category in core_categories[:2]:
            print(f"\nCategory: {category}")
            page_titles = get_category_members(category)
            print(f"Found articles: {len(page_titles)}")
            
        
            for title in page_titles[:2]:
                if title in visited_pages:
                    continue
                
                print(f"Fetching text: {title}")
                text = get_clean_text(title)
                
                if text:
                    clean_content = "\n".join([line.strip() for line in text.split("\n") if line.strip()])
                    
                    record = {
                        "title": title,
                        "source_category": category,
                        "content": clean_content
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    f.flush()
                    
                visited_pages.add(title)
                time.sleep(1)

    print(f"\nData saved to: {OUTPUT_FILE.resolve()}")

if __name__ == "__main__":
    main()