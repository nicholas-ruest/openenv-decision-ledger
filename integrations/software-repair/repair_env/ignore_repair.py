"""Original small Gitignore-subset module task; independent regular-expression oracle."""
import functools
import random
import re

INSTRUCTIONS = r"""Implement classify_ignore(ignore_lines, entries), a root .gitignore classifier. Return exactly a dictionary mapping EVERY entry's path to a boolean: true means ignored. Each entry has path (canonical relative path, no dot/dotdot, no leading/trailing slash) and is_dir:boolean. Entries form a consistent tree; implicit parents are directories. Paths are case-sensitive ASCII, depth at most3 and length at most40. There are four entries and at most four rules. Do not mutate inputs.
Rules follow this precise Gitignore subset. Empty lines have no effect. A # in the FIRST position starts a comment, unless escaped as \#. An unescaped ! in the first position negates a pattern (re-includes matches). \! instead matches a literal leading !. Leading spaces are literal. Trailing unescaped spaces are removed; a backslash-escaped trailing space is literal. Backslashes in these inputs escape leading !/# or a trailing space; there are no character classes, tabs, inline newlines, adjacent slashes or adjacent ** components.
A leading / anchors at the root. A pattern with a / in its body is ALSO root-relative. Otherwise the pattern matches a basename at ANY depth. A trailing / matches directories only, including implicit parents. Other patterns match both files and directories. Within a component, * matches zero or more characters and ? one character, never /. A complete ** component matches zero or more path components when followed by another component. A trailing /** matches everything INSIDE the preceding directory, at any depth, but does NOT match that directory itself. A standalone ** matches everything.
For an entry or directory, the LAST applicable rule wins; default is included. Crucially, an ignored parent directory blocks all descendants: a later !dir/file cannot re-include the file unless the parent itself has been re-included. Evaluate implicit parents as directories too. The six examples illustrate the contract; hidden examples are independently instantiated.
match_segment(pattern, word) and match_parts(pattern_parts, path_parts) are complete reusable glob helpers in the supplied module. Implement rule_mode(line,path,is_dir), returning -1 for no applicable match, 0 for a negated match and 1 for an ignoring match, and classify_ignore. You may change the module, but keep the public entrypoint. Helpers must be top-level; no lambdas, keyword arguments or imports. Bounded pure string methods are available. Four root result fields correspond to four meaningful path decisions; only improvement over the supplied code earns partial reward. Unchanged/cosmetic/non-improving code earns0; full reward requires every hidden case correct."""

HELPERS = r'''def match_segment(pattern, word):
    tokens = []
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if char == "\\" and i+1 < len(pattern):
            tokens.append(["literal", pattern[i+1]])
            i += 2
        else:
            tokens.append(["star" if char == "*" else "any" if char == "?" else "literal", char])
            i += 1
    table = [[False]*(len(word)+1) for unused in range(len(tokens)+1)]
    table[0][0] = True
    for i in range(len(tokens)):
        for j in range(len(word)+1):
            if tokens[i][0] == "star":
                table[i+1][j] = table[i][j] or (j > 0 and table[i+1][j-1])
            elif j < len(word) and table[i][j] and (tokens[i][0] == "any" or tokens[i][1] == word[j]):
                table[i+1][j+1] = True
    return table[len(tokens)][len(word)]

def match_parts(pattern, words):
    table = [[False]*(len(words)+1) for unused in range(len(pattern)+1)]
    table[0][0] = True
    for i in range(len(pattern)):
        for j in range(len(words)+1):
            if not table[i][j]:
                continue
            if pattern[i] == "**":
                if i != len(pattern)-1 or len(pattern) == 1:
                    table[i+1][j] = True
                if j < len(words):
                    table[i][j+1] = True
                    table[i+1][j+1] = True
            elif j < len(words) and match_segment(pattern[i], words[j]):
                table[i+1][j+1] = True
    return table[len(pattern)][len(words)]
'''

RULE = r'''
def rule_mode(line, path, is_dir):
    while line.endswith(" "):
        pos = len(line)-2
        slashes = 0
        while pos >= 0 and line[pos] == "\\":
            slashes += 1
            pos -= 1
        if slashes % 2 == 1:
            break
        line = line[:-1]
    if not line or line[0] == "#":
        return -1
    negative = line[0] == "!"
    if negative:
        line = line[1:]
    if not line:
        return -1
    directory = line.endswith("/")
    if directory:
        line = line[:-1]
    anchored = line.startswith("/")
    if anchored:
        line = line[1:]
    if not line or directory and not is_dir:
        return -1
    anchored = anchored or "/" in line
    words = path.split("/")
    matches = match_parts(line.split("/"), words) if anchored else match_segment(line, words[-1])
    return (0 if negative else 1) if matches else -1
'''

CLASSIFIER = r'''
def classify_ignore(ignore_lines, entries):
    result = {}
    for entry in entries:
        path = entry["path"]
        prefixes = [path[:i] for i in range(len(path)) if path[i] == "/"] + [path]
        ignored = False
        for prefix in prefixes:
            is_dir = prefix != path or entry["is_dir"]
            ignored = False
            for line in ignore_lines:
                mode = rule_mode(line, prefix, is_dir)
                if mode != -1:
                    ignored = mode == 1
            if ignored:
                break
        result[path] = ignored
    return result
'''
REFERENCE = HELPERS + RULE + CLASSIFIER
SCAFFOLD = HELPERS + '''
def rule_mode(line, path, is_dir):
    return -1

def classify_ignore(ignore_lines, entries):
    return {entry["path"]: False for entry in entries}
'''


