import customtkinter as ct
from tkinter import filedialog
import os
import logging
from CTkToolTip import CTkToolTip
from CTkMessagebox import CTkMessagebox
import threading
import queue
import requests
import io
import time


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

class App(ct.CTk):
    def __init__(self):
        super().__init__()
        self.queue = queue.Queue()

        self.title("SaveManager Setup")
        window_width = 1000
        window_height = 600

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

        self.iconbitmap(os.path.join(os.path.dirname(os.path.realpath(__file__)), "docs\\icon.ico"))
        self.protocol("WM_DELETE_WINDOW", self.show_close_popup)

        self.pages: list = []
        self.page_progress: float = 0
        self.current_page: int = 0
        self.installation_path = os.path.join(os.getenv("LOCALAPPDATA"), "SaveManager")
        os.makedirs(self.installation_path, exist_ok=True)

        ct.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
        ct.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure((0, 1), weight=1)
        self.grid_rowconfigure(2, weight=0)

        # Button frame
        self.button_frame = ct.CTkFrame(self, fg_color="transparent")
        self.button_frame.grid(column=0, columnspan=2, row=2, padx=40, pady=(0, 40))
        self.button_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.button_frame.grid_rowconfigure(0, weight=1)

        self.back_button = ct.CTkButton(self.button_frame, text="Cancel", font=ct.CTkFont(family="Segoe UI"), width=130)
        self.back_button.grid(column=0, row=0, padx=30)

        self.page_progress_bar = ct.CTkProgressBar(self.button_frame)
        self.page_progress_bar.grid(column=1, row=0, padx=20)
        self.page_progress_bar.set(self.page_progress)

        self.next_button = ct.CTkButton(self.button_frame, text="Next", font=ct.CTkFont(family="Segoe UI"), width=130, command=lambda: self.switch_page(self.current_page + 1))
        self.next_button.grid(column=2, row=0, padx=30)

        # Page setup
        self.set_page_1()
        self.set_page_2()
        self.set_page_3()
        self.set_page_4()
        self.set_page_5()
        self.switch_page(0)

    def switch_page(self, page_num):
        if page_num > 4:
            quit()
            return

        if self.current_page == 1 and page_num == 2:
            if self.installation_path != None:
                logging.debug(f"Installation folder selected: {self.installation_path}")
            else:
                return

        for page in self.pages:
            page.grid_forget()
        self.pages[page_num].grid(column=0, columnspan=2, row=0, rowspan=2, padx=40, pady=40)

        self.current_page = page_num
        self.page_progress_bar.set(page_num / (len(self.pages) - 1))

        if page_num == 3:
            self.next_button.configure(text="Install", command=self.start_installation)

            self.final_path_entry.configure(state="normal")
            self.final_path_entry.delete(0, "end")
            self.final_path_entry.insert(0, self.installation_path)
            self.final_path_entry.configure(state="disabled")

            desktop_shortcut_value = self.desktop_shortcut.get()
            if desktop_shortcut_value == 1:
                self.final_desktop_shortcut.configure(state="normal")
                self.final_desktop_shortcut.select()
                self.final_desktop_shortcut.configure(state="disabled")
            else:
                self.final_desktop_shortcut.configure(state="normal")
                self.final_desktop_shortcut.deselect()
                self.final_desktop_shortcut.configure(state="disabled")
        
        if page_num == len(self.pages) - 1 and page_num != 3:
            self.next_button.configure(text="Finish")
        elif page_num != len(self.pages) - 1 and page_num != 3:
            self.next_button.configure(text="Next")

        if page_num > 0:
            self.back_button.configure(text="Back", command=lambda: self.switch_page(self.current_page - 1))
        else:
            self.back_button.configure(text="Cancel", command=self.show_close_popup)

    def start_installation(self):
        self.next_button.configure(state="disabled", command=lambda: self.switch_page(self.current_page + 1))
        self.back_button.configure(state="disabled")
        self.switch_page(4)
        thread = threading.Thread(target=self.install_thread, daemon=True)
        self.process_queue()
        thread.start()

    def set_page_1(self):
        page = ct.CTkFrame(self, border_width=4, corner_radius=10)
        page.grid(column=0, columnspan=2, row=0, rowspan=2, padx=40, pady=40)
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure((0, 1), weight=1)
        self.pages.append(page)

        title_label = ct.CTkLabel(page, text="Welcome to SaveManager installer", font=ct.CTkFont(family="Comic Sans MS", size=22, weight="bold"))
        title_label.grid(row=0, column=0, padx=80, pady=(80, 30), sticky="nsew")
        info_label = ct.CTkLabel(page, text="This installer will help you install the app", font=ct.CTkFont(family="Microsoft JhengHei"))
        info_label.grid(row=1, column=0, padx=80, pady=(30, 100), sticky="nsew")
    
    def set_page_2(self):
        page = ct.CTkFrame(self, border_width=4, corner_radius=10)
        page.grid(column=0, columnspan=2, row=0, rowspan=2, padx=40, pady=40)
        page.grid_columnconfigure(0, weight=5)
        page.grid_columnconfigure(1, weight=1)
        page.grid_rowconfigure((0, 1), weight=1)
        self.pages.append(page)

        installation_folder_label = ct.CTkLabel(page, text="Select installation directory", font=ct.CTkFont(family="Comic Sans MS", size=22, weight="bold"))
        installation_folder_label.grid(row=0, column=0, columnspan=2, padx=10, pady=(40, 20), sticky="nsew")
        CTkToolTip(installation_folder_label, message="Where to install the app")

        self.path_entry = ct.CTkEntry(page, width=600, border_color="#2E7D32")
        self.path_entry.grid(row=1, column=0, padx=(30, 5), pady=30, sticky="nsew")
        self.path_entry.insert(0, self.installation_path)
        self.path_entry.bind("<KeyRelease>", self.validate_folder_path)

        open_folder = ct.CTkButton(page, text="Browse", width=100, command=self.select_folder)
        open_folder.grid(row=1, column=1, padx=(5, 30), pady=30, sticky="nsew")
        CTkToolTip(open_folder, message="Select folder")
    
    def set_page_3(self):
        page = ct.CTkFrame(self, border_width=4, corner_radius=10)
        page.grid(column=0, columnspan=2, row=0, rowspan=2, padx=40, pady=40)
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure((0, 1, 2), weight=1)
        self.pages.append(page)

        option_label = ct.CTkLabel(page, text="Additional options", font=ct.CTkFont(family="Comic Sans MS", size=22, weight="bold"))
        option_label.grid(row=0, column=0, padx=120, pady=(40, 20), sticky="nsew")

        self.desktop_shortcut = ct.CTkCheckBox(page, text="Create desktop shortcut")
        self.desktop_shortcut.grid(row=1, column=0, padx=30, pady=(30, 10))

        self.start_menu = ct.CTkCheckBox(page, text="Add to start menu")
        self.start_menu.grid(row=2, column=0, padx=30, pady=(10, 30))
    
    def set_page_4(self):
        page = ct.CTkFrame(self, border_width=4, corner_radius=10)
        page.grid(column=0, columnspan=2, row=0, rowspan=2, padx=40, pady=40)
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure((0, 1, 2, 3, 4, 5), weight=1)
        self.pages.append(page)

        confirm_label = ct.CTkLabel(page, text="Confirm choices", font=ct.CTkFont(family="Comic Sans MS", size=22, weight="bold"))
        confirm_label.grid(row=0, column=0, padx=120, pady=(40, 20), sticky="nsew")

        path_label = ct.CTkLabel(page, text="Install in:", font=ct.CTkFont(family="Microsoft JhengHei", size=14))
        path_label.grid(row=1, column=0, padx=30, pady=(30, 0), sticky="nsew")

        self.final_path_entry = ct.CTkEntry(page, width=600, state="disabled", border_color="#FF6F00")
        self.final_path_entry.grid(row=2, column=0, padx=30, pady=(0, 30), sticky="nsew")

        other_options_label = ct.CTkLabel(page, text="Other options:", font=ct.CTkFont(family="Microsoft JhengHei", size=14))
        other_options_label.grid(row=3, column=0, padx=30, pady=(10, 0), sticky="nsew")

        self.final_desktop_shortcut = ct.CTkCheckBox(page, text="Create desktop shortcut", state="disabled", border_color="#FF6F00", fg_color="#FF6F00", text_color_disabled=("gray10", "#DCE4EE"))
        self.final_desktop_shortcut.grid(row=4, column=0, padx=30, pady=(10, 10))

        final_start_menu = ct.CTkCheckBox(page, text="Add to start menu", state="disabled", border_color="#FF6F00", fg_color="#FF6F00", text_color_disabled=("gray10", "#DCE4EE"))
        final_start_menu.grid(row=5, column=0, padx=30, pady=(10, 30))
    
    def set_page_5(self):
        page = ct.CTkFrame(self, border_width=4, corner_radius=10)
        page.grid(column=0, columnspan=2, row=0, rowspan=2, padx=40, pady=40)
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure((0, 1), weight=1)
        page.grid_rowconfigure(2, weight=0)
        page.grid_rowconfigure(3, weight=10)
        self.pages.append(page)

        install_label = ct.CTkLabel(page, text="Installing...", font=ct.CTkFont(family="Comic Sans MS", size=22, weight="bold"))
        install_label.grid(row=0, column=0, padx=120, pady=(40, 20), sticky="nsew")

        copy_label = ct.CTkLabel(page, text="", font=ct.CTkFont(family="Microsoft JhengHei", size=14))
        copy_label.grid(row=1, column=0, padx=30, pady=(20, 5), sticky="nsew")

        self.install_progressbar = ct.CTkProgressBar(page, orientation="horizontal", height=20, corner_radius=8)
        self.install_progressbar.grid(row=2, column=0, padx=30, pady=(5, 20), sticky="nsew")
        self.install_progressbar.set(0)

        self.install_log = ct.CTkTextbox(page, width=500)
        self.install_log.grid(row=3, column=0, padx=30, pady=(10, 30), sticky="nsew")
    
    def process_queue(self):
        while not self.queue.empty():
            try:
                msg = self.queue.get_nowait()
                if msg["type"] == "progress":
                    self.install_progressbar.set(msg["value"])
                    self.update()
                elif msg["type"] == "log":
                    self.install_log.insert("end", msg["message"] + "\n")
                    self.install_log.see("end")
                elif msg["type"] == "complete":
                    self.next_button.configure(text="Finish", state="normal")
                    CTkMessagebox(title="Success", message="Installation completed!")
                elif msg["type"] == "error":
                    self.show_error_popup(msg["error"])
            except queue.Empty:
                pass
        self.after(100, self.process_queue)

    def install_thread(self):
        try:
            repo_url = "https://github.com/FlamingWater35/SaveManager/releases/download/v2.5.3/SaveManager.7z"
            self.queue.put({"type": "log", "message": "Downloading files..."})

            # Download 7z archive
            response = requests.get(repo_url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            archive_buffer = io.BytesIO()

            for chunk in response.iter_content(chunk_size=8192):
                archive_buffer.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    self.queue.put({"type": "progress", "value": downloaded / total_size})

            self.queue.put({"type": "log", "message": "Extracting files..."})
            archive_buffer.seek(0)

            # Extract 7z archive
            import py7zr
            with py7zr.SevenZipFile(archive_buffer, mode='r') as archive:
                archive.extractall(path=self.installation_path)
            
            # Create desktop shortcut
            if self.desktop_shortcut.get():
                self.create_desktop_shortcut()
            
            self.queue.put({"type": "progress", "value": 1.0})
            self.queue.put({"type": "log", "message": "Installation complete!"})
            self.queue.put({"type": "complete"})
        
        except Exception as e:
            self.queue.put({"type": "error", "error": str(e)})
            logging.error(f"Installation failed: {e}")
        
    def create_desktop_shortcut(self):
        try:
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            shortcut_path = os.path.join(desktop_path, "SaveManager.lnk")
            target = os.path.join(self.installation_path, "SaveManager.exe")
            
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = target
            shortcut.WorkingDirectory = self.installation_path
            shortcut.save()
            
        except Exception as e:
            self.queue.put({"type": "log", "message": f"Failed to create shortcut: {str(e)}"})

    def select_folder(self):
        try:
            folder = filedialog.askdirectory()
            if folder and os.path.exists(folder):
                self.path_entry.delete(0, "end")
                self.path_entry.insert(0, folder)
            self.validate_folder_path()
        except Exception as e:
            self.show_error_popup(e)
            logging.error(f"Error in select_folder: {e}")
    
    def validate_folder_path(self, event=None):
        try:
            folder_path = self.path_entry.get()
            if os.path.exists(folder_path):
                self.installation_path = folder_path.replace(" ", "")
                self.path_entry.configure(border_color="#2E7D32")
            else:
                self.installation_path = None
                self.path_entry.configure(border_color="#B71C1C")
        except Exception as e:
            self.show_error_popup(e)
            logging.error(f"Error in validate_folder_path: {e}")

    def show_error_popup(self, e):
        msg = CTkMessagebox(title="Error", message=f"An error occurred: {e}", icon="cancel", border_width=4, option_1="Exit", border_color="#F4511E", fade_in_duration=50, justify="center")
        if msg.get() == "Exit":
            self.destroy()
    
    def show_close_popup(self):
        msg = CTkMessagebox(title="Confirm exit", message="Do you want to cancel the install?", icon="question", option_2="No", option_1="Yes", border_width=4, border_color="#43A047", fade_in_duration=50, justify="center")
        if msg.get() == "Yes":
            self.destroy()
    
    def show_warning(self):
        msg = CTkMessagebox(title="Warning", message="Unable to connect to internet", icon="warning", option_2="Cancel", option_1="Retry", border_color="#43A047", fade_in_duration=50, justify="center")
        if msg.get() == "Retry":
            pass


if __name__ == "__main__":
    app = App()
    app.mainloop()