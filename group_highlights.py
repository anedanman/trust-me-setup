"""
Groups TRUST-ME.xlsx data into per-user, per-day JSON files.

Structure: highlights/<username>/<YYYY-MM-DD>.json
Each file contains:
  - sleep_hours: float or null
  - highlights: list of {
      highlight_number: int,
      timing_seconds: float or null,
      score: float or null,
      chunk: int,
      recording_start: str (HH:MM:SS),
      questions: { question_text: answer, ... }
    }
"""

import openpyxl
import re
import json
import os
from collections import defaultdict

XLSX_PATH = './highlights/TRUST-ME.xlsx'
OUTPUT_DIR = './highlights'

wb = openpyxl.load_workbook(XLSX_PATH)
ws = wb['Responses']

# Read all rows
rows = []
for row in ws.iter_rows(min_row=2, values_only=True):
    rows.append(row)
rows.sort(key=lambda r: r[0] if r[0] else 0)

# Group rows into sessions by close timestamps (within 5 seconds)
sessions = []
current_session = [rows[0]]
for r in rows[1:]:
    if r[0] and current_session[-1][0] and abs((r[0] - current_session[-1][0]).total_seconds()) < 5:
        current_session.append(r)
    else:
        sessions.append(current_session)
        current_session = [r]
sessions.append(current_session)

# Regex for highlight filenames
# Format: highlight_N_USERNAME_chunkM_YYYY-MM-DD$HH-MM-SS-microseconds[_tTIMINGs_scoreSCORE].mp4[ (copy)]
hl_pattern = re.compile(
    r'highlight_(\d+)_(.+?)_chunk(\d+)_(\d{4}-\d{2}-\d{2})\$(\d{2})-(\d{2})-(\d{2})-(\d+)'
    r'(?:_t([\d.]+)s_score([\d.]+))?'
    r'\.mp4'
)

def parse_highlight_name(name):
    """Parse a highlight video filename. Returns dict or None."""
    # Strip copy suffixes like " (copy)", " (3rd copy)", " (another copy)"
    clean = re.sub(r'\s*\((?:\d+\w+\s+)?(?:another\s+)?copy\)', '', str(name).strip())
    m = hl_pattern.match(clean)
    if not m:
        return None
    date_str = m.group(4)
    # Skip 1970 bug entries
    if date_str.startswith('1970'):
        return None
    return {
        'highlight_number': int(m.group(1)),
        'username': m.group(2),
        'chunk': int(m.group(3)),
        'date': date_str,
        'recording_start': '%s:%s:%s' % (m.group(5), m.group(6), m.group(7)),
        'timing_seconds': float(m.group(9)) if m.group(9) else None,
        'score': float(m.group(10)) if m.group(10) else None,
        'original_name': name,
    }

# Question key mapping for the batch JSON format
QUESTION_MAP = {
    'q0': 'How positive or negative emotions did you feel at that moment?',
    'q1': 'How intense were your emotions at that moment?',
    'q2': 'How tired did you feel at that moment?',
    'q3': 'How enthusiastic about your job did you feel at that moment?',
    'q4': 'How immersed in your work did you feel at that moment?',
    'q5': 'How physically uncomfortable or comfortable did you feel at that moment?',
    'q6': 'How negative or positive was the social interaction you had at that moment?',
    'q7': 'How stressful did you find your job at that moment?',
    'q8': 'How productive did you feel at that moment?',
}

# Accumulate: user -> date -> { sleep_hours, highlights }
user_day_data = defaultdict(lambda: defaultdict(lambda: {'sleep_hours': None, 'highlights': {}}))

skipped_1970 = 0
skipped_no_parse = 0
processed_sessions = 0

