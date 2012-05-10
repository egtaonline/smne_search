 #~/local/bin/python2.7

import os, sys, policy
import yaml
import numpy as np
import copy
import commands
import ssh

from argparse import ArgumentParser

_GA = './GameAnalysis'

sys.path.append(_GA)
from RoleSymmetricGame import Game
from RoleSymmetricGame import Profile

from policy import Policy
import RoleSymmetricGame
import GameIO 
import AnalysisScript
import egta_comm

#constants
SSH_URL = "nyx-login.engin.umich.edu"
#rm script
RM_SCRIPT = 'rm_policy' 
COMPLIANCE_THRESHOLD = 0.25

_d = 0.001

_r = 100

def contains(arr,b):
    for a in arr:
        if (a.is_equal(b)):
            return True
    return False

def filter_list(a,b):
    a1 = []
    for policy in a:
        if not contains(b,policy):
            a1.append(policy)
    return a1

def remove_policy_configs(origin_path,removed_policy_names):
    count = 0
    while count < 20:
        try:
            s = ssh.Connection(SSH_URL)
            break
        except:
            count += 1
            print 'ssh error'
        
    for name in removed_policy_names:
        print('COMPL:')
        print('remove policy ' + name + ' from nyx')
        s.execute('rm ' + origin_path + '/' + name)
    s.close()

def write_deviation_list(deviations,out_file,out_file_template,origin_path):
    result = ''
    print('COMPL:')
    print(out_file + '....')
    # Note: we only add profiles, 
    out = open(out_file,'a')
    count = 0
    while count < 20:
        try:
            s = ssh.Connection(SSH_URL)
            break
        except:
            count += 1
            print 'ssh error'
    
    for deviation in deviations:
        out.write(deviation.get_name() + '\n')
        filename = out_file_template.replace('*',deviation.get_name())
        out1 = open(filename,'w')
        out1.write(deviation.write() + '\n')
        result += deviation.get_name() + ' (compliance score: ' + str(deviation.compliance_score()) + ')\n'
        
        out1.close()

        s.put(filename)
        s.execute('mv ' + filename.split('/')[-1] + ' ' + origin_path)
    out.close()
    s.close()
    return result

def lookup_policy_name(dir,policy_name):
    output = commands.getoutput('ls ' + dir + '/ibr/policy.*.cfg').split()

    for filename in output:
        in1 = open(filename,'r')
        name = ''
        for line in in1:
            if (line.find('name') != -1):

                name = line.split()[1].replace(' ','')
                break
        in1.close()
        if name != '' and name == policy_name:
            return filename
    return ''

class MixedProfile:
    def __init__(self,game,profile,regret,best_responses,gains,confirmed = True):
        self.game = game
        self.profile = profile
        self.regret = regret
        self.confirmed = confirmed 
        self.best_responses = best_responses
        self.gains = gains
        
    def is_matched(self,other):
        # first the subgame of self is a subset of other
        # assume that they have the same roles
        for role in self.game.roles:
            if not role in other.game.roles:
                return False
            for strategy in self.game.strategies[role]:
                r_index = self.game.roles.index(role)
                s_index = self.game.strategies[role].index(strategy)

                # allow for profiles of different subgames to be matched
                if not strategy in other.game.strategies[role]: 
                    if self.profile[r_index,s_index] > _d:
                        return False
                    else: 
                        continue

                r_index_1 = other.game.roles.index(role)
                s_index_1 = other.game.strategies[role].index(strategy)
                
                if abs(self.profile[r_index,s_index] - other.profile[r_index_1,s_index_1]) > _d:
                    return False
            
        return True

    def is_semi_matched(self,other):
        for role in self.game.roles:
            if not role in other.game.roles:
                return False
            for strategy in self.game.strategies[role]:
                r_index = self.game.roles.index(role)
                s_index = self.game.strategies[role].index(strategy)

                if not strategy in other.game.strategies[role]: 
                    if self.profile[r_index,s_index] > _d:
                        return False
                    else: 
                        continue                

                r_index_1 = other.game.roles.index(role)
                s_index_1 = other.game.strategies[role].index(strategy)

                if (self.profile[r_index,s_index] > _d and other.profile[r_index_1,s_index_1] < _d):
                    return False

                if (self.profile[r_index,s_index] < _d and other.profile[r_index_1,s_index_1] > _d):
                    return False
        return True
    

