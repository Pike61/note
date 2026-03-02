#!/usr/bin/env python3
"""
NoteCaddy — Помощник для заметок
Работает в двух режимах: CLI и веб (Flask)
"""

import json
import datetime
import argparse
import sys
import re
import os

# ============================================================================
# КОНСТАНТЫ
# ============================================================================

NOTES_FILE = "notes.json"
DEFAULT_PORT = 5000

# ============================================================================
# ЯДРО (CORE) — Работа с данными
# ============================================================================

def load_notes() -> list:
    """Загрузка заметок из JSON-файла"""
    if not os.path.exists(NOTES_FILE):
        return []
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_notes(notes: list) -> None:
    """Сохранение заметок в JSON-файл"""
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)


def get_next_id(notes: list) -> int:
    """Получение следующего ID для новой заметки"""
    if not notes:
        return 1
    return max(note["id"] for note in notes) + 1


def add_note(raw_text: str) -> dict:
    """
    Создание новой заметки
    Возвращает созданную заметку
    """
    notes = load_notes()
    processed = process_text(raw_text)
    
    note = {
        "id": get_next_id(notes),
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "raw_text": raw_text,
        "processed_text": processed["processed_text"],
        "summary": processed["summary"]
    }
    
    notes.append(note)
    save_notes(notes)
    return note


def delete_note(note_id: int) -> bool:
    """
    Удаление заметки по ID
    Возвращает True если заметка была удалена, False если не найдена
    """
    notes = load_notes()
    initial_len = len(notes)
    notes = [n for n in notes if n["id"] != note_id]
    
    if len(notes) == initial_len:
        return False
    
    save_notes(notes)
    return True


def get_note_by_id(note_id: int) -> dict | None:
    """Получение заметки по ID"""
    notes = load_notes()
    for note in notes:
        if note["id"] == note_id:
            return note
    return None


# ============================================================================
# ОБРАБОТКА ТЕКСТА
# ============================================================================

