from flask import Flask, render_template
from collections import OrderedDict, defaultdict
import json
import os
import socket
import string
import sys

py3 = sys.version_info[0] >= 3
if not py3:
    input = raw_input

app = Flask('voice')

def readall(s):
    text = []
    while True:
        j = json.loads(s.readline())
        if j['cmd'] == 'print':
            text.append(j['text'].rstrip('\n'))
        else:
            break
    return '\n'.join(text)

def repl_run(lines):
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(os.path.expanduser('~/.talon/.sys/repl.sock'))
        if py3:
            sin = s.makefile('r', buffering=1, encoding='utf8')
        else:
            sin = s.makefile('r', bufsize=1)

        motd = readall(sin)

        responses = []
        for line in lines.split('\n'):
            m = {'cmd': 'input', 'text': line}
            s.send((json.dumps(m) + '\n').encode('utf8'))
            responses.append(readall(sin))
        s.shutdown(socket.SHUT_WR)
        s.shutdown(socket.SHUT_RD)
        return responses
    finally:
        try: s.close()
        except Exception: pass

FETCH_SCRIPT = r'''from collections import defaultdict
from talon import registry
from talon.legacy.voice import Key
import json
try:
    from user import std
    alnum = std.alpha_alt
except Exception:
    alnum = []

response = {'contexts': {}}
response['alnum'] = alnum

def pretty(target):
    if isinstance(target, Key):
        return f'key({target.data})'
    elif callable(target):
        return f'{target.__name__}()'
    elif isinstance(target, list):
        return ' '.join([pretty(v) for v in target])
    else:
        return repr(target)

active_contexts = registry.active_contexts()

for name, ctx in registry.contexts.items():
    d = response['contexts'][name] = {
        'active': ctx in active_contexts,
        'commands': [],
    }
    commands = d['commands']
    for impl in ctx.commands.values():
        desc = pretty(impl.target)
        commands.append((impl.rule.rule, desc))

print(json.dumps(response))
'''

def get_grammar():
    response = '\n'.join(repl_run(FETCH_SCRIPT))
    try:
        return json.loads(response)
    except ValueError:
        print(response)
        raise

replacements = {
    '(0 | 1 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 2 | 20 | 3 | 30 | 4 | 40 | 5 | 50 | 6 | 60 | 7 | 70 | 8 | 80 | 9 | 90 | oh)': '<number>',
}

def fixup(name, cmd):
    for a, b in replacements.items():
        name = name.replace(a, b)
    if isinstance(cmd, list):
        cmd = ', '.join(cmd)
    cmd = cmd.replace(a, b)
    return name, cmd

@app.route('/')
def slash():
    grammar = get_grammar()
    for name, ctx in grammar['contexts'].items():
        ctx['commands'] = [fixup(trigger, cmd)
                           for trigger, cmd in ctx['commands']]
    alpha = map(str.lower, grammar['alnum'])
    return render_template('index.html', contexts=grammar['contexts'], alpha=alpha)

if __name__ == '__main__':
    app.run(port=6001, debug=True)
