#!/usr/bin/env python3
"""NoteCaddy Web Server - использует встроенный http.server"""

import http.server
import socketserver
import json
import os
from datetime import datetime
import re
import urllib.parse
import threading

PORT = 5000
NOTES_FILE = "notes.json"

HTML_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NoteCaddy</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #1a1a2e, #16213e); min-height: 100vh; padding: 20px; color: #e0e0e0; }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 30px; color: #00d9ff; }
        h2 { margin-bottom: 15px; }
        .form-card { background: #1f2937; border-radius: 12px; padding: 24px; margin-bottom: 30px; }
        textarea { width: 100%; height: 100px; padding: 12px; border: 2px solid #374151; border-radius: 8px; background: #111827; color: #e0e0e0; font-size: 14px; }
        .btn { background: #00d9ff; color: #000; border: none; padding: 12px 24px; border-radius: 8px; font-size: 16px; cursor: pointer; margin-top: 12px; }
        .btn-delete { background: #ff4757; color: #fff; padding: 8px 16px; font-size: 14px; }
        .note-card { background: #1f2937; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
        .note-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #374151; padding-bottom: 12px; }
        .note-id { color: #00d9ff; font-weight: bold; }
        .note-date { color: #9ca3af; font-size: 13px; margin-left: 10px; }
        .note-text { background: #111827; padding: 12px; border-radius: 8px; white-space: pre-wrap; margin-bottom: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>NoteCaddy</h1>
        
        <div class="form-card">
            <h2>Новая заметка</h2>
            <form method="POST" action="/add">
                <textarea name="text" placeholder="Введите текст заметки..."></textarea>
                <button type="submit" class="btn">Сохранить</button>
            </form>
        </div>
        
        <h2>Все заметки (COUNT)</h2>
        NOTES_HTML
    </div>
</body>
</html>
"""

def load_notes():
    if not os.path.exists(NOTES_FILE):
        return []
    try:
        with open(NOTES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_notes(notes):
    with open(NOTES_FILE, 'w', encoding='utf-8') as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)

def process_text(raw):
    sentences = re.split(r'(?<=[.!?])\s+', raw.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    processed, dates = [], []
    for s in sentences:
        if re.search(r'\d{1,2}:\d{2}|завтра|сегодня', s.lower()):
            dates.append(s)
        else:
            processed.append(s)
    result = ('📅 ' + ' | '.join(dates) + '\n\n') if dates else ''
    result += '📝 ' + ' | '.join(processed)
    return result, (dates[0] if dates else (processed[0] if processed else raw[:50]))[:100]

def add_note(text):
    notes = load_notes()
    note_id = max([n['id'] for n in notes], default=0) + 1
    processed, summary = process_text(text)
    notes.append({
        'id': note_id,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'raw_text': text,
        'processed_text': processed,
        'summary': summary
    })
    save_notes(notes)

def delete_note(note_id):
    save_notes([n for n in load_notes() if n['id'] != note_id])

class NoteCaddyHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    
    def do_GET(self):
        if self.path == '/':
            notes = load_notes()[::-1]
            notes_html = ''
            for n in notes:
                notes_html += f'''
                <div class="note-card">
                    <div class="note-header">
                        <div><span class="note-id">#{n['id']}</span><span class="note-date">{n['created_at']}</span></div>
                        <form method="POST" action="/delete"><input type="hidden" name="id" value="{n['id']}"><button type="submit" class="btn btn-delete">Удалить</button></form>
                    </div>
                    <div class="note-text"><b>Кратко:</b> {n['summary']}</div>
                    <div class="note-text"><b>Обработано:</b> {n['processed_text']}</div>
                    <div class="note-text"><b>Исходник:</b> {n['raw_text']}</div>
                </div>'''
            
            html = HTML_PAGE.replace('COUNT', str(len(notes))).replace('NOTES_HTML', notes_html)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = urllib.parse.parse_qs(post_data)
        
        if self.path == '/add':
            text = params.get('text', [''])[0]
            if text:
                add_note(text)
        elif self.path == '/delete':
            note_id = int(params.get('id', [0])[0])
            delete_note(note_id)
        
        self.send_response(303)
        self.send_header('Location', '/')
        self.end_headers()

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Многопоточный HTTP сервер"""
    allow_reuse_address = True

if __name__ == '__main__':
    print(f'NoteCaddy: http://localhost:{PORT}')
    server = ThreadedHTTPServer(('127.0.0.1', PORT), NoteCaddyHandler)
    server.serve_forever()
