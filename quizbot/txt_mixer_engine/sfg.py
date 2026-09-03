import re
from typing import List, Dict, Any, Callable
import fitz

def extract_page_text(page: fitz.Page) -> str:
    blocks = page.get_text("dict")["blocks"]
    items = []
    
    for b in blocks:
        if "lines" not in b: continue
        for l in b["lines"]:
            for s in l["spans"]:
                if s["text"].strip():
                    bbox = s["bbox"]
                    # PyMuPDF y is from top. pdfjs-dist transform[5] is from bottom.
                    # We will just use top-y (bbox[1]) for sorting.
                    items.append({
                        "text": s["text"],
                        "x": bbox[0],
                        "y": bbox[1]
                    })
                    
    if not items: return ""
    
    # Sort by Y, then X
    items.sort(key=lambda a: (a["y"], a["x"]))
    
    rows = []
    current_y = None
    current_row = []
    
    for item in items:
        y = item["y"]
        if current_y is None or abs(y - current_y) > 4:
            if current_row:
                rows.append(current_row)
            current_row = [item]
            current_y = y
        else:
            current_row.append(item)
            
    if current_row:
        rows.append(current_row)
        
    return "\n".join([" ".join([it["text"] for it in row]) for row in rows])

def clean_lines(raw_text: str) -> List[str]:
    lines = raw_text.split('\n')
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line: continue
        if re.search(r'(?i)^Forum Learning Centre', line): continue
        if re.search(r'^9311\d{6}', line): continue
        if re.search(r'^\d{10}\s*,\s*\d{10}', line): continue
        if re.search(r'^\[\d+\]$', line): continue
        if re.search(r'(?i)^SFG 20\d\d\s*\|\s*Level', line): continue
        if re.search(r'(?i)^https?://', line) and len(line) < 120: continue
        if re.search(r'(?i)^admissions@forumias', line): continue
        if re.search(r'(?i)^helpdesk@forumias', line): continue
        if re.search(r'^\d{4,5}\s*,\s*\d{4,5}', line): continue
        cleaned.append(line)
    return cleaned

