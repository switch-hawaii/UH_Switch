"""
This script allows to run all possible scenarios at one time.
The script creates input folder for each scenarion, run that scenario withe the UH-SWITCH model and then store the final results
with graphs.
"""

import os
import pathlib


print("=" *50)
print("=" *50)
print("Run multiple scnearios")
print("=" *50)
print("=" *50)


EM = ["0", "1"]
load = ["00", "10", "20", "30"]
Echarge = ["1", "2", "3"]
Non_Echarge = ["0", "1"]
CampusPV = ["0", "1"]
CampusPPA = ["0", "1"]
Cogen = ["1", "4"]
GreenTariffProj = ["WO1_VRM0", "WO1_VRM1", "WO2_VRM0", "WO2_VRM1"]

#Thes below lines can be used to run a single sceanario 
#EM = ["0"]
#load = ["00"]
#Echarge = ["1"]
#Non_Echarge = ["1"]
#CampusPV = ["1"]
#CampusPPA = ["1"]
#Cogen = ["1"]
#GreenTariffProj = ["WO0_VRM0"]

for var0 in EM:
    for var1 in load:
        for var2 in Echarge:
                for var3 in Non_Echarge:
                    for var4 in CampusPV:
                        for var5 in CampusPPA:
                            for var6 in Cogen:
                                for var7 in GreenTariffProj:
                                    scenario = "EM" + var0 + "_" + var1 + "L" + "_EC" + var2 + "_NEC" + var3 + "_PV" + var4 + "_PPA" + var5 + "_CG" + var6 +"_" + var7
                                    print(scenario)
#                                    file = pathlib.Path(scenario)
#                                    if file.exists ():
#                                        print ("Scenario exist")
#                                    else:
#                                        print ("Scenario not exist")

                                    try:
                                        #this script includes energy transition plan (EM0 and EM1)
                                        os.system('python create_input_folder.py {}'.format(scenario))
                                        os.system('switch solve --inputs-dir inputs_{} --outputs-dir {} '.format(scenario, scenario))
                                        os.system('python prepare_final_results.py {}'.format(scenario))
                                        os.system('python compute_NPV.py {}'.format(scenario))
        #                                    break

                                    except:
                                        print("OOps! There is an error")
        #                                except OSError:
        #                                    os.system('say "there is an error"')
        #                                else:
        #                                    os.system('say "the process is done"')


#create a input folder
#try:
    #scenario = "00L_EC1_NEC1_PV1_PPA1_CG0_PPA_Varcost"
    #scenario = "00L_EC1_NEC1_PV1_PPA1_CG0_test_WO_Varcost_1"
#    scenario = "00L_EC2_NEC1_PV1_PPA1_CG0_WO3"
#    os.system('python create_input_folder.py {}'.format(scenario))
#    os.system('switch solve --inputs-dir inputs_{} --outputs-dir {} '.format(scenario, scenario))
#    os.system('python prepare_final_results.py {}'.format(scenario))
#except OSError:
#    os.system('say "there is an error"')
#else:
#    os.system('say "the process is done"')

#scenario = "00L_EC1_NEC1_PV1_PPA1_CG0_PPA_Varcost_1"
