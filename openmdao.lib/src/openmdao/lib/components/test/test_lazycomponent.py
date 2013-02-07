import unittest

from openmdao.main.api import Component, Assembly
from openmdao.lib.components.api import LazyComponent
from openmdao.lib.datatypes.api import Float


class SinkComp(Component):         
    i1 = Float(0.0, iotype="in")
    i2 = Float(0.0, iotype="in")
    i3 = Float(0.0, iotype="in")

    def execute(self): 
        pass


class TestComp(LazyComponent): 
    a = Float(0.0, iotype="in")

    x = Float(0.0, iotype="out")
    y = Float(0.0, iotype="out")
    z = Float(0.0, iotype="out")

    def execute(self): 
        outputs = self._connected_outputs
        if ('x' in outputs): 
            self.x = self.a+1
        if ('y' in outputs): 
            self.y = self.a+2
        if ('z' in outputs):
            self.z = self.a+3


class BrokenTestComp(TestComp): 

    def execute(self):
        self.x = 10


class TestLazyComponent(unittest.TestCase):
    
    def setUp(self): 
        self.top = Assembly()
        self.top.add("t", TestComp())
        self.top.add("s", SinkComp())
        self.top.driver.workflow.add(["t", "s"])
        self.top.set('t.a', 1)

    def tearDown(self): 
        self.top = None

    def test_full_connected(self): 
        self.top.connect('t.x', 's.i1')
        self.top.connect('t.y', 's.i2')
        self.top.connect('t.z', 's.i3')

        self.top.run()

        self.assertEqual(self.top.t.x, 2)
        self.assertEqual(self.top.t.y, 3)
        self.assertEqual(self.top.t.z, 4)

        valids = self.top.t._valid_dict
        self.assertEqual(valids['x'], True)
        self.assertEqual(valids['y'], True)
        self.assertEqual(valids['z'], True)

    def test_partial_connected(self): 
        self.top.connect('t.x', 's.i1')
        self.top.connect('t.y', 's.i2')

        self.top.run()

        self.assertEqual(self.top.t.x, 2)
        self.assertEqual(self.top.t.y, 3)
        self.assertEqual(self.top.t.z, 0)

        valids = self.top.t._valid_dict
        self.assertEqual(valids['x'], True)
        self.assertEqual(valids['y'], True)
        self.assertEqual(valids['z'], False)

        #now try re-running with a different configuration to test the validy reseting
        self.top.disconnect('t')
        self.top.connect('t.x', 's.i1')
        self.top.set('t.a', 2)

        self.top.run()

        self.assertEqual(self.top.t.x, 3)
        self.assertEqual(self.top.t.y, 3) #this value is carried over from the first run call, but it's wrong... so not valid
        self.assertEqual(self.top.t.z, 0)

        valids = self.top.t._valid_dict
        self.assertEqual(valids['x'], True)
        self.assertEqual(valids['y'], False) 
        self.assertEqual(valids['z'], False)

    def test_partial_connect_exec_error(self):
        self.top.add('t', BrokenTestComp())
        self.top.connect('t.x', 's.i1')
        self.top.set('t.a', 1)

        self.top.run()

        self.assertEqual(self.top.t.x, 10)
        self.assertEqual(self.top.t.y, 0)
        self.assertEqual(self.top.t.z, 0)

        self.top.connect('t.y', 's.i2')
        self.top.set('t.a', 2)

        try:
            self.top.run()
        except RuntimeError as err: 
            msg = str(err)
            self.assertEqual(msg, "t: output 'y' is connected to something in your model, but was not calculated during execution")
        else: 
            self.fail("RuntimeError Expected")

    def test_new_connection_invalidation(self): 
        self.top.connect('t.x', 's.i1')
        self.top.set('t.a', 1)

        self.top.run()

        self.assertEqual(self.top.t.x, 2)
        self.assertEqual(self.top.t.y, 0)
        self.assertEqual(self.top.t.z, 0)

        valids = self.top.t._valid_dict
        self.assertEqual(valids['x'], True)
        self.assertEqual(valids['y'], False) 
        self.assertEqual(valids['z'], False)

        #new connection is made, but no inputs are invalid. Still need to run!
        self.top.connect('t.y', 's.i2')

        self.top.run()

        self.assertEqual(self.top.t.x, 2)
        self.assertEqual(self.top.t.y, 3)
        self.assertEqual(self.top.t.z, 0)

        valids = self.top.t._valid_dict
        self.assertEqual(valids['x'], True)
        self.assertEqual(valids['y'], True) 
        self.assertEqual(valids['z'], False)

    def test_dynamic_trait(self): 
        self.top.connect('t.x', 's.i1')
        self.top.connect('t.y', 's.i2')

        self.top.t.add('w', Float(0.0, iotype="out"))
        self.top.connect('t.w', 's.i3')

        try:
            self.top.run()
        except RuntimeError as err: 
            msg = str(err)
            self.assertEqual(msg, "t (1-1): output 'w' is connected to something in your model, but was not calculated during execution")
        else: 
            self.fail("RuntimeError Expected")

if __name__ == "__main__": 
    unittest.main()

