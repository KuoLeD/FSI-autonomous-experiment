"""
Automated experimental control program for rigid-cylinder FSI experiments.

Modules integrated:
- TCP command sender (towing / camera / actuator)
- TCP listener (status feedback from devices)
- Towing carriage control
- Camera control
- Forced oscillation control
- MATLAB-compiled optimization interface (AnalysisOptimize)

Notes:
- Input tables and parameters are written as plain text and CSV.
- The listener waits for three finish flags: FINISHMOVE / FINISHPHOTO / FINISHCONTROL.
"""

from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, List

import pandas as pd

import AnalysisOptimize as AnalyOpti


# ----------------------------- Low-level TCP sender -----------------------------


def send_command(
    ip: str,
    port: int,
    command: str,
    *,
    timeout_s: float = 5.0,
    retries: int = 2,
    retry_delay_s: float = 0.3,
    encoding: str = "ascii",
) -> None:
    """
    Send a single TCP command to (ip, port).

    - Adds socket timeout
    - Adds small retry to reduce transient network failures
    """
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout_s)
                sock.connect((ip, port))
                sock.sendall(command.encode(encoding))
                print(f"[SEND] {ip}:{port} -> {command}")
                return
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(retry_delay_s)
            else:
                print(f"[ERROR] Sending failed: {ip}:{port} -> {command} | {e}")
                return


# ----------------------------- Listener / Feedback -----------------------------


stopMoving_event = threading.Event()
stopRecoding_event = threading.Event()
stopControl_event = threading.Event()


def start_server(
    tuoche_obj: "TowingCarriage",
    shexiang_obj: "CameraController",
    forceback_obj: "ForcedOscillationController",
    *,
    host: str = "0.0.0.0",
    port: int = 55001,
    accept_timeout_s: float = 5.0,
) -> None:
    """
    TCP listener for device status feedback.

    Expected messages:
      - FINISHPHOTO
      - FINISHMOVE:<position>
      - FINISHCONTROL
    """
    stopMoving_event.clear()
    stopRecoding_event.clear()
    stopControl_event.clear()

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((host, port))
        server_sock.listen(5)
        server_sock.settimeout(accept_timeout_s)

        print(f"[LISTEN] Listening on {host}:{port}")

        while not (
            stopMoving_event.is_set()
            and stopRecoding_event.is_set()
            and stopControl_event.is_set()
        ):
            print(
                f"[STATUS] towing={stopMoving_event.is_set()} | "
                f"recording={stopRecoding_event.is_set()} | "
                f"control={stopControl_event.is_set()}"
            )
            try:
                client_socket, client_address = server_sock.accept()
                with client_socket:
                    msg = client_socket.recv(1024).decode("utf-8", errors="ignore").strip()
                    if msg:
                        print(f"[RECV] {client_address[0]} -> {msg}")
                        process_command(msg, tuoche_obj, shexiang_obj, forceback_obj)
            except socket.timeout:
                continue

        print("[LISTEN] Listener closed (all finish flags received).")

    except Exception as e:
        print(f"[ERROR] Listener error: {e}")
    finally:
        try:
            server_sock.close()
        except Exception:
            pass


def process_command(
    message: str,
    tuoche_obj: "TowingCarriage",
    shexiang_obj: "CameraController",
    forceback_obj: "ForcedOscillationController",
) -> None:
    """
    Parse feedback messages and set finish flags + update states.
    """
    if ":" in message:
        action, payload = message.split(":", 1)
        payload = payload.strip()
    else:
        action, payload = message.strip(), None

    action_u = action.upper()

    if action_u.startswith("FINISHPHOTO"):
        shexiang_obj.photostatus = False
        stopRecoding_event.set()

    elif action_u.startswith("FINISHMOVE"):
        tuoche_obj.movestatus = False
        if payload is not None:
            try:
                tuoche_obj.position = float(payload)
            except ValueError:
                pass
        stopMoving_event.set()

    elif action_u.startswith("FINISHCONTROL"):
        forceback_obj.movestatus = False
        stopControl_event.set()


# ----------------------------- MATLAB-compiled interface -----------------------------


def create_input0(stepn: int, filenametxt: str, filenamecsv: str) -> None:
    """
    Generate initial condition table (CSV) using MATLAB-compiled package.
    """
    pkg = AnalyOpti.initialize()
    try:
        pkg.Step0_Total_program(stepn, filenametxt, filenamecsv, "", "")
    finally:
        pkg.terminate()


def deal_create_coeff(stepn: int, filenametxt: str, filenamecsv: str, filenamestorematlab: str) -> None:
    """
    Process experiment data, compute coefficients, write back to CSV, etc.
    """
    pkg = AnalyOpti.initialize()
    try:
        pkg.Step0_Total_program(stepn, filenametxt, filenamecsv, filenamestorematlab, "")
    finally:
        pkg.terminate()


