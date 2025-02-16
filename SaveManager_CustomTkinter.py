import customtkinter as ct
import os
from tkinter import filedialog
from PIL import Image


class App(ct.CTk):
    def __init__(self):
        super().__init__()

        self.title("Save Manager")
        self.geometry(f"{1100}x{580}")
        self.iconbitmap(os.path.join(os.path.dirname(os.path.realpath(__file__)), "docs\\icon.ico"))

        ct.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
        ct.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.icon_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "docs\\icon.png")

        self.sidebar = Sidebar(self, border_width=5, fg_color=("gray86", "#213844"), icon_path=self.icon_path)

        self.copy_manager_button = ct.CTkButton(self.sidebar.button_frame, text="Copy Manager", height=32, command=self.open_copy_manager_frame)
        self.copy_manager_button.grid(row=0, column=0, padx=20, pady=10)

        self.settings_menu_button = ct.CTkButton(self.sidebar.button_frame, text="Settings", height=32, command=self.open_settings_frame)
        self.settings_menu_button.grid(row=1, column=0, padx=20, pady=10)

        self.copy_manager_frame = CopyManager(self, corner_radius=0, fg_color="transparent")
        self.settings_menu_frame = SettingsMenu(self, corner_radius=0, fg_color="transparent")

        self.select_tool(1)
        # print("Color:", self.copy_manager_frame.name_entry.cget("text_color"))

    def select_tool(self, tool_id):
        self.copy_manager_button.configure(fg_color=("green", "green") if tool_id == 1 else ("#3B8ED0", "#1F6AA5"), text_color_disabled=("#FFC107", "#FF9800"))
        self.settings_menu_button.configure(fg_color=("green", "green") if tool_id == 2 else ("#3B8ED0", "#1F6AA5"), text_color_disabled=("#FFC107", "#FF9800"))
        self.copy_manager_button.configure(state="disabled" if tool_id == 1 else "normal")
        self.settings_menu_button.configure(state="disabled" if tool_id == 2 else "normal")

        match tool_id:
            case 1:
                self.copy_manager_frame.grid(row=0, column=1, padx=20, pady=10)
                self.settings_menu_frame.grid_forget()
            case 2:
                self.settings_menu_frame.grid(row=0, column=1, padx=20, pady=10)
                self.copy_manager_frame.grid_forget()
                self.copy_manager_frame.folderpair_status_text.configure(text="")
    
    def open_copy_manager_frame(self):
        self.select_tool(1)

    def open_settings_frame(self):
        self.select_tool(2)


