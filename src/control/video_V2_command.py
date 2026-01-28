import os
import glob
import pyautogui
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
import time
from pynput import mouse, keyboard
import threading
import socket
# 文件夹名
folders = [
    "192.168.1.54_8000_1_7A89E8B2D673481E85B9EF8F8C800E28_",
    "192.168.1.65_8000_1_BFA5A13AD6324C7A800E2073C4523754_",
]
positions = [
    [1370,685],
    [1370,1315]
    #[1050, 500],
    #[1050, 950],
    # 可根据需要添加更多坐标
]
# 主机端口位置
ip_main = {"ip": '192.168.1.101', "port": 55001}
# ===================录像操作相关===================
# 重命名最新的MP4文件
def rename_latest_mp4(folder, new_name):
    mp4_files = glob.glob(os.path.join(folder, '*.mp4'))
    if not mp4_files:
        messagebox.showinfo("信息", f"No mp4 files found in {folder}")
        return

    latest_file = max(mp4_files, key=os.path.getctime) 
    count=1
    name0,extension=os.path.splitext(new_name)
    new_name=name0+f"V{count}"+extension
    new_path = os.path.join(folder, new_name)
    while os.path.exists(new_path):
        count+=1
        new_name=name0+f"V{count}"+extension
        new_path = os.path.join(folder, new_name)
    os.rename(latest_file, new_path)
    # messagebox.showinfo("信息", f"Renamed {latest_file} to {new_path}")

# 删除最新的MP4文件
def delete_latest_mp4(folder):
    mp4_files = glob.glob(os.path.join(folder, '*.mp4'))
    if not mp4_files:
        messagebox.showinfo("信息", f"No mp4 files found in {folder}")
        return
    latest_file = max(mp4_files, key=os.path.getctime)
    os.remove(latest_file)
    # messagebox.showinfo("信息", f"Removed {latest_file}")

# 删除所有JPG文件
def delete_all_jpg(folder):
    jpg_files = glob.glob(os.path.join(folder, '*.jpg'))
    if not jpg_files:
        messagebox.showinfo("信息", f"No jpg files found in {folder}")
        return
    for j in jpg_files:
        os.remove(j)
    # messagebox.showinfo("信息", f"All jpg files in {folder} are cleaned")

# 执行点击操作
def start_end_recording():
    for pos in positions:
        x, y = pos
        pyautogui.moveTo(x, y, duration=1)
        pyautogui.click()

    # messagebox.showinfo("信息", "操作完成")

# ===================调试操作相关===================
# 调试界面读取点坐标
def getposition():
    # 定义一个标志来控制监听器的运行状态
    running = True
    positionnew = []

    def on_click(x, y, button, pressed):
        if pressed:
            print(f"鼠标点击位置的坐标是: ({x}, {y})")
            positionnew.append([x, y])

    def on_press(key):
        nonlocal running  # 使用nonlocal来修改外部作用域的变量
        if key == keyboard.Key.esc:  # 检查是否按下了Esc键
            print("检测到Esc键，退出监听器")
            running = False  # 设置标志以停止监听器
            return False  # 返回False以停止键盘监听器

    # 启动鼠标和键盘监听器
    mouse_listener = mouse.Listener(on_click=on_click)
    keyboard_listener = keyboard.Listener(on_press=on_press)

    mouse_listener.start()
    keyboard_listener.start()

    # 主循环，保持监听器运行直到检测到Esc键
    while running:
        time.sleep(0.1)  # 轻量休眠以避免占用过多CPU资源

    # 在退出前停止监听器
    mouse_listener.stop()
    keyboard_listener.stop()

    return positionnew

