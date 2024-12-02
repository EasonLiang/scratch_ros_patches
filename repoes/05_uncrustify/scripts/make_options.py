#!/usr/bin/env python

import argparse
import io
import os
import re

max_name_len = 60

re_name = re.compile(r'^[a-z][a-z0-9_]*$')
re_group = re.compile(r'//BEGIN')
re_option = re.compile(r'extern (Bounded)?Option<[^>]+>')
re_default = re.compile(r' *// *= *(.*)')
groups = []

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
script = os.path.relpath(__file__, root)


# =============================================================================
class Group(object):
    # -------------------------------------------------------------------------
    def __init__(self, desc):
        self.desc = desc
        self.options = []

    # -------------------------------------------------------------------------
    def append(self, option):
        self.options.append(option)


# =============================================================================
class Option(object):
    # -------------------------------------------------------------------------
    def __init__(self, name, dval, decl, desc):
        if re_name.match(name) is None:
            raise ValueError('{!r} is not a valid option name'.format(name))
        if len(name) > max_name_len:
            raise ValueError(
                '{!r} (length={:d}) exceeds the maximum length {:d}'.format(
                    name, len(name), max_name_len))

        self.desc = u'\n'.join(desc)
        self.decl = decl[7:]
        self.name = name
        self.dval = dval

    # -------------------------------------------------------------------------
    def write_declaration(self, out):
        out.write(u'{} {} = {{\n'.format(self.decl, self.name))
        out.write(u'  "{}",\n'.format(self.name))
        out.write(u'  R"__(\n{}\n)__"'.format(self.desc))
        if self.dval is not None:
            out.write(u',\n  {}'.format(self.dval))
        out.write(u'\n};\n\n')

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


# -----------------------------------------------------------------------------
def extract_default(decl):
    m = re_default.match(decl)
    if m:
        return m.group(1)
    return None


# -----------------------------------------------------------------------------
def write_banner(out, args):
    out.write(
        u'/**\n'
        u' * @file {out_name}\n'
        u' * Declaration and initializers for all options.\n'
        u' * Automatically generated by <code>{script}</code>\n'
        u' * from {in_name}.\n'
        u' */\n'
        u'\n'.format(
            in_name=os.path.basename(args.header),
            out_name=os.path.basename(args.output),
            script=script))


# -----------------------------------------------------------------------------
def write_declarations(out, args):
    for group in groups:
        for option in group.options:
            option.write_declaration(out)


# -----------------------------------------------------------------------------
def write_registrations(out, args):
    for group in groups:
        out.write(u'\n  begin_option_group(R"__(\n{}\n)__");\n\n'.format(
            group.desc))

        for option in group.options:
            out.write(u'  register_option(&options::{});\n'.format(
                option.name))


# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='Generate options.cpp')
    parser.add_argument('output', type=str,
                        help='location of options.cpp to write')
    parser.add_argument('header', type=str,
                        help='location of options.h to read')
    parser.add_argument('template', type=str,
                        help='location of options.cpp.in to use as template')
    args = parser.parse_args()

    with io.open(args.header, 'rt', encoding='utf-8') as f:
        desc = []
        for line in iter(f.readline, ''):
            line = line.strip()

            if re_group.match(line):
                groups.append(Group(line[8:]))

            elif not len(line):
                desc = []

            elif line == '//':
                desc.append('')

            elif line.startswith('// '):
                desc.append(line[3:])

            elif re_option.match(line):
                n, d = f.readline().split(';')
                o = Option(n, extract_default(d.strip()), line, desc)
                groups[-1].append(o)

    replacements = {
        u'##BANNER##': write_banner,
        u'##DECLARATIONS##': write_declarations,
        u'##REGISTRATIONS##': write_registrations,
    }

    with io.open(args.output, 'wt', encoding='utf-8') as out:
        with io.open(args.template, 'rt', encoding='utf-8') as t:
            for line in t:
                directive = line.strip()
                if directive in replacements:
                    replacements[directive](out, args)
                else:
                    out.write(line)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


if __name__ == '__main__':
    main()
