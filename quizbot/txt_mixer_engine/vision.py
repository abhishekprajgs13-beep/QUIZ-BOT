import re
from typing import List, Dict, Any, Callable
from .pdf_utils import extract_pages

def items_to_lines(items: List[Dict[str, Any]], y_tol: int = 6) -> List[Dict[str, Any]]:
    if not items:
        return []
        
    sorted_items = sorted(items, key=lambda i: (i['y'], i['x']))
    rows = []
    cur = [sorted_items[0]]
    
    for i in range(1, len(sorted_items)):
        if abs(sorted_items[i]['y'] - cur[0]['y']) <= y_tol:
            cur.append(sorted_items[i])
        else:
            rows.append(cur)
            cur = [sorted_items[i]]
    rows.append(cur)
    
    result = []
    for r in rows:
        y = round(r[0]['y'])
        x = round(min(i['x'] for i in r))
        r_sorted = sorted(r, key=lambda i: i['x'])
        text = " ".join(i['text'] for i in r_sorted)
        text = re.sub(r'\s{2,}', ' ', text).strip()
        if text:
            result.append({'y': y, 'x': x, 'text': text})
            
    return result

def page_to_text(page: Dict[str, Any]) -> str:
    mid_x = page['width'] * 0.52
    left_items = [i for i in page['items'] if i['x'] < mid_x]
    right_items = [i for i in page['items'] if i['x'] >= mid_x]
    
    left_lines = items_to_lines(left_items)
    right_lines = items_to_lines(right_items)
    
    if len(left_lines) >= 5 and len(right_lines) >= 5:
        return "\n".join([l['text'] for l in left_lines] + [l['text'] for l in right_lines])
        
    all_lines = items_to_lines(page['items'])
    return "\n".join([l['text'] for l in all_lines])

HF_PATTERNS = [
    r'(?i)visionias', r'(?i)vision\s*ias', r'(?i)www\.visionias', r'(?i)©\s*vision',
    r'(?i)general\s+studies\s*\(p\)', r'(?i)test\s+booklet',
    r'(?i)answers?\s*[&and]*\s*explanations?',
    r'(?i)^https?://', r'(?i)upscpdf\.com', r'(?i)^www\.', r'(?i)iasscore',
    r'(?i)time\s+allowed', r'(?i)maximum\s+marks',
    r'(?i)do\s+not\s+open', r'(?i)rough\s+work', r'(?i)invigilator',
    r'(?i)permitted\s+to\s+take', r'(?i)hand\s+over',
    r'(?i)answer\s+sheet', r'(?i)roll\s+number',
    r'(?i)test\s+booklet\s+series',
    r'^\d{1,3}\s*$', r'^[A-D]\s*$',
    r'(?i)IMMEDIATELY\s+AFTER', r'(?i)ENCODE\s+CLEARLY',
    r'(?i)this\s+test\s+booklet\s+contains\s+\d+\s+items',
    r'(?i)you\s+have\s+to\s+(mark|enter)',
    r'(?i)all\s+items\s+carry\s+equal',
    r'(?i)before\s+you\s+proceed\s+to\s+mark',
    r'(?i)after\s+you\s+have\s+completed\s+filling',
    r'(?i)sheet\s+for\s+rough',
    r'(?i)^\d+(st|nd|rd|th)\s*of\s*the\s*allotted',
    r'(?i)^responses?\s*\(answers?\)',
    r'(?i)check\s+that\s+this\s+booklet',
    r'(?i)do\s+not\s+write\s+anything',
    r'(?i)select\s+the\s+response',
    r'(?i)separate\s+answer\s+sheet',
    r'(?i)only\s+on\s+the\s*separate',
    r'(?i)each\s+item\s+(is\s+)?printed\s+in',
]

def is_hf(t: str) -> bool:
    s = t.strip()
    if not s: return True
    return any(re.search(p, s) for p in HF_PATTERNS)

def is_item_stem(line: str) -> bool:
    if re.search(r'(?i)^(which\s+of\s+the|how\s+many\s+of\s+the|how\s+many\s+are|how\s+many\s+among|how\s+many\s+provisions|how\s+many\s+of\s+above|select\s+the\s+correct|choose\s+the\s+correct|in\s+how\s+many|arrange\s+the\s+following|what\s+is\s+the\s+correct|which\s+one\s+of\s+the)', line): return True
    if re.search(r'\?\s*$', line): return True
    if re.search(r'(?i)\bhow\s+many\b', line): return True
    if re.search(r'(?i)select\s+the\s+correct\s+answer', line): return True
    return False

