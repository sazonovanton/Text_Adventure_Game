import json
import os
import sys
import re
import time
import threading
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from colorama import init, Fore, Back, Style

# Initialize colorama
init()

# Load environment variables
load_dotenv()

client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url=os.getenv('BASE_URL')
)
MODEL_NAME = os.getenv('MODEL_NAME', 'openai/gpt-4o-mini')
CUSTOM_INPUT_KEY = int(os.getenv('CUSTOM_INPUT_KEY', '9'))  # Default to TAB (ord('\t') == 9)
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Create a logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Generate a unique filename for the session log and player status
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_filename = f"logs/session_{timestamp}.md"
status_filename = f"logs/player_status_{timestamp}.json"

def log_to_file(content):
    with open(log_filename, 'a', encoding='utf-8') as f:
        f.write(content + '\n\n')

def save_player_status(player_info, inventory, current_scene, memory, character_background, action_history):
    status = {
        "player_info": player_info,
        "inventory": inventory,
        "current_scene": current_scene,
        "memory": memory,
        "character_background": character_background,
        "action_history": action_history
    }
    with open(status_filename, 'w', encoding='utf-8') as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def load_game_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_color_tags(text):
    def replace_color(match):
        color = match.group(1).lower()
        content = match.group(2)
        if color == 'black':
            color_code = Fore.BLACK
        else:
            color_code = getattr(Fore, color.upper(), Fore.WHITE)
        return f"{color_code}{content}{Fore.RESET}"

    text = text.replace("<color='", "<color=\"").replace("'>", "\">")
    return re.sub(r'<color="(\w+)">(.*?)</color>', replace_color, text)

def display_header(player_info, inventory):
    header_items = [f"{key.capitalize()}: {value}" for key, value in player_info.items()]
    header = " | ".join(header_items)
    print(parse_color_tags(header))
    print("-" * len(header))
    inventory_str = ", ".join(inventory) if inventory else "Empty"
    print(f"Inventory: {inventory_str}")
    print("-" * len(header))

def display_scene(scene_data, player_info, inventory, selected_option, last_choice=None):
    clear_screen()
    display_header(player_info, inventory)
    if last_choice:
        last_choice = re.sub(r'<color="(\w+)">(.*?)</color>', r'\2', last_choice)
        print(f"\n{Fore.CYAN}Previous choice: {last_choice}{Style.RESET_ALL}")
    print(f"\n{parse_color_tags(scene_data['text'])}")
    print()
    for i, option in enumerate(scene_data['options']):
        option_text = parse_color_tags(option['text'])
        if i == selected_option:
            print(f"{Back.WHITE}{Fore.BLACK}{option_text}{Style.RESET_ALL}")
        else:
            print(option_text)
    print(f"\n{Fore.YELLOW}Press TAB to enter your own option{Style.RESET_ALL}")

def get_key():
    import msvcrt
    while True:
        if msvcrt.kbhit():
            key = ord(msvcrt.getch())
            if key == 224:  # Special keys (arrows, f keys, ins, del, etc.)
                key = ord(msvcrt.getch())
                if key == 72:  # Up arrow
                    return 'UP'
                elif key == 80:  # Down arrow
                    return 'DOWN'
            elif key == 13:  # Enter key
                return 'SELECT'
            elif key == CUSTOM_INPUT_KEY:  # Custom input key (TAB by default)
                return 'CUSTOM'
            elif key == 3:  # Ctrl+C
                raise KeyboardInterrupt
        time.sleep(0.1)  # Add a small delay to reduce CPU usage

loading_animation_active = False

def loading_animation():
    global loading_animation_active
    animation = "|/-\\"
    idx = 0
    while loading_animation_active:
        sys.stdout.write(f"\rPlease wait... {animation[idx % len(animation)]}")
        sys.stdout.flush()
        idx += 1
        time.sleep(0.1)
    sys.stdout.write("\r" + " " * 20 + "\r")  # Clear the loading message
    sys.stdout.flush()

def update_action_history(action_history, user_action, model_response):
    """Update action history with both user action and model response"""
    # Add user action
    action_history.append({
        "type": "user_action",
        "text": user_action
    })
    # Add model response
    action_history.append({
        "type": "model_response",
        "text": model_response['text'] if isinstance(model_response, dict) and 'text' in model_response else str(model_response)
    })
    # Keep only last 6 items (3 pairs of user actions and model responses)
    while len(action_history) > 6:
        action_history.pop(0)

