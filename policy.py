#!/usr/bin/env python 

import os, sys, copy

class Policy:
    def __init__(self, policy_file):

        in1 = open(policy_file,'r')
        eps = 1e-6

        # determine the type first

        while True:
            line = in1.readline()
            if len(line) == 0:
                break
            if (line.find('APrioriInitialReputation') != -1 or line.find('INITIAL_APRIORI') != -1):
                self.initial_reputation = float(line.split()[1])
                # determine the type
                if (line.find('APrioriInitialReputation') != -1):
                    self.type = 0
                else:
                    self.type = 1

            if (line.find('closeConnectionThreshold') != -1 or line.find('CONNECTION_THRESHOLD') != -1):
                self.connection_threshold = float(line.split()[1])
                
            if (line.find('introductionThreshold') != -1 or line.find('INTRODUCTION_THRESHOLD') != -1):
                self.introduction_threshold = float(line.split()[1])
            if (line.find('goodSubjectIncrementValue') != -1 or line.find('GOOD_BEHAVIOR_INCREMENT') != -1):
                self.good_message = float(line.split()[1])
            if (line.find('badSubjectDecrementValue') != -1 or line.find('BAD_BEHAVIOR_DECREMENT') != -1):
                self.bad_message = float(line.split()[1])
            if (line.find('goodIntroducerIncrementValue') != -1 or line.find('GOOD_INTRODUCER_INCREMENT') != -1):
                self.good_intro = float(line.split()[1])
            if (line.find('badIntroducerDecrementValue') != -1 or line.find('BAD_INTRODUCER_DECREMENT') != -1):
                self.bad_intro = float(line.split()[1])

            if (line.find('feedbackDistanceFactor') != -1 or line.find('DISTANCE_FACTOR') != -1):
                self.distance_factor = float(line.split()[1])

            if (line.find('projectedReputation') != -1 or line.find('INTRODUCTION_PROJECTION') != -1):
                self.projected = float(line.split()[1])

            if (line.find('name') != -1):
                self.name = line.split()[1]

            # type 0 parameters only
            if (line.find('reputationSlope') != -1):
                self.slope = float(line.split()[1])

            if (line.find('introducerPositiveFeedbackIncrement') != -1):
                self.good_intro_feedback = float(line.split()[1])
            if (line.find('introducerNegativeFeedbackDecrement') != -1):
                self.bad_intro_feedback = float(line.split()[1])
            if (line.find('subjectPositiveFeedbackIncrement') != -1):
                self.good_subject_feedback = float(line.split()[1])
            if (line.find('subjectNegativeFeedbackDecrement') != -1):
                self.bad_subject_feedback = float(line.split()[1])

            if (line.find('closeAPrioriConnectionThreshold') != -1):
                self.apriori_threshold= float(line.split()[1])
            if (line.find('reputationThreshold') != -1):
                self.reputation_threshold= float(line.split()[1])


            # type 1 parameters only
            if (line.find('TIME_TO_REMEMBER') != -1):
                self.time_remeber = float(line.split()[1])                                

            
        in1.close()

    def __str__(self):
        x = 'Policy ' + self.name + '\n'
        x = x + str(self.good_message) + ' . ' + str(self.bad_message) + '\n'
        x = x + str(self.good_intro) + ' . ' + str(self.bad_intro)    + '\n'
        x = x + str(self.initial_reputation) + '\n'
        x = x + str(self.connection_threshold) + ' . ' + str(self.introduction_threshold) + '\n'
        return x
        

    def is_equal(self,other,esp=1e-10):
        equality = (abs(self.connection_threshold - other.connection_threshold) < esp)
        equality = equality and (abs(self.initial_reputation - other.initial_reputation) < esp)
        equality = equality and (abs(self.good_message - other.good_message) < esp)
        equality = equality and (abs(self.bad_message - other.bad_message) < esp)
        equality = equality and (abs(self.good_intro - other.good_intro) < esp)
        equality = equality and (abs(self.bad_intro - other.bad_intro) < esp)

        # optional?
        equality = equality and (abs(self.projected - other.projected) < esp)
        equality = equality and (abs(self.distance_factor - other.distance_factor) < esp)

        return equality
    
    def write(self):
        # return a string
        result = ''
        if (self.type == 1):
            result += 'policy.class: trustedrouting.sim.AttenuatedFeedbackPolicy\n'
            result = result + 'PROPERTY_BAD_BEHAVIOR_DECREMENT: ' +  str(self.bad_message) + '\nPROPERTY_BAD_INTRODUCER_DECREMENT: ' + str(self.bad_intro) + '\nPROPERTY_CONNECTION_THRESHOLD: ' + str(self.connection_threshold) + '\nPROPERTY_DISTANCE_FACTOR: ' + str(self.distance_factor) + '\nPROPERTY_GOOD_BEHAVIOR_INCREMENT: ' + str(self.good_message) + '\nPROPERTY_GOOD_INTRODUCER_INCREMENT: ' + str(self.good_intro) + '\nPROPERTY_INITIAL_APRIORI_REPUTATION: ' + str(self.initial_reputation) + '\nPROPERTY_INTRODUCTION_PROJECTION: ' + str(self.projected) + '\nPROPERTY_INTRODUCTION_THRESHOLD: ' + str(self.introduction_threshold)
            if (hasattr(self,'time_remember')):
                result = result + '\nPROPERTY_TIME_TO_REMEMBER: ' + str(self.time_remember)
            result = result + '\nPROPERTY_name: ' + self.name + '\n'
        else:
            result += 'policy.class: trustedrouting.sim.ConfigurablePolicy3\n'
            result = result + 'PROPERTY_closeAPrioriConnectionThreshold: ' + str(self.apriori_threshold) + '\nPROPERTY_goodSubjectIncrementValue: ' + str(self.good_message) + '\nPROPERTY_reputationThreshold: ' + str(self.reputation_threshold) + '\nPROPERTY_feedbackDistanceFactor: ' + str(self.distance_factor) + '\nPROPERTY_closeConnectionThreshold: ' + str(self.connection_threshold) + '\nPROPERTY_introducerPositiveFeedbackIncrement: ' + str(self.good_intro_feedback) + '\nPROPERTY_projectedReputation: ' + str(self.projected) + '\nPROPERTY_reputationSlope: ' + str(self.slope) + '\nPROPERTY_badSubjectDecrementValue: ' + str(self.bad_message) + '\nPROPERTY_APrioriInitialReputation: ' + str(self.initial_reputation) + '\nPROPERTY_subjectNegativeFeedbackDecrement: ' + str(self.bad_subject_feedback) + '\nPROPERTY_badIntroducerDecrementValue: ' + str(self.bad_intro) + '\nPROPERTY_subjectPositiveFeedbackIncrement: ' + str(self.good_subject_feedback) + '\nPROPERTY_goodIntroducerIncrementValue: ' + str(self.good_intro) + '\nPROPERTY_introductionThreshold: ' + str(self.introduction_threshold) + '\nPROPERTY_introducerNegativeFeedbackDecrement: ' + str(self.bad_intro_feedback) + '\nPROPERTY_name: ' + self.name + '\n'
        return result


    def valid(self):
        result = self.inbound(self.connection_threshold) and self.inbound(self.introduction_threshold) and self.inbound(self.initial_reputation)

        result = result and self.inbound(self.good_intro) and (self.good_intro >= 0) and self.inbound(self.good_message) and (self.good_message >=0)
        result = result and self.inbound(self.bad_intro) and (self.bad_intro >= 0) and self.inbound(self.bad_message) and (self.bad_message >= 0)

        return result

    def inbound(self,reputation):
        return (reputation >= -2.0 and reputation <= 2.0)

    def generate_deviations(self,dev=0.01):
        result = []
        
        # generate deviations that are one parameter different from the original one

        temp = copy.deepcopy(self)
        temp.connection_threshold += dev

        if (temp.valid()):
            result.append(temp)
        temp = copy.deepcopy(self)
        temp.connection_threshold -= dev
        if (temp.valid()):
            result.append(temp)
        temp = copy.deepcopy(self)
        temp.introduction_threshold += dev
        if (temp.valid()):
            result.append(temp)
        temp = copy.deepcopy(self)
        temp.introduction_threshold -= dev 
        if (temp.valid()):
            result.append(temp)
        temp = copy.deepcopy(self)
        temp.initial_reputation -= dev
        if (temp.valid()):
            result.append(temp)
        temp = copy.deepcopy(self)
        temp.initial_reputation += dev
        if (temp.valid()):
            result.append(temp)
        temp = copy.deepcopy(self)
        temp.good_message -= dev
        if (temp.valid()):
            result.append(temp)
        temp = copy.deepcopy(self)
        temp.good_message += dev
        if (temp.valid()):
            result.append(temp)
        temp = copy.deepcopy(self)
        temp.bad_message -= dev
        if (temp.valid()):
            result.append(temp)
        temp = copy.deepcopy(self)
        temp.bad_message += dev
        if (temp.valid()):
            result.append(temp)
        temp = copy.deepcopy(self)
        temp.good_intro -= dev
        if (temp.valid()):
            result.append(temp)
        temp = copy.deepcopy(self)
        temp.good_intro += dev
        if (temp.valid()):
            result.append(temp)
        temp = copy.deepcopy(self)
        temp.bad_intro -= dev
        if (temp.valid()):
            result.append(temp)
        temp = copy.deepcopy(self)
        temp.bad_intro += dev
        if (temp.valid()):
            result.append(temp)
        
        return result

    def get_name(self):
        return self.name

    def set_name(self,name):
        self.name = name

    def compliance_score(self):

        message_distance = self.initial_reputation - self.connection_threshold
        intro_distance = self.initial_reputation -self.introduction_threshold
        recovery_distance = self.introduction_threshold - self.connection_threshold 

        if (self.bad_message == 0):
            d = 1e10
        else:
            d = self.good_message / self.bad_message

        if (self.bad_intro == 0):
            e = 1e10
        else:
            e = self.good_intro / self.bad_intro            

        if (message_distance != 0):
            # scale = intro_distance / message_distance
            # for now, we assume scale = 1
            scale = 1
        else:
            scale = 1
        
        #d = (message_distance / self.bad_message) / (max(recovery_distance,self.bad_message) / self.good_message)
        #e = (intro_distance / self.bad_intro) / (self.bad_intro / self.good_intro)

            
        return min((d * e) * scale,1)
    

if __name__ == '__main__':
    policy_file = sys.argv[1]
    policy = Policy(policy_file)
    print('Policy score for ' + policy_file) 
    print(policy.compliance_score())


        
        