# ===================主程序界面相关===================
# GUI界面设置
def main_program():
    stopAll_event=threading.Event()
    stopRecoding_event=threading.Event()
    def stop_recoding():
        stopRecoding_event.set()
    def select_folder():
        folder_selected = filedialog.askdirectory()
        folder_entry.delete(0, tk.END)  # 清空输入框内容
        folder_entry.insert(0, folder_selected)  # 插入选择的路径

    # 自动开始结束
    def motion0(name, time0):
        def record_thread():
            start_end_recording()
            totaltime=int(float(time0) + 2)
            for i in range(totaltime):
                if stopRecoding_event.is_set() or stopAll_event.is_set():
                    rename_button1.config(state="disabled")
                    record_button1.config(state="normal")
                    auto_button1.config(state="normal")
                    return
                time.sleep(1) 
            start_end_recording()
            time.sleep(1)
            send_command(ip_main,"FINISHPHOTO")
            rename_button1.config(state="disabled")
            record_button1.config(state="normal")
            auto_button1.config(state="normal")
            for index, folder in enumerate(folders, start=1):
                new_name = name + f"-{index}.mp4"
                rename_latest_mp4(folder_entry.get() + "/" + folder, new_name)
        stopRecoding_event.clear()
        rename_button1.config(state="normal")
        record_button1.config(state="disabled")
        auto_button1.config(state="disabled")
        thread1=threading.Thread(target=record_thread)
        thread1.start()
    # 开始
    def motion11():
        rename_button1.config(state="normal")
        record_button1.config(state="disabled")
        auto_button1.config(state="disabled")
        start_end_recording()
    # 结束
    def motion1(name):
        stop_recoding()
        rename_button1.config(state="disabled")
        start_end_recording()
        time.sleep(1)
        send_command(ip_main,"FINISHPHOTO")
        for index, folder in enumerate(folders, start=1):
            new_name = name + f"-{index}.mp4"
            rename_latest_mp4(folder_entry.get() + "/" + folder, new_name)
        record_button1.config(state="normal")
        auto_button1.config(state="normal")
    # 删除jpg
    def motion2():
        if messagebox.askyesno("确认", "确定要删除所有JPG文件吗？"):
            for index, folder in enumerate(folders, start=1):
                delete_all_jpg(folder_entry.get() + "/" + folder)
    # 删除录像
    def motion3():
        if messagebox.askyesno("确认", "确定要删除最近一次录像吗？"):
            for index, folder in enumerate(folders, start=1):
                delete_latest_mp4(folder_entry.get() + "/" + folder)
    #修改工况
    def motion4():
        name0 = name_entry.get()
        num0 = int(num_entry.get())
        index_f = name0.rfind("F")
        index_z = name0.rfind("Z")
        if index_f > index_z:
            new_char = "Z"
            index = index_f
        else:
            new_char = "F"
            index = index_z
        number = ""
        i = index - 1
        while i >= 0 and name0[i].isdigit():
            number = name0[i] + number
            i -= 1
        if number:
            modified_number = str(int(number) + num0)
            name_entry.delete(0, tk.END)  # 清空输入框内容
            name_entry.insert(0, name0[:i + 1] + modified_number + new_char + name0[index + 1:])
        else:
            pass
    # ===================接受端程序相关===================
    def start_server(host="0.0.0.0",port=55000):
        try:
            sever_socket=socket.socket(socket.AF_INET)
            sever_socket.bind((host,port))
            sever_socket.listen(5)
            print(f"Listening port {port}：")
            while not stopAll_event.is_set():
                sever_socket.settimeout(5)
                try:
                    client_socket, client_address=sever_socket.accept()
                    print(f"connected by client {client_address[0]}:")
                    message=client_socket.recv(1024).decode("utf-8")
                    print(f"{message}")
                    process_command(message)
                    client_socket.close()
                except socket.timeout:
                    continue
            print("LISTNER CLOSED")

        except Exception as e:
            print(f"find error when sending command：{e}")
            sever_socket.close()

    def process_command(message):
        if ":" in message:
            action,name=message.split(":",1)
            if action.startswith("CHANGETIME"):
                time_entry.delete(0, tk.END)  
                time_entry.insert(0, name)
            else:
                name_entry.delete(0, tk.END)
                name_entry.insert(0, name)
        else:
            action,name=message,None
        
        if action.startswith("AUTOPHOTO"):
            motion0(name_entry.get(), time_entry.get())
        if action.startswith("STARTPHOTO"):
            motion11()
        if action.startswith("STOPPHOTO"):  
            motion1(name_entry.get())
        else:
            pass
    def shutdown():
        if messagebox.askokcancel("退出","确认退出程序？"):
            stopAll_event.set()
            print("CLOSING......")
            thread2.join()
            root.destroy()
            print("ALL CLOSED")
    # ===================发送端程序===================
    def send_command(target, command,timeout=3):
        ip = target["ip"]
        port = target["port"]
        try:
            # 创建一个 TCP/IP socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                # 连接到服务器
                sock.connect((ip, port))
                print("connect to server {}:".format(ip))

                # 发送数据
                sock.sendall(command.encode('ascii'))
                print(f"{command}")
        except Exception as e:
            print(f"find error when sending command: {e}")
    thread2=threading.Thread(target=start_server)  
    thread2.start() 
    # 创建窗口
    root = tk.Tk()
    root.title("录像管理")
    root.protocol("WM_DELETE_WINDOW",shutdown)
    # 输入文件夹名区域
    folder_label = tk.Label(root, text="选择文件夹:")
    folder_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
    folder_entry = tk.Entry(root, width=25)
    folder_entry.grid(row=0, column=1, padx=10, pady=10, sticky="w")
    select_button = tk.Button(root, text="选择", command=select_folder)
    select_button.grid(row=0, column=2, padx=10, pady=10, sticky="w")
    # 删除操作区域
    record_button = tk.Button(root, text="删除 jpg", width=14, height=1, command=motion2)
    record_button.grid(row=0, column=3, padx=10, pady=10, sticky="w")

    rename_button = tk.Button(root, text="删除最近录像", width=14, height=1, command=motion3)
    rename_button.grid(row=0, column=4, padx=10, pady=10, sticky="w")

    # 分割线1
    sep1 = tk.Frame(root, height=2, bd=1, relief="sunken")
    sep1.grid(row=1, column=0, columnspan=5, padx=10, pady=5, sticky="ew")

    # 工况名及编号修改区域
    name_label = tk.Label(root, text="工况名:")
    name_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")
    name_entry = tk.Entry(root, width=25)
    name_entry.grid(row=2, column=1, padx=10, pady=10, sticky="w")
    name_entry.insert(0, "4DU02BM10UR300Z")

    frame1 = tk.Frame(root)
    frame1.grid(row=2, column=3)
    num_label = tk.Label(frame1, text="+")
    num_label.grid(row=0, column=0, padx=(20, 0), sticky="e")
    num_entry = tk.Entry(frame1, width=6)
    num_entry.grid(row=0, column=1, padx=(15, 0), sticky="e")
    num_entry.insert(0, "100")

    namechange_button = tk.Button(root, text="修改工况名", width=14, height=1, command=motion4)
    namechange_button.grid(row=2, column=4, padx=10, pady=10, sticky="w")

    # 分割线2
    sep2 = tk.Frame(root, height=2, bd=1, relief="sunken")
    sep2.grid(row=3, column=0, columnspan=5, padx=10, pady=5, sticky="ew")

    # 录像控制区域
    # 间隔时间(s):
    time_label = tk.Label(root, text="间隔时间(s):")
    time_label.grid(row=4, column=0, padx=10, pady=10, sticky="w")

    # 创建一个 Frame 占据 grid 布局的一个单元格
    frame0 = tk.Frame(root)
    frame0.grid(row=4, column=1, padx=0, pady=0)

    time_entry = tk.Entry(frame0, width=5)
    time_entry.grid(row=0, column=0, sticky="w", padx=(0, 30))
    time_entry.insert(0, "75")

    auto_button1 = tk.Button(frame0, text="开始并自动结束", command=lambda: motion0(name_entry.get(), time_entry.get()))
    auto_button1.grid(row=0, column=1, sticky="w", padx=(10, 0))
    # 竖直分割线
    separator = tk.Frame(root, width=0.2, bg="black")
    separator.grid(row=4, column=2, sticky="nse", padx=(5, 5), pady=(9, 9))
    # 开始录像
    record_button1 = tk.Button(root, text="开始录像", command=motion11)
    record_button1.grid(row=4, column=3, padx=20, pady=10, sticky="e")
    # 结束录像改编号
    rename_button1 = tk.Button(root, text="结束录像&改编号", command=lambda: motion1(name_entry.get()))
    rename_button1.grid(row=4, column=4, padx=10, pady=10, sticky="e")
    rename_button1.config(state="disabled")
    root.mainloop()