def compliance_score(mixed_p, policies, role=None):
    score = 0

    # assume that the profile is mixed 
    if role == None:
        roles = mixed_p.game.roles
    else:
        roles = [role]

    for r in roles:
        for p in mixed_p.game.strategies[r]:
            r_index = mixed_p.game.roles.index(r)
            p_index = mixed_p.game.strategies[r].index(p)

            if mixed_p.profile[r_index,p_index] > 0:
                tmp_policy = ''
                for policy in policies[r]:
                    if policy.name == p:
                        tmp_policy = policy
                        break

                if tmp_policy == '':
                    print 'ERROR: compliance score is undefined'
                else:
                    score += tmp_policy.compliance_score() * mixed_p.profile[r_index,p_index]

    return score / len(roles)

def read_mixed_profile(file,roles, counts, game, regret,confirmed):
    line = file.readline()
    profile = game.zeros()

    for i in range(len(roles)):
        r = line.replace(':','').replace('\n','')

        # assume that roles are sorted
        while True:

            line = file.readline().replace(' ','').replace('\t','').replace('\n','')
            items = line.split(':')

            if 'responses' in line or (reduce(lambda a,b: a or b, [(role == items[0]) for role in roles])):                
                break
            strat = items[0]
            prob = float(items[1].replace('%',''))/100
            profile[game.index(r),game.index(r,strat)] = prob
    

    best_responses = {}
    gains = {}
    # read the best reponses
    for i in range(len(roles)):
        items = file.readline().replace(' ','').replace('\t','').replace('\n','').split(';')
        r = items[0].split(':')[0]
        best_responses[r] = items[0].split(':')[1]
        gains[r] = float(items[1].split('=')[1])

    return MixedProfile(game,profile,regret,best_responses,gains,confirmed)
        

def read_subgame(file,roles,counts, threshold):
    # read the roles
    line = file.readline()
    strategies = {}
    
    for i in range(len(roles)):
        r = line.replace(':','').replace('\n','')
        strategies[r] = []
        while (True):
            line = file.readline()
            if len(line) <= 1 or ':' in line:
                break
            s = line.replace(' ','').replace('\t','').replace('\n','')
            strategies[r].append(s)

    results = list()
    game = Game(roles,counts,strategies,{})
    results.append(game)
    
    line = file.readline()

    if 'Nash' in line:
        num_equi = int(line.split()[0])
        for i in range(num_equi):
            line = file.readline().replace('\n','')
            
            regret = float(line.split()[-1])
            confirmed = True
            if not line.split()[-2] == '=':
                # approximate results
                confirmed = False
            mixed_profile = read_mixed_profile(file, roles, counts, game, regret, confirmed)
            if regret <= threshold:
                results.append(mixed_profile)
    return results

def add_most_current_deviating_policies(list_file, experiment_dir, mem = 5):
    if not os.path.exists(list_file):
        return [[],[],[],[]]
    in1 = open(list_file,'r')
    Cnew = []
    Cexamined = []
    fnew = []
    fexamined = []
    for line in in1:
        line = line.replace('\n','')
        policy_name = line.split()[0]
        if (len(line.split()) > 1):
            f_value = float(line.split()[1])
        else:
            f_value = 0

        addr = lookup_policy_name(experiment_dir,policy_name)
        p = Policy(addr)

        if len(Cnew) >= mem:
            Cexamined.append(p)
            fexamined.append(f_value)
        else:
            Cnew.append(p)
            fnew.append(f_value)

    in1.close()
    return [Cnew,Cexamined,fnew,fexamined]
    
def read_deviating_policies_from_list(list_file, experiment_dir):
    if not os.path.exists(list_file):
        return [[],[]]
    
    in1 = open(list_file,'r')
    Cnew = []
    fnew = []
    for line in in1:
        line = line.replace('\n','')
        policy_name = line.split()[0]
        if len(line.split()) > 1:
            f_value = float(line.split()[1])
        else:
            f_value = 0
                
        addr = lookup_policy_name(experiment_dir,policy_name)
        p = Policy(addr)
        Cnew.append(p)
        fnew.append(f_value)
    in1.close()
    return [Cnew,fnew]

