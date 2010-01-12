"""
Test the ExternalCode component.
"""

import logging
import os
import pkg_resources
import shutil
import sys
import unittest

from openmdao.main.api import Assembly, FileMetadata, SimulationRoot, set_as_top
from openmdao.main.exceptions import RunInterrupted
from openmdao.lib.components.external_code import ExternalCode
from openmdao.main.eggchecker import check_save_load

# Capture original working directory so we can restore in tearDown().
ORIG_DIR = os.getcwd()
# Directory where we can find sleep.py.
DIRECTORY = pkg_resources.resource_filename('openmdao.lib.components', 'test')


class Unique(ExternalCode):
    """ Used to test `create_instance_dir` functionality. """

    def __init__(self):
        super(Unique, self).__init__(directory=DIRECTORY)
        self.create_instance_dir = True
        self.external_files = [
            FileMetadata(path='sleep.py', input=True, constant=True),
        ]
        self.command = 'python sleep.py 1'


class Model(Assembly):
    """ Run multiple `Unique` component instances. """

    def __init__(self):
        super(Model, self).__init__()
        self.add_container('a', Unique())
        self.add_container('b', Unique())


class TestCase(unittest.TestCase):
    """ Test the ExternalCode component. """

    def setUp(self):
        SimulationRoot.chroot(DIRECTORY)
        
    def tearDown(self):
        for directory in ('a', 'b'):
            if os.path.exists(directory):
                shutil.rmtree(directory)
        SimulationRoot.chroot(ORIG_DIR)
        
    def test_normal(self):
        logging.debug('')
        logging.debug('test_normal')

        # Normal run should have no issues.
        externp = set_as_top(ExternalCode())
        externp.timeout = 5
        externp.command = 'python sleep.py 1'
        externp.run()
        self.assertEqual(externp.return_code, 0)
        self.assertEqual(externp.timed_out, False)

    def test_save_load(self):
        logging.debug('')
        logging.debug('test_save_load')

        externp = set_as_top(ExternalCode())
        externp.name = 'ExternalCode'
        externp.timeout = 5
        externp.command = 'python sleep.py 1'

        # Exercise check_save_load().
        retcode = check_save_load(externp)
        self.assertEqual(retcode, 0)

    def test_timeout(self):
        logging.debug('')
        logging.debug('test_timeout')

        # Set timeout to less than execution time.
        externp = set_as_top(ExternalCode())
        externp.timeout = 1
        externp.command = 'python sleep.py 5'
        try:
            externp.run()
        except RunInterrupted, exc:
            self.assertEqual(str(exc), ': Timed out')
            self.assertEqual(externp.timed_out, True)
        else:
            self.fail('Expected RunInterrupted')

    def test_badcmd(self):
        logging.debug('')
        logging.debug('test_badcmd')

        # Set command to nonexistant path.
        externp = set_as_top(ExternalCode())
        externp.command = 'xyzzy'
        externp.stdout = 'badcmd.out'
        externp.stderr = ExternalCode.STDOUT
        try:
            externp.run()
        except RuntimeError, exc:
            if sys.platform == 'win32':
                self.assertTrue('Operation not permitted' in str(exc))
                self.assertEqual(externp.return_code, 1)
            else:
                msg = ': return_code = 127'
                self.assertEqual(str(exc).startswith(msg), True)
                self.assertEqual(externp.return_code, 127)
            self.assertEqual(os.path.exists(externp.stdout), True)
        else:
            self.fail('Expected RuntimeError')
        finally:
            if os.path.exists(externp.stdout):
                os.remove(externp.stdout)

    def test_nullcmd(self):
        logging.debug('')
        logging.debug('test_nullcmd')

        # Check response to no command set.
        externp = set_as_top(ExternalCode())
        externp.stdout = 'nullcmd.out'
        externp.stderr = ExternalCode.STDOUT
        try:
            externp.run()
        except ValueError, exc:
            self.assertEqual(str(exc), ': Null command line')
        else:
            self.fail('Expected ValueError')
        finally:
            if os.path.exists(externp.stdout):
                os.remove(externp.stdout)
    
    def test_unique(self):
        logging.debug('')
        logging.debug('test_unique')

        model = Model()
        for comp in (model.a, model.b):
            self.assertEqual(comp.create_instance_dir, True)
        self.assertNotEqual(model.a.directory, 'a')
        self.assertNotEqual(model.b.directory, 'b')

        set_as_top(model)
        for comp in (model.a, model.b):
            self.assertEqual(comp.create_instance_dir, False)
            self.assertEqual(comp.return_code, 0)
            self.assertEqual(comp.timed_out, False)
        self.assertEqual(model.a.directory, 'a')
        self.assertEqual(model.b.directory, 'b')

        model.run()
        for comp in (model.a, model.b):
            self.assertEqual(comp.return_code, 0)
            self.assertEqual(comp.timed_out, False)


if __name__ == "__main__":
    import nose
    sys.argv.append('--cover-package=openmdao')
    sys.argv.append('--cover-erase')
    nose.runmodule()