def get_system_prompt(game_state, memory, character_background, formatted_actions):
    return (
        "You are a text-based adventure game. Respond with a JSON object containing:\n"
        '- "text" (scene description)\n'
        '- "options" (array of choices with "text" and "next_scene" properties)\n'
        '- "changes" (modifications to player_info or inventory. Example: {"inventory": {"add": ["key"], "remove": ["potion"], "player_info": {"loaction": "tavern"}})\n'
        '- "character_background" (updates to the character background information)\n'
        "You can modify the player's inventory by adding or removing items.\n"
        "You can change any information in the player_info.\n"
        "You can update the character_background to reflect character development or new information.\n"
        "Use color tags like <color=\"red\">text</color> to highlight only specific important words or phrases, not entire paragraphs.\n"
        'The "memory" field should contain a concise summary of the game session, including:\n'
        "- Key plot points and events that have occurred\n"
        "- Character development and important decisions made by the player\n"
        "- Current goals or objectives the player is pursuing\n"
        "- Potential future plot directions or challenges\n"
        "- Any significant changes in the game world or relationships with NPCs\n"
        "Do not include specific game mechanics like health points or inventory items in the memory.\n"
        "Focus on creating a narrative summary that captures the essence of the story and the player's journey.\n\n"
        f"Current game state:\n{json.dumps(game_state, ensure_ascii=False, indent=2)}\n\n"
        f"Current memory:\n{memory}\n\n"
        f"Current Character Background (not visible to the player):\n{json.dumps(character_background, ensure_ascii=False, indent=2)}\n\n"
        "Use this background information to inform the character's actions, dialogue, and the overall narrative, but do not explicitly mention it to the player.\n"
        "Update the character_background if significant character development occurs or new information about the character is revealed.\n\n"
        f"Last three actions:\n{chr(10).join(formatted_actions[-6:])}\n\n"
        "Use data to maintain continuity and context in the story.\n"
        "To end the game, include an 'end_game' field in the response with a value of 'true'.\n"
        "RETURN JSON ONLY. Do not include any other text in the response."
    )

def call_openai_api(game_state, scene_data, player_info, inventory, selected_option, last_choice, memory, character_background, action_history):
    global loading_animation_active
    loading_animation_active = True
    animation_thread = threading.Thread(target=loading_animation)
    animation_thread.start()

    try:
        # Format action history for the prompt
        formatted_actions = []
        for action in action_history:
            action_type = "User" if action["type"] == "user_action" else "Game"
            formatted_actions.append(f"{action_type}: {action['text']}")

        messages = [
            {
                "role": "system",
                "content": get_system_prompt(game_state, memory, character_background, formatted_actions)
            },
            {
                "role": "user",
                "content": last_choice if last_choice else ""  # Pass only the user's choice as text
            }
        ]
        
        if DEBUG:
            with open("logs/debug_messages.json", 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
        
        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://github.com/sazonovanton/Text_Adventure_Game",  # For openrouter.ai
                "X-Title": "Text Adventure Game", # For openrouter.ai
            },
            model=MODEL_NAME,
            messages=messages,
        )
        content = response.choices[0].message.content
        if DEBUG:
            print(f"\nDebug - API Response: {content}")
        
        # Remove code block markers if present
        content = re.sub(r'^```(?:json|)\s*|\s*```$', '', content.strip())
        # Remove leading and trailing ` characters if present
        content = content.strip('`')
        
        try:
            parsed_content = json.loads(content)
            return parsed_content
        except json.JSONDecodeError as json_err:
            print(f"\nError: Invalid JSON response from API\nResponse content: {content}\nJSON Error: {json_err}")
            error_log_filename = f"logs/error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(error_log_filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Response content saved to file: {error_log_filename}")
            sys.exit(1)
    except Exception as e:
        print(f"\nOpenAI API error: {e}")
        error_log_filename = f"logs/error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(error_log_filename, 'w', encoding='utf-8') as f:
            f.write(str(e))
        print(f"Error details saved to file: {error_log_filename}")
        sys.exit(1)
    finally:
        loading_animation_active = False
        animation_thread.join()

def apply_changes(player_info, inventory, changes):
    if changes:
        if 'player_info' in changes:
            player_info.update(changes['player_info'])
        if 'inventory' in changes:
            if 'add' in changes['inventory']:
                if changes['inventory']['add'] != []:
                    inventory.extend(changes['inventory']['add'])
            if 'remove' in changes['inventory']:
                if changes['inventory']['remove'] != []:
                    for item in changes['inventory']['remove']:
                        if item in inventory:
                            inventory.remove(item)