def write_deviating_policies_to_list(list_file,Cnew,fnew):
    out = open(list_file,'w')
    for i in range(len(Cnew)):
        out.write(str(Cnew[i]) + '\t' + str(fnew[i]) + '\n')
    out.close()


def read_equi_profiles(strat_file,threshold=-1):

    in1 = open(strat_file,'r')
    num_equi = 0

    result = list()

    game_profiles = list()
    game_init = False
    subgames = list()
    
    while (True):
        line = in1.readline()

        if 'command: ' in line:
            items = line.split()
            if threshold < 0:
                threshold = _r
                #threshold = float(items[items.index('-r') + 1])

        if 'subgame' in line and ':' in line:
            subgame = read_subgame(in1,roles,counts,threshold)
            subgames.append(subgame)
            

        if not line:
            break
        
        if 'roles:' in line:
            roles = line[0:-1].split(':')[1].replace(' ','').split(',')
        
        if 'players:' in line:            
            counts = {}
            for i in range(len(roles)):
                line = in1.readline()
                items = line[0:-1].split()
                counts[items[1]] = int(items[0].replace('x','').replace(' ',''))
        if 'strategies:' in line and not game_init:
            game_init = True
            strategies = {}
            line = in1.readline()
            for i in range(len(roles)):
                role = line.replace('\n','').replace(':','').replace(' ','')
                strategies[role] = []
                while True:
                    line = in1.readline()
                    if ':' in line or 'payoff' in line:
                        break
                    strategies[role].append(line.replace(' ','').replace('\n',''))

            #assume that we have already read in all the other input data
            
            game = Game(roles, counts, strategies, {})
            result.append(game)

                
    in1.close()
    result.append(subgames)

    return result

def read_subgame_profile_indices(file):
    in1 = open(file,'r')
    result = list()
    status = list()
    for line in in1:
        if len(line) > 1:
            items = line.split('\t')
            i = int(items[0])
            j = int(items[1])
            if len(items) > 2:
                stat = [int(items[2]), int(items[3])]
            else:
                stat = []
                
            result.append([i,j])           
            status.append(stat)
    in1.close()
    return [result,status]

def write_subgame_profile_indices(file,data):
    in1 = open(file,'w')
    d = data[0]
    s = data[1]
    i = 0
    for e in d:
        in1.write(str(e[0]) + '\t' + str(e[1]) + '\t' + str(s[i][0]) + '\t' + str(s[i][1])+  '\n')
        i+= 1
    in1.close()
    
def get_unconfirmed_equi_profile_indices(game_subgameprofiles,unconfirmed_file,minmax):
    unconfirmed_data = read_subgame_profile_indices(unconfirmed_file)

    unconfirmed = []
    status = unconfirmed_data[1]
    for i in range(len(status)):
        if (status[i][minmax] == 0):
            unconfirmed.append(unconfirmed_data[0][i])

    result = list()
    i = 0
    for subgame in game_subgameprofiles[1]:
        j = 0
        new_subgame = list()
        new_subgame.append(subgame)
        
        for mixed_profile in subgame[1:]:

            if ([i,j] in unconfirmed):
                
                result.append([i,j])
            j += 1
        subgame = new_subgame
        i += 1
    return result

def extract(equi_file,output_file):
    game_subgameprofiles = read_equi_profiles(equi_file)
    write_equi_profile_indices(game_subgameprofiles[1],output_file)
    

def write_equi_profile_indices(subgameprofiles,output_file):
    output = open(output_file,'w')
    # since game analysis file is fixed, we only need to keep track of the indices of
    i = 0
    for subgame in subgameprofiles:
        j = 0
        for mixed_profile in subgame[1:]:
            output.write(str(i) + '\t' + str(j) + '\t0\t0\n')
            j += 1            
        i+= 1
    output.close()

def get_mixed_profile_by_index(game_subgameprofiles,i,j):
    return game_subgameprofiles[1][i][1 + j]

