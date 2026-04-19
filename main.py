# -*- coding: utf-8 -*-
import os
import sys
import csv
import json
import threading
from datetime import date, datetime

import requests
from kivy.app import App
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.image import Image
from kivy.uix.relativelayout import RelativeLayout
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.filechooser import FileChooserListView

# ==================== 资源路径 ====================
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    elif hasattr(sys, 'android'):
        base = os.path.dirname(os.path.abspath(__file__))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)

# ==================== 中文字体 ====================
def register_chinese_font():
    if sys.platform == 'win32':
        candidates = ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf', 'C:/Windows/Fonts/simsun.ttc']
    elif sys.platform == 'darwin':
        candidates = ['/System/Library/Fonts/PingFang.ttc', '/System/Library/Fonts/STHeiti Light.ttc']
    else:
        candidates = ['/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf']
    for path in candidates:
        if os.path.exists(path):
            try:
                LabelBase.register(name='CJK', fn_regular=path)
                return 'CJK'
            except:
                pass
    return 'Roboto'

FONT_NAME = register_chinese_font()

# ==================== 配置管理 ====================
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, 'ledger.csv')
CONFIG_FILE = os.path.join(APP_DIR, 'app_config.json')
LAST_REPORT_FILE = os.path.join(APP_DIR, 'last_report_month.txt')

DEFAULT_RATES = {
    "CNY": 1.0, "USD": 7.25, "EUR": 7.85, "JPY": 0.048, "GBP": 9.15,
    "HKD": 0.93, "KRW": 0.0054, "AUD": 4.80, "CAD": 5.30, "CHF": 8.10,
    "SGD": 5.40, "NZD": 4.40, "INR": 0.087, "RUB": 0.078, "BRL": 1.35,
}

DEFAULT_APP_CONFIG = {
    "language": "zh", "report_path": APP_DIR, "exchange_rates": DEFAULT_RATES.copy(),
    "default_currency": "CNY", "last_rate_update": None, "first_run": True,
    "username": "", "theme": "Light",
}

def load_app_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            for k, v in DEFAULT_APP_CONFIG.items():
                if k not in config:
                    config[k] = v
            fixed = False
            for cur, rate in config["exchange_rates"].items():
                if cur != "CNY" and rate < 0.5 and rate > 0:
                    config["exchange_rates"][cur] = 1.0 / rate
                    fixed = True
            if fixed:
                save_app_config(config)
            return config
    return DEFAULT_APP_CONFIG.copy()

def save_app_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

# ==================== 汇率 ====================
def fetch_exchange_rates(base="CNY"):
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{base}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        original = data["rates"]
        converted = {}
        for cur, rate in original.items():
            if cur == base:
                converted[cur] = 1.0
            else:
                converted[cur] = 1.0 / rate
        for cur in DEFAULT_RATES:
            if cur not in converted:
                converted[cur] = DEFAULT_RATES.get(cur, 1.0)
        return converted
    except:
        return None

def update_rates_async(app_config, callback=None):
    def task():
        new = fetch_exchange_rates("CNY")
        if new:
            app_config["exchange_rates"] = new
            app_config["last_rate_update"] = date.today().isoformat()
            save_app_config(app_config)
            if callback:
                callback(True, new)
        else:
            if callback:
                callback(False, None)
    threading.Thread(target=task, daemon=True).start()