for sess in sessions:
    # Extract sleep value
    sleep_val = None
    for r in sess:
        if r[2] == 'Sleep Hours':
            sleep_val = r[3]
            break

    # Process highlights - two formats:
    # Format 1: Survey Title = highlight name, Video Name = question, Response = answer
    # Format 2: Survey Title = "Batch Video Survey", Video Name = highlight name, Response = JSON
    
    highlights_in_session = {}  # hl_name -> parsed info
    highlight_qas = defaultdict(dict)  # hl_name -> {question: answer}
    
    for r in sess:
        ts, title, video_name, response = r
        
        # Format 1: Title is a highlight name
        if title and 'highlight_' in str(title):
            parsed = parse_highlight_name(title)
            if parsed is None:
                if '1970' in str(title):
                    skipped_1970 += 1
                continue
            hl_key = parsed['original_name']
            highlights_in_session[hl_key] = parsed
            # video_name is the question text (skip if it's the highlight name itself)
            q = str(video_name).strip()
            if 'highlight_' not in q:
                highlight_qas[hl_key][q] = response
        
        # Format 2: Batch Video Survey
        elif title == 'Batch Video Survey' and video_name and 'highlight_' in str(video_name):
            parsed = parse_highlight_name(video_name)
            if parsed is None:
                if '1970' in str(video_name):
                    skipped_1970 += 1
                continue
            hl_key = parsed['original_name']
            highlights_in_session[hl_key] = parsed
            # response is a JSON string
            try:
                qa_json = json.loads(str(response))
                # Convert keys like "video0_q3" to question text
                for k, v in qa_json.items():
                    # extract qN
                    qm = re.search(r'q(\d+)', k)
                    if qm:
                        q_key = 'q' + qm.group(1)
                        q_text = QUESTION_MAP.get(q_key, q_key)
                        highlight_qas[hl_key][q_text] = v
            except (json.JSONDecodeError, TypeError):
                pass
    
    if not highlights_in_session:
        continue
    
    processed_sessions += 1
    
    # All highlights in a session should share the same user and date
    for hl_key, parsed in highlights_in_session.items():
        username = parsed['username']
        date = parsed['date']
        
        # Store sleep
        if sleep_val is not None:
            user_day_data[username][date]['sleep_hours'] = sleep_val
        
        # Store highlight
        hl_info = {
            'highlight_number': parsed['highlight_number'],
            'timing_seconds': parsed['timing_seconds'],
            'score': parsed['score'],
            'chunk': parsed['chunk'],
            'recording_start': parsed['recording_start'],
            'questions': highlight_qas.get(hl_key, {}),
        }
        # Use highlight number as key to avoid duplicates
        hl_id = 'highlight_%d' % parsed['highlight_number']
        user_day_data[username][date]['highlights'][hl_id] = hl_info

# Write output files
files_written = 0
for username in sorted(user_day_data.keys()):
    user_dir = os.path.join(OUTPUT_DIR, username, 'highlights')
    os.makedirs(user_dir, exist_ok=True)
    
    for date in sorted(user_day_data[username].keys()):
        data = user_day_data[username][date]
        
        # Convert highlights dict to sorted list
        highlights_list = sorted(data['highlights'].values(), key=lambda h: h['highlight_number'])
        
        # Convert any float-looking answers to numbers for cleaner output
        for hl in highlights_list:
            cleaned_qs = {}
            for q, a in hl['questions'].items():
                cleaned_qs[q] = a
            hl['questions'] = cleaned_qs
        
        output = {
            'username': username,
            'date': date,
            'sleep_hours': data['sleep_hours'],
            'highlights': highlights_list,
        }
        
        filepath = os.path.join(user_dir, '%s.json' % date)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False, default=str)
        files_written += 1

print("Done!")
print("Processed sessions: %d" % processed_sessions)
print("Skipped 1970 entries: %d" % skipped_1970)
print("Users: %d" % len(user_day_data))
print("Files written: %d" % files_written)
print()
for username in sorted(user_day_data.keys()):
    dates = sorted(user_day_data[username].keys())
    print("  %s: %d days (%s to %s)" % (username, len(dates), dates[0], dates[-1]))
