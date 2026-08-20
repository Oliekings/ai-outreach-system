import re

def check_buttons():
    with open('dashboard/app.js', 'r') as f:
        content = f.read()

    button_pattern = re.compile(r'<button\b([^>]*)>(.*?)</button>', re.DOTALL)
    matches = button_pattern.findall(content)

    for attrs, inner_text in matches:
        # Check if button is icon-only or just an emoji (rough heuristic)
        text = inner_text.strip()
        is_icon_only = len(text) <= 3 and any(char in "▶✕🔍🚀🚀" for char in text) # Or if it's entirely emoji
        if not is_icon_only:
            # Check if it contains only emoji or short icon string
            stripped_text = re.sub(r'<[^>]+>', '', text).strip()
            if len(stripped_text) <= 2:
                is_icon_only = True

        if is_icon_only:
            print(f"Icon-only button found: '{text}' with attributes: {attrs}")
            if "aria-label" not in attrs:
                print(" -> Missing aria-label!")
            if "title" not in attrs:
                print(" -> Missing title!")

check_buttons()
