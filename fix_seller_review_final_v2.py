import os
import re

file_path = r"c:\Users\lenovo\OneDrive\Desktop\Multimart\multimart-athul-azeem\templates\seller\seller_review.html"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix Split Template Tags
# We want to merge lines like:
# ...{%
# endif %}
# Regex: matches {% at end of line, followed by optional whitespace/newlines, then endif %}
# We replace it with {% endif %}
content = re.sub(r'\{%\s*\n\s*endif %\}', r'{% endif %}', content)

# 2. Fix Equality Spacing
# e.g. rating_filter==5 -> rating_filter == 5
content = re.sub(r'(?<=[^\s!=<>])==(?=[^\s=])', ' == ', content)
content = re.sub(r'(?<=[^\s!=<>])==(?=\s)', ' == ', content)
content = re.sub(r'(?<=\s)==(?=[^\s=])', ' == ', content)
# Clean up potential double spaces
content = re.sub(r'\s+==\s+', ' == ', content)

# 3. Fix Escaped Filter Arguments
# |default:\'[]\' -> |default:"[]"
content = re.sub(r"\|default:\\'\[\]\\'", r'|default:"[]"', content)
# Also generic |default:\'...\' -> |default:'...'
content = re.sub(r"\|default:\\'([^']*)\\'", r"|default:'\1'", content)
# And |default: ... spacing
content = re.sub(r'\|default:\s+', '|default:', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Refreshed {file_path}")
