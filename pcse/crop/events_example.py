from __future__ import print_function
__author__ = 'wit015'

from ..base_classes import ParamTemplate, StatesTemplate, RatesTemplate, \
    SimulationObject, VariableKiosk
from .. import signals


class EventsExample(SimulationObject):

    def initialize(self, day, kiosk, parameters):
        self._connect_signal(self._on_NPK_Application, signals.npk_application)
        self._connect_signal(self._on_IRRIGATE, signals.irrigate)

    def calc_rates(self, day, drv):
        pass

    def integrate(self, day, delt=1.):
        pass

    # Event handler for NPK application
    def _on_NPK_Application(self, day, NPK_amount):
        msg = "NPK fertilizer applied on %s N/P/K amount: %s/%s/%s" % (day, NPK_amount[0], NPK_amount[1],
                                                                       NPK_amount[2])
        print(msg)

    # Event handler for irrigation
    def _on_IRRIGATE(self, day, irrigation_amount):
        msg = "Irrigation applied on %s, irrigation amount: %f" % (day, irrigation_amount)
        print(msg)