def gpr_predict(stepn: int, filenametxt: str, filenamecsv: str, file_pretxt1: str) -> None:
    """
    Run GPR prediction using MATLAB-compiled package.
    """
    pkg = AnalyOpti.initialize()
    try:
        pkg.Step0_Total_program(stepn, filenametxt, filenamecsv, "", file_pretxt1)
    finally:
        pkg.terminate()


def judge_next(stepn: int, filenametxt: str, filenamecsv: str) -> int:
    """
    Decide whether to stop (return flag).
    """
    pkg = AnalyOpti.initialize()
    try:
        stop_flag = pkg.Step0_Total_program(stepn, filenametxt, filenamecsv, "", "")
        # Some MATLAB runtimes return non-python int; cast robustly:
        try:
            return int(stop_flag)
        except Exception:
            return 0
    finally:
        pkg.terminate()


# ----------------------------- Utilities -----------------------------


def write_txt_kv(data: Dict[str, Any], filename: str) -> None:
    """
    Write key-value pairs line by line: 'key value'
    """
    with open(filename, "w", encoding="utf-8") as f:
        for k, v in data.items():
            f.write(f"{k} {v}\n")


def changedata(df: pd.DataFrame, row_idx: int, col_names: List[str], col_values: List[Any]) -> None:
    """
    Modify certain columns at a row.
    """
    for name, val in zip(col_names, col_values):
        df.loc[row_idx, name] = val


def timeinterval(seconds: float) -> None:
    time.sleep(seconds)


# ----------------------------- Controllers -----------------------------


@dataclass
class TowingCarriage:
    ip: str
    port: int

    initstatus: bool = False
    enablestatus: bool = False
    movestatus: bool = False

    position: float = 0.0
    movespeed: float = 0.0
    moveacc: float = 0.0
    movedec: float = 0.0

    total_distance: float = 1.0
    movedirection: int = 0  # 1 forward POS, 0 backward NEG

    def changedistance(self, distance: float) -> None:
        send_command(self.ip, self.port, f"DISTANCE:{distance}")
        self.total_distance = float(distance)

    def initial(self) -> None:
        send_command(self.ip, self.port, "INIT")
        send_command(self.ip, self.port, "RESET")
        send_command(self.ip, self.port, "SETZERO")
        self.initstatus = True
        self.position = 0.0

    def setzero(self) -> None:
        send_command(self.ip, self.port, "SETZERO")
        self.position = 0.0

    def enable(self) -> None:
        if self.initstatus:
            send_command(self.ip, self.port, "ENABLE_SERVO")
            self.enablestatus = True

    def disable(self) -> None:
        if self.enablestatus:
            send_command(self.ip, self.port, "DISABLE_SERVO")
            self.enablestatus = False

    def move(self, vel: float, acc: float = 0.2, dec: float = 0.2) -> None:
        """
        Start towing motion.

        Fixed issues vs original:
        - self.movespeed should store numeric absvel (not built-in abs)
        - direction decision preserved
        """
        absvel = float(abs(vel))
        direction = "NEG" if self.movedirection == 0 else "POS"

        if self.enablestatus and self.position == 0:
            send_command(self.ip, self.port, f"SET_SPEED:{absvel}")
            self.movespeed = absvel

            send_command(self.ip, self.port, f"SET_ACC:{acc}")
            self.moveacc = float(acc)

            send_command(self.ip, self.port, f"SET_DEC:{dec}")
            self.movedec = float(dec)

            send_command(self.ip, self.port, f"MOVE_{direction}")
            self.movestatus = True
        else:
            raise RuntimeError("Towing carriage cannot move (servo not enabled or position not zero).")

    def stop(self) -> None:
        send_command(self.ip, self.port, "STOP")
        self.movestatus = False
        send_command(self.ip, self.port, "DISABLE_SERVO")
        self.enablestatus = False


@dataclass
class CameraController:
    ip: str
    port: int
    photostatus: bool = False

    def auto(self, duration_s: float, name: str) -> None:
        send_command(self.ip, self.port, f"CHANGETIME:{duration_s}")
        send_command(self.ip, self.port, f"AUTOPHOTO:{name}")
        self.photostatus = True

    def start(self, name: str) -> None:
        send_command(self.ip, self.port, f"STRATPHOTO:{name}")
        self.photostatus = True

    def stop(self, name: str = " ") -> None:
        send_command(self.ip, self.port, f"STOPPHOTO:{name}")
        self.photostatus = False

    def changetime(self, duration_s: float) -> None:
        send_command(self.ip, self.port, f"CHANGETIME:{duration_s}")