# ==================== 多语言 ====================
TEXTS = {
    "zh": {
        "app_title": "荔枝记账", "records": "记录", "add_entry": "记账", "others": "其他",
        "settings": "设置", "add": "添加", "edit": "编辑", "delete": "删除", "refresh": "刷新",
        "stats": "统计", "filter": "筛选", "gen_report": "报告", "import_csv": "导入",
        "date": "日期", "category": "类别", "amount": "金额", "currency": "货币", "note": "备注",
        "income": "收入", "expense": "支出", "balance": "结余", "all": "全部记录",
        "preset_cats": ["餐饮", "购物", "交通", "娱乐", "医疗", "工资", "转账", "其他"],
        "ok": "确定", "cancel": "取消", "error_empty": "日期、类别和金额不能为空",
        "error_amount": "金额必须是数字", "error_date": "日期格式应为 YYYY-MM-DD",
        "confirm_delete": "确定删除吗？", "filter_prompt": "输入月份 (YYYY-MM) 或 all",
        "filter_error": "格式错误", "stats_title": "分类统计", "report_prompt": "输入月份 (YYYY-MM)",
        "report_success": "报告已保存", "report_fail": "月份格式错误", "rate_success": "汇率更新成功",
        "rate_fail": "汇率更新失败", "rate_info": "实时汇率来自 exchangerate-api.com",
        "username": "用户名", "welcome_title": "欢迎", "welcome_text": "欢迎使用荔枝记账！\n\n数据本地存储，支持实时汇率。\n如有问题请邮件 whcl412App@outlook.com",
        "start": "开始使用", "import_success": "导入成功，共 {count} 条记录", "import_fail": "导入失败",
        "import_title": "导入 CSV", "theme": "主题", "light": "浅色", "dark": "深色",
        "input_id_hint": "请输入记录ID", "record_not_exist": "记录不存在", "delete_success": "删除成功",
        "delete_fail": "请输入数字ID", "filter_placeholder": "YYYY-MM 或 all", "report_placeholder": "YYYY-MM",
    },
    "en": {
        "app_title": "Lychee Ledger", "records": "Records", "add_entry": "Add", "others": "More",
        "settings": "Settings", "add": "Add", "edit": "Edit", "delete": "Delete", "refresh": "Refresh",
        "stats": "Stats", "filter": "Filter", "gen_report": "Report", "import_csv": "Import",
        "date": "Date", "category": "Category", "amount": "Amount", "currency": "Currency", "note": "Note",
        "income": "Income", "expense": "Expense", "balance": "Balance", "all": "All Records",
        "preset_cats": ["Food", "Shopping", "Transport", "Entertainment", "Medical", "Salary", "Transfer", "Other"],
        "ok": "OK", "cancel": "Cancel", "error_empty": "Date, category and amount cannot be empty",
        "error_amount": "Amount must be a number", "error_date": "Date format should be YYYY-MM-DD",
        "confirm_delete": "Delete this record?", "filter_prompt": "Enter month (YYYY-MM) or all",
        "filter_error": "Invalid format", "stats_title": "Statistics", "report_prompt": "Enter month (YYYY-MM)",
        "report_success": "Report saved", "report_fail": "Invalid month format", "rate_success": "Exchange rates updated",
        "rate_fail": "Failed to update rates", "rate_info": "Live rates from exchangerate-api.com",
        "username": "Username", "welcome_title": "Welcome", "welcome_text": "Welcome to Lychee Ledger!\n\nLocal storage, real-time rates.\nEmail whcl412App@outlook.com for issues.",
        "start": "Start", "import_success": "Imported {count} records", "import_fail": "Import failed",
        "import_title": "Import CSV", "theme": "Theme", "light": "Light", "dark": "Dark",
        "input_id_hint": "Enter record ID", "record_not_exist": "Record not found", "delete_success": "Deleted",
        "delete_fail": "Enter numeric ID", "filter_placeholder": "YYYY-MM or all", "report_placeholder": "YYYY-MM",
    }
}

# ==================== 数据模型 ====================
class Record:
    def __init__(self, rid, date_str, category, amount, note):
        self.id = rid; self.date = date_str; self.category = category; self.amount = amount; self.note = note

class LedgerData:
    def __init__(self):
        self.records = []; self.next_id = 1; self.load()
    def load(self):
        self.records.clear()
        if not os.path.exists(DATA_FILE): return
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f); max_id = 0
            for row in reader:
                if len(row) < 5: continue
                try:
                    rid = int(row[0])
                    rec = Record(rid, row[1], row[2], float(row[3]), row[4])
                    self.records.append(rec)
                    if rid > max_id: max_id = rid
                except: pass
        self.next_id = max_id + 1
    def save(self):
        with open(DATA_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            for rec in self.records:
                writer.writerow([rec.id, rec.date, rec.category, rec.amount, rec.note])
    def import_csv(self, filepath):
        new_records = []
        max_id = max([r.id for r in self.records]) if self.records else 0
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 5: continue
                try:
                    rid = int(row[0])
                    if any(r.id == rid for r in self.records): continue
                    rec = Record(rid, row[1], row[2], float(row[3]), row[4])
                    new_records.append(rec)
                    if rid > max_id: max_id = rid
                except: pass
        self.records.extend(new_records); self.next_id = max_id + 1; self.save()
        return len(new_records)
    def add(self, date_str, category, amount, note):
        rec = Record(self.next_id, date_str, category, amount, note)
        self.records.append(rec); self.next_id += 1; self.save(); return rec
    def update(self, rid, date_str, category, amount, note):
        for rec in self.records:
            if rec.id == rid:
                rec.date, rec.category, rec.amount, rec.note = date_str, category, amount, note
                self.save(); return True
        return False
    def delete(self, rid):
        self.records = [r for r in self.records if r.id != rid]; self.save()
    def get_filtered(self, filter_month=None):
        if not filter_month or filter_month == "all": return self.records
        return [r for r in self.records if r.date.startswith(filter_month)]

# ==================== 屏幕类 ====================
class RecordsScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs); self.app = app; self.build_ui()
    def build_ui(self):
        layout = BoxLayout(orientation='vertical')
        self.top_label = Label(text=self.app.get_text("records"), size_hint_y=0.08, font_name=FONT_NAME)
        layout.add_widget(self.top_label)
        self.scroll = ScrollView()
        self.list_layout = GridLayout(cols=1, size_hint_y=None, spacing=dp(2))
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        self.scroll.add_widget(self.list_layout)
        layout.add_widget(self.scroll)
        self.status_label = Label(size_hint_y=0.06, font_name=FONT_NAME)
        layout.add_widget(self.status_label)
        btn_layout = BoxLayout(size_hint_y=0.1, spacing=dp(5))
        self.btn_add = Button(text=self.app.get_text("add"), font_name=FONT_NAME, on_press=lambda x: self.app.show_add_dialog())
        self.btn_edit = Button(text=self.app.get_text("edit"), font_name=FONT_NAME, on_press=lambda x: self.app.edit_record())
        self.btn_delete = Button(text=self.app.get_text("delete"), font_name=FONT_NAME, on_press=lambda x: self.app.delete_record())
        self.btn_refresh = Button(text=self.app.get_text("refresh"), font_name=FONT_NAME, on_press=lambda x: self.app.refresh_list())
        btn_layout.add_widget(self.btn_add)
        btn_layout.add_widget(self.btn_edit)
        btn_layout.add_widget(self.btn_delete)
        btn_layout.add_widget(self.btn_refresh)
        layout.add_widget(btn_layout)
        self.add_widget(layout)
    def update_texts(self):
        self.top_label.text = self.app.get_text("records")
        self.btn_add.text = self.app.get_text("add")
        self.btn_edit.text = self.app.get_text("edit")
        self.btn_delete.text = self.app.get_text("delete")
        self.btn_refresh.text = self.app.get_text("refresh")
        self.update_status()
    def update_status(self):
        records = self.app.display_records
        income = sum(r.amount for r in records if r.amount > 0)
        expense = sum(-r.amount for r in records if r.amount < 0)
        balance = income - expense
        filter_text = self.app.current_filter if self.app.current_filter != "all" else self.app.get_text("all")
        self.status_label.text = f"{filter_text}  {self.app.get_text('income')}:{income:.2f}  {self.app.get_text('expense')}:{expense:.2f}  {self.app.get_text('balance')}:{balance:.2f}"
        self.status_label.color = self.app.text_color
    def on_enter(self):
        self.update_texts()
        self.app.refresh_list()
        self.top_label.color = self.app.text_color
        self.btn_add.color = self.app.text_color
        self.btn_edit.color = self.app.text_color
        self.btn_delete.color = self.app.text_color
        self.btn_refresh.color = self.app.text_color

class AddEntryScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs); self.app = app; self.build_ui()
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        self.top_label = Label(text=self.app.get_text("add_entry"), size_hint_y=0.08, font_name=FONT_NAME)
        layout.add_widget(self.top_label)
        self.date_input = TextInput(hint_text=self.app.get_text("date"), text=str(date.today()), font_name=FONT_NAME)
        layout.add_widget(self.date_input)
        self.cat_input = TextInput(hint_text=self.app.get_text("category"), font_name=FONT_NAME)
        layout.add_widget(self.cat_input)
        self.preset_layout = BoxLayout(size_hint_y=None, height=dp(40))
        layout.add_widget(self.preset_layout)
        self.amt_cur_layout = BoxLayout(spacing=dp(10))
        self.amount_input = TextInput(hint_text=self.app.get_text("amount"), input_filter='float', font_name=FONT_NAME)
        self.currency_spinner = Spinner(text=self.app.default_currency, values=list(self.app.exchange_rates.keys()), font_name=FONT_NAME)
        self.amt_cur_layout.add_widget(self.amount_input)
        self.amt_cur_layout.add_widget(self.currency_spinner)
        layout.add_widget(self.amt_cur_layout)
        self.note_input = TextInput(hint_text=self.app.get_text("note"), font_name=FONT_NAME)
        layout.add_widget(self.note_input)
        self.rate_label = Label(text="", font_name=FONT_NAME)
        layout.add_widget(self.rate_label)
        self.save_btn = Button(text=self.app.get_text("ok"), font_name=FONT_NAME, on_press=self.save_record)
        layout.add_widget(self.save_btn)
        self.add_widget(layout)
        self.update_preset_buttons()
    def update_preset_buttons(self):
        self.preset_layout.clear_widgets()
        cats = self.app.get_text("preset_cats")
        for cat in cats:
            btn = Button(text=cat, font_name=FONT_NAME, size_hint_x=1.0/len(cats))
            btn.bind(on_release=lambda x, c=cat: setattr(self.cat_input, 'text', c))
            self.preset_layout.add_widget(btn)
    def update_rate_preview(self, *args):
        cur = self.currency_spinner.text
        rate = self.app.exchange_rates.get(cur, 1.0)
        self.rate_label.text = f"1 {cur} = {rate:.4f} CNY"
        try:
            amt = float(self.amount_input.text)
            cny = amt * rate
            self.rate_label.text += f"\n≈ {cny:.2f} CNY"
        except: pass
    def save_record(self, instance):
        date_str = self.date_input.text.strip()
        category = self.cat_input.text.strip()
        try:
            amount_val = float(self.amount_input.text.strip())
        except:
            self.app.show_message(self.app.get_text("error_amount")); return
        currency = self.currency_spinner.text
        note = self.note_input.text.strip()
        if not date_str or not category:
            self.app.show_message(self.app.get_text("error_empty")); return
        if len(date_str) != 10 or date_str[4] != '-' or date_str[7] != '-':
            self.app.show_message(self.app.get_text("error_date")); return
        rate = self.app.exchange_rates.get(currency, 1.0)
        amount_cny = amount_val * rate
        self.app.data.add(date_str, category, amount_cny, note)
        self.app.refresh_list()
        self.app.change_tab("records")
        self.app.show_message(self.app.get_text("add") + " " + self.app.get_text("ok"))
    def update_texts(self):
        self.top_label.text = self.app.get_text("add_entry")
        self.date_input.hint_text = self.app.get_text("date")
        self.cat_input.hint_text = self.app.get_text("category")
        self.amount_input.hint_text = self.app.get_text("amount")
        self.note_input.hint_text = self.app.get_text("note")
        self.save_btn.text = self.app.get_text("ok")
        self.update_preset_buttons()
        self.update_rate_preview()
    def on_enter(self):
        self.update_texts()
        self.date_input.text = str(date.today())
        self.cat_input.text = ""
        self.amount_input.text = ""
        self.note_input.text = ""
        self.currency_spinner.text = self.app.default_currency
        self.update_rate_preview()
        self.amount_input.bind(text=self.update_rate_preview)
        self.currency_spinner.bind(text=self.update_rate_preview)
        # 主题颜色
        self.top_label.color = self.app.text_color
        self.date_input.foreground_color = self.app.text_color
        self.cat_input.foreground_color = self.app.text_color
        self.amount_input.foreground_color = self.app.text_color
        self.note_input.foreground_color = self.app.text_color
        self.rate_label.color = self.app.text_color
        self.save_btn.color = self.app.text_color
        for btn in self.preset_layout.children:
            btn.color = self.app.text_color

class OthersScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs); self.app = app; self.build_ui()
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        self.top_label = Label(text=self.app.get_text("others"), size_hint_y=0.08, font_name=FONT_NAME)
        layout.add_widget(self.top_label)
        self.btn_stats = Button(text=self.app.get_text("stats"), font_name=FONT_NAME, on_press=lambda x: self.app.show_stats())
        self.btn_filter = Button(text=self.app.get_text("filter"), font_name=FONT_NAME, on_press=lambda x: self.app.filter_month())
        self.btn_report = Button(text=self.app.get_text("gen_report"), font_name=FONT_NAME, on_press=lambda x: self.app.manual_report())
        self.btn_import = Button(text=self.app.get_text("import_csv"), font_name=FONT_NAME, on_press=lambda x: self.app.import_csv_file())
        layout.add_widget(self.btn_stats)
        layout.add_widget(self.btn_filter)
        layout.add_widget(self.btn_report)
        layout.add_widget(self.btn_import)
        self.add_widget(layout)
    def update_texts(self):
        self.top_label.text = self.app.get_text("others")
        self.btn_stats.text = self.app.get_text("stats")
        self.btn_filter.text = self.app.get_text("filter")
        self.btn_report.text = self.app.get_text("gen_report")
        self.btn_import.text = self.app.get_text("import_csv")
    def on_enter(self):
        self.update_texts()
        self.top_label.color = self.app.text_color
        for btn in [self.btn_stats, self.btn_filter, self.btn_report, self.btn_import]:
            btn.color = self.app.text_color

class SettingsScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs); self.app = app; self.build_ui()
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        self.top_label = Label(text=self.app.get_text("settings"), size_hint_y=0.08, font_name=FONT_NAME)
        layout.add_widget(self.top_label)
        # 语言
        lang_layout = BoxLayout(size_hint_y=None, height=dp(40))
        lang_layout.add_widget(Label(text=self.app.get_text("language"), size_hint_x=0.4, font_name=FONT_NAME))
        self.lang_spinner = Spinner(text=self.app.lang, values=["zh", "en"], font_name=FONT_NAME)
        lang_layout.add_widget(self.lang_spinner)
        layout.add_widget(lang_layout)
        # 默认货币
        cur_layout = BoxLayout(size_hint_y=None, height=dp(40))
        cur_layout.add_widget(Label(text=self.app.get_text("currency"), size_hint_x=0.4, font_name=FONT_NAME))
        self.cur_spinner = Spinner(text=self.app.default_currency, values=list(self.app.exchange_rates.keys()), font_name=FONT_NAME)
        cur_layout.add_widget(self.cur_spinner)
        layout.add_widget(cur_layout)
        # 报告路径
        path_layout = BoxLayout(size_hint_y=None, height=dp(40))
        path_layout.add_widget(Label(text=self.app.get_text("report_path"), size_hint_x=0.4, font_name=FONT_NAME))
        self.path_input = TextInput(text=self.app.report_path, font_name=FONT_NAME)
        path_layout.add_widget(self.path_input)
        layout.add_widget(path_layout)
        # 用户名
        user_layout = BoxLayout(size_hint_y=None, height=dp(40))
        user_layout.add_widget(Label(text=self.app.get_text("username"), size_hint_x=0.4, font_name=FONT_NAME))
        self.user_input = TextInput(text=self.app.username, font_name=FONT_NAME)
        user_layout.add_widget(self.user_input)
        layout.add_widget(user_layout)
        # 主题
        theme_layout = BoxLayout(size_hint_y=None, height=dp(40))
        theme_layout.add_widget(Label(text=self.app.get_text("theme"), size_hint_x=0.4, font_name=FONT_NAME))
        self.theme_spinner = Spinner(text=self.app.theme, values=["Light", "Dark"], font_name=FONT_NAME)
        theme_layout.add_widget(self.theme_spinner)
        layout.add_widget(theme_layout)
        self.btn_update = Button(text=self.app.get_text("update_rates"), font_name=FONT_NAME, on_press=lambda x: self.app.update_rates())
        layout.add_widget(self.btn_update)
        self.rate_info_label = Label(text=self.app.get_text("rate_info"), size_hint_y=0.1, font_name=FONT_NAME)
        layout.add_widget(self.rate_info_label)
        save_btn = Button(text=self.app.get_text("ok"), font_name=FONT_NAME, on_press=lambda x: self.save_settings())
        layout.add_widget(save_btn)
        self.add_widget(layout)
    def save_settings(self):
        self.app.app_config["language"] = self.lang_spinner.text
        self.app.app_config["default_currency"] = self.cur_spinner.text
        self.app.app_config["report_path"] = self.path_input.text.strip()
        self.app.app_config["username"] = self.user_input.text.strip()
        self.app.app_config["theme"] = self.theme_spinner.text
        save_app_config(self.app.app_config)
        self.app.lang = self.app.app_config["language"]
        self.app.default_currency = self.app.app_config["default_currency"]
        self.app.report_path = self.app.app_config["report_path"]
        self.app.username = self.app.app_config["username"]
        self.app.theme = self.app.app_config["theme"]
        self.app.apply_theme()
        self.app.update_all_ui_texts()
        self.app.refresh_list()
        self.app.show_message(self.app.get_text("settings") + " " + self.app.get_text("ok"))
    def update_texts(self):
        self.top_label.text = self.app.get_text("settings")
        # 更新设置页内的静态标签
        for child in self.children:
            if isinstance(child, BoxLayout):
                for sub in child.children:
                    if isinstance(sub, Label):
                        if sub.text in ["语言", "Language"]:
                            sub.text = self.app.get_text("language")
                        elif sub.text in ["默认货币", "Default currency"]:
                            sub.text = self.app.get_text("currency")
                        elif sub.text in ["报告保存路径", "Report path"]:
                            sub.text = self.app.get_text("report_path")
                        elif sub.text in ["用户名", "Username"]:
                            sub.text = self.app.get_text("username")
                        elif sub.text in ["主题", "Theme"]:
                            sub.text = self.app.get_text("theme")
        self.btn_update.text = self.app.get_text("update_rates")
        self.rate_info_label.text = self.app.get_text("rate_info")
    def on_enter(self):
        self.update_texts()
        self.top_label.color = self.app.text_color
        self.lang_spinner.text = self.app.lang
        self.cur_spinner.text = self.app.default_currency
        self.path_input.text = self.app.report_path
        self.user_input.text = self.app.username
        self.theme_spinner.text = self.app.theme
        self.btn_update.color = self.app.text_color
        self.rate_info_label.color = self.app.text_color

