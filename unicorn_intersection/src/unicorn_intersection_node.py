#!/usr/bin/env python
import rospy
import numpy as np
from duckietown_msgs.msg import TurnIDandType, FSMState, BoolStamped, LanePose, Pose2DStamped, Twist2DStamped
from std_msgs.msg import Float32, Int16, Bool, String
from geometry_msgs.msg import Point, PoseStamped, Pose, PointStamped
from nav_msgs.msg import Path
import time
import math
import json

class UnicornIntersectionNode(object):
    def __init__(self):
        self.node_name = "Unicorn Intersection Node"

        ## setup Parameters
        self.setupParams()

        ## Internal variables
        self.state = "JOYSTICK_CONTROL"
        self.active = False
        self.turn_type = -1
        self.forward_pose = False


        ## Subscribers
        self.sub_turn_type = rospy.Subscriber("~turn_type", Int16, self.cbTurnType)
        self.sub_fsm = rospy.Subscriber("~fsm_state", FSMState, self.cbFSMState)
        self.sub_int_go = rospy.Subscriber("~intersection_go", BoolStamped, self.cbIntersectionGo)
        self.sub_lane_pose = rospy.Subscriber("~lane_pose_in", LanePose, self.cbLanePose)

        ## Publisher
        self.pub_int_done = rospy.Publisher("~intersection_done", BoolStamped, queue_size=1)
        self.pub_LF_params = rospy.Publisher("~lane_filter_params", String, queue_size=1)
        self.pub_lane_pose = rospy.Publisher("~lane_pose_out", LanePose, queue_size=1)


        ## update Parameters timer
        self.params_update = rospy.Timer(rospy.Duration.from_sec(1.0), self.updateParams)

    def cbLanePose(self, msg):
        if self.forward_pose: self.pub_lane_pose.publish(msg)

    def changeLFParams(self, params, reset_time):
        data = {"params": params, "time": reset_time}
        msg = String()
        msg.data = json.dumps(data)
        self.pub_LF_params.publish(msg)

    def cbIntersectionGo(self, msg):
        if not msg.data: return

        while self.turn_type == -1:
            rospy.loginfo("Requested to start intersection, but we do not see an april tag yet.")
            rospy.sleep(2)

        sleeptimes = [self.time_left_turn, self.time_straight_turn, self.time_right_turn]
        LFparams = [self.LFparams_left, self.LFparams_straight, self.LFparams_right]
        omega_ffs = [self.ff_left, self.ff_straight, self.ff_right]

        self.changeLFParams(LFparams[self.turn_type], sleeptimes[self.turn_type]+1.0)
        rospy.set_param("~lane_controller/omega_ff", omega_ffs[self.turn_type])

        # Waiting for LF to adapt to new params
        rospy.sleep(1)

        rospy.loginfo("Starting intersection control - driving to " + str(self.turn_type))
        self.forward_pose = True

        rospy.sleep(sleeptimes[self.turn_type])

        self.forward_pose = False
        rospy.set_param("~lane_controller/omega_ff", 0)

        msg_done = BoolStamped()
        msg_done.data = True
        self.pub_int_done.publish(msg_done)



    def cbFSMState(self, msg):
        if self.state != msg.state and msg.state == "INTERSECTION_COORDINATION":
            self.turn_type = -1

        self.state = msg.state

    def cbTurnType(self, msg):
        if self.turn_type == -1: self.turn_type = msg.data
        if self.debug_dir != -1: self.turn_type = self.debug_dir

    def setupParams(self):
        self.time_left_turn = self.setupParam("~time_left_turn", 2)
        self.time_straight_turn = self.setupParam("~time_straight_turn", 2)
        self.time_right_turn = self.setupParam("~time_right_turn", 2)
        self.ff_left = self.setupParam("~ff_left", 1.5)
        self.ff_straight = self.setupParam("~ff_straight", 0)
        self.ff_right = self.setupParam("~ff_right", -1)
        self.LFparams_left = self.setupParam("~LFparams_left", 0)
        self.LFparams_straight = self.setupParam("~LFparams_straight", 0)
        self.LFparams_right = self.setupParam("~LFparams_right", 0)

        self.debug_dir = self.setupParam("~debug_dir", -1)

    def updateParams(self,event):
        self.time_left_turn = rospy.get_param("~time_left_turn")
        self.time_straight_turn = rospy.get_param("~time_straight_turn")
        self.time_right_turn = rospy.get_param("~time_right_turn")
        self.ff_left = rospy.get_param("~ff_left")
        self.ff_straight = rospy.get_param("~ff_straight")
        self.ff_right = rospy.get_param("~ff_right")
        self.LFparams_left = rospy.get_param("~LFparams_left")
        self.LFparams_straight = rospy.get_param("~LFparams_straight")
        self.LFparams_right = rospy.get_param("~LFparams_right")

        self.debug_dir = rospy.get_param("~debug_dir")


    def setupParam(self,param_name,default_value):
        value = rospy.get_param(param_name,default_value)
        rospy.set_param(param_name,value) #Write to parameter server for transparancy
        rospy.loginfo("[%s] %s = %s " %(self.node_name,param_name,value))
        return value

    def onShutdown(self):
        rospy.loginfo("[UnicornIntersectionNode] Shutdown.")

if __name__ == '__main__':
    rospy.init_node('unicorn_intersection_node',anonymous=False)
    unicorn_intersection_node = UnicornIntersectionNode()
    rospy.on_shutdown(unicorn_intersection_node.onShutdown)
    rospy.spin()