class Sidebar(ct.CTkFrame):
    def __init__(self, master, width=200, height=200, corner_radius=None, border_width=None, bg_color="transparent", fg_color=None, border_color=None, background_corner_colors=None, icon_path=None, **kwargs):
        super().__init__(master, width, height, corner_radius, border_width, bg_color, fg_color, border_color, background_corner_colors, **kwargs)

        self.grid(column=0, row=0, rowspan=4, padx=30, pady=30, ipadx=20, ipady=20, sticky="nsew")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure((1, 2), weight=1)
        self.grid_rowconfigure(3, weight=0)

        self.icon = ct.CTkImage(Image.open(icon_path), size=(40, 40))

        self.logo_label = ct.CTkLabel(self, text=" SaveManager", image=self.icon, compound="left", font=ct.CTkFont(size=22, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=10, pady=(40, 10), sticky="nsew")

        self.button_frame = ct.CTkFrame(self, fg_color="transparent")
        self.button_frame.grid(row=1, rowspan=2, column=0, padx=10, pady=10)
        self.button_frame.grid_columnconfigure(0, weight=1)
        self.button_frame.grid_rowconfigure((0, 1, 2, 3, 4), weight=1)

        self.settings_button_frame = ct.CTkFrame(self, fg_color="transparent")
        self.settings_button_frame.grid(row=3, column=0, padx=10, pady=10)
        self.settings_button_frame.grid_columnconfigure(0, weight=1)
        self.settings_button_frame.grid_rowconfigure((0, 1), weight=1)

        self.appearance_mode_optionmenu = ct.CTkOptionMenu(self.settings_button_frame, values=["System", "Light", "Dark"], command=self.change_appearance_mode_event)
        self.appearance_mode_optionmenu.grid(row=0, column=0, padx=20, pady=10, sticky="s")

        self.update_check_button = ct.CTkButton(self.settings_button_frame, text="Update", command=None)
        self.update_check_button.grid(row=1, column=0, padx=20, pady=(10, 20), sticky="s")
    
    def change_appearance_mode_event(self, new_appearance_mode: str):
        ct.set_appearance_mode(new_appearance_mode)


class CopyManager(ct.CTkFrame):
    def __init__(self, master, width = 200, height = 200, corner_radius = None, border_width = None, bg_color = "transparent", fg_color = None, border_color = None, background_corner_colors = None, **kwargs):
        super().__init__(master, width, height, corner_radius, border_width, bg_color, fg_color, border_color, background_corner_colors, **kwargs)

        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.current_folderpair_number: int = 0
        self.folderpair_dictionary: dict = {}
        self.source_folder_path = ct.StringVar(value="Source Folder")
        self.destination_folder_path = ct.StringVar(value="Destination Folder")

        self.copy_manager_tabs = ct.CTkTabview(self, width=250)
        self.copy_manager_tabs.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 20), sticky="nsew")
        self.copy_manager_tabs.add("Folder Pairs")
        self.copy_manager_tabs.add("Copy Operation")

        self.copy_manager_tabs.tab("Folder Pairs").grid_columnconfigure((0, 2), weight=1)
        self.copy_manager_tabs.tab("Folder Pairs").grid_rowconfigure((0, 1, 2, 3), weight=1)
        self.copy_manager_tabs.tab("Folder Pairs").grid_rowconfigure(4, weight=10)
        self.copy_manager_tabs.tab("Folder Pairs").grid_rowconfigure(5, weight=20)
        self.copy_manager_tabs.tab("Copy Operation").grid_columnconfigure((0, 1), weight=1)

        self.name_entry = ct.CTkEntry(self.copy_manager_tabs.tab("Folder Pairs"), placeholder_text="Folder Pair Name:")
        self.name_entry.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="nsew")

        self.source_folder_entry = ct.CTkEntry(self.copy_manager_tabs.tab("Folder Pairs"), width=800, textvariable=self.source_folder_path, state="disabled", text_color=("gray52", "gray62"))
        self.source_folder_entry.grid(row=1, column=0, padx=(20, 5), pady=10, sticky="nsew")

        self.source_folder_button = ct.CTkButton(self.copy_manager_tabs.tab("Folder Pairs"), text="Select", width=80, command=self.select_source_folder)
        self.source_folder_button.grid(row=1, column=1, padx=(5, 20), pady=10, sticky="nsew")

        self.destination_folder_entry = ct.CTkEntry(self.copy_manager_tabs.tab("Folder Pairs"), width=800, textvariable=self.destination_folder_path, state="disabled", text_color=("gray52", "gray62"))
        self.destination_folder_entry.grid(row=2, column=0, padx=(20, 5), pady=10, sticky="nsew")

        self.destination_folder_button = ct.CTkButton(self.copy_manager_tabs.tab("Folder Pairs"), text="Select", width=80, command=self.select_destination_folder)
        self.destination_folder_button.grid(row=2, column=1, padx=(5, 20), pady=10, sticky="nsew")

        self.add_folderpair_button = ct.CTkButton(self.copy_manager_tabs.tab("Folder Pairs"), text="Add Folder Pair", command=self.add_folder_pair)
        self.add_folderpair_button.grid(row=3, column=0, columnspan=2, padx=20, pady=(10, 10), sticky="nsew")

        self.folderpair_status_text = ct.CTkLabel(self.copy_manager_tabs.tab("Folder Pairs"), text="", text_color=("#004D40", "#558B2F"))
        self.folderpair_status_text.grid(row=4, column=0, columnspan=2, padx=20, pady=(5, 5), sticky="nsew")

        self.folderpair_list_frame = ct.CTkScrollableFrame(self.copy_manager_tabs.tab("Folder Pairs"), label_text="Added Folder Pairs:")
        self.folderpair_list_frame.grid(row=5, column=0, columnspan=2, padx=20, pady=(5, 20), sticky="sew")
        self.folderpair_list_frame.grid_columnconfigure(0, weight=1)

        self.folderpair = ct.CTkTextbox(self.folderpair_list_frame, wrap="char", height=700)
        self.folderpair.grid(row=0, column=0, padx=10, pady=(0, 20), sticky="nsew")
        self.folderpair.configure(state="disabled")

        self.log_frame = ct.CTkScrollableFrame(self.copy_manager_tabs.tab("Copy Operation"), label_text="Log:")
        self.log_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=(5, 5), sticky="nsew")
        self.log_frame.grid_columnconfigure(0, weight=1)

    def select_source_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.source_folder_path.set(folder_path)
            self.source_folder_entry.configure(text_color="#FF6F00")
    
    def select_destination_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.destination_folder_path.set(folder_path)
            self.destination_folder_entry.configure(text_color="#FF6F00")
    
    def add_folder_pair(self):
        name = self.name_entry.get()
        source = self.source_folder_path.get()
        dest = self.destination_folder_path.get()
        if name != "" and name != " " and source != "Source Folder" and dest != "Destination Folder":
            self.folderpair_dictionary[self.current_folderpair_number] = [name, source, dest]
            self.folderpair_status_text.configure(text="")

            self.source_folder_path.set("Source Folder")
            self.destination_folder_path.set("Destination Folder")
            self.name_entry.delete(0, "end")

            self.source_folder_entry.configure(text_color=("gray52", "gray62"))
            self.destination_folder_entry.configure(text_color=("gray52", "gray62"))
            
            self.folderpair.configure(state="normal")
            self.folderpair.insert(f"{self.current_folderpair_number}.0", f"Name: {name}\nFrom: {source}\nTo: {dest}\n\n")
            self.folderpair.configure(state="disabled")
            self.current_folderpair_number += 1
        else:
            self.folderpair_status_text.configure(text="Fill out the name and select folders first")


class SettingsMenu(ct.CTkFrame):
    def __init__(self, master, width = 200, height = 200, corner_radius = None, border_width = None, bg_color = "transparent", fg_color = None, border_color = None, background_corner_colors = None, **kwargs):
        super().__init__(master, width, height, corner_radius, border_width, bg_color, fg_color, border_color, background_corner_colors, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.logo_label = ct.CTkLabel(self, text="Settings", font=ct.CTkFont(size=22, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 40), sticky="nsew")


if __name__ == "__main__":
    app = App()
    app.mainloop()
