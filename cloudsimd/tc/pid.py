#!/usr/bin/env python

# Class that implements a basic PID controller.
#
#                   |minOutput  |maxOutput
#                   |           |
#                   v           v
#                   -----------------
#                   |               |
#  Ref[-1...1] ---> | P Controller  | ---> Output [-100%...100%]
#                   |               |
#                   -----------------
#                   ^            ^
#                   |            |
#                   |minRef      |maxRef
# 
# The reference should be normalized between [-1...1] and the output is
# generated as a percentage (positive or negative).
# The 'minRef' sets the deadband of the controller.
# The 'maxRef' sets the maximum reference of the controller. Greater values of the reference
# will not generate greater values in the output.
# The 'minOutput' sets the minimum percentage of output in case of not to stay into the deadband.
# The 'maxOutput' sets the maximum percentage of output.

import math

class PID:

    def __init__(self, _name, _minRef, _maxRef, _minOutput, _maxOutput):
        self.debug = True
        self.minRef = _minRef
        self.maxRef = _maxRef
        self.minOutput = _minOutput
        self.maxOutput = _maxOutput
        self.name = _name
        self.ref = self.output = self.prev_error = self.int_error = 0.0

        self.KP = 0.41
        self.KI = 0.06
        self.KD = 0.53

        if self.debug:
            print '[PID::PID()] New ', self.name, ' controller created with the next params:'
            print 'MinRef: ', str(self.minRef), ' MaxRef: ', str(self.maxRef)
            print 'MinOutput: ', str(self.minOutput), ' MaxOutput: ', str(self.maxOutput)

    def setReference(self, _newReference):
        if self.debug:
            print '[PID::setReference()] New reference (', str(_newReference), ') for ', self.name

        #Proportional Error
        direction = _newReference / math.fabs(_newReference)
        if math.fabs(_newReference) < self.minRef:
            self.output = 0
        elif math.fabs(_newReference) > self.maxRef:
            self.output = direction * self.maxOutput
        else:
            self.output = direction * self.minOutput + _newReference * (self.maxOutput - self.minOutput)

        # Integral Error
        self.int_error = (self.int_error + self.output) * 2.0 / 3.0

        #Derivative Error
        deriv_error = self.output - self.prev_error
        self.prev_error = self.output

        self.output = self.KP * self.output + self.KI * self.int_error + self.KD * deriv_error

    def getOutput(self):
        if self.debug:
            print '[PIDController::getOutput()]  (', str(self.output), ' %) at ', self.name, ' controller'
        return self.output
