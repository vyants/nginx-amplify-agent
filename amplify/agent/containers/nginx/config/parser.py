# -*- coding: utf-8 -*-
import re
import glob
import os

from pyparsing import (
    Regex, Keyword, Literal, White, Word, alphanums, CharsNotIn, Forward, Group,
    Optional, OneOrMore, ZeroOrMore, pythonStyleComment, lineno, LineStart, LineEnd
)

from amplify.agent.context import context

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev", "Grant Hulegaard"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


tokens_cache = {}


IGNORED_DIRECTIVES = [
    'ssl_certificate',
    'ssl_certificate_key',
    'ssl_client_certificate',
    'ssl_password_file',
    'ssl_stapling_file',
    'ssl_trusted_certificate',
    'auth_basic_user_file',
    'secure_link_secret'
]


def set_line_number(string, location, tokens):
    if len(tokens) == 1:
        line_number = lineno(location, string)
        tokens_cache[tokens[0]] = line_number
        tokens.line_number = line_number
    else:
        for item in tokens:
            tokens.line_number = tokens_cache.get(item)


class NginxConfigParser(object):
    """
    Nginx config parser based on https://github.com/fatiherikli/nginxparser
    Parses single file into json structure
    """

    max_size = 10*1024*1024  # 10 mb

    # line starts/ends
    line_start = LineStart().suppress()
    line_end = LineEnd().suppress()

    # constants
    left_brace = Literal("{").suppress()
    left_parentheses = Literal("(").suppress()
    right_brace = Literal("}").suppress()
    right_parentheses = Literal(")").suppress()
    semicolon = Literal(";").suppress()
    space = White().suppress()
    singleQuote = Literal("'").suppress()
    doubleQuote = Literal('"').suppress()

    # keys
    if_key = Keyword("if").setParseAction(set_line_number)
    set_key = Keyword("set").setParseAction(set_line_number)
    rewrite_key = Keyword("rewrite").setParseAction(set_line_number)
    perl_set_key = Keyword("perl_set").setParseAction(set_line_number)
    log_format_key = Keyword("log_format").setParseAction(set_line_number)
    content_by_lua_key = Keyword("content_by_lua").setParseAction(set_line_number)
    rewrite_by_lua_key = Keyword("rewrite_by_lua").setParseAction(set_line_number)
    init_by_lua_key = Keyword("init_by_lua").setParseAction(set_line_number)
    lua_package_path_key = Keyword("lua_package_path").setParseAction(set_line_number)
    alias_key = Keyword("alias").setParseAction(set_line_number)
    return_key = Keyword("return").setParseAction(set_line_number)
    error_page_key = Keyword("error_page").setParseAction(set_line_number)
    map_key = Keyword("map").setParseAction(set_line_number)
    key = (~map_key & ~alias_key & ~perl_set_key & ~content_by_lua_key & ~if_key & ~set_key & ~rewrite_key) + \
        Word(alphanums + '$_:%?"~<>\/-+.,*()[]"' + "'").setParseAction(set_line_number)

    # values
    value = Regex(r'[^{};]*"[^\";]+"[^{};]*|[^{};]*\'[^\';]+\'|[^{};]+(?!${.+})').setParseAction(set_line_number)
    quotedValue = Regex(r'"[^;]+"|\'[^;]+\'').setParseAction(set_line_number)
    rewrite_value = CharsNotIn(";").setParseAction(set_line_number)
    any_value = CharsNotIn(";").setParseAction(set_line_number)
    map_value = Regex(r'\'[^\']*\'|"[^"*]*"|[^{};\s]+').setParseAction(set_line_number)
    if_value = Regex(r'\(.*\)').setParseAction(set_line_number)
    language_include_value = CharsNotIn("'").setParseAction(set_line_number)
    strict_value = CharsNotIn("{};").setParseAction(set_line_number)

    # modifier for location uri [ = | ~ | ~* | ^~ ]
    modifier = Literal("=") | Literal("~*") | Literal("~") | Literal("^~")

    # rules
    assignment = (
        key + Optional(space) + Optional(value) +
        Optional(space) + Optional(value) + Optional(space) + semicolon

    ).setParseAction(set_line_number)

    set = (
        set_key + Optional(space) + any_value + Optional(space) + semicolon
    ).setParseAction(set_line_number)

    rewrite = (
        rewrite_key + Optional(space) + rewrite_value + Optional(space) + semicolon
    ).setParseAction(set_line_number)

    perl_set = (
        perl_set_key + Optional(space) + key + Optional(space) +
        singleQuote + language_include_value + singleQuote + Optional(space) + semicolon
    ).setParseAction(set_line_number)

    lua_content = (
        (lua_package_path_key | init_by_lua_key | rewrite_by_lua_key | content_by_lua_key) + Optional(space) +
        singleQuote + language_include_value + singleQuote + Optional(space) + semicolon
    ).setParseAction(set_line_number)

    alias = (
        alias_key + space + any_value + Optional(space) + semicolon
    ).setParseAction(set_line_number)

    return_ = (
        (return_key | error_page_key) + space + value + Optional(space) + Optional(any_value) + Optional(space) + semicolon
    ).setParseAction(set_line_number)

    log_format = (
        log_format_key + Optional(space) + strict_value + Optional(space) + any_value + Optional(space) + semicolon
    ).setParseAction(set_line_number)

    # script

    map_block = Forward()
    map_block << Group(
        Group(
            map_key + space + map_value + space + map_value + Optional(space)
        ).setParseAction(set_line_number) +
        left_brace +
        Group(
            ZeroOrMore(
                Group(map_value + Optional(space) + Optional(map_value) + Optional(space) + semicolon)
            ).setParseAction(set_line_number)
        ) +
        right_brace
    )

    block = Forward()
    block << Group(
        (
            Group(
                key + Optional(space + modifier) + Optional(space) +
                Optional(value) + Optional(space) +
                Optional(value) + Optional(space)
            ) |
            Group(if_key + space + if_value + Optional(space))
        ).setParseAction(set_line_number) +
        left_brace +
        Group(
            ZeroOrMore(
                 Group(log_format) | Group(lua_content) | Group(perl_set) |
                 Group(set) | Group(rewrite) | Group(alias) | Group(return_) |
                 Group(assignment) |
                 map_block | block
            ).setParseAction(set_line_number)
        ).setParseAction(set_line_number) +
        right_brace
    )

    script = OneOrMore(
        Group(log_format) | Group(perl_set) | Group(lua_content) | Group(alias) | Group(return_) |
        Group(assignment) | Group(set) | Group(rewrite) |
        map_block | block
    ).ignore(pythonStyleComment)


    INCLUDE_RE = re.compile(r'.*include\s+(?P<include_file>.*);')

    def __init__(self, filename='/etc/nginx/nginx.conf'):
        global tokens_cache
        tokens_cache = {}

        self.filename = filename
        self.files = {}  # to prevent cycle files and line indexing
        self.broken_files = set()  # to prevent reloading broken files
        self.index = []  # stores index for all sections (points to file number and line number)
        self.folder = '/'.join(self.filename.split('/')[:-1])  # stores path to folder with main config
        self.errors = []
        self.tree = {}

    def parse(self):
        self.tree = self.__logic_parse(self.__pyparse(self.filename))

    def collect_all_files(self):
        """
        Tries to collect all included files and to return them as dict with mtimes and sizes
        :return: {} of files
        """
        all_files = {}

        def lightweight_include_search(include_files):
            for filename in include_files:
                if filename in all_files:
                    continue

                # set mtime
                all_files[filename] = int(os.path.getmtime(filename))

                try:
                    for line in open(filename):
                        if 'include' in line:
                            gre = self.INCLUDE_RE.match(line)
                            if gre:
                                new_includes = self.find_includes(gre.group('include_file'))
                                lightweight_include_search(new_includes)
                except Exception, e:
                    exception_name = e.__class__.__name__
                    message = 'failed to load %s due to: %s' % (filename, exception_name)
                    context.log.debug(message, exc_info=True)

        lightweight_include_search(self.find_includes(self.filename))
        return all_files

    def find_includes(self, path):
        """
        Takes include path and returns all included files
        :param path: str path
        :return: [] of str filenames
        """

        # resolve local paths
        path = path.replace('"', '')
        if not path.startswith('/'):
            path = '%s/%s' % (self.folder, path)

        # load all files
        filenames = []
        if '*' in path:
            for filename in glob.glob(path):
                filenames.append(filename)
        else:
            filenames.append(path)

        return filenames

    def __pyparse(self, path):
        """
        Loads and parses all files

        :param path: file path (can contain *)
        """
        result = {}
        for filename in self.find_includes(path):
            if filename in self.broken_files:
                continue
            elif filename not in self.files:
                file_index = len(self.files)
                self.files[filename] = {
                    'index': file_index,
                    'lines': 0,
                    'size': 0,
                    'mtime': 0
                }
            else:
                file_index = self.files[filename]['index']

            try:
                size = os.path.getsize(filename)
                mtime = int(os.path.getmtime(filename))

                self.files[filename]['size'] = size
                self.files[filename]['mtime'] = mtime

                if size > self.max_size:
                    self.errors.append('failed to load %s due to: too large %s bytes' % (filename, size))
                    continue
                source = open(filename).read()
                lines_count = source.count('\n')

                self.files[filename]['lines'] = lines_count
            except Exception, e:
                exception_name = e.__class__.__name__
                message = 'failed to load %s due to: %s' % (filename, exception_name)
                self.errors.append(message)
                self.broken_files.add(filename)
                del self.files[filename]
                context.log.error(message)
                context.log.debug('additional info:', exc_info=True)
                continue

            # check that file contains some information (not commented)
            all_lines_commented = True
            for line in source.split('\n'):
                line = line.replace(' ',  '')
                if line and not line.startswith('#'):
                    all_lines_commented = False
                    break

            if all_lines_commented:
                continue

            # replace \' with " because otherwise we cannot parse it
            slash_quote = '\\' + "'"
            source = source.replace(slash_quote, '"')

            try:
                parsed = self.script.parseString(source, parseAll=True)
            except Exception, e:
                exception_name = e.__class__.__name__
                message = 'failed to parse %s due to %s' % (filename, exception_name)
                self.errors.append(message)
                context.log.error(message)
                context.log.debug('additional info:', exc_info=True)
                continue

            result[file_index] = list(parsed)

        return result

    def __logic_parse(self, files, result=None):
        """
        Parses input files and updates result dict

        :param files: dict of files from pyparsing
        :return: dict of config tree
        """
        if result is None:
            result = {}

        for file_index, rows in files.iteritems():
            while len(rows):
                row = rows.pop(0)
                row_as_list = row.asList()
                
                if isinstance(row_as_list[0], list):
                    # this is a new key
                    key_bucket, value_bucket = row
                    key = key_bucket[0]

                    if len(key_bucket) == 1:
                        # simple key, with one param
                        subtree_indexed = self.__idx_save(
                            self.__logic_parse({file_index: row[1]}),
                            file_index, row.line_number
                        )
                        if key == 'server':
                            # work with servers
                            if key in result:
                                result[key].append(subtree_indexed)
                            else:
                                result[key] = [subtree_indexed]
                        else:
                            result[key] = subtree_indexed
                    else:
                        # compound key (for locations and upstreams for example)

                        # remove all redundant spaces
                        parts = filter(lambda x: x, ' '.join(key_bucket[1:]).split(' '))
                        sub_key = ' '.join(parts)

                        subtree_indexed = self.__idx_save(
                            self.__logic_parse({file_index: row[1]}),
                            file_index, row.line_number
                        )

                        if key in result:
                            result[key][sub_key] = subtree_indexed
                        else:
                            result[key] = {sub_key: subtree_indexed}
                else:
                    # can be just an assigment, without value
                    if len(row) >= 2:
                        key, value = row[0], ''.join(row[1:])
                    else:
                        key, value = row[0], ''

                    # transform multiline values to single one
                    if """\'""" in value or """\n""" in value:
                        value = re.sub(r"\'\s*\n\s*\'", '', value)
                        value = re.sub(r"\'", "'", value)

                    if key in IGNORED_DIRECTIVES:
                        continue  # Pass ignored directives.
                    elif key == 'log_format':
                        # work with log formats
                        gwe = re.match("([\w\d_-]+)\s+'(.+)'", value)
                        if gwe:
                            format_name, format_value = gwe.group(1), gwe.group(2)

                            indexed_value = self.__idx_save(format_value, file_index, row.line_number)
                            if key in result:
                                result[key][format_name] = indexed_value
                            else:
                                result[key] = {format_name: indexed_value}
                    elif key == 'include':
                        indexed_value = self.__idx_save(value, file_index, row.line_number)

                        if key in result:
                            result[key].append(indexed_value)
                        else:
                            result[key] = [indexed_value]

                        included_files = self.__pyparse(value)
                        self.__logic_parse(included_files, result=result)
                    elif key in ('access_log', 'error_log'):
                        # Handle access_log and error_log edge cases
                        if value == '' or '$' in value:
                            continue  # Skip log directives that are empty or use nginx variables.

                        # Otherwise handle normally (see ending else below).
                        indexed_value = self.__idx_save(value, file_index, row.line_number)
                        self.__simple_save(result, key, indexed_value)
                    else:
                        indexed_value = self.__idx_save(value, file_index, row.line_number)
                        self.__simple_save(result, key, indexed_value)

        return result

    def __idx_save(self, value, file_index, line):
        new_index = len(self.index)
        self.index.append((file_index, line))
        return value, new_index

    def __simple_save(self, result, key, indexed_value):
        """
        We ended up having duplicate code when adding key-value pairs to our parsing dictionary (
        when handling access_log and error_log directives).

        This prompted us to refactor this process out to a separate function.  Because dictionaries are passed by
        reference in Python, we can alter the value dictionary in this local __func__ scope and have it affect the dict
        in the parent (PYTHON MAGIC!?!?!?).

        :param result: dict Passed and altered by reference from the parent __func__ scope
        :param key:
        :param indexed_value:
        (No return since we are altering a pass-by-reference dict)
        """
        # simple key-value
        if key in result:
            stored_value = result[key]
            if isinstance(stored_value, list):
                result[key].append(indexed_value)
            else:
                result[key] = [stored_value, indexed_value]
        else:
            result[key] = indexed_value
    
    def simplify(self, tree=None):
        """
        returns tree without index references
        can be used for debug/pretty output

        :param tree: - dict of tree
        :return: dict of self.tree without index positions
        """
        result = {}

        if tree is None:
            tree = self.tree

        if isinstance(tree, dict):
            for key, value in tree.iteritems():
                if isinstance(value, dict):
                    result[key] = self.simplify(tree=value)
                elif isinstance(value, tuple):
                    subtree, reference = value
                    if isinstance(subtree, dict):
                        result[key] = self.simplify(tree=subtree)
                    elif isinstance(subtree, list):
                        result[key] = map(lambda x: self.simplify(tree=x), subtree)
                    else:
                        result[key] = subtree
                elif isinstance(value, list):
                    result[key] = map(lambda x: self.simplify(tree=x), value)
        elif isinstance(tree, tuple):
            subtree, reference = tree
            if isinstance(subtree, dict):
                return self.simplify(tree=subtree)
            elif isinstance(subtree, list):
                return map(lambda x: self.simplify(tree=x), subtree)
            else:
                return subtree
        elif isinstance(tree, list):
            return map(lambda x: self.simplify(tree=x), tree)

        return result