@dataclass
class ForcedOscillationController:
    ip: str
    port: int

    name: str = ""
    enablestatus: bool = False
    movestatus: bool = False
    position: float = 0.0

    a1: float = 0.0
    f1: float = 0.0
    a2: float = 0.0
    f2: float = 0.0
    theta: float = 0.0
    cycletime: float = 0.0

    def enable(self, name: str, a1: float, f1: float, a2: float, f2: float, theta: float, cycletime: float) -> None:
        """
        Fixed issues vs original:
        - self.f2 should be f2 (not f1)
        """
        self.name = str(name)

        send_command(self.ip, self.port, f"SET_NAME:{self.name}")
        send_command(self.ip, self.port, f"SET_A1:{a1}")
        send_command(self.ip, self.port, f"SET_F1:{f1}")
        send_command(self.ip, self.port, f"SET_A2:{a2}")
        send_command(self.ip, self.port, f"SET_F2:{f2}")
        send_command(self.ip, self.port, f"SET_THETA:{theta}")
        send_command(self.ip, self.port, f"SET_CYCLE:{cycletime}")

        self.a1 = float(a1)
        self.f1 = float(f1)
        self.a2 = float(a2)
        self.f2 = float(f2)
        self.theta = float(theta)
        self.cycletime = float(cycletime)

        send_command(self.ip, self.port, "ENABLE_CONTROL")
        self.enablestatus = True

    def disable(self) -> None:
        if self.enablestatus:
            send_command(self.ip, self.port, "DISABLE_CONTROL")
            self.enablestatus = False

    def move(self) -> None:
        if self.enablestatus:
            send_command(self.ip, self.port, "MOVE")
            self.movestatus = True
        else:
            raise RuntimeError("Forced oscillation cannot move (control not enabled).")


# ----------------------------- Experiment loop -----------------------------


def run_experiments_from_csv(
    filename: str,
    tow: TowingCarriage,
    cam: CameraController,
    osc: ForcedOscillationController,
    run_index: int,
    static_interval_s: float,
    *,
    listener_host: str = "0.0.0.0",
    listener_port: int = 55001,
    pre_enable_wait_s: float = 10.0,
) -> List[str]:
    """
    Execute experiments defined in CSV.
    Marks each finished case in-place by setting Finished=1 and saving CSV.

    Returns: list of completed case names.
    """
    completed_names: List[str] = []
    conditionlist = pd.read_csv(filename)

    for i in conditionlist.index:
        # Toggle direction each run (as in original logic)
        tow.movedirection = 0 if tow.movedirection == 1 else 1

        condition = conditionlist.loc[i]
        if int(condition.get("Finished", 0)) != 0:
            continue

        name = str(condition["Name"])
        speed = float(condition["Speed"])

        amp1 = float(condition["A1"])
        f1 = float(condition["f1"])
        amp2 = float(condition["A2"])
        f2 = float(condition["f2"])
        theta = float(condition["Theta"])
        cycletime = float(condition["Count"])

        runtime_s = tow.total_distance / max(abs(speed), 1e-12)

        if (not cam.photostatus) and (not tow.movestatus):
            if tow.position == 0:
                tow.initial()
                tow.enable()

            timeinterval(pre_enable_wait_s)

            # Enable oscillation program, then optional static interval, then camera + towing + oscillation move.
            osc.enable(name, amp1, f1, amp2, f2, theta, cycletime)

            # Static sampling / waiting (kept consistent with your original usage)
            timeinterval(static_interval_s)

            cam.auto(runtime_s, name)

            # Start listener thread BEFORE motion commands to avoid race conditions
            listener_thread = threading.Thread(
                target=start_server,
                args=(tow, cam, osc),
                kwargs={"host": listener_host, "port": listener_port},
                daemon=True,
            )
            listener_thread.start()

            # Start motions
            tow.move(speed)
            osc.move()

            # Wait until all finish flags received
            listener_thread.join()

            # Reset and disable
            tow.setzero()
            tow.disable()
            osc.disable()

            # Mark completed in CSV
            changedata(conditionlist, i, ["Finished"], [1])
            conditionlist.to_csv(filename, index=False, encoding="utf-8")

            completed_names.append(name)

    return completed_names


# ----------------------------- Main config -----------------------------