def initial(seed, difficulty):
    if difficulty == 2:
        return SCAFFOLD
    # An executable parent-pruning defect, exercised by every witness suite.
    return REFERENCE.replace('            if ignored:\n                break',
                             '            if False:\n                break')


def compile_rule(line):
    """Independent tokenization and host regex rather than bounded DP."""
    tokens = re.findall(r"\\.|[^\\]", line)
    while tokens and tokens[-1] == ' ':
        tokens.pop()
    if not tokens or tokens[0] == '#':
        return None
    negate = tokens[0] == '!'
    if negate:
        tokens.pop(0)
    directory = bool(tokens and tokens[-1] == '/')
    if directory:
        tokens.pop()
    anchored = bool(tokens and tokens[0] == '/')
    if anchored:
        tokens.pop(0)
    if not tokens:
        return None
    anchored = anchored or '/' in tokens
    parts = [[]]
    for token in tokens:
        if token == '/':
            parts.append([])
        else:
            parts[-1].append(token)
    starstar = lambda p: p == ['*','*']
    def segment(p):
        return ''.join('[^/]*' if t == '*' else '[^/]' if t == '?' else re.escape(t[1:] if t.startswith('\\') else t) for t in p)
    if not anchored:
        expression = segment(parts[0])
    else:
        pieces = []
        for index,part in enumerate(parts):
            if index and not starstar(parts[index-1]):
                pieces.append('/')
            if starstar(part):
                pieces.append('(?:[^/]+(?:/[^/]+)*)' if index == len(parts)-1 else '(?:[^/]+/)*')
            else:
                pieces.append(segment(part))
        expression = ''.join(pieces)
    return re.compile(expression), anchored, directory, not negate


def reference(args):
    lines,entries = args
    rules = [x for x in map(compile_rule,lines) if x is not None]
    @functools.lru_cache(maxsize=64)
    def status(path, directory):
        parent,_,basename = path.rpartition('/')
        if parent and status(parent,True):
            return True
        decision = False
        for regex,anchored,only_dirs,ignored in rules:
            if only_dirs and not directory:
                continue
            if regex.fullmatch(path if anchored else basename):
                decision = ignored
        return decision
    return {entry['path']:status(entry['path'],entry['is_dir']) for entry in entries}


def entry(path, directory=False):
    return {'path':path,'is_dir':directory}


def witnesses(rng):
    d,other,a,b = rng.sample(['a','b','c','d','x','y','log','tmp'],4)
    suffix=str(rng.randrange(10000))
    d+=suffix; other+=suffix; a+=suffix; b+=suffix
    return [
        [[d+'/', '!'+d+'/'+a],[entry(d+'/'+a),entry(d+'/'+b),entry(other+'/'+a),entry(b)]],
        [[d+'/', '!'+d+'/', d+'/'+b, '*.tmp'],[entry(d+'/'+b),entry(d+'/'+a),entry(other+'/'+b),entry(a+'.tmp')]],
        [[d+'/**/'+a, '/'+b],[entry(d+'/'+a),entry(b),entry(other+'/'+d+'/'+a),entry(other+'/'+b)]],
        [['*.tmp'],[entry(a+'.tmp'),entry(d+'/'+a+'.tmp'),entry(a+'.txt'),entry(d+'/'+a+'.txt')]],
        [[d+'/**','!'+d+'/'+a],[entry(d,True),entry(d+'/'+a),entry(d+'/'+b),entry(d+'/'+other+'/'+b)]],
        [['#comment','\\#'+a,a+'\\ ','\\!'+a],[entry('#'+a),entry(a+' '),entry(a),entry('!'+b)]],
    ]


def inputs(rng,count):
    for args in witnesses(rng)[:count]:
        assert sum(reference(args).values()) == 2
        yield args
    emitted=min(count,6)
    attempts=0
    while emitted<count:
        attempts+=1
        if attempts>count*1000:
            raise ValueError('insufficient balanced ignore cases')
        d,other,a,b=rng.sample(['a','b','c','d','x','y','log','tmp'],4)
        pool=[entry(a),entry(b),entry(a+'.tmp'),entry(a+'.txt'),entry(a+' '),entry('#'+a),entry('!'+a),entry(' '+a),
              entry(d,True),entry(other,True),entry(d+'/'+other,True),entry(d+'/'+a),entry(d+'/'+a+'.tmp'),
              entry(d+'/'+other+'/'+a),entry(other+'/'+b)]
        patterns=['*','**','*.tmp',a,'/'+a,'#comment','\\#'+a,'\\!'+a,a+'\\ ',' '+a,d+'/',d+'/**',
                  d+'/*',d+'/?','**/'+a,d+'/**/'+a,d+'/'+a,'/'+d+'/'+a,'!'+d+'/','!'+d+'/'+a,'!*.tmp','']
        args=[rng.sample(patterns,rng.randrange(1,5)),rng.sample(pool,4)]
        if sum(reference(args).values())!=2:
            continue
        yield args
        emitted+=1