def process_text(raw_text: str) -> dict:
    """
    Обработка сырого текста
    Возвращает словарь с processed_text и summary
    """
    # Разбиваем на предложения
    sentences = re.split(r'(?<=[.!?])\s+', raw_text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    
    processed_lines = []
    lists = []
    dates_times = []
    
    for sentence in sentences:
        # Поиск дат и времени
        date_patterns = [
            r'\d{1,2}[./]\d{1,2}[./]\d{2,4}',
            r'\d{1,2}\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)',
            r'завтра|сегодня|послезавтра',
        ]
        time_pattern = r'\d{1,2}:\d{2}'
        
        has_date = any(re.search(p, sentence.lower()) for p in date_patterns)
        has_time = re.search(time_pattern, sentence)
        
        if has_date or has_time:
            dates_times.append(sentence)
            continue
        
        # Определение списков (слова через запятую или точку с запятой)
        if re.search(r'[,;].*[,;]', sentence) and len(sentence) < 100:
            items = re.split(r'[,;]\s*', sentence)
            items = [item.strip().rstrip('.') for item in items if item.strip()]
            if len(items) >= 2:
                lists.append(items)
                continue
        
        # Обычные предложения
        if sentence:
            processed_lines.append(sentence)
    
    # Формирование обработанного текста
    result_parts = []
    
    if dates_times:
        result_parts.append("📅 События и даты:")
        for dt in dates_times:
            result_parts.append(f"  • {dt}")
        result_parts.append("")
    
    if lists:
        result_parts.append("📋 Списки:")
        for lst in lists:
            for item in lst:
                result_parts.append(f"  • {item}")
        result_parts.append("")
    
    if processed_lines:
        result_parts.append("📝 Заметки:")
        for line in processed_lines:
            result_parts.append(f"  • {line}")
    
    processed_text = "\n".join(result_parts)
    if not processed_text:
        processed_text = raw_text
    
    # Формирование краткого итога (1-2 предложения)
    summary_parts = []
    if dates_times:
        summary_parts.append(dates_times[0])
    if processed_lines:
        summary_parts.append(processed_lines[0])
    
    summary = " ".join(summary_parts[:2])
    if len(summary) > 150:
        summary = summary[:147] + "..."
    
    return {
        "processed_text": processed_text,
        "summary": summary if summary else raw_text[:100]
    }


# ============================================================================
# CLI ИНТЕРФЕЙС
# ============================================================================

def run_cli_add(text: str) -> None:
    """Добавление заметки через CLI"""
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        pass  # Используем простой вывод, если rich не установлен
    
    note = add_note(text)
    
    try:
        console = Console()
        console.print(f"[green]✓[/green] Заметка создана с ID: {note['id']}")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan")
        table.add_column("Дата", style="cyan")
        table.add_column("Краткий итог", style="white")
        
        table.add_row(
            str(note["id"]),
            note["created_at"],
            note["summary"]
        )
        console.print(table)
    except Exception:
        print(f"Заметка создана с ID: {note['id']}")
        print(f"Дата: {note['created_at']}")
        print(f"Краткий итог: {note['summary']}")


def run_cli_list() -> None:
    """Просмотр списка заметок через CLI"""
    notes = load_notes()
    
    if not notes:
        print("Заметок пока нет.")
        return
    
    try:
        from rich.console import Console
        from rich.table import Table
        
        console = Console()
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", width=5)
        table.add_column("Дата", style="cyan", width=18)
        table.add_column("Краткий итог", style="white")
        
        for note in notes:
            table.add_row(
                str(note["id"]),
                note["created_at"],
                note["summary"]
            )
        
        console.print(table)
        console.print(f"\nВсего заметок: {len(notes)}")
    except Exception:
        # Простой вывод без rich
        print(f"{'ID':<5} {'Дата':<18} Краткий итог")
        print("-" * 60)
        for note in notes:
            summary = note["summary"][:50] + "..." if len(note["summary"]) > 50 else note["summary"]
            print(f"{note['id']:<5} {note['created_at']:<18} {summary}")
        print(f"\nВсего заметок: {len(notes)}")


def run_cli_delete(note_id: int) -> None:
    """Удаление заметки через CLI"""
    if delete_note(note_id):
        try:
            from rich.console import Console
            console = Console()
            console.print(f"[green]✓[/green] Заметка {note_id} удалена")
        except Exception:
            print(f"Заметка {note_id} удалена")
    else:
        try:
            from rich.console import Console
            console = Console()
            console.print(f"[red]✗[/red] Заметка с ID={note_id} не найдена")
        except Exception:
            print(f"Ошибка: Заметка с ID={note_id} не найдена")


def run_cli() -> None:
    """Запуск CLI-режима"""
    parser = argparse.ArgumentParser(
        description="NoteCaddy — Помощник для заметок",
        prog="notecaddy"
    )
    subparsers = parser.add_subparsers(dest="command", help="Команды")
    
    # Команда add
    add_parser = subparsers.add_parser("add", help="Создать заметку")
    add_parser.add_argument("text", help="Текст заметки", nargs="+")
    
    # Команда list
    subparsers.add_parser("list", help="Показать все заметки")
    
    # Команда delete
    delete_parser = subparsers.add_parser("delete", help="Удалить заметку")
    delete_parser.add_argument("id", type=int, help="ID заметки")
    
    args = parser.parse_args()
    
    if args.command == "add":
        text = " ".join(args.text)
        run_cli_add(text)
    elif args.command == "list":
        run_cli_list()
    elif args.command == "delete":
        run_cli_delete(args.id)
    else:
        parser.print_help()


# ============================================================================
# ВЕБ-ИНТЕРФЕЙС (FLASK)
# ============================================================================

# HTML-шаблон (встроенный)
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NoteCaddy — Помощник для заметок</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 20px;
            color: #e0e0e0;
        }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 30px; color: #00d9ff; }
        .form-card {
            background: #1f2937;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .form-card h2 { margin-bottom: 16px; color: #00d9ff; }
        textarea {
            width: 100%;
            height: 120px;
            padding: 12px;
            border: 2px solid #374151;
            border-radius: 8px;
            background: #111827;
            color: #e0e0e0;
            font-size: 14px;
            resize: vertical;
            font-family: inherit;
        }
        textarea:focus { outline: none; border-color: #00d9ff; }
        .btn {
            background: linear-gradient(135deg, #00d9ff 0%, #0099cc 100%);
            color: #000;
            border: none;
            padding: 12px 32px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 12px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,217,255,0.3); }
        .btn-delete {
            background: linear-gradient(135deg, #ff4757 0%, #c0392b 100%);
            color: #fff;
            padding: 8px 16px;
            font-size: 14px;
        }
        .notes-grid { display: grid; gap: 20px; }
        .note-card {
            background: #1f2937;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .note-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 1px solid #374151;
        }
        .note-id { color: #00d9ff; font-weight: bold; }
        .note-date { color: #9ca3af; font-size: 13px; }
        .note-summary {
            background: #111827;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 12px;
            border-left: 3px solid #00d9ff;
        }
        .note-summary-label { color: #9ca3af; font-size: 12px; margin-bottom: 4px; }
        .note-section { margin-bottom: 10px; }
        .note-section-label { color: #9ca3af; font-size: 12px; margin-bottom: 4px; }
        .note-text {
            background: #111827;
            padding: 12px;
            border-radius: 8px;
            white-space: pre-wrap;
            font-size: 14px;
            line-height: 1.5;
        }
        .empty-state { text-align: center; padding: 40px; color: #9ca3af; }
        .flash { 
            background: #22c55e; color: #000; padding: 12px; 
            border-radius: 8px; margin-bottom: 20px; text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🐍 NoteCaddy</h1>
        
        {% if flash %}
        <div class="flash">{{ flash }}</div>
        {% endif %}
        
        <div class="form-card">
            <h2>📝 Новая заметка</h2>
            <form method="POST" action="/add">
                <textarea name="text" placeholder="Введите текст заметки...&#10;Пример: Купить продукты молоко хлеб яйца. Завтра встреча с Анной в 15:00, обсудить проект."></textarea>
                <button type="submit" class="btn">Сохранить</button>
            </form>
        </div>
        
        <h2 style="margin-bottom: 20px;">📋 Все заметки ({{ notes|length }})</h2>
        
        {% if notes %}
        <div class="notes-grid">
            {% for note in notes %}
            <div class="note-card">
                <div class="note-header">
                    <div>
                        <span class="note-id">#{{ note.id }}</span>
                        <span class="note-date">{{ note.created_at }}</span>
                    </div>
                    <form method="POST" action="/delete" style="display:inline;">
                        <input type="hidden" name="id" value="{{ note.id }}">
                        <button type="submit" class="btn btn-delete" onclick="return confirm('Удалить заметку #{{ note.id }}?')">Удалить</button>
                    </form>
                </div>
                
                <div class="note-summary">
                    <div class="note-summary-label">КРАТКИЙ ИТОГ</div>
                    {{ note.summary }}
                </div>
                
                {% if note.processed_text %}
                <div class="note-section">
                    <div class="note-section-label">ОБРАБОТАННЫЙ ТЕКСТ</div>
                    <div class="note-text">{{ note.processed_text }}</div>
                </div>
                {% endif %}
                
                <div class="note-section">
                    <div class="note-section-label">ИСХОДНЫЙ ТЕКСТ</div>
                    <div class="note-text">{{ note.raw_text }}</div>
                </div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <div class="empty-state">
            <p>Заметок пока нет. Создайте первую заметку выше!</p>
        </div>
        {% endif %}
    </div>
</body>
</html>
'''


def create_flask_app(enable_auth: bool = False, username: str = "admin", password: str = "secret"):
    """Создание Flask-приложения"""
    try:
        from flask import Flask, render_template_string, request, redirect, url_for, flash, session
    except ImportError:
        print("Ошибка: Flask не установлен. Установите: pip install flask")
        sys.exit(1)
    
    app = Flask(__name__)
    app.secret_key = 'notecaddy-secret-key'
    
    # Простая авторизация
    def check_auth():
        if not enable_auth:
            return True
        return session.get('logged_in', False)
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            user = request.form.get('username', '')
            pwd = request.form.get('password', '')
            if user == username and pwd == password:
                session['logged_in'] = True
                return redirect(url_for('index'))
            flash('Неверный логин или пароль')
        return '''<!DOCTYPE html><html><head><title>Login</title></head>
<body style="background:#1a1a2e;color:#fff;padding:50px;font-family:Arial;text-align:center;">
<h2>NoteCaddy - Вход</h2>
<form method="post" style="display:inline-block;text-align:left;">
<input name="username" placeholder="Логин" style="padding:10px;margin:5px;display:block;"><br>
<input name="password" type="password" placeholder="Пароль" style="padding:10px;margin:5px;display:block;"><br>
<button style="padding:10px 30px;background:#00d9ff;border:none;cursor:pointer;">Войти</button>
</form></body></html>'''
    
    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))
    
    @app.route('/')
    def index():
        if enable_auth and not check_auth():
            return redirect(url_for('login'))
        
        notes = load_notes()
        notes = list(reversed(notes))
        return render_template_string(HTML_TEMPLATE, notes=notes)
    
    @app.route('/add', methods=['POST'])
    def add():
        if enable_auth and not check_auth():
            return redirect(url_for('login'))
        
        text = request.form.get('text', '').strip()
        if text:
            add_note(text)
            flash('Заметка успешно сохранена!')
        return redirect(url_for('index'))
    
    @app.route('/delete', methods=['POST'])
    def delete():
        if enable_auth and not check_auth():
            return redirect(url_for('login'))
        
        note_id = request.form.get('id')
        if note_id:
            delete_note(int(note_id))
            flash('Заметка удалена')
        return redirect(url_for('index'))
    
    return app


def run_web(port: int = DEFAULT_PORT, enable_auth: bool = False, username: str = "admin", password: str = "secret") -> None:
    """Запуск веб-сервера Flask"""
    app = create_flask_app(enable_auth=enable_auth, username=username, password=password)
    
    if enable_auth:
        print(f"🔐 Веб-интерфейс доступен по адресу: http://localhost:{port}")
        print(f"   Логин: {username}")
        print(f"   Пароль: {password}")
    else:
        print(f"🌐 Веб-интерфейс доступен по адресу: http://localhost:{port}")
    
    print(f"   Нажмите Ctrl+C для остановки")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    

# ============================================================================
# ТОЧКА ВХОДА
# ============================================================================

def main():
    """Определение режима запуска"""
    parser = argparse.ArgumentParser(
        description="NoteCaddy — Помощник для заметок",
        prog="notecaddy"
    )
    parser.add_argument(
        "--cli", 
        action="store_true", 
        help="Запустить в режиме CLI"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=DEFAULT_PORT, 
        help=f"Порт для веб-сервера (по умолчанию: {DEFAULT_PORT})"
    )
    # Аргументы авторизации
    parser.add_argument(
        "--auth", 
        action="store_true", 
        help="Включить авторизацию"
    )
    parser.add_argument(
        "--username", 
        default="admin", 
        help="Имя пользователя для авторизации"
    )
    parser.add_argument(
        "--password", 
        default="secret", 
        help="Пароль для авторизации"
    )
    parser.add_argument(
        "command", 
        nargs="?", 
        help="Команда: add, list, delete (автоматически включает CLI-режим)"
    )
    parser.add_argument("args", nargs="*", help="Аргументы команды")
    
    args = parser.parse_args()
    
    # Если есть команда — запускаем CLI
    if args.command in ("add", "list", "delete") or args.cli:
        run_cli()
    else:
        # По умолчанию — веб-режим
        run_web(args.port, args.auth, args.username, args.password)


if __name__ == "__main__":
    main()
