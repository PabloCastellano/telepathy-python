#!/usr/bin/python

import os
from distutils import log
from distutils.command.build import build as _build
from distutils.command.build_py import build_py
from distutils.core import setup
from distutils.dep_util import newer_group
from distutils.spawn import spawn

# can't import telepathy._version because that imports telepathy,
# which needs telepathy._generated, which we haven't yet built...
loc = {}
execfile(os.path.join(os.curdir, 'telepathy', '_version.py'),
         globals(), loc)
__version__ = loc['__version__']

def ls_spec_xml():
    names = os.listdir(os.path.join(os.curdir, 'spec'))
    return [os.path.join(os.curdir, 'spec', name) for name in names]


XSLTPROC = ['xsltproc', '--nonet', '--novalid', '--xinclude']
ALL_SPEC_XML = ls_spec_xml()

class build_gen_py(build_py):
    def finalize_options(self):
        build_py.finalize_options(self)
        self.packages = []
        self.py_modules = ['telepathy._generated.interfaces',
                           'telepathy._generated.errors',
                           'telepathy._generated.constants']
        self.package_data = []
        self.data_files = []

    def find_modules(self):
        return [('telepathy._generated', 'interfaces',
                 'tools/python-interfaces-generator.xsl'),
                ('telepathy._generated', 'constants',
                 'tools/python-constants-generator.xsl'),
                ('telepathy._generated', 'errors',
                 'tools/python-errors-generator.xsl')]

    def build_module(self, module, module_file, package):
        # "module_file" is actually the stylesheet
        package = package.split('.')
        outfile = self.get_module_outfile(self.build_lib, package, module)
        dir = os.path.dirname(outfile)
        self.mkpath(dir)
        return self.run_xsl(module_file, outfile)

    def run_xsl(self, stylesheet, outfile):
        if newer_group(ALL_SPEC_XML + [stylesheet], outfile):
            command = XSLTPROC + ['-o', outfile,
                                  stylesheet,
                                  os.path.join(os.curdir, 'spec', 'all.xml')]
            log.info('Generating %s using %s' % (outfile, stylesheet))
            spawn(command, dry_run=self.dry_run)


class build(_build):
    sub_commands = (_build.sub_commands
                    + [('build_gen_py', (lambda self: True))])

setup(
    cmdclass={'build': build, 'build_gen_py': build_gen_py},
    name='telepathy-python',
    version=__version__,
    packages=[
        'telepathy',
        'telepathy.client',
        'telepathy.server'
        ],
    )

