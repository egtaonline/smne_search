#~/local/bin/python2.7

import os, sys
from policy import Policy 
import time
import commands

import egta_comm
import equilibrium_evaluator

# constants for game analysis script
# adjust accordingly
_GA = equilibrium_evaluator._GA
_R = equilibrium_evaluator._r
_D = equilibrium_evaluator._d

# change this to where the game analysis script is stored
sys.path.append(_GA)

import RoleSymmetricGame
from AnalysisScript import *


NUM_SAMPLES = 15
# num of samples that need to be collected to improve confidence in the resulting SMNEs
ADDITIONAL_NUM_SAMPLES = 30

# receive updates about the process' status
EMAIL_ADDRESSES = ['qduong@umich.edu','wellman@umich.edu']

GENERIC_SCHEDULER_ID = '4f708e4a4a980603a7000004'
GAME_ID = '4fa932464a9806623c000001'
SIMULATOR_ID = '4f42b6d94a98065c36000001'

def schedule_deviations(mixed_profile,num_samples,subgame,game,e_connection,deviations):
    # construct the set of strategies to extend to 
    for role in game.roles:
        new_strategies = list(set(game.strategies[role]) - set(subgame.strategies[role]))
        for new_strategy in new_strategies:
            tmp = mixed_profile.game.mixtureNeighbors(mixed_profile.profile,role,new_strategy)
            for deviation in tmp:
                if not deviation in deviations:
                    e_connection.add_profile_to_scheduler(deviation,num_samples)
                    deviations.append(deviation)
    return deviations

def schedule_support_profiles(mixed_profile,num_samples,e_connection):
    profiles = mixed_profile.game.feasibleProfiles(mixed_profile.profile)
    for p in profiles:
        e_connection.add_profile_to_scheduler(p,num_samples)
    return profiles

def schedule_subgame(subgame,best_responses,num_samples):
    for role in subgame.roles:
        if not best_responses[role] in subgame.strategies[role]:
            subgame.strategies[role].append(best_responses[role])
    template = subgame.zeros()
    threshold = 0.005
    for role in subgame.roles:
        for strategy in subgame.strategies[role]:
            i = subgame.roles.index(role)
            j = subgame.strategies[role].index(strategy)
            template[i,j] = threshold * 2

    profiles = subgame.feasibleProfiles(template,threshold)
    for p in profiles:
        print('EGTA:' + str(p))
        e_connection.add_profile_to_scheduler(p,num_samples)

mode = sys.argv[1]
game_data_file = sys.argv[2]
equi_file = sys.argv[3]
out_file = sys.argv[4]
e_connection = egta_comm.EgtaConnection(GAME_ID,GENERIC_SCHEDULER_ID,SIMULATOR_ID)