def parse_and_format(raw_text: str) -> str:
    lines = clean_lines(raw_text)
    output = []
    i = 0
    q_number = 0
    
    ROMAN_MAP = {'I':'1','II':'2','III':'3','IV':'4','V':'5','VI':'6','VII':'7','VIII':'8','IX':'9','X':'10'}
    
    def roman_digit(r: str) -> str:
        return ROMAN_MAP.get(r.upper(), r)
        
    def is_question_start(l: str) -> bool:
        return bool(re.search(r'(?i)^Q\.?\s*\d+\s*[)\.]', l))
        
    def get_q_num(l: str) -> int:
        m = re.match(r'(?i)^Q\.?\s*(\d+)\s*[)\.]', l)
        return int(m.group(1)) if m else None
        
    def strip_q_prefix(l: str) -> str:
        return re.sub(r'(?i)^Q\.?\s*\d+\s*[)\.]\s*', '', l).strip()
        
    def is_option(l: str) -> bool:
        return bool(re.search(r'(?i)^[a-d]\s*[)\.]\s*.{1,}', l))
        
    def clean_opt(l: str) -> str:
        return re.sub(r'(?i)^[a-d]\s*[)\.]\s*', '', l).strip()
        
    def classify_body_line(l: str) -> Dict[str, str]:
        roman = re.match(r'(?i)^(I{1,3}|IV|V|VI{1,3}|IX|X)\s*[\.\)\-]\s*(.*)', l)
        if roman: return {'type': 'roman', 'num': roman_digit(roman.group(1)), 'rest': roman.group(2).strip()}
        
        stmt_roman = re.match(r'(?i)^Statement\s+(I{1,3}|IV|V|VI{1,3}|IX|X)\s*[:\.]\s*(.*)', l)
        if stmt_roman: return {'type': 'statementWord', 'num': roman_digit(stmt_roman.group(1)), 'rest': stmt_roman.group(2).strip()}
        
        stmt_arabic = re.match(r'(?i)^Statement\s+(\d+)\s*[:\.]\s*(.*)', l)
        if stmt_arabic: return {'type': 'statementWord', 'num': stmt_arabic.group(1), 'rest': stmt_arabic.group(2).strip()}
        
        arabic = re.match(r'^(\d+)\s*[\.\)\-]\s+(.*)', l)
        if arabic: return {'type': 'arabic', 'num': arabic.group(1), 'rest': arabic.group(2).strip()}
        
        if re.search(r'(?i)^(Which\b|How many\b|Select\b|In how many\b|Who\b|What\b|When\b|Where\b|Name\b|Identify\b|Arrange\b|Among\b|Of the above|From the above|Based on\b|In the above|The above)', l):
            return {'type': 'directive', 'rest': l}
            
        return None
        
    def is_table_data_row(l: str) -> bool:
        return bool(re.search(r'\s{3,}', l)) and (bool(re.search(r'(?i)^(I{1,3}|IV|V|VI{1,3}|IX|X)\s*[\.\)\-]', l)) or bool(re.search(r'^\d+\s*[\.\)\-]', l)))
        
    def is_table_header_row(l: str) -> bool:
        return bool(re.search(r'\s{4,}', l)) and not is_option(l) and not is_table_data_row(l) and not bool(re.search(r'(?i)^(Ans|Exp|Source|Subject|Topic|Subtopic)\s*[)\.]', l)) and bool(re.search(r'^[A-Z]', l))
        
    def table_to_items(table_lines: List[str]) -> List[str]:
        result = []
        row_num = 0
        for l in table_lines:
            if is_table_header_row(l): continue
            roman_row = re.match(r'(?i)^(I{1,3}|IV|V|VI{1,3}|IX|X)\s*[\.\)\-]\s*(.*)', l)
            digit_row = re.match(r'^(\d+)\s*[\.\)\-]\s*(.*)', l)
            if roman_row or digit_row:
                row_num += 1
                rest = (roman_row.group(2) if roman_row else digit_row.group(2)).strip()
                parts = [p.strip() for p in re.split(r'\s{3,}', rest) if p.strip()]
                result.append(f"{row_num}. " + " — ".join(parts))
            elif row_num > 0 and result:
                parts = [p.strip() for p in re.split(r'\s{3,}', l) if p.strip()]
                result[-1] += " " + " ".join(parts)
        return result
        
    def build_question_body(first_stem_line: str, body_lines: List[str]) -> List[str]:
        items = [{'text': first_stem_line, 'kind': 'stem'}]
        stmt_counter = 0
        in_table = False
        table_buffer = []
        
        def flush_table():
            nonlocal in_table, table_buffer
            if not table_buffer: return
            for t in table_to_items(table_buffer):
                items.append({'text': t, 'kind': 'statement'})
            table_buffer.clear()
            in_table = False
            
        for l in body_lines:
            if not l: continue
            if is_table_header_row(l):
                flush_table()
                in_table = True
                table_buffer.append(l)
                continue
            if in_table and is_table_data_row(l):
                table_buffer.append(l)
                continue
            if in_table:
                if re.search(r'\s{3,}', l) and not re.search(r'(?i)^(Ans|Exp|Source|Subject|Topic)', l):
                    table_buffer.append(l)
                    continue
                flush_table()
                
            cls = classify_body_line(l)
            if cls and cls['type'] == 'roman':
                stmt_counter += 1
                items.append({'text': f"{stmt_counter}. {cls['rest']}", 'kind': 'statement'})
                continue
            if cls and cls['type'] == 'statementWord':
                stmt_counter += 1
                items.append({'text': f"{stmt_counter}. {cls['rest']}", 'kind': 'statement'})
                continue
            if cls and cls['type'] == 'arabic':
                items.append({'text': f"{cls['num']}. {cls['rest']}", 'kind': 'statement'})
                continue
            if cls and cls['type'] == 'directive':
                items.append({'text': cls['rest'], 'kind': 'directive'})
                continue
                
            if items:
                items[-1]['text'] += " " + l
            else:
                items.append({'text': l, 'kind': 'stem'})
                
        flush_table()
        return [it['text'].strip() for it in items if it['text'].strip()]
        
    def extract_explanation(block: List[str]) -> str:
        exp_idx = -1
        for j in range(len(block)):
            if re.search(r'(?i)^Exp\s*[)\.]', block[j]):
                exp_idx = j
                break
        if exp_idx == -1: return ''
        
        parts = []
        for j in range(exp_idx, len(block)):
            l = block[j].strip()
            if re.search(r'(?i)^(Source|Subject|Topic|Subtopic)\s*[)\.:]', l): break
            if re.search(r'(?i)^Source\s*[)\.:]', l): break
            if re.search(r'(?i)^https?://', l): continue
            
            if re.search(r'(?i)^Exp\s*[)\.]\s*Option\s+[a-d]\s+is\s+the\s+correct', l):
                after = re.sub(r'(?i)^Exp\s*[)\.]\s*Option\s+[a-d]\s+is\s+the\s+correct\s+answer[,\.]?\s*', '', l).strip()
                if after: parts.append(after)
                continue
                
            if j == exp_idx and re.search(r'(?i)^Exp\s*[)\.]', l):
                after = re.sub(r'(?i)^Exp\s*[)\.]\s*', '', l).strip()
                if after: parts.append(after)
                continue
                
            clean = re.sub(r'^[●•·▪▸►\*\-]\s+', '', l).strip()
            if clean: parts.append(clean)
            
        res = " ".join(parts)
        res = re.sub(r'\s{2,}', ' ', res)
        res = res.replace('**', '').strip()
        return res
        
    while i < len(lines):
        if not is_question_start(lines[i]):
            i += 1
            continue
            
        q_number += 1
        q_num = get_q_num(lines[i]) or q_number
        block = [lines[i]]
        i += 1
        while i < len(lines) and not is_question_start(lines[i]):
            block.append(lines[i])
            i += 1
            
        option_start = -1
        answer_idx = -1
        
        for j in range(1, len(block)):
            if option_start == -1 and is_option(block[j]):
                option_start = j
            if re.search(r'(?i)^Ans\s*[)\.]', block[j]):
                answer_idx = j
                
        body_end = option_start if option_start > -1 else (answer_idx if answer_idx > -1 else len(block))
        body_raw = [l.strip() for l in block[1:body_end] if l.strip()]
        
        q_lines = build_question_body(strip_q_prefix(block[0]), body_raw)
        q_text = "\n".join(q_lines)
        
        opts = []
        if option_start > -1:
            for j in range(option_start, len(block)):
                ol = block[j].strip()
                if is_option(ol):
                    opts.append(ol)
                elif re.search(r'(?i)^Ans\s*[)\.]', ol) or re.search(r'(?i)^Exp\s*[)\.]', ol):
                    break
                elif len(opts) > 0 and ol and not re.search(r'(?i)^(Source|Subject|Topic|Subtopic)', ol):
                    opts[-1] += " " + ol
                    
        ans_letter = ""
        if answer_idx > -1:
            m = re.match(r'(?i)^Ans\s*[)\.]\s*([a-d])', block[answer_idx])
            if m: ans_letter = m.group(1).lower()
            
        ans_idx = ord(ans_letter[0]) - 97 if ans_letter else -1
        exp_text = extract_explanation(block)
        
        if not q_text and len(opts) == 0:
            continue
            
        output.append(f"Q{q_num}. {q_text}")
        output.append("😂")
        
        for idx, opt in enumerate(opts):
            txt = clean_opt(opt.strip())
            output.append(f"{txt} ✅" if idx == ans_idx else txt)
            
        if exp_text:
            output.append(f"Ex: {exp_text}")
        output.append("")
        
    return "\n".join(output)

