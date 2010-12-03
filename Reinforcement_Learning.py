"""
Copyright 2007 Greg Pinero
gregpinero@gmail.com

This file is part of Dragon Fighter.

Dragon Fighter is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

Dragon Fighter is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

--------------------

Reinforcement Learning Module

Greg Pinero (gregpinero@gmail.com)
October, 2007

I believe this can be a very general module and depend on whatever
is calling it to act and provide states.  It is currently use for
my dragon fighter game.

TODO:
    Learn more about Reinforcement learning, and make sure this is a correct
    implementation of Q Learning.

"""
from __future__ import division

#-----------------------------------------------------------------------------
#USER SETTINGS
alpha=5000
beta=10000

#-----------------------------------------------------------------------------
#UTILITY FUNCTIONS





#-----------------------------------------------------------------------------
#CLASSES

class Brain(object):
    """ """
    def __init__(self,discount_rate,available_actions):
        """for a real RL library, available actions depend on state """
        assert 0<=discount_rate<=1
        self.Q_Values_Table={}
        self.discount_rate=discount_rate
        self.time_step=0
        self.learning_rate=alpha/(beta+self.time_step)
        self.available_actions=available_actions

    def learn(self,previous_state,action,new_state,cost):
        """ Q Learning"""
        key=str(previous_state)+str(action.func_name)
        self.Q_Values_Table[key]= \
        (1-self.learning_rate)*self.Q_Values_Table.get(key,0) + self.learning_rate*(
            cost+self.discount_rate*self.Q_Values_Table.get(str(new_state)+str(self.get_best_action(new_state,self.available_actions)),0)
            )
        self.learning_rate=alpha/(beta+self.time_step)
        self.time_step+=1

    def get_best_action(self,state,available_actions=None):
        """ """
        if not available_actions:available_actions=self.available_actions
        best_action=available_actions[0]
        for action in available_actions:
            if self.Q_Values_Table.get(str(state)+str(action.func_name),0)<self.Q_Values_Table.get(str(state)+str(best_action.func_name),0):
                best_action=action
        return best_action

#-----------------------------------------------------------------------------
#TESTING
if __name__=='__main__':
    pass