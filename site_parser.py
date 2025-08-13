import requests
import json
from bs4 import BeautifulSoup
import re
import sys
import argparse
from urllib.parse import urlparse

def clean_html_tags(text):
    if not text:
        return ""
    clean_text = re.sub(r'<br\s*/?>', '\n', text)
    clean_text = re.sub(r'<.*?>', '', clean_text)
    return clean_text.strip()

def parse_itmo_program(url: str):
    print(f"requesting: {url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(e)
        return None

    print("Page loaded, parsing...")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})
    
    try:
        if next_data_script:
            script_content = next_data_script.get_text()
            if script_content:
                data = json.loads(script_content)
                page_props = data.get('props', {}).get('pageProps', {})
            else:
                print("Script content is empty")
                return None
        else:
            print("Could not find __NEXT_DATA__ script")
            return None
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"Error parsing JSON data: {e}")
        return None

    api_program = page_props.get('apiProgram', {})
    json_program = page_props.get('jsonProgram', {})
    supervisor_data = page_props.get('supervisor', {})
    team_data = page_props.get('team', [])
    
    # Парсинг информации о команде преподавателей
    teaching_staff = []
    for member in team_data:
        staff_member = {
            "name": f"{member.get('firstName', '')} {member.get('lastName', '')}".strip(),
            "middle_name": member.get('middleName'),
            "photo_url": member.get('photo'),
            "degree": member.get('degree'),
            "rank": member.get('rank'),
            "positions": []
        }
        
        # Парсинг должностей
        positions = member.get('positions', [])
        for position in positions:
            staff_member["positions"].append({
                "department_name": position.get('department_name'),
                "department_link": position.get('department_link'),
                "position_name": position.get('position_name')
            })
        
        teaching_staff.append(staff_member)
    
    program_info = {
        "program_name": api_program.get('title'),
        "page_url": url,
        "faculty": {
            "name": api_program.get('faculties', [{}])[0].get('title'),
            "link": api_program.get('faculties', [{}])[0].get('link'),
        },
        "description": {
            "short": clean_html_tags(json_program.get('about', {}).get('lead')),
            "full": clean_html_tags(json_program.get('about', {}).get('desc')),
        },
        "main_parameters": {
            "study_format": api_program.get('study', {}).get('mode'),
            "duration": api_program.get('study', {}).get('label'),
            "language": api_program.get('language'),
            "tuition_fee_rub_per_year": api_program.get('educationCost', {}).get('russian'),
            "state_accreditation": api_program.get('hasAccreditation'),
            "military_training_center": api_program.get('isMilitary'),
            "additional_options": api_program.get('type'),
        },
        "career_prospects": clean_html_tags(json_program.get('career', {}).get('lead')),
        "program_manager": {
            "name": f"{supervisor_data.get('firstName')} {supervisor_data.get('lastName')}",
            "middle_name": supervisor_data.get('middleName'),
            "photo_url": supervisor_data.get('photo'),
            "degree": supervisor_data.get('degree'),
            "rank": supervisor_data.get('rank'),
            "positions": [
                {
                    "department_name": pos.get('department_name'),
                    "department_link": pos.get('department_link'),
                    "position_name": pos.get('position_name')
                } for pos in supervisor_data.get('positions', [])
            ],
            "contacts": {
                "email": json_program.get('supervisor', {}).get('email'),
                "phone": json_program.get('supervisor', {}).get('phone'),
            }
        },
        "teaching_staff": teaching_staff,
        "social_media": json_program.get('social'),
        "fields_of_study": [
            {
                "code": direction.get("code"),
                "name": direction.get("title"),
                "admission_quotas": {
                    "budget_funded": direction.get("admission_quotas", {}).get("budget"),
                    "fee_based": direction.get("admission_quotas", {}).get("contract"),
                    "targeted": direction.get("admission_quotas", {}).get("target_reception"),
                }
            } for direction in api_program.get('directions', [])
        ],
        "partners": [f"https://abit.itmo.ru/{img_path}" for img_path in json_program.get('partnersImages', [])],
    }

    print("Succesfully parsed")
    return program_info


def extract_program_id_from_url(url: str) -> str:
    try:
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        if len(path_parts) >= 3 and path_parts[0] == 'program':
            return path_parts[-1]
        else:
            return path_parts[-1] if path_parts else 'unknown'
    except Exception as e:
        print(f"Error extracting program ID from URL: {e}")
        return 'unknown'


def save_to_json(data: dict, filename: str):
    if not data:
        return
    
    try:
        with open(f'results/{filename}', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Saved to file: {filename}")
    except IOError as e:
        print(f"Error saving file {e}")

def main():
    parser = argparse.ArgumentParser(description='Parse ITMO program data from URL')
    parser.add_argument('url', nargs='?',
                       default="https://abit.itmo.ru/program/master/ai_product",
                       help='URL of the ITMO program page to parse')
    
    args = parser.parse_args()
    url = args.url
    
    program_id = extract_program_id_from_url(url)
    output_filename = f"itmo_program_data_{program_id}.json"
    
    print(f"Parsing URL: {url}")
    print(f"Output file: {output_filename}")
    
    parsed_data = parse_itmo_program(url)
    
    if parsed_data:
        save_to_json(parsed_data, output_filename)
    else:
        print("Failed to parse program data")
        sys.exit(1)


if __name__ == "__main__":
    main()