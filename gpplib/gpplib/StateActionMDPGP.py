from gpplib.GliderFileTools import *
import random
from sets import Set
import gpplib
from gpplib.Utils import *
from gpplib.GenGliderModelUsingRoms import *
from gpplib.StateActionMDP import *
from gpplib.LatLonConversions import *
from gpplib.PseudoWayptGenerator import *
import datetime
import ftplib

class SA_MDP_GP( SA_MDP ):
    ''' Sub-class of SA_MDP dealing with the new type of Risk-map
    '''
    def __init__(self,shelfName='RiskMap3.shelf',sfcst_directory='./',dMax=1.5):
        super(SA_MDP_GP,self).__init__(shelfName,sfcst_directory,dMax)
        self.LastPolicyLoaded = ''
        self.shelfName = shelfName
                
    def GetTransitionModelFromShelf(self,yy,mm,dd,numDays,posNoise=None,shelfDirectory='.'):
        """ Loads up Transition models from the shelf for a given number of days, starting from a particular day, and a given amount of noise in position and/or a given amount of noise in the current predictions. We assume these models have been created earlier using ProduceTransitionModels.
            
            Args:
                * yy (int): year
                * mm (int): month
                * dd (int): day
                * numDays (int): number of days the model is being built over
                * posNoise (float): Amount of std-deviation of the random noise used in picking the start location
                * shelfDirectory (str): Directory in which the Transition models are located.
            
            Updates:
                * self.gm.FinalLocs: Stores the final locations 
        """
        self.posNoise = posNoise; 
        self.currentNoise = 0. 
        #import pdb; pdb.set_trace()
        if posNoise!=None:
                gmShelf = shelve.open('%s/gliderModelGP_%04d%02d%02d_%d_%.3f.shelf'%(shelfDirectory,yy,mm,dd,numDays,posNoise), writeback=False)
        self.gm.TransModel = gmShelf['TransModel']
        #if gmShelf.has_key('FinalLocs'):
        self.gm.FinalLocs = gmShelf['FinalLocs']
        #if gmShelf.has_key('TracksInModel'):
        self.gm.TracksInModel = gmShelf['TracksInModel']
        gmShelf.close()
        # Now that we have loaded the new transition model, we better update our graph.
        self.ReInitializeMDP()
        
    
    def GetIndexedPolicy(self,yy,mm,dd,numDays,goal,**kwargs):
        '''
        Loads the policy corresponding to the goal, date, noise from shelf. 
        (Need to create these before-hand using StoreAllPolicies.py)
        Also need to ensure that all locations in this tour are also the same in StoreAllPolicies.py
        
        Args:
            yy, mm, dd, numDays (int) : Self-explanatory
            goal (tuple) : Goal in graph-coordinates
        
        Kwargs:
            posNoise (float) : How much noise in start position to assume. defaults to 0.01
            romsNoise (float): How much noise in ROMS predictions to assume. defaults to 0.01
            
            --- IMPORTANT ---- Always check to make sure that your risk-map is the right one!
            Policy will have the shelf-name in it, but you've got to be careful in any case.
        '''
        if kwargs.has_key('posNoise'):
            posNoise = kwargs['posNoise']
        else:
            posNoise = 0.01
            
        if kwargs.has_key('curNoise'):
            romsNoise = kwargs['curNoise']
        else:
            romsNoise = 0.01
        
        if kwargs.has_key('theta'):
            theta = kwargs['theta']
        else:
            theta = {'w_r':-1, 'w_g':10.}
            self.theta = theta
        
        if kwargs.has_key('delta'):
            delta = kwargs['delta']
        else:
            delta = 0.00001
            
        if kwargs.has_key('numIters'):
            numIters = kwargs['numIters']
        else:
            numIters = 50
            
        if kwargs.has_key('gamma'):
            gamma = kwargs['gamma']
        else:
            gamma = 1.0
        self.gamma = gamma
        
        if kwargs.has_key('shelfDirectory'):
            shelfDirectory=kwargs['shelfDirectory']
        else:
            shelfDirectory='.'
        
        policyStr = 'Pol_GP_%s_%04d%02d%02d_%d_G_%d_%d_%.3f_WR_%.3f_WG_%.3f'%(self.shelfName,yy,mm,dd,numDays, \
                                                goal[0],goal[1],posNoise,self.theta['w_r'],self.theta['w_g'])
        if self.LastPolicyLoaded != policyStr:
            policyTable = shelve.open('%s/PolicyTableGP_%04d%02d%02d_%d.shelve'%(shelfDirectory,yy,mm,dd,numDays))
            keyForGoalAndNoise = 'G_%d_%d_PN_%.3f_WR_%.3f_WG_%.3f'%(goal[0],goal[1],posNoise,self.theta['w_r'],self.theta['w_g'])
            mdp_key = 'MDP_%s'%(keyForGoalAndNoise);
            if policyTable.has_key(mdp_key):
                print 'Loading policy for %s'%(policyStr)
                if policyTable[mdp_key].has_key('U'):
                        self.mdp['U'] = policyTable[mdp_key]['U']
                if policyTable[mdp_key].has_key('polTree'):
                        self.gm2 = policyTable[mdp_key]['polTree']
                        
                self.LastPolicyLoaded = policyStr
            else:
                print 'Policy not found. Doing Value iteration to find it.'
                self.SetGoalAndRewardsAndInitTerminalStates(goal, theta)
                self.doValueIteration(delta,numIters)
                policyForKey={}
                policyForKey['U'] = self.mdp['U']
                policyForKey['polTree'] = self.gm2
                policyTable[mdp_key] = policyForKey
                self.LastPolicyLoaded = policyStr
            policyTable.close()
            