def parse_body(raw_lines: List[str]) -> Dict[str, Any]:
    main_parts = []
    sub_items = []
    sub_stem = ""
    match_header = ""
    
    state = "main"
    cur_item = ""
    
    def flush_item():
        nonlocal cur_item
        t = cur_item.strip()
        if t: sub_items.append(t)
        cur_item = ""
        
    for raw in raw_lines:
        line = raw.strip()
        if not line: continue
        
        is_match_header = bool(re.match(r'^[^0-9\(].+\|.+', line)) and not bool(re.match(r'^(\d{1,2})\.\s+(.+)$', line))
        is_match_row = bool(re.match(r'^(\d{1,2})\.\s+.+\|.+', line))
        sm = re.match(r'^(\d{1,2})\.\s+(.+)$', line)
        is_sub_item = not is_match_row and sm and 1 <= int(sm.group(1)) <= 15
        is_stmt1 = bool(re.match(r'(?i)^statement[- ]i\s*:', line))
        is_stmt2 = bool(re.match(r'(?i)^statement[- ]ii\s*:', line))
        
        if state == "main":
            if is_match_header and not sub_items and not match_header:
                match_header = line
                state = "items"
            elif is_sub_item or is_match_row or is_stmt1:
                state = "items"
                cur_item = line
            else:
                main_parts.append(line)
        elif state == "items":
            if is_item_stem(line):
                flush_item()
                sub_stem = line
                state = "stem"
            elif is_match_header and not match_header:
                flush_item()
                match_header = line
            elif is_sub_item or is_match_row or is_stmt1 or is_stmt2:
                flush_item()
                cur_item = line
            else:
                cur_item += " " + line
        else:
            sub_stem += " " + line
            
    flush_item()
    main_q = " ".join(main_parts)
    main_q = re.sub(r'\s{2,}', ' ', main_q).strip()
    stem = re.sub(r'\s{2,}', ' ', sub_stem).strip()
    
    if re.search(r'(?i)how\s+many', main_q) and sub_items and re.search(r'(?i)select\s+the\s+correct\s+answer', stem):
        stem = "How many of the above are correct?"
        
    return {"mainQ": main_q, "subItems": sub_items, "subStem": stem, "matchHeader": match_header}

def parse_test_pdf(pages: List[Dict[str, Any]], log_fn: Callable = None) -> Dict[int, Any]:
    q_map = {}
    all_lines = []
    
    for page in pages:
        txt = page_to_text(page)
        if not re.search(r'(?i)\(\s*[abcd]\s*\)', txt):
            continue
        ls = [l.strip() for l in txt.split('\n')]
        ls = [l for l in ls if l and not is_hf(l)]
        all_lines.extend(ls)
        
    if log_fn: log_fn(f"  Total lines after HF removal: {len(all_lines)}")
    
    a_idxs = []
    for i in range(len(all_lines)):
        m = re.match(r'(?i)^\(([a-d])\)\s+(.+)$', all_lines[i])
        if m and m.group(1).lower() == 'a':
            a_idxs.append(i)
            
    if log_fn: log_fn(f"  \"(a)\" anchors found: {len(a_idxs)}")
    
    for ai in range(len(a_idxs)):
        a_idx = a_idxs[ai]
        candidates = []
        
        for j in range(a_idx - 1, max(-1, a_idx - 80) - 1, -1):
            line = all_lines[j]
            om = re.match(r'(?i)^\(([a-d])\)\s+(.+)$', line)
            if om and om.group(1).lower() != 'a':
                break
            m = re.match(r'^(\d{1,3})\.\s+(.+)$', line)
            if m:
                n = int(m.group(1))
                if 1 <= n <= 100:
                    candidates.append({'n': n, 'idx': j, 'text': m.group(2).strip()})
                    
        if not candidates: continue
        
        q_num = candidates[-1]['n']
        q_line_idx = candidates[-1]['idx']
        q_first_line = candidates[-1]['text']
        
        body_lines = [q_first_line]
        for j in range(q_line_idx + 1, a_idx):
            line = all_lines[j]
            bm = re.match(r'(?i)^\(([a-d])\)\s+(.+)$', line)
            if bm and bm.group(1).lower() != 'a': break
            body_lines.append(line)
            
        options = []
        cur_opt = None
        next_a_idx = a_idxs[ai + 1] if ai + 1 < len(a_idxs) else len(all_lines)
        scan_end = min(next_a_idx, a_idx + 40)
        
        for j in range(a_idx, scan_end):
            m = re.match(r'(?i)^\(([a-d])\)\s+(.+)$', all_lines[j])
            if m:
                if cur_opt: options.append(cur_opt)
                cur_opt = {'letter': m.group(1).lower(), 'text': m.group(2).strip()}
                if m.group(1).lower() == 'd':
                    options.append(cur_opt)
                    cur_opt = None
                    break
            elif cur_opt:
                if re.match(r'^(\d{1,3})\.\s+(.+)$', all_lines[j]) and len(options) < 3: break
                if j != a_idx and j in a_idxs: break
                cur_opt['text'] += " " + all_lines[j]
                
        if cur_opt and not any(o['letter'] == cur_opt['letter'] for o in options):
            options.append(cur_opt)
            
        if len(options) >= 2:
            parsed = parse_body(body_lines)
            if q_num not in q_map or len(options) > len(q_map[q_num]['options']):
                q_map[q_num] = {'parsed': parsed, 'options': options}
                
    if log_fn: log_fn(f"  Questions parsed: {len(q_map)}")
    return q_map