def main() -> None:
    # File paths
    filenametxt0 = "Input0_parameters.txt"
    file_pretxt1 = "Input1_pre_parameters.txt"
    filenamecsv0 = "initial_data.csv"

    # IMPORTANT: keep '*' for MATLAB side auto-detect pattern
    filenamestorematlab = r"D:\DPQ\主机-联合控制\Test实验\*"
    filenamestoreforceback = r"D:\DPQ\主机-联合控制\Test实验"  # kept for compatibility (if needed later)

    # Experiment setup
    distance0 = 12.0
    tinterval = 10.0  # static sampling time between enabling osc and moving

    # Device endpoints
    ip_tuoche = {"ip": "192.168.1.102", "port": 55000}
    ip_shexiang = {"ip": "192.168.1.104", "port": 55000}
    ip_forceback = {"ip": "192.168.1.101", "port": 55000}

    # Controllers
    tow = TowingCarriage(ip=ip_tuoche["ip"], port=int(ip_tuoche["port"]))
    cam = CameraController(ip=ip_shexiang["ip"], port=int(ip_shexiang["port"]))
    osc = ForcedOscillationController(ip=ip_forceback["ip"], port=int(ip_forceback["port"]))

    # Modify towing travel distance
    tow.changedistance(distance0)

    # ----------------------------- Parameters -----------------------------
    data0 = {
        "S": 13,  # towing travel distance (will be overwritten)
        "D": 0.1,  # riser diameter
        "L": 0.8,  # submerged length
        "M": 0.59,  # riser mass
        "A1non0": 0.1,
        "StepA1": 0.5,
        "A1non1": 1.2,
        "f1non0": 0.1,
        "StepF1": 0.1,
        "f1non1": 0.3,
        "A2non0": 0.1,
        "StepA2": 0.3,
        "A2non1": 0.4,
        "f2non0": 0,
        "StepF2": 0,
        "f2non1": 0,
        "theta0": 0,
        "Steptheta": 180,
        "thetaend": 360,
        "U0": 0.2,
        "StepU": 0.1,
        "Uend": 0.3,
        "Tinterval": 15,
        "Errcoe": 0.5,
        "ErrcoeType": 1,
        "YtrainDirection": 1,
        "YtrainType": 3,
        "ErrFinal": 0.01,
        "CoePosTypePre": 1,
        "XtrainType": 6,
        "Coe_Zhengzhi": 0,
        "Conv_thresh": 1111,
        "Windowvalue": 10,
    }

    data1 = {
        "S": 13,  # towing travel distance
        "D": 0.1,
        "L": 0.8,
        "M": 0.59,
        "A1non0": 0.1,
        "StepA1": 0.1,
        "A1non1": 1.2,
        "f1non0": 0.1,
        "StepF1": 0.01,
        "f1non1": 0.3,
        "A2non0": 0.1,
        "StepA2": 0.05,
        "A2non1": 0.4,
        "f2non0": 0,
        "StepF2": 0,
        "f2non1": 0,
        "theta0": 0,
        "Steptheta": 30,
        "thetaend": 360,
        "U0": 0.2,
        "StepU": 0.01,
        "Uend": 0.3,
        "XtrainType": 6,
        "Kernelfun": 1111,
        "Basisfun": 1111,
        "Nextpointmethod": 6,
        "Sigma": 7e-3,
        "Explorationratio": 0.5,
        "MaxEvaluations": 10,
        "Boundzone": 0,
        "w_mu": 0,
        "w_sigma": 1,
        "lambda": 0,
        "Dis_Penalty": 0,
        "Bounds_Penalty": 0,
        "penalty_w1": 0,
        "penalty_w2": 0,
        "Multiply": 1,
        "JiaoTi_YorN": 25,
        "JiaoTi_YorN2": 0,
        "Fun_option": 0,
        "ConstantSigma": 0,
    }

    # Sync runtime parameters
    data0["S"] = distance0
    data0["Tinterval"] = tinterval

    write_txt_kv(data0, filenametxt0)
    write_txt_kv(data1, file_pretxt1)

    # ----------------------------- Workflow -----------------------------
    number = 0

    # If initial CSV needs to be generated, enable the next line:
    # create_input0(1, filenametxt0, filenamecsv0)

    run_experiments_from_csv(filenamecsv0, tow, cam, osc, number, tinterval)

    number = 1
    deal_create_coeff(4, filenametxt0, filenamecsv0, filenamestorematlab)

    run_experiments_from_csv(filenamecsv0, tow, cam, osc, number, tinterval)
    deal_create_coeff(4, filenametxt0, filenamecsv0, filenamestorematlab)

    gpr_predict(5, filenametxt0, filenamecsv0, file_pretxt1)
    stop_flag = judge_next(6, filenametxt0, filenamecsv0)

    while stop_flag == 0:
        print(f"[LOOP] Newly added experiment count: run #{number}")
        run_experiments_from_csv(filenamecsv0, tow, cam, osc, number, tinterval)
        number += 1

        deal_create_coeff(4, filenametxt0, filenamecsv0, filenamestorematlab)

        run_experiments_from_csv(filenamecsv0, tow, cam, osc, number, tinterval)
        deal_create_coeff(4, filenametxt0, filenamecsv0, filenamestorematlab)

        gpr_predict(5, filenametxt0, filenamecsv0, file_pretxt1)
        stop_flag = judge_next(6, filenametxt0, filenamecsv0)


if __name__ == "__main__":
    main()
