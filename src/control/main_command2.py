import socket
import pandas as pd
import threading
import time
import AnalysisOptimizeSELF as AnalyOpti
#import A1 as AnalyOpti

#  Command List
#  Connection test: S
#  " 1 - Test whether the server can be connected (TEST)
#  Towing carriage:
#  " 1 - Set speed (SET_SPEED:)
#  " 2 - Set acceleration (SET_ACC:)
#  " 3 - Set deceleration (SET_DEC:)
#  " 4 - Initialize (INIT)
#  " 5 - Reset (RESET)
#  " 6 - Position zeroing (SETZERO)
#  " 7 - Enable servo (ENABLE_SERVO)
#  " 8 - Disable servo (DISABLE_SERVO)
#  " 9 - Forward motion (MOVE_POS)
#  "10 - Reverse motion (MOVE_NEG)
#  " 0 - Stop motion (STOP)
#  Camera:
#  "1 - Modify recording duration (CHANGETIME:)
#  "2 - Start and auto stop (AUTO:)
#  "3 - Start recording (STRATPHOTO:)
#  "4 - Stop recording (STOPPHOTO:)



# =================== Sender Program ===================
def send_command(ip, port, command):
    try:
        # Create a TCP/IP socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock: # auto destroy after use
            # Connect to the server
            sock.connect((ip, port))
            print("connect to server {}:".format(ip))

            # Send data
            sock.sendall(command.encode('ascii'))
            print(f"{command}")
    except Exception as e:
        print(f"find error when sending command: {e}")


# =================== Receiver Program (Status Feedback) ============================
stopMoving_event = threading.Event()
stopRecoding_event = threading.Event()
stopControl_event = threading.Event()
Maxposition = 1


def start_server(tuoche, shexiang, forceback, host="0.0.0.0", port=55001):
    stopMoving_event.clear()
    stopRecoding_event.clear()
    stopControl_event.clear()
    try:
        sever_socket = socket.socket(socket.AF_INET)
        sever_socket.bind((host, port))
        sever_socket.listen(5)
        print(f"Listening port {port}:")
        while not (stopMoving_event.is_set() and stopRecoding_event.is_set() and stopControl_event.is_set()):
        #while not (stopMoving_event.is_set() and stopControl_event.is_set()):
            print(f"Towing finished:{stopMoving_event.is_set()}")
            print(f"Recording finished:{stopRecoding_event.is_set()}")
            print(f"Feedback finished:{stopControl_event.is_set()}")
            sever_socket.settimeout(5)
            try:
                client_socket, client_address = sever_socket.accept()
                print(f"connected by client {client_address[0]}")
                message = client_socket.recv(1024).decode("utf-8")
                print(f"{message}")
                process_command(message, tuoche, shexiang, forceback)
                client_socket.close()
            except socket.timeout:
                continue
        print("LISTNER CLOSED")
    except Exception as e:
        print(f"Error occurred: {e}")
        sever_socket.close()


def process_command(message, tuoche, shexiang, forceback):
    if ":" in message:
        action, name = message.split(":", 1)
    else:
        action, name = message, None
    if action.startswith("FINISHPHOTO"):
        setattr(shexiang, "Photostatus", False)
        stopRecoding_event.set()
    elif action.startswith("FINISHMOVE"):
        setattr(tuoche, "Movestatus", False)
        setattr(tuoche, "Position", float(name))
        stopMoving_event.set()
    elif action.startswith("FINISHCONTROL"):
        setattr(forceback, "Movestatus", False)
        stopControl_event.set()

# =================== Initial Experiment Table Generation ==============
def Creatinput0(stepn,filenametxt,filenamecsv):
    my_package=AnalyOpti.initialize()
    my_package.Step0_Total_program(stepn,filenametxt,filenamecsv,'','')
    my_package.terminate()