def filter(equi_file,unconfirmed_file,experiment_dir,minmax):

    game_subgameprofiles = read_equi_profiles(equi_file)
    tmp = get_unconfirmed_equi_profile_indices(game_subgameprofiles,unconfirmed_file,minmax)
    
    #print(str(tmp))    
    subgames = game_subgameprofiles[1]

    results = {r : [] for r in game_subgameprofiles[0].roles}
    policies = {r : [] for r in game_subgameprofiles[0].roles}

    i = 0

    for subgame in subgames:
        j = 0
        for mixed_p in subgame[1:]:
            if ([i,j] in tmp):
                for r in mixed_p.game.roles:
                    for p in mixed_p.game.strategies[r]:
                        r_index = mixed_p.game.roles.index(r)
                        p_index = mixed_p.game.strategies[r].index(p)

                        if (mixed_p.profile[r_index,p_index] > 0) and (not p in results[r]):
                            
                            results[r].append(p)
                            policy_address = lookup_policy_name(experiment_dir,p)
                            policies[r].append(Policy(policy_address))

            j += 1
        i += 1
    return policies
    
        
def write_deviation_profiles(deviations,out_file,spec_yaml_file):

    # write to yaml file
    stream = open(spec_yaml_file, 'r+')
    
    sim_spec_list = list(yaml.load_all(stream))

    index = 0

    sim_spec_list.append(dict())    

    out = open(out_file.replace('*','list'),'w')
    print('COMPL:')
    print('write deviations to file ' + str(len(deviations)))
    
    for deviation in deviations:        
        # outfile should be deviation.*.yaml, each iteration has a different folder
        file_name = out_file.replace('*',str(index))
        stream = open(file_name,'w')
        #print(deviation.asDict())
        for role,sp in deviation.items():
            s = []
            for strategy,count in sp.items():
                s += [strategy] * count
            sim_spec_list[1][role] = s

        part1 = yaml.dump(sim_spec_list[0]['web parameters'], default_flow_style = False)
        part2 = yaml.dump(sim_spec_list[1], default_flow_style = False)
        stream.write( '---\n')
        stream.write(part2)
        stream.write( '---\n')
        stream.write(part1)
        out.write(file_name + '\n')
        stream.close()
        index += 1                

    out.close()
        

def generate_deviating_policies(C,original_equi_file,unconfirmed_file,minmax,limited=False,Cnew=[],Cexamined=[]):

    print('COMPL:')
    print('generate deviating policies')
    #print([str(p.name) for p in C])    
    # read in profiles,for each profile create a game

    all_game_profiles = read_equi_profiles(original_equi_file)
    unconfirmed = get_unconfirmed_equi_profile_indices(all_game_profiles,unconfirmed_file,minmax)
    subgames = all_game_profiles[1]
    # first pick out the most/least compliant
    min_compliance = 1e10
    max_compliance = -1
    min_index_str = ''
    max_index_str = ''
    i = 0
    for subgame in subgames:
        j = 0
        for profile in subgame[1:]:
            if ([i,j] in unconfirmed):
                score = compliance_score(profile,C)
                print('COMPL: score: ' + str(score) + ' ' )
                if score < min_compliance:
                    min_compliance = score
                    min_profile = profile
                    min_index_str = str(i) + '\t' + str(j)
                if score > max_compliance:
                    max_compliance = score
                    max_profile = profile
                    max_index_str = str(i) + '\t' + str(j)            
            j+=1
        i+=1
    
    index_str = ''
    if minmax == 0:
        target_profile = min_profile
        index_str = min_index_str
    else:
        target_profile = max_profile
        index_str = max_index_str
    
    # pick out the role that has the highest regret
    max_regret = -1.0
    max_role = ''

    print('COMPL: target score ' + str(min_compliance) + ' ' + str(max_compliance))

    for role in all_game_profiles[0].roles:
        score = compliance_score(target_profile,C,role)
        print('COMPL: target role score ' + str(score))
        if (score < COMPLIANCE_THRESHOLD and minmax == 0) or (score > COMPLIANCE_THRESHOLD and minmax == 1):

            if target_profile.gains[role] > max_regret:
                max_regret = target_profile.gains[role]
                max_role = role

    
    if max_role == '':
        print 'NONE OF THE PROFILES SATISFIES THE COMPLIANCE REQUIREMENT'
        return []

    target_policy = ''
    if minmax == 0:
        target_score = 0
    else:
        target_score = 1e10

    if len(Cnew)==0:
        Cnew = C[max_role]
        
    # find the deviation policies        

    results = []
    results.append(target_profile)
    results.append(index_str)
    print(Cnew)

    target_policies = Cnew

    #print(target_policy)
    #print(target_score)
    results.append(max_role)

    print('COMPL: target profile')
    print(target_profile.profile)
    print(target_profile.regret)
    print(target_profile.game.strategies)
    results.append([])

    dev = 0.05
    distance = 1
    while True:
        for target_policy in target_policies:
            candidates = target_policy.generate_deviations(dev * distance)
            # filter out compliant or non compliant
            candidates = filter_list(candidates,C[max_role])
            candidates = filter_list(candidates,Cnew)
            candidates = filter_list(candidates,Cexamined)

            deleted_candidates = []
            for candidate in candidates:
                if ((candidate.compliance_score() < COMPLIANCE_THRESHOLD or candidate.compliance_score() >= 1) and minmax == 0):
                    deleted_candidates.append(candidate)
                if ((candidate.compliance_score() >= COMPLIANCE_THRESHOLD or candidate.compliance_score() <= 0) and minmax == 1):
                    deleted_candidates.append(candidate)
            for deleted in deleted_candidates:
                candidates.remove(deleted)
        if len(candidates) > 0:
            results[-1] += candidates
            break
        elif dev > 20:
            break
        else:
            dev += 1


    print('test')
    for x in results[3]:
        print(x.compliance_score())


    return results


