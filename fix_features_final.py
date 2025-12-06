import os

file_path = r"c:\Users\lenovo\OneDrive\Desktop\Multimart\multimart-athul-azeem\templates\seller\features.html"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip_next = False
fixed_split = False
fixed_spacing = 0

for i, line in enumerate(lines):
    if skip_next:
        skip_next = False
        continue
    
    # Fix split tag
    if "request.GET.category==category.id|stringformat:'s'" in line and not "%}selected{% endif %}" in line:
        if i + 1 < len(lines) and "%}selected{% endif %}" in lines[i+1]:
            # Merge
            indent = line[:line.find('<')]
            fixed_line = indent + '<option value="{{ category.id }}" {% if request.GET.category == category.id|stringformat:\'s\' %}selected{% endif %}>{{ category.name }}</option>\n'
            new_lines.append(fixed_line)
            skip_next = True
            fixed_split = True
            continue

    # Fix spacing
    current_line = line
    if "request.GET.category==" in current_line:
        current_line = current_line.replace("request.GET.category==", "request.GET.category == ")
        fixed_spacing += 1
    
    if "request.GET.status==" in current_line:
        current_line = current_line.replace("request.GET.status==", "request.GET.status == ")
        fixed_spacing += 1
        
    new_lines.append(current_line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Fixed split: {fixed_split}")
print(f"Fixed spacing count: {fixed_spacing}")
