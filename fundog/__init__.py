from email.header import Header
from email.mime.text import MIMEText
import io
import json
import os
import re
import shutil
import smtplib
import sys
import time

import requests

version = '0.8.0'
hinted = False

def load_config(channel):
    global hinted

    conf_path = os.path.expanduser('~/.fundog.json')
    if not os.path.isfile(conf_path):
        tmpl_path = os.path.dirname(__file__) + '/conf/fundog.json'
        shutil.copy(tmpl_path, conf_path)

    with open(conf_path, 'r') as f_conf:
        conf = json.load(f_conf)[channel]
        if channel == 'smtp' and conf['from_email'] != 'someone@gmail.com':
            return conf
        if channel == 'telegram' and conf['token'] != '123456789:-----------------------------------':
            return conf

    if not hinted:
        print('-' * 65)
        print('  Please change fundog config file (~/.fundog.json) to enable.')
        print('-' * 65)
        os.system('open -t ~/.fundog.json')
        hinted = True

def telegram_send_message(conf, summary, detail):
    message = '{}\n```\n{}\n```'.format(summary, detail)

    api = 'https://api.telegram.org/bot{}/sendMessage'.format(conf['token'])
    params = {
        'chat_id': conf['master'],
        'text': message,
        'parse_mode': 'markdown'
    }

    sent = False
    retry = -1
    while not sent and retry < 3:
        r = requests.post(api, data=params)
        if r.status_code != 200:
            retry += 1
        else:
            sent = True

def watch_by_email(func=None, subject=''):
    state = {
        'begin': 0,
        'conf': None,
        'func_name': ''
    }

    def pre_task():
        state['conf'] = load_config('smtp')
        if state['conf'] is not None:
            state['begin'] = time.time()
            sys.stdout = io.StringIO()

    def post_task():
        if state['conf'] is not None:
            conf = state['conf']
            elapsed = time.time() - state['begin']
            sys.stdout.seek(0)
            outstr = sys.stdout.read().rstrip()
            sys.stdout.close()
            sys.stdout = sys.__stdout__

            # Compose email
            contents = re.sub(r'\s+\| ', '\n', '''
                | <p>STDOUT:</p>
                | <pre style="border:1px solid #aaa; border-radius:5px; background:#e7e7e7; padding:10px;">
                | {}
                | </pre>
                | <ul style="padding: 5px">
                | <li>Begin at: </li>
                | <li>End at: </li>
                | <li>Time elapsed: {:.2f}</li>
                | </ul>
                | <p style="color: #d0d0d0;">Sent by fundog {}</p>
                ''') \
                .format(outstr, elapsed, version)

            msg = MIMEText(contents, 'html', 'utf-8')
            if subject == '':
                msg['Subject'] = Header('Function {}() executed.'.format(state['func_name']))
            else:
                msg['Subject'] = Header(subject)
            msg['From'] = '{} <{}>'.format(Header(conf['from_name']).encode(), conf['from_email'])
            msg['To'] = '{} <{}>'.format(Header(conf['to_name']).encode(), conf['to_email'])
            smtp_message = msg.as_string()

            # Send email
            try:
                with smtplib.SMTP(conf['host'], conf['port'], timeout=30) as smtp:
                    smtp.set_debuglevel(2)
                    smtp.starttls()
                    smtp.login(conf['user'], conf['pass'])
                    smtp.sendmail(conf['from_email'], conf['to_email'], smtp_message)
            except Exception as ex:
                print('Failed to send email.')
                print(ex)

    def func_wrapper(*args):
        pre_task()
        fret = func(*args)
        state['func_name'] = func.__name__
        post_task()
        return fret

    def deco_wrapper(func):
        def func_wrapper(*args):
            pre_task()
            fret = func(*args)
            state['func_name'] = func.__name__
            post_task()
            return fret
        return func_wrapper

    return deco_wrapper if func is None else func_wrapper

def watch_by_telegram(func=None, subject='Fuck'):
    state = {
        'begin': 0,
        'conf': None,
        'func_name': ''
    }

    def pre_task():
        state['conf'] = load_config('telegram')
        if state['conf'] is not None:
            state['begin'] = time.time()
            sys.stdout = io.StringIO()

    def post_task():
        if state['conf'] is not None:
            conf = state['conf']
            elapsed = time.time() - state['begin']
            sys.stdout.seek(0)
            outstr = sys.stdout.read().strip()
            sys.stdout.close()
            sys.stdout = sys.__stdout__

            def start(bot, update):
                print('start')

            telegram_send_message(conf, subject, outstr)

    def func_wrapper(*args):
        pre_task()
        fret = func(*args)
        state['func_name'] = func.__name__
        post_task()
        return fret

    def deco_wrapper(func):
        def func_wrapper(*args):
            pre_task()
            fret = func(*args)
            state['func_name'] = func.__name__
            post_task()
            return fret
        return func_wrapper

    return deco_wrapper if func is None else func_wrapper