def parse_sol_pdf(pages: List[Dict[str, Any]], log_fn: Callable = None) -> Dict[str, Any]:
    answers = {}
    explanations = {}
    all_lines = []
    
    for page in pages:
        ls = [l['text'] for l in items_to_lines(page['items']) if not is_hf(l['text'])]
        all_lines.extend(ls)
        
    full_text = "\n".join(all_lines)
    
    marker_re = re.compile(r'(?m)^Q\s*(\d{1,3})\s*\.\s*([A-D])\s*$')
    blocks = []
    for m in marker_re.finditer(full_text):
        blocks.append({'num': int(m.group(1)), 'letter': m.group(2).lower(), 'start': m.start(), 'end': m.end()})
        
    if len(blocks) < 5:
        if log_fn: log_fn('  Trying inline answer pattern...')
        inline_re = re.compile(r'(?i)\bQ\s*(\d{1,3})\s*\.\s*([A-D])\b')
        for m in inline_re.finditer(full_text):
            n = int(m.group(1))
            if 1 <= n <= 100 and not any(b['num'] == n for b in blocks):
                blocks.append({'num': n, 'letter': m.group(2).lower(), 'start': m.start(), 'end': m.end()})
        blocks.sort(key=lambda b: b['start'])
        
    if log_fn: log_fn(f"  Answer blocks found: {len(blocks)}")
    
    for b in blocks: answers[b['num']] = b['letter']
    
    for i in range(len(blocks)):
        num = blocks[i]['num']
        end = blocks[i]['end']
        next_pos = blocks[i+1]['start'] if i + 1 < len(blocks) else len(full_text)
        raw = full_text[end:next_pos]
        cl = clean_explanation(raw)
        if len(cl) > 10: explanations[num] = cl
        
    if log_fn: log_fn(f"  Explanations extracted: {len(explanations)}")
    return {'answers': answers, 'explanations': explanations}

def clean_explanation(raw: str) -> str:
    t = raw
    t = re.sub(r'(?i)Hence[,\s]+option\s*\([a-d]\)\s*is\s*(the\s+)?correct\s*(answer)?\.?[^\n]*', '', t)
    t = re.sub(r'(?i)Hence\s+option\s*\(?[a-d]\)?\s*is[^.\n]*\.\s*', '', t)
    t = re.sub(r'(?i)Hence\s+option\s*\d[^.]*\.\s*', '', t)
    t = re.sub(r'(?i)Therefore[,\s]+option\s*\(?[a-d]\)?[^.]*\.\s*', '', t)
    t = re.sub(r'(?i)Hence\s+the\s+correct\s+(answer|option)[^.]*\.\s*', '', t)
    t = re.sub(r'(?i)Hence\s+statement\s+\d+\s+is\s+(correct|not\s+correct)\.\s*', '', t)
    t = re.sub(r'(?i)Hence\s+(the\s+)?statement\s+\d+\s+is[^.]*\.\s*', '', t)
    t = re.sub(r'(?i)Hence\s+option\s+\d+\s+is\s+(correct|not\s+correct)\.\s*', '', t)
    t = re.sub(r'(?mi)^(Source|Note|Reference)\s*:[^\n]*', '', t)
    t = re.sub(r'[●○•▪◆▸▹→‣]', '', t)
    t = re.sub(r'(?m)^\s*o\s+', ' ', t)
    t = re.sub(r'(?m)^Q\s*\d{1,3}\s*\.\s*[A-D]\s*$', '', t)
    
    lines = [l.strip() for l in t.split('\n') if len(l.strip()) > 3 and not is_hf(l)]
    cleaned_str = " ".join(lines)
    cleaned_str = re.sub(r'\s{2,}', ' ', cleaned_str)
    cleaned_str = re.sub(r'\.\s*\.', '.', cleaned_str).strip()
    return cleaned_str