def generate_deviating_profiles(p,index_str,role,new_strategies,original_equi_file,unconfirmed_file,out_file,spec_yaml_file, e_connection, num_samples,minmax):
    # generate deviating profiles
    print('COMPL:')
    print 'generate deviating profiles'

    all_game_profiles = read_equi_profiles(original_equi_file)
    unconfirmed = get_unconfirmed_equi_profile_indices(all_game_profiles,unconfirmed_file,minmax)

    game = all_game_profiles[0]
    subgames = all_game_profiles[1]

    deviations = []

    print('COMPL: mixed strategy profile')
    print(p.profile)
    print(role)    

    for s in new_strategies:
        tmp =  p.game.mixtureNeighbors(p.profile,role,s.name)
        deviations = deviations + list(tmp)

    #write down the index of the original profile

    if True:
        write_deviation_profiles(deviations,out_file,spec_yaml_file)
        out = open(out_file.replace('*','index'),'w')
        out.write(index_str + '\n')
        out.close()
    
        for s in new_strategies:
            print('COMPL: add strategy ')
            print(s.name)
            e_connection.add_strategy_to_simulator(role,s.name)        
    
        for deviation in deviations:
            print('COMPL:')
            print(deviation)
            e_connection.add_profile_to_scheduler(deviation,num_samples)
                

def read_payoff_file(payoff_data_file):
    stream = file(payoff_data_file)
    payoff_data = list(yaml.load_all(stream))

    payoff_dict = payoff_data[0]
    for d in payoff_data[1:]:
        for r,payoff in d.items():
            for policy,value in payoff.items():
                payoff_dict[r][policy] += value

    for r in payoff_dict:
        for policy in payoff_dict[r]:
            payoff_dict[r][policy] = payoff_dict[r][policy] / len(payoff_data)
    return payoff_dict

def get_profile(sim_list):    
    profile = {}
    for role in sim_list[0].keys():
        profile[role] = sim_list[0][role]
    return profile

