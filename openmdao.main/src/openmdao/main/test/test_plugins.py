import cStringIO
import logging
import nose
import os.path
import shutil
import sys
import tempfile
import unittest
from subprocess import check_call, STDOUT

from openmdao.main.plugin import _get_plugin_parser, plugin_quickstart, \
                                 plugin_build_docs, plugin_makedist, \
                                 plugin_list, _plugin_docs, plugin_install
from openmdao.util.fileutil import find_files
from openmdao.util.testutil import assert_raises


class PluginsTestCase(unittest.TestCase):

    def setUp(self):
        self.tdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tdir)

    def test_basic(self):
        logging.debug('')
        logging.debug('test_basic')

        # Just run through a complete cycle.
        orig_dir = os.getcwd()
        orig_stdout = sys.stdout
        orig_stderr = sys.stderr

        # Quickstart.
        logging.debug('')
        logging.debug('quickstart')
        os.chdir(self.tdir)
        try:
            argv = ['quickstart', 'foobar']
            parser = _get_plugin_parser()
            options, args = parser.parse_known_args(argv)
            retval = plugin_quickstart(parser, options, args)
            self.assertEqual(retval, 0)
            fandd = find_files(self.tdir, nodirs=False)
            self.assertEqual(set([os.path.basename(f) for f in fandd]), 
                             set(['foobar', 'src', 'docs', 'setup.cfg', 'setup.py',
                                  'MANIFEST.in', '__init__.py', 'conf.py',
                                  'usage.rst', 'index.rst',
                                  'srcdocs.rst', 'pkgdocs.rst', 'foobar.py', 
                                  'README.txt',
                                  'test','test_foobar.py']))
        finally:
            os.chdir(orig_dir)

        # Makedist.
        logging.debug('')
        logging.debug('makedist')
        sys.stdout = cStringIO.StringIO()
        sys.stderr = cStringIO.StringIO()
        logdata = ''
        os.chdir(os.path.join(self.tdir, 'foobar'))
        try:
            argv = ['makedist', 'foobar']
            parser = _get_plugin_parser()
            options, args = parser.parse_known_args(argv)
            retval = plugin_makedist(parser, options, args, capture='makedist.out')
            with open('makedist.out', 'r') as inp:
                logdata = inp.read()
            self.assertEqual(retval, 0)
            if sys.platform == 'win32':
                self.assertTrue(os.path.exists('foobar-0.1.zip'))
            else:
                self.assertTrue(os.path.exists('foobar-0.1.tar.gz'))
        finally:
            captured_stdout = sys.stdout.getvalue()
            captured_stderr = sys.stderr.getvalue()
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr
            os.chdir(orig_dir)
            logging.debug('captured stdout:')
            logging.debug(captured_stdout)
            logging.debug('captured stderr:')
            logging.debug(captured_stderr)
            logging.debug('captured subprocess output:')
            logging.debug(logdata)

        # Existing distribution error.
        logging.debug('')
        logging.debug('makedist error')
        sys.stdout = cStringIO.StringIO()
        sys.stderr = cStringIO.StringIO()
        os.chdir(os.path.join(self.tdir, 'foobar'))
        try:
            argv = ['makedist', 'foobar']
            parser = _get_plugin_parser()
            options, args = parser.parse_known_args(argv)
            retval = plugin_makedist(parser, options, args, capture='makedist.out')
            with open('makedist.out', 'r') as inp:
                logdata = inp.read()
            self.assertEqual(retval, -1)
        finally:
            captured_stdout = sys.stdout.getvalue()
            captured_stderr = sys.stderr.getvalue()
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr
            os.chdir(orig_dir)
            logging.debug('captured stdout:')
            logging.debug(captured_stdout)
            logging.debug('captured stderr:')
            logging.debug(captured_stderr)
            logging.debug('captured subprocess output:')
            logging.debug(logdata)

        # Install
        logging.debug('')
        logging.debug('install')
        sys.stdout = cStringIO.StringIO()
        sys.stderr = cStringIO.StringIO()
        logdata = ''
        os.chdir(self.tdir)
        try:
            argv = ['install', 'foobar']
            parser = _get_plugin_parser()
            options, args = parser.parse_known_args(argv)
            retval = plugin_install(parser, options, args, capture='install.out')
            with open('install.out', 'r') as inp:
                logdata = inp.read()
            self.assertEqual(retval, 0)
        finally:
            captured_stdout = sys.stdout.getvalue()
            captured_stderr = sys.stderr.getvalue()
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr
            os.chdir(orig_dir)
            logging.debug('captured stdout:')
            logging.debug(captured_stdout)
            logging.debug('captured stderr:')
            logging.debug(captured_stderr)
            logging.debug('captured subprocess output:')
            logging.debug(logdata)

        try:
            # List in subprocess to grab updated package environment.
            logging.debug('')
            logging.debug('list')
            os.chdir(self.tdir)
            stdout = open('list.out', 'w')
            try:
                check_call(('plugin', 'list', '-g', 'driver', '-g', 'component',
                            '--external'), stdout=stdout, stderr=STDOUT)
            finally:
                stdout.close()
                with open('list.out', 'r') as inp:
                    captured_stdout = inp.read()
                os.remove('list.out')
                os.chdir(orig_dir)
                logging.debug('captured subprocess output:')
                logging.debug(captured_stdout)
            self.assertTrue('foobar.foobar.Foobar' in captured_stdout)

            # Docs.
            logging.debug('')
            logging.debug('docs')
            argv = ['docs', 'foobar']
            parser = _get_plugin_parser()
            options, args = parser.parse_known_args(argv)
            url = _plugin_docs(options.plugin_dist_name)
            expected = os.path.join(self.tdir, 'foobar', 'src', 'foobar',
                                    'sphinx_build', 'html', 'index.html')
            self.assertEqual(url, expected)
        finally:
            # Uninstall
            logging.debug('')
            logging.debug('uninstall')
            with open('pip.in', 'w') as out:
                out.write('y\n')
            stdin = open('pip.in', 'r')
            stdout = open('pip.out', 'w')
            # On EC2 Windows, 'pip' genreates an absurdly long temp directory
            # name, apparently to allow backing-out of the uninstall.
            # The name is so long Windows can't handle it. So we try to
            # avoid that by indirectly influencing mkdtemp().
            env = os.environ.copy()
            env['TMP'] = os.path.expanduser('~')
            try:
                check_call(('pip', 'uninstall', 'foobar'), env=env,
                           stdin=stdin, stdout=stdout, stderr=STDOUT)
            finally:
                stdin.close()
                stdout.close()
                with open('pip.out', 'r') as inp:
                    captured_stdout = inp.read()
                os.remove('pip.in')
                os.remove('pip.out')
                logging.debug('captured stdout:')
                logging.debug(captured_stdout)

        # Show removed.
        logging.debug('')
        logging.debug('list removed')
        os.chdir(self.tdir)
        stdout = open('list.out', 'w')
        try:
            check_call(('plugin', 'list', '--external'),
                       stdout=stdout, stderr=STDOUT)
        finally:
            stdout.close()
            with open('list.out', 'r') as inp:
                captured_stdout = inp.read()
            os.remove('list.out')
            os.chdir(orig_dir)
            logging.debug('captured subprocess output:')
            logging.debug(captured_stdout)
        self.assertFalse('foobar.foobar.Foobar' in captured_stdout)

    def test_quickstart(self):
        # All options.
        argv = ['quickstart', 'foobar', '-c', 'FooBar', '-g', 'component',
                '-v', '1.1', '-d', self.tdir]
        parser = _get_plugin_parser()
        options, args = parser.parse_known_args(argv)
        retval = plugin_quickstart(parser, options, args)
        self.assertEqual(retval, 0)
        fandd = find_files(self.tdir, nodirs=False)
        self.assertEqual(set([os.path.basename(f) for f in fandd]), 
                         set(['foobar', 'src', 'docs', 'setup.cfg', 'setup.py',
                              'MANIFEST.in', '__init__.py', 'conf.py',
                              'usage.rst', 'index.rst',
                              'srcdocs.rst', 'pkgdocs.rst', 'foobar.py', 
                              'README.txt',
                              'test','test_foobar.py']))

        # Errors.
        code = 'plugin_quickstart(parser, options, args)'
        assert_raises(self, code, globals(), locals(), OSError,
                      "Can't create directory '%s' because it already exists."
                      % os.path.join(self.tdir, 'foobar'))

        argv = ['quickstart', 'foobar', 'stuff']
        parser = _get_plugin_parser()
        options, args = parser.parse_known_args(argv)
        retval = plugin_quickstart(parser, options, args)
        self.assertEqual(retval, -1)

    def test_makedist(self):
        # Errors.
        argv = ['makedist', 'foobar', 'distdir', 'stuff']
        parser = _get_plugin_parser()
        options, args = parser.parse_known_args(argv)
        retval = plugin_makedist(parser, options, args)
        self.assertEqual(retval, -1)

        argv = ['makedist', 'foobar', 'no-such-directory']
        parser = _get_plugin_parser()
        options, args = parser.parse_known_args(argv)
        code = 'plugin_makedist(parser, options, args)'
        distdir = os.path.join(os.getcwd(), 'no-such-directory')
        assert_raises(self, code, globals(), locals(), IOError,
                      "directory '%s' does not exist" % distdir)

    def test_list(self):
        logging.debug('')
        logging.debug('test_list')

        orig_stdout = sys.stdout
        orig_stderr = sys.stderr
        sys.stdout = cStringIO.StringIO()
        sys.stderr = cStringIO.StringIO()
        try:
            argv = ['list']
            parser = _get_plugin_parser()
            options, args = parser.parse_known_args(argv)
            retval = plugin_list(parser, options, args)
            self.assertEqual(retval, 0)
        finally:
            captured_stdout = sys.stdout.getvalue()
            captured_stderr = sys.stderr.getvalue()
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr
            logging.debug('captured stdout:')
            logging.debug(captured_stdout)
            logging.debug('captured stderr:')
            logging.debug(captured_stderr)
        # Just a selection from each category.
        expected = ['openmdao.lib.architectures.bliss.BLISS',
                    'openmdao.lib.casehandlers.caseset.CaseArray',
                    'openmdao.lib.components.broadcaster.Broadcaster',
                    'openmdao.lib.datatypes.array.Array',
                    'openmdao.lib.differentiators.finite_difference.FiniteDifference',
                    'openmdao.lib.doegenerators.central_composite.CentralComposite',
                    'openmdao.lib.drivers.broydensolver.BroydenSolver',
                    'openmdao.lib.surrogatemodels.kriging_surrogate.KrigingSurrogate',
                    'openmdao.main.assembly.Assembly']
        for plugin in expected:
            self.assertTrue(plugin in captured_stdout)

        sys.stdout = cStringIO.StringIO()
        sys.stderr = cStringIO.StringIO()
        try:
            argv = ['list', '-g', 'driver', '--builtin']
            parser = _get_plugin_parser()
            options, args = parser.parse_known_args(argv)
            retval = plugin_list(parser, options, args)
            self.assertEqual(retval, 0)
        finally:
            captured_stdout = sys.stdout.getvalue()
            captured_stderr = sys.stderr.getvalue()
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr
            logging.debug('captured stdout:')
            logging.debug(captured_stdout)
            logging.debug('captured stderr:')
            logging.debug(captured_stderr)
        if 'openmdao.lib.drivers.doedriver.DOEdriver' not in captured_stdout:
            self.fail('-g driver filter failed to include')
        if 'openmdao.main.assembly.Assembly' in captured_stdout:
            self.fail('-g driver filter failed to exclude')

        # Errors.
        argv = ['list', 'stuff']
        parser = _get_plugin_parser()
        options, args = parser.parse_known_args(argv)
        retval = plugin_list(parser, options, args)
        self.assertEqual(retval, -1)

    def test_build_docs(self):
        logging.debug('')
        logging.debug('test_build_docs')

        argv = ['quickstart', 'foobar', '-v', '1.1', '-d', self.tdir]
        parser = _get_plugin_parser()
        options, args = parser.parse_known_args(argv)
        plugin_quickstart(parser, options, args)

        orig_dir = os.getcwd()
        os.chdir(os.path.join(self.tdir, 'foobar'))
        orig_stdout = sys.stdout
        orig_stderr = sys.stderr
        sys.stdout = cStringIO.StringIO()
        sys.stderr = cStringIO.StringIO()
        try:
            argv = ['build_docs', 'foobar']
            parser = _get_plugin_parser()
            options, args = parser.parse_known_args(argv)
            retval = plugin_build_docs(parser, options, args)
            self.assertEqual(retval, 0)
        finally:
            captured_stdout = sys.stdout.getvalue()
            captured_stderr = sys.stderr.getvalue()
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr
            os.chdir(orig_dir)
            logging.debug('captured stdout:')
            logging.debug(captured_stdout)
            logging.debug('captured stderr:')
            logging.debug(captured_stderr)

        # Errors.
        argv = ['build_docs', 'foobar', 'no-such-directory', 'stuff']
        parser = _get_plugin_parser()
        options, args = parser.parse_known_args(argv)
        retval = plugin_build_docs(parser, options, args)
        self.assertEqual(retval, -1)

        argv = ['build_docs', 'foobar', 'no-such-directory']
        parser = _get_plugin_parser()
        options, args = parser.parse_known_args(argv)
        code = 'plugin_build_docs(parser, options, args)'
        distdir = os.path.join(os.getcwd(), 'no-such-directory')
        assert_raises(self, code, globals(), locals(), IOError,
                      "directory '%s' does not exist" % distdir)

        distdir = os.path.join(self.tdir, 'foobar')
        os.remove(os.path.join(distdir, 'setup.py'))
        argv = ['build_docs', 'foobar', distdir]
        parser = _get_plugin_parser()
        options, args = parser.parse_known_args(argv)
        code = 'plugin_build_docs(parser, options, args)'
        assert_raises(self, code, globals(), locals(), IOError,
                      "directory '%s' does not contain 'setup.py'" % distdir)

    def test_docs(self):
        argv = ['docs', 'no-such-plugin']
        parser = _get_plugin_parser()
        options, args = parser.parse_known_args(argv)
        code = '_plugin_docs(options.plugin_dist_name)'
        assert_raises(self, code, globals(), locals(), RuntimeError,
                      "Can't locate package/module 'no-such-plugin'")

        argv = ['docs', 'subprocess']
        parser = _get_plugin_parser()
        options, args = parser.parse_known_args(argv)
        url = _plugin_docs(options.plugin_dist_name)
        expected = os.path.join(os.path.dirname(sys.modules['subprocess'].__file__),
                                'sphinx_build', 'html', 'index.html')
        self.assertEqual(url, expected)

    def test_install(self):
        # Errors.
        argv = ['install', 'no-such-plugin', 'stuff']
        parser = _get_plugin_parser()
        options, args = parser.parse_known_args(argv)
        retval = plugin_install(parser, options, args)
        self.assertEqual(retval, -1)


if __name__ == '__main__':
    sys.argv.append('--cover-package=openmdao.main')
    sys.argv.append('--cover-erase')
    nose.runmodule()