# =================== Towing Carriage Parameters and Control ================
class tuoche():
    ip = ""
    port = ""
    Initstatus = False
    Enablestatus = False
    Movestatus = False
    Position = 0  ## initial position is 0
    Movespeed = 0
    Moveacc = 0
    Mocedec = 0
    totalDistance = 1  # towing travel distance
    Movedirection = 0  # 1 means forward (----->), 0 means backward (<-----). Initially set to the opposite because the main program will automatically toggle it.
    def changedistance(self,distance):
        send_command(self.ip, self.port, "DISTANCE:{}".format(distance))
        self.totalDistance=distance

    def initial(self):
        send_command(self.ip, self.port, "INIT")
        send_command(self.ip, self.port, "RESET")
        send_command(self.ip, self.port, "SETZERO")
        self.Initstatus = True

    def Setzero(self):
        send_command(self.ip, self.port, "SETZERO")
        self.Position = 0

    def Enable(self):
        if self.Initstatus:
            send_command(self.ip, self.port, "ENABLE_SERVO")
            self.Enablestatus = True

    def Disable(self):
        if self.Enablestatus:
            send_command(self.ip, self.port, "DISABLE_SERVO")
            self.Enablestatus = False

    def Move(self, vel, acc=0.2, dec=0.2):
        absvel = abs(vel)
        direction = "NEG" if self.Movedirection == 0 else "POS"
        if self.Enablestatus and self.Position == 0:
            send_command(self.ip, self.port, "SET_SPEED:{}".format(absvel))
            self.Movespeed = abs
            send_command(self.ip, self.port, "SET_ACC:{}".format(acc))
            self.Moveacc = acc
            send_command(self.ip, self.port, "SET_DEC:{}".format(dec))
            self.Mocedec = dec
            send_command(self.ip, self.port, "MOVE_{}".format(direction))
            self.Movestatus = True
        else:
            print("cannot move")
            raise KeyError

    def Stop(self):
        send_command(self.ip, self.port, "STOP")
        self.Movestatus = False
        send_command(self.ip, self.port, "DISABLE_SERVO")
        self.Enablestatus = False


# =================== Camera Parameters and Control ================
class shexiang():
    ip = ""
    port = ""
    Photostatus = False

    def Auto(self, time, name):
        send_command(self.ip, self.port, "CHANGETIME:{}".format(time))
        send_command(self.ip, self.port, "AUTOPHOTO:{}".format(name))
        self.Photostatus = True

    def Start(self, name):
        send_command(self.ip, self.port, "STRATPHOTO:{}".format(name))
        self.Photostatus = True

    def Stop(self, name=" "):
        send_command(self.ip, self.port, "STOPPHOTO:{}".format(name))
        self.Photostatus = False

    def Changetime(self, time):
        send_command(self.ip, self.port, "CHANGETIME:{}".format(time))


# =================== Self-Excited Oscillation Program ==================
class forceback():
    ip = ""
    port = ""
    name = ""
    Enablestatus = False
    Movestatus = False
    Position = 0  # initial position is 0
    mass = 0
    dampingratio = 0
    stiffnessCF = 0
    stiffnessIL = 0
    realmass = 0
    vr = 0
    addzeta = 0

    def Enable(self, name, mass, dampingratio, stiffnessCF, stiffnessIL, realmass,vr, addzeta, runtime):
        send_command(self.ip, self.port, "SET_NAME:{}".format(name))
        self.name = name
        send_command(self.ip, self.port, "SET_VM:{}".format(mass))
        self.mass = mass
        send_command(self.ip, self.port, "SET_DRATIO:{}".format(dampingratio))
        self.dampingratio = dampingratio
        send_command(self.ip, self.port, "SET_VSCF:{}".format(stiffnessCF))
        self.stiffnessCF = stiffnessCF
        send_command(self.ip, self.port, "SET_VSIL:{}".format(stiffnessIL))
        self.stiffnessIL = dampingratio
        send_command(self.ip, self.port, "SET_RM:{}".format(realmass))
        self.realmass = realmass
        send_command(self.ip, self.port, "SET_Vr:{}".format(vr))
        self.vr = vr
        send_command(self.ip, self.port, "SET_AddZeta:{}".format(addzeta))
        self.addzeta = addzeta
        send_command(self.ip, self.port, "SET_RUNTIME:{}".format(runtime))
        self.runtime = runtime
        #send_command(self.ip, self.port, "SET_STORE:{}".format(filenamestore))
        #elf.filenamestore = filenamestore
        send_command(self.ip, self.port, "ENABLE_CONTROL")
        self.Enablestatus = True

    def Disable(self):
        if self.Enablestatus:
            send_command(self.ip, self.port, "DISABLE_CONTROL")
            self.Enablestatus = False

    def Move(self):
        if self.Enablestatus:
            send_command(self.ip, self.port, "MOVE")
            self.Movestatus = True
        else:
            print("cannot move")
            raise KeyError