def build_output(q_map: Dict[int, Any], answers: Dict[int, str], explanations: Dict[int, str]) -> Dict[str, Any]:
    nums = sorted(q_map.keys())
    lines = []
    matched = 0
    no_ans = 0
    no_expl = 0
    
    for num in nums:
        parsed = q_map[num]['parsed']
        options = q_map[num]['options']
        main_q = parsed['mainQ']
        sub_items = parsed['subItems']
        sub_stem = parsed['subStem']
        match_header = parsed['matchHeader']
        
        ans_letter = answers.get(num)
        expl = explanations.get(num, '')
        
        if not ans_letter: no_ans += 1
        if not expl: no_expl += 1
        if ans_letter and expl: matched += 1
        
        if main_q:
            lines.append(f"Q{num}.{main_q}")
            if match_header: lines.append(match_header)
            for item in sub_items: lines.append(item)
            if sub_stem: lines.append(sub_stem)
        elif sub_stem:
            lines.append(f"Q{num}.{sub_stem}")
            if match_header: lines.append(match_header)
            for item in sub_items: lines.append(item)
        else:
            lines.append(f"Q{num}.")
            
        lines.append('😂')
        
        for lt in ['a', 'b', 'c', 'd']:
            opt = next((o for o in options if o['letter'] == lt), None)
            if not opt: continue
            txt = opt['text']
            txt = re.sub(r'\s{2,}', ' ', txt)
            txt = re.sub(r'(?i)^\s*\(([a-d])\)\s*', '', txt).strip()
            mark = ' ✅' if ans_letter and opt['letter'] == ans_letter else ''
            lines.append(txt + mark)
            
        lines.append(f"Ex: {expl}" if expl else f"Ex: [Explanation not extracted for Q{num}]")
        lines.append("")
        
    return {
        'text': "\n".join(lines),
        'total': len(nums),
        'matched': matched,
        'noAns': no_ans,
        'noExpl': no_expl
    }

def process_vision(test_buffer: bytes, sol_buffer: bytes, on_progress: Callable = None) -> Dict[str, Any]:
    try:
        if on_progress: on_progress(5, 'Extracting Test PDF...')
        test_pages = extract_pages(test_buffer)
        
        if on_progress: on_progress(22, 'Parsing questions from Test PDF...')
        q_map = parse_test_pdf(test_pages, lambda msg: on_progress(22, msg) if on_progress else None)
        q_count = len(q_map)
        
        if q_count == 0:
            return {
                'success': False,
                'error': 'No questions found in Test PDF.\nMake sure the PDF has text-based (a)(b)(c)(d) options and is not scanned.'
            }
            
        if on_progress: on_progress(46, 'Extracting Solution PDF...')
        sol_pages = extract_pages(sol_buffer)
        
        if on_progress: on_progress(68, 'Parsing answers and explanations...')
        parsed_sols = parse_sol_pdf(sol_pages, lambda msg: on_progress(68, msg) if on_progress else None)
        answers = parsed_sols['answers']
        explanations = parsed_sols['explanations']
        
        if not answers:
            return {
                'success': False,
                'error': 'No answers found in Solution PDF.\nMake sure the solution PDF has "Q 1.A" style answer headers.'
            }
            
        if on_progress: on_progress(88, 'Building output...')
        output_data = build_output(q_map, answers, explanations)
        
        if on_progress: on_progress(100, f"Done! {output_data['total']} questions · {output_data['matched']} matched")
        
        return {
            'success': True,
            'output': output_data['text'],
            'questionCount': output_data['total'],
            'lineCount': len(output_data['text'].split('\n')),
            'stats': {
                'matched': output_data['matched'],
                'noAns': output_data['noAns'],
                'noExpl': output_data['noExpl'],
                'explanationsFound': output_data['total'] - output_data['noExpl']
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