# ===================调试界面相关===================
def test_program():
    global folders, positions

    def add_folder():
        folder_name = simpledialog.askstring("输入", "请输入新的文件夹名:")
        if folder_name:
            folders.append(folder_name)
        listbox_folders.delete(0, tk.END)
        for folder0 in folders:
            listbox_folders.insert(tk.END, str(folder0))

    def del_folder():
        global folders
        folders = []
        listbox_folders.delete(0, tk.END)

    def add_position():

        # 隐藏主窗口
        root.iconify()
        # 等待鼠标点击
        positionnew = getposition()
        listbox_positions.delete(0, tk.END)
        for position0 in positionnew:
            positions.append(position0)
        for p in positions:
            listbox_positions.insert(tk.END, str(p))
        root.deiconify()
        root.lift()

    def del_position():
        global positions
        positions = []
        listbox_positions.delete(0, tk.END)

    def restartmain():
        root.destroy()
        main_program()

    root = tk.Tk()
    root.title("测试界面")

    # Folder input section
    frame00 = tk.Frame(root)
    frame00.grid(row=0, column=0, padx=0, pady=0)
    folder_label = tk.Label(frame00, text="录像文件夹")
    folder_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
    add_folder_button = tk.Button(frame00, text=" 添加 ", command=add_folder)
    add_folder_button.grid(row=0, column=1, padx=10, pady=10, sticky="w")
    del_folder_button = tk.Button(frame00, text="删除所有", command=del_folder)
    del_folder_button.grid(row=0, column=2, padx=10, pady=10, sticky="e")

    listbox_folders = tk.Listbox(root, width=40, height=10)
    listbox_folders.grid(row=1, column=0, padx=(35, 15), pady=(5, 15))
    for folder in folders:
        listbox_folders.insert(tk.END, str(folder))

    # Position input section
    frame01 = tk.Frame(root)
    frame01.grid(row=0, column=1, padx=0, pady=0)
    position_label = tk.Label(frame01, text="鼠标点击位置")
    position_label.grid(row=0, column=1, padx=10, pady=10, sticky="w")
    add_button = tk.Button(frame01, text=" 添加 ", command=add_position)
    add_button.grid(row=0, column=2, padx=10, pady=10, sticky="w")
    del_button = tk.Button(frame01, text="删除所有", command=del_position)
    del_button.grid(row=0, column=3, padx=10, pady=10, sticky="e")

    listbox_positions = tk.Listbox(root, width=40, height=10)
    listbox_positions.grid(row=1, column=1, padx=(15, 35), pady=(5, 15))
    for position in positions:
        listbox_positions.insert(tk.END, str(position))

    open_button = tk.Button(root, text="开始录像", command=restartmain)
    open_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

    root.mainloop()

def open_main_program(root):
    root.destroy()
    main_program()

def open_test_program(root):
    root.destroy()
    test_program()

# 开始界面
def start_program():
    root = tk.Tk()
    root.title("选择界面")
    button1 = tk.Button(root, text="录像程序", command=lambda: open_main_program(root), width=20, height=2)
    button1.pack(padx=20, pady=20)
    button2 = tk.Button(root, text="调试", command=lambda: open_test_program(root), width=20, height=2)
    button2.pack(padx=20, pady=20)
    root.mainloop()


if __name__ == "__main__":
    start_program()
