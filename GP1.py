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

Dragon Evolver

A simple Gentic Programming implementation for use in my learning
dragon game.

Greg Pinero
gregpinero@gmail.com
October 2007
"""
from __future__ import division
import random
import sys

#------------------------------------------------------------------------------
# SETTINGS

logfile=file('logfile.txt','w') #set to none for no logging
PROB_MUTATION=.5
#can one individual be both a mother and father for a child
PREVENT_SELF_BREEDING=True

#------------------------------------------------------------------------------

class node:
    def __init__(self):
        self.args=[]
    def __str__(self):
        retstr=self.__class__.__name__+'('
        myargs=[str(arg) for arg in self.args]
        retstr+=','.join(myargs)+')'
        return retstr
#--------------------------------------
#GP Functions
class ikfm(node):
    """two arg conditional, do a if knight is facing me, b otherwise."""
    def __init__(self):
        self.args=[0,0]
    def execute(self,dragon):
        if dragon.knight_facing_me():
            return self.args[0].execute(dragon)
        else:
            return self.args[1].execute(dragon)
class ifle(node):
    """(if a<=b, then c, else d)"""
    def __init__(self):
        self.args=[0,0,0,0]
    def execute(self,dragon):
        a=self.args[0].execute(dragon)
        b=self.args[1].execute(dragon)
        if a<=b:return self.args[2].execute(dragon)
        else:return self.args[3].execute(dragon)

#--------------------------------------
#GP Terminals
class mafk(node):
    def execute(self,dragon):
        dragon.move_away_from_knight()
        raise 'Done'
class mtk(node):
    def execute(self,dragon):
        dragon.move_towards_knight()
        raise 'Done'
class attack(node):
    def execute(self,dragon):
        dragon.attack()
        raise 'Done'
class knightdistance(node):
    def execute(self,dragon):
        return dragon.get_knights_distance()

class constant(node):
    def __init__(self,allowed_values=[0,1,20,50]):
        node.__init__(self)
        random.seed()
        self.value=random.choice(allowed_values)
    def execute(self,dragon):
        return self.value
    def __str__(self):
        return str(self.value)

FUNCTION_SET=[ikfm,ifle]
TERMINAL_SET=[mafk,mtk,attack,knightdistance,constant] #,constant]

#--------------------------------------
#Main Program Part
def snip(node):
    """Return a partial program"""
    random.seed()
    prob_of_returning_this_node=.3
    if random.random()<=prob_of_returning_this_node:
        return node
    else:
        if node.args:
            #choose a random branch
            return snip(random.choice(node.args))
        else:
            #have reached a leaf node
            return node

def replace_within_node(node,oldnode,newnode):
    """ """
    random.seed()
    if random.random()<PROB_MUTATION:
        return generate_random_program(currdepth=0,mindepth=1,maxdepth=3)
    else:
        if node is oldnode:
            return newnode
        else:
            for i in range(len(node.args)):
                node.args[i]=replace_within_node(node.args[i],oldnode,newnode)
            return node

def generate_initial_programs(dragons):
    """Generate one program"""
    if logfile:logfile.write('Initial population:\n')
    random.seed()
    for dragon in dragons:
        dragon.program=generate_random_program(0)
        if logfile:logfile.write(str(dragon.program)+'\n')
    if logfile:logfile.write('\n\n')

def generate_random_program(currdepth,mindepth=2,maxdepth=4):
    random.seed()
    if currdepth==maxdepth:
        #only add from terminal set
        node=random.choice(TERMINAL_SET)()
        return node
    elif currdepth<mindepth:
        #only add from function set
        node=random.choice(FUNCTION_SET)()
        for i in range(len(node.args)):
            node.args[i]=generate_random_program(currdepth+1,mindepth,maxdepth)
        return node
    else:
        node=random.choice(TERMINAL_SET+FUNCTION_SET)()
        for i in range(len(node.args)):
            node.args[i]=generate_random_program(currdepth+1,mindepth,maxdepth)
        return node

def exec_programs(dragons):
    for dragon in dragons:
        try:dragon.program.execute(dragon)
        except 'Done':continue #execute needs to break after first action

def copy(rootnode):
    """return a new tree copied from rootnode"""
    newnode=rootnode.__class__()
    for i in range(len(rootnode.args)):
        newnode.args[i]=copy(rootnode.args[i])
    return newnode

def breed(father,mother):
    """ """
    f_program=copy(father.program)
    m_program=copy(mother.program)

    logfile.write('breeding function\n')
    logfile.write('    father:\n    '+str(father.program)+'\n    mother:\n    '+str(mother.program)+'\n')

    snip_from_mother=snip(m_program)
    snip_from_father=snip(f_program)

    logfile.write('    snip_from_mother:\n    '+str(snip_from_mother)+'\n    snip_from_father:\n    '+str(snip_from_father)+'\n')

    program_for_father=replace_within_node(f_program,snip_from_father,snip_from_mother)

    logfile.write('    program_for_father:\n    '+str(program_for_father)+'\n')

    program_for_mother=replace_within_node(m_program,snip_from_mother,snip_from_father)

    logfile.write('    program_for_mother:\n    '+str(program_for_mother)+'\n')
    logfile.flush()
    return program_for_father,program_for_mother

def get_adjusted_fitness(raw_fitness,maxpoints):
    #standardized fitness means a smaller value is always better.
    standardized_fitness=maxpoints-raw_fitness
    #adjusted fitness is used to emphasize small differences for highly fit individuals
    adjusted_fitness=1/(1+standardized_fitness)
    return adjusted_fitness

def get_normalized_fitness(adjusted_fitness,sum_of_everyones_adjusted_fitness):
    normalized_fitness=adjusted_fitness/(sum_of_everyones_adjusted_fitness)
    return normalized_fitness

def choose_ind_fitness_proportionately(fitnesses):
    """expecting fitnesses to contain [fitness,dragon]"""
    random.seed()
    val=random.random()
    lastitem=0
    newitem=0
    for item in fitnesses:
        newitem+=item[0]
        #print lastitem,val,newitem
        if lastitem<=val<newitem:
            #print 'found',item,'for',val
            return item[1] #de dragon
        else:
            lastitem=newitem
    raise "broken choose_ind_fitness_proportionately"

def reproduce(dragons,maxtime):
    """ """
    maxpoints=maxtime+(dragons[0].reward_factor_for_killing_knight)
    total_adjusted_fitnesses=sum([get_adjusted_fitness(dragon.get_raw_fitness(),maxpoints) for dragon in dragons])
    fitnesses=[
            [
                get_normalized_fitness(get_adjusted_fitness(dragon.get_raw_fitness(),maxpoints),total_adjusted_fitnesses),
                dragon
            ]
            for dragon in dragons
            ]
    #print [fitness[0] for fitness in fitnesses]
    #print 'most fit is\n\t',[fitness[1] for fitness in fitnesses if fitness[0]==max([fitness[0] for fitness in fitnesses])][0].program
    logfile.write('New Generation: //////\n\n')
    logfile.write('fitnesses '+str(fitnesses)+'\n')
    logfile.write('\tMost fit dragon is: '+str([fitness[1] for fitness in fitnesses if fitness[0]==max([fitness[0] for fitness in fitnesses])][0].program)+'\n')
    newprograms=[]
    i=0
    while i<=len(dragons):
        father=choose_ind_fitness_proportionately(fitnesses)
        mother=choose_ind_fitness_proportionately(fitnesses)
        if PREVENT_SELF_BREEDING:
            while father==mother:
                mother=choose_ind_fitness_proportionately(fitnesses)
        newprograms+=breed(father,mother)
        i+=2
    newprograms=newprograms[:len(dragons)] #for odd numbers we make 1 too many so ignore last
    for i in range(len(dragons)):
        dragons[i].program=newprograms[i]
    logfile.write('------------------\n\n')
    return dragons

if __name__=='__main__':
    #Just a simple test
    class Test_Class:
        pass
    dragons=[Test_Class() for i in range(10)]
    generate_initial_programs(dragons)
    for i in range(10):
        #breed(random.choice(dragons),random.choice(dragons))
        breed(dragons[0],dragons[1])