def writetxt(data,filename):
    with open(filename,'w') as file:
        for keys,values in data.items():
            file.write(f"{keys} {values}\n")

# =================== Result Analysis / Processing / Optimization Program ===================
def DealCreatCoe(stepn,filenametxt,filenamecsv,filenamestorematlab):
    # eng = matlab.engine.start_matlab()
    # result = matlab.batch_function(datafilename)
    # eng.quit()
    # return result
    my_package=AnalyOpti.initialize()
    my_package.Step0_Total_program(stepn,filenametxt,filenamecsv,filenamestorematlab,'')
    my_package.terminate()

def GPRpre(stepn,filenametxt,filenamecsv,file_pretxt1):
    my_package=AnalyOpti.initialize()
    my_package.Step0_Total_program(stepn,filenametxt,filenamecsv,'',file_pretxt1)
    my_package.terminate()

def JudgeNext(stepn,filenametxt,filenamecsv):
    my_package=AnalyOpti.initialize()
    stopYoN=my_package.Step0_Total_program(stepn,filenametxt,filenamecsv,'','')
    my_package.terminate()
    return stopYoN

# =================== Modify Condition Table Parameter File ===================
def changedata(conditionlist, num, listname, listdata):
    for index, namei in enumerate(listname):
        conditionlist.loc[num, namei] = listdata[index]


 # =================== Set Interval Time Between Conditions ===================
def timeinterval(timen):
    time.sleep(timen)


# =================== Run Program for n Consecutive Times ===================
## Run n tests according to csv0
def StartNtest(filename, tuoche, shexiang, forceback,number,t):
    completedName = []
    # Read conditions
    conditionlist = pd.read_csv(filename) # library: pandas reads csv
    for i in conditionlist.index: # index: row index of csv starting from 0
        tuoche.Movedirection = 0 if tuoche.Movedirection == 1 else 1
        condition = conditionlist.loc[i] # get the (i+1)-th condition
        if condition["Finished"] == 0:
            Name = condition["Name"]
            Speed = float(condition["Speed"])
            mass = condition["VirtM"]
            dampingratio = condition["DampR"]
            stiffnessCF = condition["StiffKCF"]
            stiffnessIL = condition["StiffKIL"]
            realmass = condition["RealMass"]
            addzeta = condition["AddZeta"]
            vr = condition["Vr"]
            runtime = tuoche.totalDistance / abs(Speed)
            if shexiang.Photostatus == False and tuoche.Movestatus == False:
                if tuoche.Position == 0:
                    tuoche.initial()
                    tuoche.Enable()
                timeinterval(10)
                forceback.Enable(Name, mass, dampingratio, stiffnessCF, stiffnessIL, realmass,vr, addzeta, runtime)

                shexiang.Auto(runtime, Name)
                forceback.Move()
                timeinterval(t)
                tuoche.Move(Speed)
                threadtest = threading.Thread(target=start_server(tuoche, shexiang, forceback))
                threadtest.start()
                threadtest.join()
                tuoche.Setzero()
                tuoche.Disable()
                # process.stdin.flush()
                forceback.Disable()
                # Modify condition table and mark as completed
                changedata(conditionlist, i, ['Finished'], [1])
                conditionlist.to_csv(filename, index=False, encoding="utf-8")
                completedName.append(Name)


        else:
            continue