def main():
    game_data = load_game_data(os.getenv('GAME_DATA_FILE', 'game_data.json'))
    player_info = game_data['player_info']
    inventory = game_data['inventory']
    current_scene = game_data['current_scene']
    character_background = game_data.get('character_background', {})
    last_choice = None
    memory = ""
    action_history = []

    log_to_file(f"# Game Session Log\n\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_to_file(f"## Initial Character Background\n\n{json.dumps(character_background, ensure_ascii=False, indent=2)}")

    try:
        while True:
            game_state = {
                "player_info": player_info,
                "inventory": inventory,
                "current_scene": current_scene,
                "last_choice": last_choice
            }
            
            scene_data = {"text": "", "options": [{"text": "Please wait...", "next_scene": ""}]}
            selected_option = 0
            api_response = call_openai_api(game_state, scene_data, player_info, inventory, selected_option, last_choice, memory, character_background, action_history)
            scene_data = {k: v for k, v in api_response.items() if k not in ['memory', 'character_background']}
            memory = api_response.get('memory', memory)
            
            if 'character_background' in api_response:
                new_background = api_response['character_background']
                if new_background != character_background:
                    log_to_file(f"## Updated Character Background\n\n{json.dumps(new_background, ensure_ascii=False, indent=2)}")
                    character_background = new_background
            
            selected_option = 0
            
            log_to_file(f"## Scene: {current_scene}\n\n### Description\n\n{scene_data['text']}\n\n### Options\n\n" + 
                        "\n".join([f"- {option['text']}" for option in scene_data['options']]) +
                        f"\n\n### Memory\n\n{memory}")
            
            custom_input = None
            while True:
                display_scene(scene_data, player_info, inventory, selected_option, last_choice=last_choice)
                
                key = get_key()
                if key == 'UP' and selected_option > 0:
                    selected_option -= 1
                elif key == 'DOWN' and selected_option < len(scene_data['options']) - 1:
                    selected_option += 1
                elif key == 'SELECT':
                    break
                elif key == 'CUSTOM':
                    custom_input = input(f"{Fore.YELLOW}Enter your own option (press Enter to send): {Style.RESET_ALL}")
                    if custom_input.strip():  # Check if the input is not empty
                        break
                    else:
                        custom_input = None
            
            if custom_input:
                last_choice = custom_input
            else:
                chosen_option = scene_data['options'][selected_option]
                last_choice = chosen_option['text']
            
            # Update action history with user's choice
            update_action_history(action_history, last_choice, scene_data)
            
            api_response = call_openai_api(game_state, scene_data, player_info, inventory, selected_option, last_choice, memory, character_background, action_history)
            scene_data = {k: v for k, v in api_response.items() if k not in ['memory', 'character_background']}
            memory = api_response.get('memory', memory)
            
            # Update action history with model's response
            update_action_history(action_history, last_choice, api_response)
            
            if 'character_background' in api_response:
                new_background = api_response['character_background']
                if new_background != character_background:
                    log_to_file(f"## Updated Character Background\n\n{json.dumps(new_background, ensure_ascii=False, indent=2)}")
                    character_background = new_background
            
            log_to_file(f"### Player's Choice\n\n{last_choice}\n\n### Status\n\n" + 
                        "\n".join([f"- {key}: {value}" for key, value in player_info.items()]) + 
                        f"\n- Inventory: {', '.join(inventory)}")
            
            if 'changes' in scene_data:
                apply_changes(player_info, inventory, scene_data['changes'])
            
            if 'end_game' in scene_data and scene_data['end_game']:
                log_to_file(f"## Game Over\n\nEnded at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n### Final Memory\n\n{memory}")
                log_to_file(f"## Final Character Background\n\n{json.dumps(character_background, ensure_ascii=False, indent=2)}")
                save_player_status(player_info, inventory, current_scene, memory, character_background, action_history)
                clear_screen()
                print(f"\n{Fore.GREEN}Game Over. Thank you for playing!{Fore.RESET}")
                print(f"Game log saved to file: {log_filename}")
                print(f"Player status saved to file: {status_filename}")
                input("Press Enter to exit...")
                sys.exit(0)
            
            current_scene = scene_data['options'][0]['next_scene']

    except KeyboardInterrupt:
        log_to_file(f"## Game Interrupted\n\nEnded at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_to_file(f"## Final Character Background\n\n{json.dumps(character_background, ensure_ascii=False, indent=2)}")
        save_player_status(player_info, inventory, current_scene, memory, character_background, action_history)
        clear_screen()
        print(f"\n{Fore.YELLOW}Exiting the game...{Fore.RESET}")
        print(f"Game log saved to file: {log_filename}")
        print(f"Player status saved to file: {status_filename}")
        sys.exit(0)

if __name__ == "__main__":
    main()