def process_sfg(buffer: bytes, on_progress: Callable = None) -> Dict[str, Any]:
    try:
        if on_progress: on_progress(5, 'Extracting PDF...')
        doc = fitz.open(stream=buffer, filetype="pdf")
        total_pages = len(doc)
        
        if on_progress: on_progress(10, 'Processing pages...')
        full_text = ""
        for p in range(total_pages):
            page = doc[p]
            full_text += extract_page_text(page) + "\n"
            if on_progress: on_progress(10 + round(((p+1)/total_pages)*50), f'Processed page {p+1}/{total_pages}')
            
        if on_progress: on_progress(65, 'Formatting output...')
        formatted = parse_and_format(full_text)
        
        if on_progress: on_progress(95, 'Calculating stats...')
        q_count = len(re.findall(r'(?m)^Q\d+\.', formatted))
        answers_matched = len(re.findall(r'✅', formatted))
        explan_found = len(re.findall(r'(?m)^Ex:', formatted))
        lines = len(formatted.split('\n'))
        
        if on_progress: on_progress(100, 'Done!')
        return {
            'success': True,
            'output': formatted,
            'questionCount': q_count,
            'lineCount': lines,
            'stats': {
                'matched': answers_matched,
                'noAns': q_count - answers_matched,
                'explanationsFound': explan_found,
                'noExpl': q_count - explan_found
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
