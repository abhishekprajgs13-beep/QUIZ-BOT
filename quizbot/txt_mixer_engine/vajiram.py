import re
from typing import List, Dict, Any, Callable
from .pdf_utils import extract_pages

def consolidate_spatial_tokens(tokens_list: List[Dict[str, Any]], y_tolerance: int = 4) -> List[Dict[str, Any]]:
    if not tokens_list:
        return []
    
    # Sort by Y, then X
    sorted_tokens = sorted(tokens_list, key=lambda t: (t['y'], t['x']))
    rows = []
    cur_row = [sorted_tokens[0]]
    
    for i in range(1, len(sorted_tokens)):
        if abs(sorted_tokens[i]['y'] - cur_row[0]['y']) <= y_tolerance:
            cur_row.append(sorted_tokens[i])
        else:
            rows.append(cur_row)
            cur_row = [sorted_tokens[i]]
    rows.append(cur_row)
    
    result = []
    for bucket in rows:
        bucket.sort(key=lambda t: t['x'])
        text = " ".join([t['text'] for t in bucket])
        text = re.sub(r'\s{2,}', ' ', text).strip()
        if text:
            result.append({
                'y': bucket[0]['y'],
                'x': min(t['x'] for t in bucket),
                'text': text
            })
    return result

def is_header_footer_noise(line: str) -> bool:
    s = line.strip().upper()
    if not s:
        return True
    
    patterns = [
        r'VAJIRAM\s*(&|AND)\s*RAVI', r'PRELIMS\s*TEST\s*SERIES',
        r'FULL\s*LENGTH\s*TEST', r'TEST\s*BOOKLET',
        r'MAXIMUM\s*MARKS', r'TIME\s*ALLOWED', r'DO\s*NOT\s*OPEN',
        r'COMMENCEMENT\s*OF\s*THE\s*EXAMINATION', r'UNPRINTED\s*OR\s*TORN',
        r'CANDIDATE\'S\s*RESPONSIBILITY', r'ROLL\s*NUMBER',
        r'OMR\s*ANSWER', r'ANSWER\s*SHEET', r'PENALTY\s*FOR\s*WRONG',
        r'WRONG\s*ANSWERS\s*MARKED', r'ALTERNATIVES\s*FOR\s*THE\s*ANSWER',
        r'QUESTION\s*IS\s*LEFT\s*BLANK', r'ECONOMICS\s*\(V\d+\)',
        r'SCIENCE\s*&\s*TECHNOLOGY\s*\(V\d+\)', r'POLITY\s*\(V\d+\)',
        r'GS\s*TEST\s*-\s*\d+', r'POWERUP\s*PRELIMS',
        r'^\d{1,3}$'
    ]
    for p in patterns:
        if re.search(p, line, re.IGNORECASE):
            return True
    return False

def is_cover_page(lines: List[Dict[str, Any]]) -> bool:
    combined = " ".join([l['text'] for l in lines])
    return not (re.search(r'\(a\)', combined, re.IGNORECASE) or re.search(r'\(b\)', combined, re.IGNORECASE))

def parse_test_booklet(pages: List[Dict[str, Any]], log_fn: Callable = None) -> Dict[int, Any]:
    question_map = {}
    for page in pages:
        master_lines = consolidate_spatial_tokens(page['items'])
        filtered_lines = [l for l in master_lines if not is_header_footer_noise(l['text'])]
        
        if is_cover_page(filtered_lines):
            if log_fn: log_fn(f"  Skipping non-question page: {page['pageNum']}", 'warn')
            continue
            
        mid_x = page['width'] / 2
        left_items = [t for t in page['items'] if t['x'] < mid_x - 15]
        right_items = [t for t in page['items'] if t['x'] >= mid_x - 15]
        is_two_column = len(left_items) > 6 and len(right_items) > 6
        
        unified_text = ""
        if is_two_column:
            left_lines = [l for l in consolidate_spatial_tokens(left_items) if not is_header_footer_noise(l['text'])]
            right_lines = [l for l in consolidate_spatial_tokens(right_items) if not is_header_footer_noise(l['text'])]
            unified_text = "\n".join([l['text'] for l in left_lines + right_lines])
        else:
            unified_text = "\n".join([l['text'] for l in filtered_lines])
            
        parse_questions_from_text(unified_text, question_map)
    return question_map

