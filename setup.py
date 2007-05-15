#!/usr/bin/python

import os
import sys
from distutils import log
from distutils.command.build import build as _build
from distutils.command.sdist import sdist
from distutils.command.build_py import build_py
from distutils.core import setup
from distutils.dep_util import newer_group
from distutils import dir_util
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

def ls_spec_basenames():
    names = os.listdir(os.path.join(os.curdir, 'spec'))
    for name in names:
        assert name.endswith('.xml')
    # we only want the interfaces, which start with a capital letter
    return [name[:-4] for name in names if name[0].upper() == name[0]]


XSLTPROC = ['xsltproc', '--nonet', '--novalid', '--xinclude']
ALL_SPEC_XML = ls_spec_xml()
SPEC_BASENAMES = ls_spec_basenames()

class build_empty_py(build_py):
    def finalize_options(self):
        build_py.finalize_options(self)
        self.packages = []
        self.py_modules = ['telepathy._generated']
        self.package_data = []
        self.data_files = []

    def find_modules(self):
        return [('telepathy._generated', '__init__', '')]

    def build_module(self, module, module_file, package):
        # "module_file" is actually the empty string
        package = package.split('.')
        outfile = self.get_module_outfile(self.build_lib, package, module)
        dir = os.path.dirname(outfile)
        log.info('Generating empty %s' % outfile)
        self.mkpath(dir)
        if not self.dry_run:
            f = file(outfile, 'w')
            f.write('# Placeholder for package')
            f.close()

class build_gen_py_ifaces(build_py):
    def finalize_options(self):
        build_py.finalize_options(self)
        self.packages = []
        self.py_modules = ['telepathy._generated.%s' % name
                           for name in SPEC_BASENAMES]
        self.package_data = []
        self.data_files = []
        self.stylesheet = os.path.join(os.curdir, 'tools',
                                       'spec-to-python.xsl')

    def find_modules(self):
        return [('telepathy._generated', name,
                 os.path.join(os.curdir, 'spec', '%s.xml' % name))
                for name in SPEC_BASENAMES]

    def build_module(self, module, module_file, package):
        # "module_file" is actually the XML
        package = package.split('.')
        outfile = self.get_module_outfile(self.build_lib, package, module)
        dir = os.path.dirname(outfile)
        self.mkpath(dir)
        return self.run_xsl(module_file, outfile)

    def run_xsl(self, xml, outfile):
        if newer_group([xml, self.stylesheet], outfile):
            command = XSLTPROC + ['-o', outfile,
                                  self.stylesheet,
                                  xml]
            log.info('Generating %s from %s using %s' % (outfile, xml,
                                                         self.stylesheet))
            spawn(command, dry_run=self.dry_run)


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
                    + [('build_gen_py', (lambda self: True)),
                       ('build_gen_py_ifaces', (lambda self: True)),
                       ('build_empty_py', (lambda self: True))])

class distcheck(sdist):

    def run(self):
        sdist.run(self)

        if self.dry_run:
            return

        base_dir = self.distribution.get_fullname()
        distcheck_dir = os.path.join(self.dist_dir, 'distcheck')
        self.mkpath(distcheck_dir)
        self.mkpath(os.path.join(distcheck_dir, 'again'))

        cwd = os.getcwd()
        os.chdir(distcheck_dir)

        if os.path.isdir(base_dir):
            dir_util.remove_tree(base_dir)

        for archive in self.archive_files:
            if archive.endswith('.tar.gz'):
                cmd = ['tar', '-xzf',
                       os.path.join(os.pardir, os.pardir, archive), base_dir]
                spawn(cmd)
                break
        else:
            raise ValueError('No supported archives were created')

        # make sdist again, then make clean
        os.chdir(cwd)
        os.chdir(os.path.join(distcheck_dir, base_dir))
        cmd = [sys.executable, 'setup.py', 'sdist', '--formats', 'gztar']
        spawn(cmd)

        # make sure the two tarballs have the same contents
        os.chdir(cwd)
        os.chdir(os.path.join(distcheck_dir, 'again'))
        cmd = ['tar', '-xzf',
               os.path.join(os.pardir, base_dir, 'dist', base_dir + '.tar.gz'),
               base_dir]
        spawn(cmd)

        os.chdir(cwd)
        os.chdir(os.path.join(distcheck_dir, base_dir))
        dir_util.remove_tree('dist')
        os.remove('MANIFEST')

        os.chdir(cwd)
        cmd = ['diff', '-ru',
               os.path.join(distcheck_dir, base_dir),
               os.path.join(distcheck_dir, 'again', base_dir)]
        spawn(cmd)

        # make sure the whole spec was included
        from xml.dom.minidom import parse
        dom = parse(os.path.join(distcheck_dir, base_dir, 'spec', 'all.xml'))
        inclusions = dom.getElementsByTagName('xi:include')
        for inclusion in inclusions:
            filename = inclusion.getAttribute('href')
            if not os.path.isfile(os.path.join(distcheck_dir, base_dir, 'spec',
                                               filename)):
                if not inclusion.getElementsByTagName('xi:fallback'):
                    raise AssertionError('%s was not packaged' % filename)
        dom.unlink()


setup(
    cmdclass={'build': build,
              'build_gen_py': build_gen_py,
              'build_empty_py': build_empty_py,
              'distcheck': distcheck,
              'build_gen_py_ifaces': build_gen_py_ifaces},
    name='telepathy-python',
    version=__version__,
    packages=[
        'telepathy',
        'telepathy.client',
        'telepathy.server'
        ],
    )