# ==================== 主应用 ====================
class LedgerApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app_config = load_app_config()
        self.lang = self.app_config.get("language", "zh")
        self.exchange_rates = self.app_config.get("exchange_rates", DEFAULT_RATES)
        self.default_currency = self.app_config.get("default_currency", "CNY")
        self.username = self.app_config.get("username", "")
        self.report_path = self.app_config.get("report_path", APP_DIR)
        self.theme = self.app_config.get("theme", "Light")
        self.data = LedgerData()
        self.current_filter = "all"
        self.display_records = []
        self.text_color = (0,0,0,1)

    def build(self):
        self.sm = ScreenManager()
        self.records_screen = RecordsScreen(self, name="records")
        self.add_entry_screen = AddEntryScreen(self, name="add_entry")
        self.others_screen = OthersScreen(self, name="others")
        self.settings_screen = SettingsScreen(self, name="settings")
        self.sm.add_widget(self.records_screen)
        self.sm.add_widget(self.add_entry_screen)
        self.sm.add_widget(self.others_screen)
        self.sm.add_widget(self.settings_screen)

        bottom_bar = BoxLayout(size_hint_y=0.08, spacing=dp(2))
        self.btn_records = Button(text=self.get_text("records"), font_name=FONT_NAME, on_press=lambda x: self.change_tab("records"))
        self.btn_add = Button(text=self.get_text("add_entry"), font_name=FONT_NAME, on_press=lambda x: self.change_tab("add_entry"))
        self.btn_others = Button(text=self.get_text("others"), font_name=FONT_NAME, on_press=lambda x: self.change_tab("others"))
        self.btn_settings = Button(text=self.get_text("settings"), font_name=FONT_NAME, on_press=lambda x: self.change_tab("settings"))
        bottom_bar.add_widget(self.btn_records)
        bottom_bar.add_widget(self.btn_add)
        bottom_bar.add_widget(self.btn_others)
        bottom_bar.add_widget(self.btn_settings)

        main_layout = BoxLayout(orientation='vertical')
        main_layout.add_widget(self.sm)
        main_layout.add_widget(bottom_bar)

        root_layout = RelativeLayout()
        # 背景图片：居中、等比例缩放、完整显示（不裁剪）
        bg_path = resource_path(os.path.join('system photos', 'photos', 'bg.jpg'))
        if not os.path.exists(bg_path):
            bg_dir = resource_path(os.path.join('system photos', 'photos'))
            if os.path.exists(bg_dir):
                for f in os.listdir(bg_dir):
                    if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                        bg_path = os.path.join(bg_dir, f)
                        break
        if os.path.exists(bg_path):
            bg_image = Image(source=bg_path, allow_stretch=True, keep_ratio=True, size_hint=(1,1))
            root_layout.add_widget(bg_image)
        root_layout.add_widget(main_layout)
        return root_layout

    def on_start(self):
        # 设置窗口图标
        icon_path = resource_path(os.path.join('system photos', 'photos', 'icon.png'))
        if os.path.exists(icon_path):
            Window.set_icon(icon_path)
        self.apply_theme()
        if self.app_config.get("first_run", True):
            self.show_welcome()
        self.refresh_list()
        self.check_auto_report()

    def apply_theme(self):
        if self.theme == "Dark":
            Window.clearcolor = (0.1, 0.1, 0.1, 1)
            self.text_color = (1, 1, 1, 1)
        else:
            Window.clearcolor = (0.95, 0.95, 0.95, 1)
            self.text_color = (0, 0, 0, 1)
        # 递归设置所有控件的颜色
        def set_color(widget):
            if isinstance(widget, (Label, Button)):
                widget.color = self.text_color
            elif isinstance(widget, TextInput):
                widget.foreground_color = self.text_color
            if hasattr(widget, 'children'):
                for child in widget.children:
                    set_color(child)
        if self.root:
            set_color(self.root)

    def update_all_ui_texts(self):
        self.records_screen.update_texts()
        self.add_entry_screen.update_texts()
        self.others_screen.update_texts()
        self.settings_screen.update_texts()
        self.btn_records.text = self.get_text("records")
        self.btn_add.text = self.get_text("add_entry")
        self.btn_others.text = self.get_text("others")
        self.btn_settings.text = self.get_text("settings")
        self.refresh_list()

    def get_text(self, key):
        return TEXTS.get(self.lang, TEXTS['zh']).get(key, key)

    def change_tab(self, name):
        self.sm.current = name

    def refresh_list(self, filter_month=None):
        if filter_month is not None:
            self.current_filter = filter_month
        self.display_records = self.data.get_filtered(self.current_filter)
        self.records_screen.list_layout.clear_widgets()
        for rec in self.display_records:
            label = Label(
                text=f"{rec.id} | {rec.date} | {rec.category} | {rec.amount:.2f} | {rec.note}",
                size_hint_y=None, height=dp(40), text_size=(None, dp(40)), valign='middle',
                font_name=FONT_NAME, color=self.text_color
            )
            self.records_screen.list_layout.add_widget(label)
        self.records_screen.update_status()

    def show_add_dialog(self):
        self.show_record_dialog()

    def show_record_dialog(self, rec=None):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        date_input = TextInput(hint_text=self.get_text("date"), text=str(date.today()) if not rec else rec.date, font_name=FONT_NAME, foreground_color=self.text_color)
        content.add_widget(date_input)
        cat_input = TextInput(hint_text=self.get_text("category"), text=rec.category if rec else "", font_name=FONT_NAME, foreground_color=self.text_color)
        content.add_widget(cat_input)

        preset_layout = BoxLayout(size_hint_y=None, height=dp(40))
        cats = self.get_text("preset_cats")
        for cat in cats:
            btn = Button(text=cat, font_name=FONT_NAME, size_hint_x=1.0/len(cats), color=self.text_color)
            btn.bind(on_release=lambda x, c=cat: setattr(cat_input, 'text', c))
            preset_layout.add_widget(btn)
        content.add_widget(preset_layout)

        amt_cur_layout = BoxLayout(spacing=dp(10))
        amount_input = TextInput(hint_text=self.get_text("amount"), text=str(rec.amount) if rec else "", input_filter='float', font_name=FONT_NAME, foreground_color=self.text_color)
        currency_spinner = Spinner(text=self.default_currency, values=list(self.exchange_rates.keys()), font_name=FONT_NAME)
        amt_cur_layout.add_widget(amount_input)
        amt_cur_layout.add_widget(currency_spinner)
        content.add_widget(amt_cur_layout)

        note_input = TextInput(hint_text=self.get_text("note"), text=rec.note if rec else "", font_name=FONT_NAME, foreground_color=self.text_color)
        content.add_widget(note_input)

        rate_label = Label(text="", font_name=FONT_NAME, color=self.text_color)
        content.add_widget(rate_label)

        def update_rate_preview(*args):
            cur = currency_spinner.text
            rate = self.exchange_rates.get(cur, 1.0)
            rate_label.text = f"1 {cur} = {rate:.4f} CNY"
            try:
                amt = float(amount_input.text)
                cny = amt * rate
                rate_label.text += f"\n≈ {cny:.2f} CNY"
            except: pass
        currency_spinner.bind(text=update_rate_preview)
        amount_input.bind(text=update_rate_preview)
        Clock.schedule_once(lambda dt: update_rate_preview(), 0.1)

        def save(*args):
            date_str = date_input.text.strip()
            category = cat_input.text.strip()
            try:
                amount_val = float(amount_input.text.strip())
            except:
                self.show_message(self.get_text("error_amount")); return
            currency = currency_spinner.text
            note = note_input.text.strip()
            if not date_str or not category:
                self.show_message(self.get_text("error_empty")); return
            if len(date_str) != 10 or date_str[4] != '-' or date_str[7] != '-':
                self.show_message(self.get_text("error_date")); return
            rate = self.exchange_rates.get(currency, 1.0)
            amount_cny = amount_val * rate
            if rec:
                self.data.update(rec.id, date_str, category, amount_cny, note)
            else:
                self.data.add(date_str, category, amount_cny, note)
            self.refresh_list()
            popup.dismiss()
        popup = Popup(title=self.get_text("add") if not rec else self.get_text("edit"), content=content, size_hint=(0.9, 0.7))
        content.add_widget(Button(text=self.get_text("ok"), font_name=FONT_NAME, on_press=save, color=self.text_color))
        content.add_widget(Button(text=self.get_text("cancel"), font_name=FONT_NAME, on_press=lambda x: popup.dismiss(), color=self.text_color))
        popup.open()

    def edit_record(self):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        ti = TextInput(hint_text=self.get_text("input_id_hint"), font_name=FONT_NAME, foreground_color=self.text_color)
        def edit():
            try:
                rid = int(ti.text.strip())
                rec = next((r for r in self.data.records if r.id == rid), None)
                if rec:
                    self.show_record_dialog(rec)
                else:
                    self.show_message(self.get_text("record_not_exist"))
            except:
                self.show_message(self.get_text("delete_fail"))
            popup.dismiss()
        content.add_widget(ti)
        content.add_widget(Button(text=self.get_text("ok"), font_name=FONT_NAME, on_press=lambda x: edit(), color=self.text_color))
        popup = Popup(title=self.get_text("edit"), content=content, size_hint=(0.8, 0.4))
        popup.open()

    def delete_record(self):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        ti = TextInput(hint_text=self.get_text("input_id_hint"), font_name=FONT_NAME, foreground_color=self.text_color)
        def delete():
            try:
                rid = int(ti.text.strip())
                self.data.delete(rid)
                self.refresh_list()
                self.show_message(self.get_text("delete_success"))
            except:
                self.show_message(self.get_text("delete_fail"))
            popup.dismiss()
        content.add_widget(ti)
        content.add_widget(Button(text=self.get_text("ok"), font_name=FONT_NAME, on_press=lambda x: delete(), color=self.text_color))
        popup = Popup(title=self.get_text("delete"), content=content, size_hint=(0.8, 0.4))
        popup.open()

    def show_stats(self):
        stats = {}
        for r in self.data.records:
            cat = r.category
            amt = r.amount
            if cat not in stats:
                stats[cat] = {"income": 0.0, "expense": 0.0}
            if amt > 0:
                stats[cat]["income"] += amt
            else:
                stats[cat]["expense"] += -amt
        text = self.get_text("stats_title") + "\n\n"
        for cat, val in stats.items():
            text += f"{cat}: {self.get_text('income')} {val['income']:.2f}  {self.get_text('expense')} {val['expense']:.2f}\n"
        popup = Popup(title=self.get_text("stats_title"), content=Label(text=text, font_name=FONT_NAME, color=self.text_color), size_hint=(0.8, 0.6))
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 5)

    def filter_month(self):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        ti = TextInput(hint_text=self.get_text("filter_placeholder"), font_name=FONT_NAME, foreground_color=self.text_color)
        def apply(*args):
            val = ti.text.strip()
            if val == "all" or (len(val) == 7 and val[4] == '-'):
                self.refresh_list(val)
                popup.dismiss()
            else:
                self.show_message(self.get_text("filter_error"))
        content.add_widget(ti)
        content.add_widget(Button(text=self.get_text("ok"), font_name=FONT_NAME, on_press=apply, color=self.text_color))
        popup = Popup(title=self.get_text("filter"), content=content, size_hint=(0.8, 0.3))
        popup.open()

    def manual_report(self):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        ti = TextInput(hint_text=self.get_text("report_placeholder"), font_name=FONT_NAME, foreground_color=self.text_color)
        def generate(*args):
            month = ti.text.strip()
            if len(month) == 7 and month[4] == '-':
                self.generate_report(month)
                popup.dismiss()
            else:
                self.show_message(self.get_text("report_fail"))
        content.add_widget(ti)
        content.add_widget(Button(text=self.get_text("ok"), font_name=FONT_NAME, on_press=generate, color=self.text_color))
        popup = Popup(title=self.get_text("gen_report"), content=content, size_hint=(0.8, 0.3))
        popup.open()

    def generate_report(self, year_month):
        month_records = [r for r in self.data.records if r.date.startswith(year_month)]
        cat_expense = {}
        cat_income = {}
        total_income = total_expense = 0.0
        for r in month_records:
            cat, amt = r.category, r.amount
            if amt > 0:
                total_income += amt
                cat_income[cat] = cat_income.get(cat, 0.0) + amt
            else:
                exp = -amt
                total_expense += exp
                cat_expense[cat] = cat_expense.get(cat, 0.0) + exp
        lines = [f"Monthly Report - {year_month}", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "-"*50,
                 f"Total Income: {total_income:.2f} CNY", f"Total Expense: {total_expense:.2f} CNY", f"Balance: {total_income - total_expense:.2f} CNY", "",
                 "Expense by Category:"]
        if cat_expense:
            for cat, amt in sorted(cat_expense.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  {cat}: {amt:.2f} CNY")
        else:
            lines.append("  No expense")
        lines.append(""); lines.append("Income by Category:")
        if cat_income:
            for cat, amt in cat_income.items():
                lines.append(f"  {cat}: {amt:.2f} CNY")
        else:
            lines.append("  No income")
        lines.append(""); lines.append("Details:")
        if month_records:
            for r in month_records:
                lines.append(f"  {r.date} | {r.category} | {r.amount:.2f} CNY | {r.note}")
        else:
            lines.append("  No records")
        save_dir = self.report_path
        if not os.path.exists(save_dir):
            save_dir = APP_DIR
        report_file = os.path.join(save_dir, f"report_{year_month}.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        self.show_message(f"{self.get_text('report_success')}\n{report_file}")

    def import_csv_file(self):
        content = BoxLayout(orientation='vertical')
        filechooser = FileChooserListView(path=APP_DIR, filters=['*.csv'])
        content.add_widget(filechooser)
        def do_import(*args):
            if filechooser.selection:
                filepath = filechooser.selection[0]
                try:
                    count = self.data.import_csv(filepath)
                    self.refresh_list()
                    self.show_message(self.get_text("import_success").format(count=count))
                except Exception as e:
                    self.show_message(self.get_text("import_fail") + f"\n{e}")
            popup.dismiss()
        btn_box = BoxLayout(size_hint_y=0.1)
        btn_box.add_widget(Button(text=self.get_text("ok"), font_name=FONT_NAME, on_press=do_import, color=self.text_color))
        btn_box.add_widget(Button(text=self.get_text("cancel"), font_name=FONT_NAME, on_press=lambda x: popup.dismiss(), color=self.text_color))
        content.add_widget(btn_box)
        popup = Popup(title=self.get_text("import_title"), content=content, size_hint=(0.9, 0.8))
        popup.open()

    def update_rates(self):
        def callback(success, rates):
            if success:
                self.exchange_rates = rates
                self.show_message(self.get_text("rate_success"))
            else:
                self.show_message(self.get_text("rate_fail"))
        update_rates_async(self.app_config, callback)

    def show_message(self, msg):
        popup = Popup(title="提示", content=Label(text=msg, font_name=FONT_NAME, color=self.text_color), size_hint=(0.8, 0.3))
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 2)

    def show_welcome(self):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        content.add_widget(Label(text=self.get_text("welcome_text"), font_name=FONT_NAME, color=self.text_color))
        user_input = TextInput(text=self.username, hint_text=self.get_text("username"), font_name=FONT_NAME, foreground_color=self.text_color)
        content.add_widget(user_input)
        lang_spinner = Spinner(text=self.lang, values=["zh", "en"], font_name=FONT_NAME)
        content.add_widget(lang_spinner)
        cur_spinner = Spinner(text=self.default_currency, values=list(self.exchange_rates.keys()), font_name=FONT_NAME)
        content.add_widget(cur_spinner)
        theme_spinner = Spinner(text=self.theme, values=["Light", "Dark"], font_name=FONT_NAME)
        content.add_widget(theme_spinner)

        def finish(*args):
            self.app_config["username"] = user_input.text.strip() or "用户"
            self.app_config["language"] = lang_spinner.text
            self.app_config["default_currency"] = cur_spinner.text
            self.app_config["theme"] = theme_spinner.text
            self.app_config["first_run"] = False
            save_app_config(self.app_config)
            self.lang = self.app_config["language"]
            self.default_currency = self.app_config["default_currency"]
            self.username = self.app_config["username"]
            self.theme = self.app_config["theme"]
            self.apply_theme()
            self.update_all_ui_texts()
            self.refresh_list()
            popup.dismiss()
        popup = Popup(title=self.get_text("welcome_title"), content=content, size_hint=(0.9, 0.7))
        content.add_widget(Button(text=self.get_text("start"), font_name=FONT_NAME, on_press=finish, color=self.text_color))
        popup.open()

    def check_auto_report(self):
        today = date.today()
        if today.day != 1:
            return
        if today.month == 1:
            target = f"{today.year-1:04d}-12"
        else:
            target = f"{today.year:04d}-{today.month-1:02d}"
        last = ""
        if os.path.exists(LAST_REPORT_FILE):
            with open(LAST_REPORT_FILE, 'r') as f:
                last = f.read().strip()
        if last == target:
            return
        self.generate_report(target)
        with open(LAST_REPORT_FILE, 'w') as f:
            f.write(target)

if __name__ == "__main__":
    LedgerApp().run()
