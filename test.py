import customtkinter as ct
from tkinter import filedialog
import os
import logging
from CTkToolTip import CTkToolTip
from CTkMessagebox import CTkMessagebox


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

class App(ct.CTk):
    def __init__(self):
        super().__init__()

        self.title("SaveManager Setup")
        window_width = 1100
        window_height = 580

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
        
        if page_num == len(self.pages) - 1:
            self.next_button.configure(text="Finish")
        else:
            self.next_button.configure(text="Next")

        if page_num > 0:
            self.back_button.configure(text="Back", command=lambda: self.switch_page(self.current_page - 1))
        else:
            self.back_button.configure(text="Cancel", command=self.show_close_popup)

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
        page.grid_rowconfigure((0, 1, 2), weight=1)
        self.pages.append(page)

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