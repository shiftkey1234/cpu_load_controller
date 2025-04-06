# cpu_load_controller.py
import tkinter as tk
import tkinter.ttk as ttk
import psutil
import time
import multiprocessing
import threading

# ------------------------------
# 전역 설정
# ------------------------------
TARGET_LOAD = 80
CHECK_INTERVAL = 0.5
MAX_PROCESSES = psutil.cpu_count(logical=True) * 16
MIN_PROCESSES = 1

burn_processes = []
CURRENT_PROCESSES = 0

WORK_ITERATION = 10000
TIME_SLEEP = 0.001

should_stop_monitor = threading.Event()


# ------------------------------
# CPU 부하 함수
# ------------------------------
def burn_cpu(stop_event):
    while not stop_event.is_set():
        x = 0
        for i in range(WORK_ITERATION):
            x += i ** 2
        time.sleep(TIME_SLEEP)

# ------------------------------
# 모니터링 함수 (백그라운드)
# ------------------------------
def monitor_load():
    global CURRENT_PROCESSES
    current_processes = 0

    # 초기 프로세스 3개 시작
    initial_count = 3
    for _ in range(initial_count):
        stop_event = multiprocessing.Event()
        p = multiprocessing.Process(target=burn_cpu, args=(stop_event,))
        p.start()
        burn_processes.append((p, stop_event))
    current_processes = initial_count
    CURRENT_PROCESSES = current_processes

    while not should_stop_monitor.is_set():
        cpu_percent = psutil.cpu_percent(interval=1)
        global TARGET_LOAD
        target = TARGET_LOAD

        if cpu_percent < target - 5 and current_processes < MAX_PROCESSES:
            stop_event = multiprocessing.Event()
            p = multiprocessing.Process(target=burn_cpu, args=(stop_event,))
            p.start()
            burn_processes.append((p, stop_event))
            current_processes += 1
        elif cpu_percent > target + 5 and current_processes > MIN_PROCESSES:
            p, se = burn_processes.pop()
            se.set()
            p.join()
            current_processes -= 1

        CURRENT_PROCESSES = current_processes
        time.sleep(CHECK_INTERVAL)

# ------------------------------
# 메인 GUI 클래스
# ------------------------------
class CpuLoadApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CPU Load Controller")

        # (선택) 창 크기를 지정하거나 고정하고 싶다면 사용:
        # self.root.geometry("400x300")
        # self.root.resizable(False, False)

        # (선택) 아이콘 지정:
        # self.root.iconbitmap("path/to/icon.ico")

        # ------------------------------
        # ttk 스타일 설정
        # ------------------------------
        style = ttk.Style()
        # 사용할 수 있는 테마들: 'clam', 'alt', 'default', 'classic', 'vista', 'xpnative' 등
        style.theme_use("clam")

        # 큰 제목 스타일 (예시)
        style.configure("Title.TLabel", font=("Arial", 16, "bold"), foreground="#333")

        # 일반 라벨 스타일 (예시)
        style.configure("Regular.TLabel", font=("Arial", 12))

        # 숫자 라벨(진한 표시)
        style.configure("Num.TLabel", font=("Arial", 13, "bold"))

        # 버튼 스타일
        style.configure("TButton", font=("Arial", 12), padding=5)

        # Entry 스타일
        style.configure("TEntry", font=("Arial", 12))

        # 프로그레스바 두께
        style.configure("Horizontal.TProgressbar", thickness=20)

        # ------------------------------
        # 메인 프레임
        # ------------------------------
        main_frame = ttk.Frame(self.root, padding="10 10 10 10")
        main_frame.pack(fill="both", expand=True)

        # ------------------------------
        # 제목 라벨
        # ------------------------------
        title_label = ttk.Label(main_frame, text="CPU Load Controller", style="Title.TLabel")
        title_label.pack(pady=(0, 10))

        # ------------------------------
        # CPU 사용률 영역 (라벨 + 프로그레스바)
        # ------------------------------
        usage_frame = ttk.Frame(main_frame)
        usage_frame.pack(fill="x", pady=5)

        self.cpu_label = ttk.Label(usage_frame, text="CPU Usage: 0.00%", style="Regular.TLabel")
        self.cpu_label.pack(anchor="center", pady=5)

        self.cpu_bar = ttk.Progressbar(usage_frame, orient="horizontal",
                                       length=300, mode="determinate",
                                       style="Horizontal.TProgressbar")
        self.cpu_bar.pack(anchor="center", pady=5)

        # ------------------------------
        # 프로세스(쓰레드) 개수 표시
        # ------------------------------
        self.proc_label = ttk.Label(main_frame, text="Processes: 0", style="Num.TLabel")
        self.proc_label.pack(pady=10)

        # ------------------------------
        # 목표 CPU 설정 영역 (Entry + 버튼)
        # ------------------------------
        setting_frame = ttk.Frame(main_frame)
        setting_frame.pack(fill="x", pady=5)

        self.entry_label = ttk.Label(setting_frame, text="Set Target CPU (%)", style="Regular.TLabel")
        self.entry_label.pack(anchor="w", pady=2)

        self.cpu_entry = ttk.Entry(setting_frame, style="TEntry")
        self.cpu_entry.insert(0, str(TARGET_LOAD))
        self.cpu_entry.pack(anchor="w", fill="x")

        self.apply_button = ttk.Button(setting_frame, text="Apply", command=self.on_apply_click)
        self.apply_button.pack(anchor="e", pady=5)

        # ------------------------------
        # 윈도우 종료 이벤트
        # ------------------------------
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # ------------------------------
        # 주기적 업데이트
        # ------------------------------
        self.update_display()

    def on_apply_click(self):
        global TARGET_LOAD
        try:
            val = float(self.cpu_entry.get())
            if val < 0:
                val = 0
            elif val > 100:
                val = 100
            TARGET_LOAD = val
        except ValueError:
            # 잘못된 입력이면 무시. 더 나은 안내 메시지를 띄울 수도 있음
            pass

    def update_display(self):
        cpu_percent = psutil.cpu_percent(interval=None)
        self.cpu_label.config(text=f"CPU Usage: {cpu_percent:.2f}%")
        self.cpu_bar["value"] = cpu_percent

        global CURRENT_PROCESSES
        self.proc_label.config(text=f"Processes: {CURRENT_PROCESSES}")

        self.root.after(500, self.update_display)

    def on_closing(self):
        should_stop_monitor.set()
        for p, stop_event in burn_processes:
            stop_event.set()
            p.join()
        self.root.destroy()

# ------------------------------
# 메인 함수
# ------------------------------
def main():
    root = tk.Tk()
    app = CpuLoadApp(root)

    monitor_thread = threading.Thread(target=monitor_load, daemon=True)
    monitor_thread.start()

    root.mainloop()

# ------------------------------
# 실행
# ------------------------------
if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
