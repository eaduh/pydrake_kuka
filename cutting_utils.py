import numpy as np

from pydrake.all import (
    AbstractValue,
    LeafSystem,
    PortDataType,
    RigidBodyPlant,
    RigidBodyTree
)

class CuttingGuard(LeafSystem):
    def __init__(self, rbt, rbp, cutting_body_index, blade_start_pt,
                 blade_stop_pt, cut_direction, min_cut_force,
                 blade_width, timestep=0.01):
        ''' Watches the RBT contact results output, and
        raises an exception (to pause simulation). '''
        LeafSystem.__init__(self)
        self.set_name('Cutting Guard')

        self._DeclarePeriodicPublish(timestep, 0.0)
        self.rbt = rbt
        self.rbp = rbp

        self.collision_id_to_body_index_map = {}
        for k in range(self.rbt.get_num_bodies()):
            for i in rbt.get_body(k).get_collision_element_ids():
                self.collision_id_to_body_index_map[i] = k

        self.cutting_body_index = cutting_body_index
        self.cutting_body_ids = rbt.get_body(cutting_body_index).get_collision_element_ids()
        self.cut_direction = np.array(cut_direction)
        self.min_cut_force = min_cut_force
        self.blade_pts = np.zeros([3, 2])
        self.blade_pts[:, 0] = blade_start_pt
        self.blade_pts[:, 1] = blade_stop_pt
        self.blade_width = blade_width

        self.state_input_port = \
            self._DeclareInputPort(PortDataType.kVectorValued,
                                   rbt.get_num_positions() +
                                   rbt.get_num_velocities())
        self.contact_results_input_port = \
            self._DeclareInputPort(PortDataType.kAbstractValued,
                                   rbp.contact_results_output_port().size())

    def _DoPublish(self, context, events):
        contact_results = self.EvalAbstractInput(
            context, self.contact_results_input_port.get_index()).get_value()
        x = self.EvalVectorInput(
                context, self.state_input_port.get_index()).get_value()
            
        this_contact_info = []
        for contact_i in range(contact_results.get_num_contacts()):
            # Cludgy -- would rather keep things as objects.
            # But I need to work out how to deepcopy those objects.
            # (Need to bind their various constructive methods)
            contact_info = contact_results.get_contact_info(contact_i)
            contact_force = contact_info.get_resultant_force()
            cut_body_index = None
            cut_pt = contact_force.get_application_point()
            if contact_info.get_element_id_1() in self.cutting_body_ids:
                cut_body_index = contact_info.get_element_id_2()
                cut_force = contact_force.get_force()
            elif contact_info.get_element_id_2() in self.cutting_body_ids:
                cut_body_index = contact_info.get_element_id_1()
                cut_force = -contact_force.get_force()
            if cut_body_index:
                # Point and force are in *world* frame
                # So see them in knife frame
                kinsol = self.rbt.doKinematics(x[0:self.rbt.get_num_positions()])
                tf = self.rbt.relativeTransform(kinsol, self.cutting_body_index, 0)
                body_force = tf[0:3, 0:3].dot(cut_force)
                body_cut_pt = tf[0:3, 0:3].dot(cut_pt) + tf[0:3, 3]
                print "Got potential cut with body %d: " % cut_body_index, " force ", body_force, " and pt ", body_cut_pt,
                print " and cut body index ", self.collision_id_to_body_index_map[cut_body_index]



if __name__ == "__main__":
    print "Goodbye"