def test_deviations(deviation_profile_file_template,equi_file,payoff_file,postfix,esp,e_connection,deviation_policy_file):

    target_index_data = read_subgame_profile_indices(deviation_profile_file_template.replace('*','index'))
    target_index = target_index_data[0][0]
    all_game_profiles = read_equi_profiles(equi_file)
    print('COMPL:')
    print(target_index)


    mixed_profile = get_mixed_profile_by_index(all_game_profiles,target_index[0],target_index[1])
    print(mixed_profile.game.strategies)

    # the new file is in data_file + '.new'
    # first refresh the game
    # new strategies
    target_strategies = []
    other_strategies = []
    other_fvalue = []
    in1 = open(deviation_policy_file,'r')
    for line in in1:
        line = line.replace('\n','').replace(' ','').split()
        # only add the current round of new strategies
        if (len(line) <= 1):
            target_strategies.append(line[0])
        else:
            other_strategies.append(line[0])
            other_fvalue.append(float(line[1]))
    
    in1.close()
    target_role = ''
    for role in mixed_profile.game.roles:
        if role in target_strategies[0]:
            target_role = role
            break

    # can't add all the strategies in at the same time since that will overload the game analysis
    results = []
    results_alt = []

    print(target_strategies)

    if True:
        print('COMPL: REFRESH GAME')
        e_connection.refresh_game()
    
        # add support for the mixed_profile
        for role in mixed_profile.game.roles:
            for strategy in mixed_profile.game.strategies[role]:
                r_index = mixed_profile.game.roles.index(role)
                s_index = mixed_profile.game.strategies[role].index(strategy)
                print('COMPL: add strategy to game (' +role + ':' + strategy + ')')
                e_connection.add_strategy_to_game(role,strategy)

        for strategy in target_strategies:
            e_connection.add_strategy_to_game(target_role,strategy)

        # get game
        e_connection.get_game(payoff_file +'.' +postfix)

    # generate game 
    new_game = GameIO.readGame(payoff_file + '.' + postfix)
    print('COMPL:')
    print(new_game.roles)
    print(new_game.strategies)
    print(target_role)
    
    regret_dict = {}
    print('COMPL : compute regret')
    print(mixed_profile.profile)
    new_profile = new_game.zeros()
    
    for role in new_game.roles:
        for strategy in new_game.strategies[role]:
            if strategy in mixed_profile.game.strategies[role]:
                r_index = new_game.roles.index(role)
                s_index_new = new_game.strategies[role].index(strategy)
                s_index_old = mixed_profile.game.strategies[role].index(strategy)

                new_profile[r_index, s_index_new] = mixed_profile.profile[r_index, s_index_old]
    print(new_profile)
    
    for strategy in target_strategies:
        print(strategy)
        regret = new_game.regret(new_profile,target_role,deviation=strategy)
        print(regret)
        regret_dict[strategy] = regret
    
    # sort these regrets so that the largest ones are last
    for i in range(len(target_strategies)):
        for j in range(i+1,len(target_strategies)):
            if regret_dict[target_strategies[i]] < regret_dict[target_strategies[j]]:
                #swap
                x = target_strategies[i]
                target_strategies[i] = target_strategies[j]
                target_strategies[j] = x

    # update these regrets in the deviating profiles
    Cnew = []
    fnew = []
    for strategy in target_strategies:
        regret = regret_dict[strategy]
        Cnew.append(strategy)
        fnew.append(regret)

        print('COMPL: ' + str(strategy) + ' : ' + str(regret))
        if regret > esp:
            if len(results) == 0:
                results.append(1)
                results.append(strategy)
                results.append(target_role)
                results.append(regret)
        else:
            if len(results)==0:                
                results.append(0)
                results.append(target_index)
                results.append(target_role)                
                
            results.append(strategy)

    current_max = max(fnew)
    print(target_strategies)

    print('COMPL: new strategies and fvalues\n')
    print(Cnew)
    print(fnew)

    print('COMPL: other strategies and fvalues \n')
    print(other_strategies)
    print(other_fvalue)

    # add other strategies, update strategy list file now
    Cnew = Cnew + other_strategies
    fnew = fnew + other_fvalue
    all_max = max(fnew)

    print(fnew)
    print('COMPL: max f ' + str(current_max))
    print('COMPL: all max f ' + str(all_max))
    
    if (current_max < all_max):
        # hit local maximum 
        results[0] = -1
        
    print('COMPL: result ' + str(results[0]))

    write_deviating_policies_to_list(deviation_policy_file, Cnew, fnew)

    return results


def update_equi(unconfirmed_equi_file,profile_index,minmax,value):
    
    unconfirmed_equi_indices_data = read_subgame_profile_indices(unconfirmed_equi_file)
    print('COMPL: unconfirmed equi indices')
    print(unconfirmed_equi_indices_data)        
    print('COMPL: profile index')
    print(profile_index)
    i = unconfirmed_equi_indices_data[0].index(profile_index)        
    # 1 is refuted, 2 is confirmed
    unconfirmed_equi_indices_data[1][i][minmax] = value
    write_subgame_profile_indices(unconfirmed_equi_file,unconfirmed_equi_indices_data)    
    
