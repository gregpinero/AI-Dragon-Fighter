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

Dragon Fighter

Greg Pinero (gregpinero@gmail.com)
October, 2007

A game where a knight tries to kill dragons.  Dragons use AI (Genetic Programming
or Reinforcement learning) to learn how to be good oppenents.

Requirements:
    Python 2.4 or higher
    Pygame (http://pygame.org/news.html)
    Linux (Should work in Windows but not tested)

TODO:
Reinforcement Learing:
    It works but I'm not seeing good learning or any aggressive behavoir.
    Q value table mostly 0's
ideas to fix:
1. kinght dead and dragon dead need to be states otherwise doesn't know what state to work towards.
2. generalized states e.g. rounding distance cause dragon to be in same state before and after action, thus
has no idea what actions will do. ...
3. Are negative numbers allowed for cost?
4. How to better initialize values?
"""
from __future__ import division

#-----------------------------------------------------------------------------
# SETTINGS

#How many dragons to have on the board
NUMDRAGRONS=5
#How long should a round last
TIMELIMITSECONDS=60
#Use Reinforcement learning to train dragons.  Uses Genetic Programming if false
DRAGON_RL_AI=False

#-----------------------------------------------------------------------------
import sys
import os
import math
import random
import pygame
from pygame.locals import *
if not pygame.font: print 'Warning, fonts disabled'
if not pygame.mixer: print 'Warning, sound disabled'
from charactor_images import d_knight_image_paths,d_dragon_image_paths,d_fire_image_paths
import GP1
import Reinforcement_Learning

curdir=os.path.abspath(os.curdir) #fix for pyexe later

#---Utility Functions---

directions_to_degrees={
    'e':0,
    'ne':45,
    'n':90,
    'nw':135,
    'w':180,
    'sw':225,
    's':270,
    'se':315
}

def opposite_direction(direction):
    directions=['e','ne','n','nw','w','sw','s','se']
    return directions[(directions.index(direction)+4)%8]

def sign(number):return cmp(number,0)

def euclidean_distance(side1,side2):
    return math.sqrt((float(side1)**2)+(float(side2)**2))

def load_image(path, transparentcolorkey=None):
    """This function takes the path of an image to load.
    It also optionally takes an argument it can use to
    set a colorkey for the image. A colorkey is used in
    graphics to represent a color of the image that is transparent.
    Returns a tuple of image, and rect
    """
    try:image = pygame.image.load(path)
    except pygame.error, message:
        print 'Cannot load image:', path
        raise SystemExit, message
    image = image.convert()
    if transparentcolorkey is not None:
        if transparentcolorkey is -1:
            transparentcolorkey = image.get_at((0,0))
        image.set_colorkey(transparentcolorkey, RLEACCEL)
    return image #, image.get_rect()

def load_sound(path):
    class NoneSound:
        def play(self): pass
    if not pygame.mixer:return NoneSound()
    try:sound = pygame.mixer.Sound(path)
    except pygame.error, message:
        print 'Cannot load sound:', wav
        raise SystemExit, message
    return sound

def load_images(d_image_paths,trans_color=None):
    d_images={}
    for label,actions in d_image_paths.items():
        #print 'examining',label
        for direction,imagelist in actions.items():
            #print '  exmining',direction
            for imagefilepath in imagelist:
                if not os.path.exists(os.path.join(curdir,imagefilepath)):
                    print '    image',imagefilepath,'not found'
                else:
                    #make sure d_images has needed keys
                    if not d_images.has_key(label):d_images[label]={}
                    if not d_images[label].has_key(direction):d_images[label][direction]=[]
                    #add image and rect
                    d_images[label][direction].append(load_image(imagefilepath,trans_color))
    return d_images

def free_sound_channel():
    """Get next available sound channel
    Usage:
    free_channels=free_sound_channel()
    id=free_channels.next()
    """
    id=0
    while id<pygame.mixer.get_num_channels():
        yield id
        id+=1
    return    # or: raise StopIteration()

#---Main Classes---

class Image_lib:
    """A class to track images being used by characters"""
    def __init__(self,image_store):
        self.d_images=image_store
        self.reset()
    def reset(self):
        self.last_action=''
        self.last_direction=''
        self.index=0
        self.portray_death=False
    def get_next_image(self,action,direction):
        """feeds client the next image in sequence."""
        if self.portray_death:
            ret_image=self.d_images['tipping over'][self.last_direction][len(self.d_images['tipping over'][self.last_direction])-1]
            ret_rect=ret_image.get_rect()
            return ret_image,ret_rect
        if action==self.last_action and direction==self.last_direction:
            pass #no need to reset index
        elif action=='walking' and direction==self.last_direction:
            pass #again no need to reset index
        else:
            self.index=0
        if self.index>=len(self.d_images[action][direction]):self.index=len(self.d_images[action][direction])-1
        ret_image=self.d_images[action][direction][self.index]
        ret_rect=ret_image.get_rect()
        self.index=(self.index+1)%len(self.d_images[action][direction])
        self.last_action=action
        self.last_direction=direction
        return ret_image,ret_rect
    def is_action_seq_done(self,action,direction):
        return self.index==len(self.d_images[action][direction])-1

class Fire(pygame.sprite.Sprite):
    """Simply makes animated fire for a dragon. """
    def __init__(self,fire_images_store):
        pygame.sprite.Sprite.__init__(self) #call Sprite initializer
        self.image_lib=Image_lib(fire_images_store)
        self.in_action_seq=False
        self.direction='e'
        self.action='paused'
        self.image,self.rect=self.image_lib.get_next_image(self.action,'all')
        self.rect.left,self.rect.top=-600,-600
    def burn(self,dragons_rect,direction):
        """run a burn cycle there"""
        self.in_action_seq=True
        self.direction=direction
        self.action='burn'
        #move fire base to line up with dragon direction
        if direction in ['e','w','n','s']:shrinkratio=.3
        else: shrinkratio=.7
        dragons_rect=dragons_rect.inflate(-dragons_rect.width*shrinkratio,-dragons_rect.height*shrinkratio)
        if direction=='w':self.rect.midright=dragons_rect.midleft
        elif direction=='n':self.rect.midbottom=dragons_rect.midtop
        elif direction=='e':self.rect.midleft=dragons_rect.midright
        elif direction=='s':self.rect.midtop=dragons_rect.midbottom
        elif direction=='nw':self.rect.bottomright=dragons_rect.topleft
        elif direction=='ne':self.rect.bottomleft=dragons_rect.topright
        elif direction=='sw':self.rect.topright=dragons_rect.bottomleft
        elif direction=='se':self.rect.topleft=dragons_rect.bottomright
        else:raise "not a direction"
    def update(self):
        if self.in_action_seq and self.image_lib.is_action_seq_done('burn','all'):
            self.action='paused'
            self.image,self.rect=self.image_lib.get_next_image(self.action,'all')
            self.rect.left,self.rect.top=-600,-600
        else:
            self.base_image,junk = self.image_lib.get_next_image('burn','all')
            #rotate to direction
            self.rotate_to_face(directions_to_degrees[self.direction])
    def rotate_to_face(self,degrees):
        oldcenter=self.rect.center
        self.image=pygame.transform.rotate(self.base_image,degrees)
        self.rect=self.image.get_rect()
        self.rect.center=oldcenter

class Charactor(pygame.sprite.Sprite):
    """Main Charactor class, everyone inherits from here"""
    def __init__(self,left,top,image_store,moveamount=1):
        pygame.sprite.Sprite.__init__(self) #call Sprite initializer
        self.image_lib=Image_lib(image_store)
        self.lunge_foward_by=12 #pixels
        self.sound_channel=pygame.mixer.Channel(free_channels.next())
        self.in_action_seq=False
        self.move_amount=moveamount
        self.action='paused'
        self.direction='w'
        self.image,self.rect = self.image_lib.get_next_image(self.action,self.direction)
        self.rect.center=(left,top)
    def reset(self):
        self.action='paused'
        self.direction='w'
        self.in_action_seq=False
        self.image_lib.reset()
    def update(self):
        """Just handle final positions, image display, and collisions """
        newpos=self.rect.center
        self.image,self.rect = self.image_lib.get_next_image(self.action,self.direction)
        self.rect.center=newpos
        if self.in_action_seq:
            if self.image_lib.is_action_seq_done(self.action,self.direction):
                if self.action=='tipping over':
                    #we should stay dead here!
                    self.image_lib.portray_death=True
                else:
                    self.in_action_seq=False
                    self.action='paused'
    def move(self,direction):
        """left,up,right,down"""
        if not self.in_action_seq:
            #you can only move when you're not doing an action like attack
            oldpos=self.rect.center
            ma=self.move_amount
            if direction=='w':amountright,amountdown=-1*ma,0*ma
            elif direction=='n':amountright,amountdown=0*ma,-1*ma
            elif direction=='e':amountright,amountdown=1*ma,0*ma
            elif direction=='s':amountright,amountdown=0*ma,1*ma
            elif direction=='nw':amountright,amountdown=-1*ma,-1*ma
            elif direction=='ne':amountright,amountdown=1*ma,-1*ma
            elif direction=='sw':amountright,amountdown=-1*ma,1*ma
            elif direction=='se':amountright,amountdown=1*ma,1*ma
            else:
                raise "not a direction"
            #set these values so update will update us
            self.action='walking'
            self.direction=direction
            pre=self.am_in_collision()#test for collision before we move
            potential_move_rect=self.rect.move(amountright,amountdown)
            post=self.am_in_collision(potential_move_rect)#test for collision after move
            #make world round:
            #self.rect.center=(self.rect.center[0]%width,self.rect.center[1]%height)
            stayed_in_world=0<=potential_move_rect.center[0]<=width and 0<=potential_move_rect.center[1]<=height
            if ((not post) or (pre and post)) and stayed_in_world:
                self.rect=self.rect.move(amountright,amountdown)
    def attack(self):
        """ """
        if not self.am_in_collision() and not self.in_action_seq:
            #you can only attack when you're not overlapping
            #go through whole attack sequence
            #print 'attack requested'
            self.action='attack'
            self.in_action_seq=True
            #did attack hit anything?
            first_hit=self.who_was_hit_by_attack()
            #if so, kill charactor
            if first_hit and hasattr(first_hit,'dye'):
                first_hit.dye()
                return first_hit
    def dye(self):
        self.action='tipping over'
        self.in_action_seq=True
    def who_was_hit_by_attack(self):
        ma=self.lunge_foward_by
        direction=self.direction
        if direction=='w':amountright,amountdown=-1*ma,0*ma
        elif direction=='n':amountright,amountdown=0*ma,-1*ma
        elif direction=='e':amountright,amountdown=1*ma,0*ma
        elif direction=='s':amountright,amountdown=0*ma,1*ma
        elif direction=='nw':amountright,amountdown=-1*ma,-1*ma
        elif direction=='ne':amountright,amountdown=1*ma,-1*ma
        elif direction=='sw':amountright,amountdown=-1*ma,1*ma
        elif direction=='se':amountright,amountdown=1*ma,1*ma
        else:
            raise "not a direction"
        me_attacking=self.rect.move(amountright,amountdown)
        return self.who_am_I_colliding_with(me_attacking)
    def pause(self):
        if not self.in_action_seq:
            self.action='paused'
    def who_am_I_colliding_with(self,my_temp_rect=None):
        """Simple collision detector """
        v_shrink_by=.70
        h_shrink_by=.70
        if my_temp_rect:
            smaller_me=my_temp_rect.inflate(-my_temp_rect.width*h_shrink_by,-my_temp_rect.height*v_shrink_by)
        else:
            smaller_me=self.rect.inflate(-self.rect.width*h_shrink_by,-self.rect.height*v_shrink_by)
        all_collidable2=all_collidable.copy()
        all_collidable2.remove(self)
        smaller_all=[sprite.rect.inflate(-sprite.rect.width*h_shrink_by,-sprite.rect.height*v_shrink_by)
            for sprite in all_collidable2]
        collide_list=smaller_me.collidelistall(smaller_all)
        if len(collide_list)>0:
            return all_collidable2.sprites()[collide_list[0]] #return the sprite
        else:
            return None
    def am_in_collision(self,temp_rect=None):
        return bool(self.who_am_I_colliding_with(temp_rect))

class Knight(Charactor):
    """ """
    die_sound=None
    attack_sound_miss=None
    attack_sound_hit_obstacle=None
    attack_sound_hit_dragon=None
    def __init__(self,left,top,image_store):
        move_amount=10
        if not Knight.die_sound:Knight.die_sound=load_sound(os.path.join(curdir,'sounds','knight_die.wav'))
        if not Knight.attack_sound_hit_obstacle:Knight.attack_sound_hit_obstacle=load_sound(os.path.join(curdir,'sounds','knight_attack_hit_obstacle.aif'))
        Charactor.__init__(self,left,top,image_store,move_amount)
    def attack(self):
        #play sound
        if not self.image_lib.portray_death and not self.in_action_seq:
            self.sound_channel.play(Knight.attack_sound_hit_obstacle)
            Charactor.attack(self)
    def dye(self):
        #play sound
        if not self.image_lib.portray_death:
            self.sound_channel.play(Knight.die_sound)
            Charactor.dye(self)

class Dragon(Charactor):
    """ """
    die_sound=None
    attack_sound=None
    if DRAGON_RL_AI:
        reward_factor_for_killing_knight=1
    else:
        reward_factor_for_killing_knight=300
    def __init__(self,left,top,image_store,fire_images_store):
        move_amount=3
        if not Dragon.die_sound:Dragon.die_sound=load_sound(os.path.join(curdir,'sounds','dragon_die.wav'))
        if not Dragon.attack_sound:Dragon.attack_sound=load_sound(os.path.join(curdir,'sounds','dragon_attack.wav'))
        self.fire=Fire(fire_images_store)
        Charactor.__init__(self,left,top,image_store,move_amount)
        self.lunge_foward_by=80
        self.available_actions=[
            self.move_away_from_knight,
            self.move_towards_knight,
            self.attack,
        ]
        if DRAGON_RL_AI:
            self.Brain=Reinforcement_Learning.Brain(discount_rate=.30,available_actions=self.available_actions)
        self.reset()

    #--Added for Reinforcement Learning--

    def get_game_state(self):
        """Keep it simple for now.  A grid might allow more complex behavior. """
        #switch to me_facing_knight
        return [
        round(self.get_knights_distance(),-1),
        self.knight_facing_me(),
        self.me_facing_knight(),
        ]

    def do(self):
        previous_state=self.get_game_state()
        #switch between getting best action or try random action
        random.seed()
        prob_use_best_action=min(game/30,1)
        if random.random()<=prob_use_best_action:
            action=self.Brain.get_best_action(previous_state,self.available_actions)
        else:
            action=random.choice(self.available_actions)
        action()
        new_state=self.get_game_state()
        if self.image_lib.portray_death:
            cost=50
        elif self.I_killed_the_knight:
            cost=-800
        else:
            cost=0 #normally #todo: I want a cost here for timeing out, but default cost for unknown must be equal to this??
        self.Brain.learn(previous_state,action,new_state,cost)

    #------------------------------------

    def reset(self):
        #fitness attr's defaults
        self.time_of_death=TIMELIMITSECONDS*10
        self.I_killed_the_knight=False
        Charactor.reset(self)
    def get_raw_fitness(self):
        if DRAGON_RL_AI:
            return (self.time_of_death+(int(self.I_killed_the_knight)
                *Dragon.reward_factor_for_killing_knight
                *self.time_of_death))
        else:
            return (self.time_of_death+(int(self.I_killed_the_knight)
            *Dragon.reward_factor_for_killing_knight))
    def place_randomly(self):
        #move to a random position and direction:
        random.seed()
        self.rect.center=random.randrange(0,width),random.randrange(0,height)
        self.direction=random.choice(['e','ne','n','nw','w','sw','s','se'])
        i=1
        while self.am_in_collision() and i<30:
            self.rect.center=random.randrange(0,width),random.randrange(0,height)
            self.direction=random.choice(['e','ne','n','nw','w','sw','s','se'])
            i+=1
    def attack(self):
        #play sound
        if not self.image_lib.portray_death and not self.in_action_seq:
            self.sound_channel.play(Dragon.attack_sound)
            self.fire.burn(self.rect,self.direction)
            if Charactor.attack(self)==knight:
                self.I_killed_the_knight=True
    def dye(self):
        #play sound
        if not self.image_lib.portray_death:
            self.time_of_death=count
            self.sound_channel.play(Dragon.die_sound)
            Charactor.dye(self)
    def move_away_from_knight(self):
        #print 'move_away_from_knight'
        self.move(opposite_direction(self.get_direction_of_knight()))
    def move_towards_knight(self):
        self.move(self.get_direction_of_knight())
    def get_knights_distance(self):
        xdist=knight.rect.center[0]-self.rect.center[0]
        ydist=knight.rect.center[1]-self.rect.center[1]
        return euclidean_distance(xdist,ydist)
    def me_facing_knight(self):
        if self.get_direction_of_knight()==self.direction:
            return True
        else:
            return False
    def knight_facing_me(self):
        #get opp dir and compare to knight's dir
        if opposite_direction(self.get_direction_of_knight())==knight.direction:
            return True
        else:
            return False
    def get_direction_of_knight(self):
        #get knight angle from me
        xdist=self.rect.center[0]-knight.rect.center[0]
        ydist=self.rect.center[1]-knight.rect.center[1]
        degrees_me_to_knight=math.degrees(math.atan2(ydist,-xdist))%360
        directions_to_degrees_ranges=[
            ('e',(337.5,360)),
            ('e',(0,22.5)),
            ('ne',(22.5,67.5)),
            ('n',(67.5,112.5)),
            ('nw',(112.5,157.5)),
            ('w',(157.5,202.5)),
            ('sw',(202.5,247.5)),
            ('s',(247.5,292.5)),
            ('se',(292.5,337.5))
            ]
        for item in directions_to_degrees_ranges:
            low,hi=item[1]
            if low<=degrees_me_to_knight<=hi:
                return item[0]
        print degrees_me_to_knight,'not found'
        raise 'Range not found'

class Obstacle(pygame.sprite.Sprite):
    """ """
    def __init__(self,left,top,width,height,image_path):
        pygame.sprite.Sprite.__init__(self) #call Sprite initializer
        self.image = load_image(image_path,-1)
        self.image=pygame.transform.scale(self.image,(width, height))
        self.rect =self.image.get_rect()
        self.rect.center=(left,top)

#---Main Program---

if __name__=='__main__':
    print """
Welcome.
You are the knight.  Kill as many dragons as fast as you can.
The arrow keys move ye.
The space bar swings your sword.
ctrl+c to quit.

    """
    logfile=file('rllog.txt','w')
    global game
    game=0
    pygame.init()
    #sound init
    pygame.mixer.init()
    pygame.mixer.set_num_channels(16)
    free_channels=free_sound_channel() #call as free_channels.next()
    #display init
    pygame.display.set_caption('Dragon Fighter')
    pygame.key.set_repeat(5, 50)
    pygame.mouse.set_visible(1)
    size = width, height = 800,600
    black = 0, 0, 0
    white=255, 255, 255
    lightgreen=102,255,51
    screen = pygame.display.set_mode(size)
    #background = pygame.Surface(size)
    background=load_image(r'background1.jpg')
    screen.blit(background, (0, 0))
    pygame.display.flip()
    #load images
    knight_image_store=load_images(d_knight_image_paths,-1)
    dragon_image_store=load_images(d_dragon_image_paths,-1)
    fire_images_store=load_images(d_fire_image_paths,-1)
    #make charactors
    knight=Knight(200,200,knight_image_store)
    #be the dragon! knight=Dragon(200,200,dragon_image_store)
    dragons=[Dragon(400,300,dragon_image_store,fire_images_store) for i in range(NUMDRAGRONS)]
    dragon_fires=[dragon.fire for dragon in dragons]
    #Initiate dragon behavior programs
    if not DRAGON_RL_AI:
        GP1.generate_initial_programs(dragons)
    #Build some scenery
    bush1=Obstacle(250,400,50,50,os.path.join(curdir,'graphics','reddishbush.bmp'))
    bush2=Obstacle(100,300,50,50,os.path.join(curdir,'graphics','reddishbush.bmp'))
    bush3=Obstacle(500,500,45,45,os.path.join(curdir,'graphics','reddishbush.bmp'))
    hedge1=Obstacle(670,120,43,43,os.path.join(curdir,'graphics','hedge.bmp'))
    hedge2=Obstacle(720,123,50,50,os.path.join(curdir,'graphics','hedge.bmp'))
    hedge3=Obstacle(760,118,46,46,os.path.join(curdir,'graphics','hedge.bmp'))
    deadtree1=Obstacle(180,400,100,100,os.path.join(curdir,'graphics','deadtree.bmp'))
    deadtree2=Obstacle(70,520,110,110,os.path.join(curdir,'graphics','deadtree.bmp'))
    pine1=Obstacle(300,300,90,90,os.path.join(curdir,'graphics','pinetree.bmp'))
    pine2=Obstacle(200,100,80,80,os.path.join(curdir,'graphics','pinetree.bmp'))
    pine3=Obstacle(600,500,100,100,os.path.join(curdir,'graphics','pinetree.bmp'))
    allsprites = pygame.sprite.RenderUpdates(knight,dragons,bush1,bush2,bush3,
        deadtree1,deadtree2,pine1,pine2,pine3,hedge1,hedge2,hedge3,dragon_fires)
    all_collidable=pygame.sprite.Group(knight,dragons,bush1,bush2,bush3,deadtree1,
        deadtree2,pine1,pine2,pine3,hedge1,hedge2,hedge3)
    while 1:
        #place dragons randomly to avoid collisions:
        [dragon.place_randomly() for dragon in dragons]
        count=0.
        while (count<TIMELIMITSECONDS
            and [dragon for dragon in dragons if not dragon.image_lib.portray_death]
            and not knight.image_lib.portray_death):
            count+=.1 #count * 10 is approx 1 second
            pygame.time.delay(60)
            #Get input
            pygame.event.pump()
            keysPressed=pygame.key.get_pressed()
            if keysPressed[K_UP] and keysPressed[K_LEFT]:knight.move('nw')
            elif keysPressed[K_DOWN] and keysPressed[K_LEFT]:knight.move('sw')
            elif keysPressed[K_DOWN] and keysPressed[K_RIGHT]:knight.move('se')
            elif keysPressed[K_UP] and keysPressed[K_RIGHT]:knight.move('ne')
            elif keysPressed[K_UP]:knight.move('n')
            elif keysPressed[K_DOWN]:knight.move('s')
            elif keysPressed[K_RIGHT]:knight.move('e')
            elif keysPressed[K_LEFT]:knight.move('w')
            else:knight.pause()
            if keysPressed[K_SPACE]:knight.attack()
            #Execute all dragons:
            if DRAGON_RL_AI:
                [dragon.do() for dragon in dragons]
            else:
                GP1.exec_programs(dragons)
            #Game updates:
            allsprites.update()
            rectlist=allsprites.draw(screen)
            pygame.display.update(rectlist)
            allsprites.clear(screen, background)
        print 'Game Over - Starting next level ..'
        print count
        game+=1
        if not DRAGON_RL_AI:
            #reproduce dragons, only for Genetic programming
            GP1.reproduce(dragons,TIMELIMITSECONDS)
        else:
            #Useful log info for RL
            import pprint
            logfile.write(pprint.pformat(dragons[0].Brain.Q_Values_Table)+'\n\n')
        pygame.time.delay(3000)
        knight.reset()
        [dragon.reset() for dragon in dragons]
