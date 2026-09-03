import re

EMOJI_NUMBERS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

def fix_questions_file(content: str) -> dict:
    lines = content.split("\n")
    result = []
    removed_count = 0
    i = 0
    
    while i < len(lines):
        current_line = lines[i]
        result.append(current_line)
        
        if current_line.rstrip().endswith(":"):
            j = i + 1
            found_digit = False
            next_non_blank_idx = -1
            
            while j < len(lines):
                if lines[j].strip() != "":
                    next_non_blank_idx = j
                    if re.match(r'^\d+\.', lines[j].lstrip()):
                        found_digit = True
                    break
                j += 1
                
            if found_digit:
                removed_count += (next_non_blank_idx - i - 1)
                i = next_non_blank_idx - 1
                
        i += 1
        
    return {
        "fixedContent": "\n".join(result),
        "removedCount": removed_count,
        "totalLines": len(lines),
        "finalLines": len(result)
    }

def count_questions(content: str) -> int:
    lines = content.split("\n")
    count = 0
    for l in lines:
        if re.match(r'^\s*\d+[\.\)]', l) or re.match(r'^\s*Q\.\d+\)', l):
            count += 1
    return count

def convert_format(content: str) -> str:
    # Lookahead split matching blockSplitRegex = /(?=^\s*[Qq]\.\d+\))/gm
    raw_blocks = re.split(r'(?m)(?=^\s*[Qq]\.\d+\))', content)
    raw_blocks = [b for b in raw_blocks if b.strip()]
    
    if not raw_blocks:
        return convert_numbered_format(content)
        
    converted_blocks = [convert_single_block(b) for b in raw_blocks]
    return "\n\n".join(converted_blocks)

def convert_single_block(block: str) -> str:
    lines = [l.rstrip() for l in block.split("\n")]
    result_lines = []
    i = 0
    question_stem_done = False
    separator_added = False
    
    while i < len(lines):
        line = lines[i]
        
        if i == 0 or (not question_stem_done and re.match(r'^\s*[Qq]\.\d+\)', line)):
            expanded = expand_emoji_points(line)
            for el in expanded["lines"]:
                result_lines.append(el)
            
            if expanded["hadPoints"]:
                result_lines.append("😂")
                separator_added = True
                
            question_stem_done = True
            i += 1
            continue
            
        if not separator_added and has_inline_emoji_points(line):
            expanded = expand_emoji_points(line)
            for el in expanded["lines"]:
                result_lines.append(el)
            if expanded["hadPoints"]:
                result_lines.append("😂")
                separator_added = True
            i += 1
            continue
            
        if line.strip() == "":
            next_non_blank = next((l for l in lines[i+1:] if l.strip() != ""), None)
            if not next_non_blank or next_non_blank.strip().lower().startswith("ex"):
                result_lines.append("")
            i += 1
            continue
            
        if line.strip() == "😂":
            if not separator_added:
                result_lines.append("😂")
                separator_added = True
            i += 1
            continue
            
        is_option = is_option_line(line)
        is_ex = re.match(r'^\s*Ex[:.]', line, re.IGNORECASE)
        
        if (is_option or is_ex) and not separator_added:
            result_lines.append("😂")
            separator_added = True
            
        result_lines.append(line)
        
        if is_ex:
            result_lines.append("")
            
        i += 1
        
    return "\n".join(result_lines).rstrip()

def has_inline_emoji_points(line: str) -> bool:
    return any(e in line for e in EMOJI_NUMBERS)

def expand_emoji_points(line: str) -> dict:
    emoji_pattern = "|".join(re.escape(e) for e in EMOJI_NUMBERS)
    splitter = re.compile(f'({emoji_pattern})')
    
    parts = [p for p in splitter.split(line) if p != ""]
    
    if len(parts) <= 1 or not any(e in line for e in EMOJI_NUMBERS):
        return {"lines": [line], "hadPoints": False}
        
    result_lines = []
    
    prefix = parts[0].strip()
    if prefix:
        result_lines.append(re.sub(r'\s+$', '', prefix))
        
    i = 1
    while i < len(parts):
        emoji = parts[i]
        is_emoji = emoji in EMOJI_NUMBERS
        if is_emoji:
            text = (parts[i+1] if i + 1 < len(parts) else "").strip()
            i += 2
            result_lines.append(f"{emoji} {text}")
        else:
            stem = parts[i].strip()
            if stem:
                result_lines.append(stem)
            i += 1
            
    return {"lines": result_lines, "hadPoints": True}

def is_option_line(line: str) -> bool:
    t = line.strip()
    if not t:
        return False
    if re.match(r'^\s*[Qq]\.\d+\)', t):
        return False
    if re.match(r'^\s*Ex[:.]', t, re.IGNORECASE):
        return False
    if re.match(r'^\s*\d+[\.\)]', t):
        return False
    if any(t.startswith(e) for e in EMOJI_NUMBERS):
        return False
    return True

def convert_numbered_format(content: str) -> str:
    lines = content.split("\n")
    result = []
    i = 0
    inside_question = False
    separator_added = False
    
    while i < len(lines):
        line = lines[i]
        t = line.strip()
        
        if re.match(r'^\s*\d+[\.\)]', t) and not any(t.startswith(e) for e in EMOJI_NUMBERS):
            inside_question = True
            separator_added = False
            expanded = expand_emoji_points(line)
            for el in expanded["lines"]:
                result.append(el)
            if expanded["hadPoints"]:
                result.append("😂")
                separator_added = True
            i += 1
            continue
            
        if inside_question and has_inline_emoji_points(t) and not separator_added:
            expanded = expand_emoji_points(line)
            for el in expanded["lines"]:
                result.append(el)
            if expanded["hadPoints"]:
                result.append("😂")
                separator_added = True
            i += 1
            continue
            
        is_ex = re.match(r'^\s*Ex[:.]', t, re.IGNORECASE)
        is_opt = inside_question and is_option_line(line) and not separator_added
        
        if (is_opt or is_ex) and not separator_added:
            result.append("😂")
            separator_added = True
            
        result.append(line)
        
        if is_ex:
            result.append("")
            
        i += 1
        
    return "\n".join(result)