def parse_questions_from_text(text_stream: str, target_map: Dict[int, Any]):
    lines = [r.strip() for r in text_stream.split('\n') if r.strip()]
    active_q = None
    body_lines = []
    options = []
    in_options = False
    
    def flush():
        nonlocal active_q, body_lines, options, in_options
        if active_q is None: return
        if len(options) >= 2:
            if active_q not in target_map or len(options) > len(target_map[active_q]['options']):
                target_map[active_q] = {
                    'id': active_q,
                    'body': list(body_lines),
                    'options': list(options)
                }
        active_q = None
        body_lines = []
        options = []
        in_options = False

    for line in lines:
        opt_match = re.match(r'^\s*\(([a-d])\)\s+(.+)$', line, re.IGNORECASE)
        if opt_match and active_q is not None:
            in_options = True
            options.append({'letter': opt_match.group(1).lower(), 'text': opt_match.group(2).strip()})
            continue
            
        q_match = re.match(r'^\s*(\d{1,3})\.\s{1,6}(.+)$', line)
        if q_match:
            num = int(q_match.group(1))
            if 1 <= num <= 100:
                is_list_item = (active_q is not None and not in_options and num != active_q + 1 and num <= 6)
                if not is_list_item or active_q is None:
                    flush()
                    active_q = num
                    body_lines = [q_match.group(2).strip()]
                    options = []
                    in_options = False
                    continue
                    
        if in_options and len(options) > 0 and active_q is not None:
            if not re.match(r'^\s*\(([a-d])\)', line, re.IGNORECASE):
                options[-1]['text'] += ' ' + line
            continue
            
        if active_q is not None and not in_options:
            body_lines.append(line)
            
    flush()

def parse_solutions(pages: List[Dict[str, Any]], log_fn: Callable = None) -> Dict[str, Any]:
    all_lines = []
    for page in pages:
        formatted = [l['text'] for l in consolidate_spatial_tokens(page['items']) if not is_header_footer_noise(l['text'])]
        all_lines.extend(formatted)
        
    full_text = "\n".join(all_lines)
    
    answer_keys = {}
    key_regex = re.compile(r'\b(\d{1,3})\.\s*\(([a-d])\)', re.IGNORECASE)
    for m in key_regex.finditer(full_text):
        num = int(m.group(1))
        if 1 <= num <= 100:
            answer_keys[num] = m.group(2).lower()
            
    if log_fn: log_fn(f"  Answer keys found: {len(answer_keys)}")
    
    explanations = {}
    block_regex = re.compile(r'\nQ(\d{1,3})\.\s*\n')
    blocks = []
    for m in block_regex.finditer(full_text):
        blocks.append({'num': int(m.group(1)), 'start': m.end()})
        
    for i in range(len(blocks)):
        num = blocks[i]['num']
        start = blocks[i]['start']
        end = blocks[i+1]['start'] if i + 1 < len(blocks) else len(full_text)
        slice_text = full_text[start:end]
        explanations[num] = clean_explanation(slice_text)
        
    if len(blocks) < 5:
        inline_regex = re.compile(r'\bQ\s*(\d{1,3})\s*\.\s*([A-D])\b')
        for m in inline_regex.finditer(full_text):
            num = int(m.group(1))
            if 1 <= num <= 100 and num not in answer_keys:
                answer_keys[num] = m.group(2).lower()
                
    return {'answerKeys': answer_keys, 'explanations': explanations}

def clean_explanation(raw: str) -> str:
    t = raw
    t = re.sub(r'(?mi)^Answer\s*:\s*[a-d]\s*$', '', t)
    t = re.sub(r'(?mi)^Explanation\s*:\s*$', '', t)
    t = re.sub(r'(?i)Therefore[,\s]+option\s*\([a-d]\)\s*is\s*the\s*correct\s*answer\.?[^\n]*', '', t)
    t = re.sub(r'(?i)So[,\s]+option\s*\([a-d]\)\s*is\s*the\s*correct\s*answer\.?[^\n]*', '', t)
    t = re.sub(r'(?i)Therefore[,\s]+the\s*correct\s*answer[^\n]*', '', t)
    t = re.sub(r'(?i)Relevance\s*:[^\n]*', '', t)
    t = re.sub(r'(?mi)^(?:Source|Ref|Reference)\s*:[^\n]*', '', t)
    t = re.sub(r'(?m)^[\s]*[●○•▪◆▸▹→\-–—]+\s*', '', t)
    t = re.sub(r'(?m)^Q\d{1,3}\.\s*', '', t)
    
    cleaned = [l.strip() for l in t.split('\n') if len(l.strip()) > 2]
    cleaned_str = " ".join(cleaned)
    cleaned_str = re.sub(r'\s{2,}', ' ', cleaned_str)
    cleaned_str = re.sub(r'\.\s*\.', '.', cleaned_str).strip()
    return cleaned_str

def compile_question_core_lines(raw_lines: List[str]) -> List[str]:
    normalized = [normalize_roman(l.strip()) for l in raw_lines if l.strip()]
    if not normalized: return []
    
    new_line_re = [
        re.compile(r'^\d{1,2}\.\s+\S'),
        re.compile(r'(?i)^Statement\s+[IVXLC]+\s*:'),
        re.compile(r'(?i)^(Which|How\s+many|How\s+|What|Select|Arrange|In\s+how|Who\s+|Where\s+|Among\s+|Identify|Of\s+the|With\s+reference|With\s+regard|Consider|Regarding|As\s+per|According\s+to|In\s+which\s+of\s+the\s+above)')
    ]
    
    output = []
    buf = ""
    for i, line in enumerate(normalized):
        is_new = (i == 0) or any(p.search(line) for p in new_line_re)
        if is_new:
            if buf:
                output.append(re.sub(r'\s{2,}', ' ', buf).strip())
            buf = line
        else:
            buf += " " + line
            
    if buf:
        output.append(re.sub(r'\s{2,}', ' ', buf).strip())
    return output

