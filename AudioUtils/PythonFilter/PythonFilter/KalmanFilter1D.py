import sys
import os

class KalmanFilter1D:
    def __init__(self, x0, P, R, Q):
        self.x = x0 #initial state
        self.P = P  #initial variance estimate 
        self.R = R  # sensor noise (measurement error estimate)  
        self.Q = Q  # movement noise  (process noise estimate) 


    def update(self, z):
        self.x = (self.P * z + self.x * self.R) / (self.P + self.R)
        self.P = 1. / (1./self.P + 1./self.R)


    def predict(self, u=0.0):
        self.x += u
        self.P += self.Q