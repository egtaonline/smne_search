
#!~/local/bin/python2.7

import urllib2, sys, urllib

import json
import os
import smtplib
from email.mime.text import MIMEText

DEBUG = False
NUM_SAMPLES = 15

class EgtaConnection:

    def __init__(self,game_id,generic_scheduler_id,simulator_id ='4f42b6d94a98065c36000001'):
        self.game_id = game_id
        self.generic_scheduler_id = generic_scheduler_id
        
        self.auth_token = 'auth_token=g2LHz1mEtbysFngwLMCz'

        self.a_tok = 'g2LHz1mEtbysFngwLMCz'
        #self.a_tok = '53tqUJ699zxsa9ckWwMz'
        self.url = 'http://d-108-249.eecs.umich.edu'
        self.simulator_id = simulator_id        

    def open_url(self,target,outfile=''):
        #print(target)
        count = 0
        while count < 20:
            try:
                print(target)

                s = urllib2.urlopen(target)
                
                result = s.read()
                s.close()
                if not outfile == '':
                    out = open(outfile,'w')
                    out.write(result)
                    out.close()
                else:
                    return result
                count = 20
            except urllib2.URLError, e:
                print(e)
                count += 1
            
    
    def post_url(self,target,data):
        if DEBUG:
            return 

        count = 0
        while count < 20:
            try:
                req = urllib2.Request(target,urllib.urlencode(data))
                s = urllib2.urlopen(req)
                s.close()
                count = 20
            except urllib2.URLError, e:
                print(e)
                count += 1
            

    def get_game(self,file):
        target = self.url + '/api/v2/games/' + self.game_id + '.json?' + self.auth_token    
        self.open_url(target,file)

    def refresh_game(self):
        tmp_file = 'old_game.json'
        self.get_game(tmp_file)
        in1 = open(tmp_file,'r')
        tmp_data = in1.read()
        in1.close()
        data = json.loads(tmp_data)        
        strategies = {r["name"] : r["strategies"] for r in data["roles"]}
        
        for r,s_list in strategies.items():
            for s in s_list:
                self.remove_strategy_from_game(r,s)

        os.system('rm ' + tmp_file)

    def add_strategy_to_game(self,role,strategy):
        target = self.url + '/api/v2/games/' + self.game_id + '/add_strategy.json' 
        data = {'role': role, 'strategy' : strategy, 'auth_token' : self.a_tok}
        self.post_url(target,data)

    def remove_strategy_from_game(self,role,strategy):
        target = self.url + '/api/v2/games/' + self.game_id + '/remove_strategy.json' 
        data = {'role': role, 'strategy' : strategy, 'auth_token' : self.a_tok}
        self.post_url(target,data)
        

    def add_strategy_to_simulator(self,role, strategy):
        target = self.url + '/api/v2/simulators/' + self.simulator_id + '/add_strategy.json' 
        data = {'role': role, 'strategy' : strategy, 'auth_token' : self.a_tok}
        self.post_url(target,data)
    

    def remove_strategy_from_simulator(self,role,strategy):
        target = self.url + '/api/v2/simulators/' + self.simulator_id + '/remove_strategy.json'
        data = {'role': role, 'strategy' : strategy, 'auth_token' : self.a_tok}
        self.post_url(target,data)

    def add_profile_to_scheduler(self,profile,n_samples=NUM_SAMPLES):
        target = self.url + '/api/v2/generic_schedulers/' + self.generic_scheduler_id + '/add_profile.json'
        data = {'auth_token' : self.a_tok}
        data['sample_count'] = str(n_samples)
        name = ''
        for role,sp in profile.items():
            name = name + role + ':'
            for strategy,count in sp.items():
                name = name + ' ' + str(count) + ' ' + strategy + ','
            name = name[:-1]
            name = name + '; '

        name = name[:-2]        
        print(name)
        data['profile_name'] = name
        print(data)
        self.post_url(target,data)

    def remove_profile_from_scheduler(self, profile_id):
        target = self.url + '/api/v2/generic_schedulers/' + self.generic_scheduler_id + '/remove_profile.json'
        data = {'auth_token' : self.a_tok}
        data['profile_id'] = profile_id;
	self.post_url(target,data)

    def read_profile_from_yaml(self,file,game):
        d = {}
        for role in game.roles:
            d[role] = []
            counts = {}
            for player in range(game.players[role]):
                if sim_spec_list[0][role][player] in counts:
                    counts[sim_spec_list[0][role][player]] += 1
                else:
                    counts[sim_spec_list[0][role][player]] = 1
            for strategy, count in counts.items():
                d[role].append(payoff_data(strategy,count,0.0))
        return d


    def count_profiles(self):
        target = self.url + '/api/v2/generic_schedulers/' + self.generic_scheduler_id + '.json?' + self.auth_token
        tmp_file = 'check_status.json'
        self.open_url(target,tmp_file)
        in1 = open(tmp_file)
        tmp_data = in1.read()
        in1.close()
        data = json.loads(tmp_data)
        samples = data['sample_hash']
        new_samples = 0
        for profile_id, num_samples in samples.items():
            if num_samples['sample_count'] < num_samples['requested_samples']:
                new_samples += 1
        return [len(samples),new_samples]

    def check_sample_count(self,requested):
        target = self.url + '/api/v2/generic_schedulers/' + self.generic_scheduler_id + '.json?' + self.auth_token
        tmp_file = 'check_status.json'
        self.open_url(target,tmp_file)
        in1 = open(tmp_file)
        tmp_data = in1.read()
        in1.close()
        data = json.loads(tmp_data)
        samples = data['sample_hash']
        for profile_id, num_samples in samples.items():
        
            if num_samples['sample_count'] < requested and num_samples['requested_samples'] >= requested:

                return False
        return True
        

    def refresh_scheduler(self):
        target = self.url + '/api/v2/generic_schedulers/' + self.generic_scheduler_id + '.json?' + self.auth_token
        tmp_file = 'check_status.json'
        self.open_url(target,tmp_file)
        in1 = open(tmp_file)
        tmp_data = in1.read()
        in1.close()
        data = json.loads(tmp_data)
        samples = data['sample_hash']
        for profile_id, num_samples in samples.items():
            self.remove_profile_from_scheduler(profile_id)
    

def send_email(content,email_address_list,body=''):
    for email_address in email_address_list:
        if body == '':
            msg = MIMEText(content)
        else:
            msg = MIMEText(body)
        msg['Subject'] = content
        msg['From'] = email_address
        msg['To'] = email_address
        s = smtplib.SMTP('localhost')
        s.sendmail(email_address,[email_address], msg.as_string())
        s.quit()
        
if __name__ == "__main__":
    add_strategy('CLIENTS','test')
    