if mode == '1' or mode == '1a':
    # get new game data
    print 'EGTA:Mode 1'
    if mode == '1':
        print 'EGTA:Download game file'
        e_connection.get_game(game_data_file)
    
        # run game analysis
        print 'EGTA:Run game analysis'
        os.system("python2.7 " + _GA + "/AnalysisScript.py -r " + str(_R) + " -d " + str(_D) + "  "  + game_data_file + " > " + equi_file)

    continued = True
    game_subgameprofiles = equilibrium_evaluator.read_equi_profiles(equi_file)

    num_scheduled = 0
    num_unconfirmed = 0
    num_smne = 0
    num_sg = 0
    confirmed_profiles = []
    scheduled = []
    unconfirmed_mixed_NE = 'Unconfirmed SMNE: '

    for subgameprofile in game_subgameprofiles[1]:
        num_sg += 1
        for mixed_profile in subgameprofile[1:]:
            num_smne += 1
            if not mixed_profile.confirmed:
                print('EGTA: unconfirmed ')
                print(mixed_profile.profile)
                print(mixed_profile.game.strategies)
                print(mixed_profile.best_responses)
                print(mixed_profile.regret)
                
                str_n_prof = ''
                role_count = 0
                for role, stgy in mixed_profile.game.strategies.items():
                    str_n_prof = str_n_prof + str(role) + ":" + str(stgy) +", "+ str(mixed_profile.profile[role_count]) + '\n'
                    role_count +=1
                str_n_prof = str_n_prof[:-1]

                unconfirmed_mixed_NE = unconfirmed_mixed_NE + '\n\n' + 'Strategies and Profiles: \n'+ str_n_prof+ '\n' + 'Best Responses: \n'+str(mixed_profile.best_responses) + '\n' + 'Regret: ' +str(mixed_profile.regret)

                continued = False
                num_unconfirmed += 1
                scheduled = schedule_deviations(mixed_profile,NUM_SAMPLES,subgameprofile[0],game_subgameprofiles[0],e_connection,scheduled)
                
            else:
                confirmed_profiles.append(mixed_profile)
    num_new = e_connection.count_profiles()
    print('EGTA: new samples' + str(num_new))
    num_scheduled = num_new[1]
    print('EGTA:  number of new profiles ' + str(num_scheduled))

    if continued:
        
        if len(confirmed_profiles) > 0:
            body = 'regret values of all confirmed profile: '
            print 'EGTA:improve confidence'

            for profile in confirmed_profiles:
                scheduled = schedule_support_profiles(profile,NUM_SAMPLES + ADDITIONAL_NUM_SAMPLES,e_connection)
                body = body + str(profile.regret) + '\n'

            confident = e_connection.check_sample_count(NUM_SAMPLES + ADDITIONAL_NUM_SAMPLES)
            print 'EGTA:check sample counts ' 
            print('EGTA:' + str(confident))
            if confident:
                os.system('cp ' + equi_file + ' ' + out_file)
                # return the confirmed equilibria
                egta_comm.send_email('mode 3: finished egta', EMAIL_ADDRESSES,body)                
                
            else:
                num_new = e_connection.count_profiles()
                print('EGTA: new samples' + str(num_new))
                num_scheduled = num_new[1]
                print('EGTA:  number of new profiles ' + str(num_scheduled))
                # move to mode 2
                egta_comm.send_email('mode 2a: collecting additional ' + str(num_scheduled) + ' profiles  to improve confidence in existing ' + str(len(confirmed_profiles)) + ' SMNEs', EMAIL_ADDRESSES,body)     
                os.system('nohup nice python2.7 smne_search.py 2a ' + sys.argv[2] + ' ' + sys.argv[3]  + ' ' + sys.argv[4] + '  0  &')
        else:
            # pick out the one with highest regret
            # extend the subgame 
            max_regret = 0
            s_index = 0
            p_index = 0
            i = 0
            for subgameprofile in game_subgameprofiles[1]:
                j = 0
                for profile in subgameprofile[1:]:
                    if profile.regret > max_regret:
                        max_regret = profile.regret
                        s_index = i
                        p_index = j
                    j+= 1
                i+=1
            schedule_subgame(game_subgameprofiles[1][s_index][0], game_subgameprofiles[1][s_index][p_index + 1].best_responses,NUM_SAMPLES)
            
            highest_regret_profile = game_subgameprofiles[1][s_index][p_index + 1]
            highest_regret = highest_regret_profile.regret
            best_response = highest_regret_profile.best_responses
            
            name = ''
            for role,sp in best_response.items():
                name = name + role + ': ' + sp + '\n'

            name = name[:-1]
     
            body = 'highest regret value: '+ str(highest_regret) + '\n\nhighest regret SMNE profile\n' + name

            egta_comm.send_email('mode 2b: extending subgame of the highest regret SMNE', EMAIL_ADDRESSES, body)                               
            os.system('nohup nice python2.7 smne_search.py 2 ' + sys.argv[2] + ' ' + sys.argv[3]  + ' ' + sys.argv[4] + '  0  &')
    else:
        # move to state 2
        egta_comm.send_email('mode 2: collecting ' + str(num_scheduled) + '  missing profiles (' + str(num_unconfirmed) + ' unconfirmed SMNEs)', EMAIL_ADDRESSES,'number of subgames: ' + str(num_sg) + '\nnumber of SMNEs: ' + str(num_smne) + '\nnumber of unconfirmed SMNEs: ' + str(num_unconfirmed) + '\nnumber of scheduled profiles: ' + str(num_scheduled)+'\n' + unconfirmed_mixed_NE)                               
        os.system('nohup nice python2.7 smne_search.py 2 ' + sys.argv[2] + ' ' + sys.argv[3]  + ' ' + sys.argv[4] + '  0  &')

elif mode == '2' or mode == '2a':
    print 'EGTA:Mode 2'
    #egta_comm.send_email('test',['qduong@umich.edu'])
    hours = int(sys.argv[5])
    hours += 1
    # test if done 
    requested = NUM_SAMPLES
    if mode == '2a':
        requested += ADDITIONAL_NUM_SAMPLES
        
    print('EGTA: check sample count ' + str(e_connection.check_sample_count(requested)))

    if e_connection.check_sample_count(requested):
        # move back to 1, outside of the loop
        egta_comm.send_email('finished collecting data (one inner loop), back to the beginning ', EMAIL_ADDRESSES)
        os.system('nohup nice python2.7 smne_search.py 1 ' + sys.argv[2] + ' ' + sys.argv[3]  + ' ' + sys.argv[4] + ' &')
    else:
        if hours > 24 * 2:
            egta_comm.send_email('time_exceeded in stage 2/2a/2b', EMAIL_ADDRESSES)
        else:
            time.sleep(1800)
            os.system('nohup nice python2.7 smne_search.py ' + mode + ' ' + sys.argv[2] + ' ' + sys.argv[3]  + ' ' + sys.argv[4] + ' ' + str(hours) + ' &')




        
        
    