# =================== Initial Condition Table Parameter File ===================
data0={
        'S': 13, # towing travel distance
        'D': 0.1,  # riser diameter
        'L': 0.8,  # submerged length of the riser
        'M': 0.59, # actual mass of the riser
        'Vr0': 3,
        'StepVr': 3,
        'Vr1': 11,
        'mass0': 2,
        'Stepmass': 3,
        'mass1': 8,
        'damp0': 0,
        'Stepdamp': 0.02,
        'damp1': 0.05,
        'U0': 0.2,
        'StepU': 0,
        'Uend': 0.2,
        'AIRorWATER': 1, # 1: use natural frequency in air; 0: use natural frequency in water
        'Tinterval': 20,  # static sampling time
        'Errcoe': 10, # coefficient error obtained (relative error between forward and reverse coefficients)
        'ErrcoeType': 1,  # coefficient-error basis selection: 1 CF A; 2 IL A; 3 Cdm
        'YtrainDirection': 2, # training data direction selection: 0 reverse only; 1 forward only; 2 mean of forward+reverse; 3 use the larger positive value
        'YtrainType': 1, # prediction data type selection: 1 CF A; 2 CF A + Cd; 3 IL A; 4 IL A + Cd
        'ErrFinal': 0.01, # predicted coefficient error
        'CoePosTypePre': 1,  # which coefficient to use for error-based next point selection: 1 first dimension; 2 second dimension; 3 first two dimensions
        'XtrainType': 1234, # training input type selection: 1 Vr; 2 Mass; 3 Damp; 4 Re; 12 Vr+Mass; 13 Vr+Damp; 14 Vr+Re; 123 Vr+Mass+Damp; 124 Vr+Mass+Re; 134 Vr+Damp+Re; 1234 Vr+Mass+Damp+Re
        'Coe_Zhengzhi': 0, # whether to take positive values for processed coefficients: 1 positive only, 0 keep original values
        'Conv_thresh': 5555, # relative hyperparameter change threshold; above this threshold no prediction is performed, 8%
        }

# =================== Prediction Condition Table Parameter File ===================
data1={
        'S': 13, # towing travel distance
        'D': 0.1,  # riser diameter
        'L': 0.8,  # submerged length of the riser
        'M': 0.59, # actual mass of the riser
        'Vr0': 3,
        'StepVr': 0.1,
        'Vr1': 14,
        'mass0': 2,
        'Stepmass': 0.1,
        'mass1': 8,
        'damp0': 0,
        'Stepdamp': 0.002,
        'damp1': 0.05,
        'U0': 0.1,
        'StepU': 0.01,
        'Uend': 0.25,
        'XtrainType': 1234,  # training input type selection: 1 Vr; 2 Mass; 3 Damp; 4 Re; 12 Vr+Mass; 13 Vr+Damp; 14 Vr+Re; 123 Vr+Mass+Damp; 124 Vr+Mass+Re; 134 Vr+Damp+Re; 1234 Vr+Mass+Damp+Re
        'Kernelfun': 1100,  # kernel function selection: 1 squaredexponential; 2 exponential; 3 matern32; 4 matern52; 5 rationalquadratic
        'Basisfun': 1100, # basis function selection: 1 none; 2 constant; 3 linear; 4 quadratic; 5 custom basis function
        'Nextpointmethod': 6, # next-point method: 1 BO EI; 2 BO LCB; 3 max variance; 4 BO PI; 5 programmed continuous EI
        'Sigma': 1e-3, # noise variance
        'Explorationratio': 0.5, # exploration ratio in EI
        'MaxEvaluations': 10, # number of Bayesian optimization evaluations
        'Boundzone': 0, # boundary isolation-zone proportion (based on lower boundary)
        'w_mu': 0, # weight of mean term in acquisition function
        'w_sigma': 10, # weight of variance term in acquisition function
        'lambda': 0.1, # distance penalty coefficient
        'Dis_Penalty': 0, # dense-distance penalty switch
        'Bounds_Penalty': 0, # boundary-distance penalty switch
        'penalty_w1': 0, # dense-distance penalty weight
        'penalty_w2': 0, # boundary-distance penalty weight
        'Multiply': 1, # acquisition improvement: 1 multiplication, 2 addition
        'JiaoTi_YorN': 0, # alternating selection switch
        'JiaoTi_YorN2': 0, # alternating selection switch 2
        'Fun_option': 0, # kernel optimization option
        'ConstantSigma': 0, # kernel optimization option
        }