def normalize_roman(line: str) -> str:
    def replacer(match):
        roman = match.group(1).upper()
        m = {'I':1, 'II':2, 'III':3, 'IV':4, 'V':5, 'VI':6, 'VII':7, 'VIII':8, 'IX':9, 'X':10, 'XI':11, 'XII':12}
        digit = m.get(roman)
        return f"{digit}. " if digit else match.group(0)
        
    return re.sub(r'^\s*(I{1,3}|IV|V?I{0,3}|IX|XI{0,3})\.\s+', replacer, line)

def unpack_options(raw_options: List[Dict[str, str]]) -> List[Dict[str, str]]:
    combined = " ".join([f"({o['letter']}) {o['text']}" for o in raw_options])
    
    match_a = re.search(r'(?i)\(a\)\s*([\s\S]*?)(?=\s*\(b\)|$)', combined)
    match_b = re.search(r'(?i)\(b\)\s*([\s\S]*?)(?=\s*\(c\)|$)', combined)
    match_c = re.search(r'(?i)\(c\)\s*([\s\S]*?)(?=\s*\(d\)|$)', combined)
    match_d = re.search(r'(?i)\(d\)\s*([\s\S]*?)$', combined)
    
    text_a = match_a.group(1) if match_a else 'Only one'
    text_b = match_b.group(1) if match_b else 'Only two'
    text_c = match_c.group(1) if match_c else 'Only three'
    text_d = match_d.group(1) if match_d else 'All the four'
    
    def pure(s: str) -> str:
        return re.sub(r'(?i)^\s*\(?[a-d]\)?\s*\.?\s*', '', s).strip()
        
    return [
        {'letter': 'a', 'text': pure(text_a)},
        {'letter': 'b', 'text': pure(text_b)},
        {'letter': 'c', 'text': pure(text_c)},
        {'letter': 'd', 'text': pure(text_d)}
    ]

def process_vajiram(test_buffer: bytes, sol_buffer: bytes, on_progress: Callable = None) -> Dict[str, Any]:
    try:
        if on_progress: on_progress(15, 'Decoding Test Booklet...')
        test_pages = extract_pages(test_buffer)
        
        if on_progress: on_progress(40, 'Compiling questions...')
        question_map = parse_test_booklet(test_pages)
        q_count = len(question_map)
        
        if on_progress: on_progress(45, f"Parsed {q_count} questions from test booklet")
        
        if q_count == 0:
            return {
                'success': False,
                'error': 'Zero valid questions found in Test PDF. Please check that it is a valid Vajiram test booklet with (a)(b)(c)(d) options.'
            }
            
        if on_progress: on_progress(60, 'Decoding Solution Booklet...')
        sol_pages = extract_pages(sol_buffer)
        
        if on_progress: on_progress(85, 'Cross-referencing answers...')
        
        def sol_log(msg):
            if on_progress: on_progress(85, msg)
            
        parsed_sols = parse_solutions(sol_pages, sol_log)
        answer_keys = parsed_sols['answerKeys']
        explanations = parsed_sols['explanations']
        
        if on_progress: on_progress(95, 'Building output...')
        
        answers_matched = 0
        explan_missing = 0
        
        sorted_keys = sorted(question_map.keys())
        lines = []
        
        for key in sorted_keys:
            q = question_map[key]
            ans_letter = answer_keys.get(key)
            expl = explanations.get(key, 'Explanation not found for this question.')
            
            if ans_letter: answers_matched += 1
            if key not in explanations: explan_missing += 1
            
            core_lines = compile_question_core_lines(q['body'])
            lines.append(f"Q{key}. {core_lines[0] if core_lines else ''}")
            for i in range(1, len(core_lines)):
                lines.append(core_lines[i])
                
            lines.append('😂')
            
            opts = unpack_options(q['options'])
            for opt in opts:
                mark = ' ✅' if ans_letter and opt['letter'] == ans_letter else ''
                lines.append(opt['text'] + mark)
                
            lines.append(f"Ex: {expl.strip()}")
            lines.append('')
            
        output = "\n".join(lines)
        if on_progress: on_progress(100, 'Done!')
        
        return {
            'success': True,
            'output': output,
            'questionCount': q_count,
            'lineCount': len(lines),
            'stats': {
                'matched': answers_matched,
                'noAns': q_count - answers_matched,
                'explanationsFound': q_count - explan_missing,
                'noExpl': explan_missing
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