if __name__ == "__main__":
    
    # Target position set
    filenametxt0 ='Input0_parameters_self.txt'
    file_pretxt1 ='Input1_pre_parameters_self.txt'
    filenamecsv0 = "initial_data_self.csv"
    filenamestorematlab ='D:\DPQ\程序处理分析优化-自激\自激振荡实验\Test实验\*'  # the '*' must not be removed; used for automatic recognition of txt suffix
    filenamestoreforceback ='D:\DPQ\程序处理分析优化-自激\自激振荡实验\Test实验'
    distance0 = 12 # towing distance                              # towing distance
    tinterval = 10                                        # static sampling time
    ip_tuoche = {"ip": '192.168.1.102', "port": 55000}    # IP and port for towing program
    ip_shexiang = {"ip": '192.168.1.104', "port": 55000}  # IP and port for camera program
    ip_forceback = {"ip": '192.168.1.101', "port": 55000}  # IP and port for feedback device
    tuoche1 = tuoche()
    tuoche1.ip = ip_tuoche["ip"]
    tuoche1.port = ip_tuoche["port"]
    shexiang1 = shexiang()
    shexiang1.ip = ip_shexiang["ip"]
    shexiang1.port = ip_shexiang["port"]
    forceback1 = forceback()
    forceback1.ip = ip_forceback["ip"]
    forceback1.port = ip_forceback["port"]
    tuoche1.changedistance(distance0) # Modify towing travel distance
    data0["S"]=distance0
    data0["Tinterval"]=tinterval
    writetxt(data0,filenametxt0)
    writetxt(data1,file_pretxt1)
    number = 0
    #Creatinput0(1,filenametxt0,filenamecsv0) # Generate initial condition table
    StartNtest(filenamecsv0, tuoche1, shexiang1, forceback1,number,tinterval)
    number = 1
    DealCreatCoe(4,filenametxt0,filenamecsv0,filenamestorematlab)
    StartNtest(filenamecsv0, tuoche1, shexiang1, forceback1,number,tinterval)
    DealCreatCoe(4,filenametxt0,filenamecsv0,filenamestorematlab)
    GPRpre(5,filenametxt0,filenamecsv0,file_pretxt1)
    stopYoN = JudgeNext(6,filenametxt0,filenamecsv0)
    
    while stopYoN == 0:
        print(f'Newly added experiment count: run #{number}')
        StartNtest(filenamecsv0, tuoche1, shexiang1, forceback1,number,tinterval)
        number = number+1
        DealCreatCoe(4,filenametxt0,filenamecsv0,filenamestorematlab)
        StartNtest(filenamecsv0, tuoche1, shexiang1, forceback1,number,tinterval)
        DealCreatCoe(4,filenametxt0,filenamecsv0,filenamestorematlab)
        GPRpre(5,filenametxt0,filenamecsv0,file_pretxt1)
        stopYoN = JudgeNext(6,filenametxt0,filenamecsv0)
