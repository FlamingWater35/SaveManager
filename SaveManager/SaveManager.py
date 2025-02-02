import dearpygui.dearpygui as dpg
import os
import json
import threading
import sys
import configparser
import pyperclip
import queue
import time


dpg.create_context()

# Lists to store source, destination directories and names
sources = []
destinations = []
names = []

copy_folder_checkbox_state = False
file_size_limit = 5
cancel_flag = False
start_time_global = 0
total_bytes_global = 0
last_update_time = 0

# File path for the JSON file
json_file_path = "save_folders.json"
config_file = "settings.ini"

config = configparser.ConfigParser()
progress_queue = queue.Queue()


def resource_path(relative_path):
    """Get the absolute path to the resource, works for dev and for PyInstaller"""
    if getattr(sys, "frozen", False):
        # If the application is frozen (i.e., running as a .exe)
        base_path = sys._MEIPASS
    else:
        # If running in a normal Python environment
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


font_path = resource_path("docs/font.otf")
default_font_size = 20
font_size = default_font_size


# Function to load settings from the .ini file
def load_settings(section, key, default=None):
    if os.path.exists(config_file):
        config.read(config_file)
        if config.has_section(section) and key in config[section]:
            return eval(
                config[section][key]
            )  # Convert string back to its original type
    return default


# Function to save settings to the .ini file
def save_settings(section, key, value):
    if not config.has_section(section):
        config.add_section(section)
    config[section][key] = str(value)
    with open(config_file, "w") as configfile:
        config.write(configfile)


def load_entries():
    global sources, destinations, names
    if os.path.exists(json_file_path):
        with open(json_file_path, "r") as f:
            entries = json.load(f)
            for entry in entries:
                names.append(entry["name"])
                sources.append(entry["source"])
                destinations.append(entry["destination"])

                item_id = dpg.add_text(
                    f"{entry['name']}: {entry['source']} -> {entry['destination']}",
                    parent="entry_list",
                    wrap=0,
                    user_data=[entry["source"], entry["destination"]],
                )

                with dpg.item_handler_registry(tag=f"text_handler_{item_id}"):
                    dpg.add_item_clicked_handler(
                        user_data=dpg.get_item_user_data(item_id)[0],
                        callback=text_click_handler,
                    )
                    dpg.add_item_double_clicked_handler(
                        user_data=dpg.get_item_user_data(item_id)[1],
                        callback=text_click_handler,
                    )
                dpg.bind_item_handler_registry(item_id, f"text_handler_{item_id}")


def save_entries():
    entries = []
    for name, source, destination in zip(names, sources, destinations):
        entries.append({"name": name, "source": source, "destination": destination})
    with open(json_file_path, "w") as f:
        json.dump(entries, f, indent=4)
    dpg.set_value("status_text", "Entries saved successfully.")


def clear_entries_callback(sender, app_data):
    global sources, destinations, names
    sources.clear()
    destinations.clear()
    names.clear()

    # Clear the displayed entries
    dpg.delete_item("entry_list", children_only=True)
    dpg.set_value("status_text", "All entries cleared.")

    # Clear the JSON file
    if os.path.exists(json_file_path):
        os.remove(json_file_path)


def add_entry_callback(sender, app_data):
    name = dpg.get_value("name_input")

    if name and sources and destinations:
        current_source = sources[-1]  # Get the last added source
        current_destination = destinations[-1]  # Get the last added destination

        # Add the new entry
        names.append(name)
        item_id = dpg.add_text(
            f"{name}: {current_source} -> {current_destination}",
            parent="entry_list",
            wrap=0,
            user_data=[current_source, current_destination],
        )

        with dpg.item_handler_registry(tag=f"text_handler_{item_id}"):
            dpg.add_item_clicked_handler(
                user_data=dpg.get_item_user_data(item_id)[0],
                callback=text_click_handler,
            )
            dpg.add_item_double_clicked_handler(
                user_data=dpg.get_item_user_data(item_id)[1],
                callback=text_click_handler,
            )
        dpg.bind_item_handler_registry(item_id, f"text_handler_{item_id}")

        # Clear the displayed paths
        dpg.set_value("source_display", "")
        dpg.set_value("destination_display", "")
        dpg.set_value("name_input", "")  # Clear name input
        dpg.set_value("status_text", f"Added entry: {name}")
    else:
        dpg.set_value("status_text", "Please fill the name and select folders.")


def set_cancel_to_true():
    global cancel_flag
    cancel_flag = True


def get_folder_size(folder):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # Check if file exists to avoid errors
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    return total_size


def copy_thread(valid_entries, total_bytes):
    global cancel_flag
    try:
        progress_queue.put(("start", total_bytes))
        copied_bytes = 0
        for index in valid_entries:
            if cancel_flag:
                progress_queue.put(("cancel", "Copy cancelled by user!"))
                break
            source = sources[index]
            dest = destinations[index]
            name = names[index]

            if copy_folder_checkbox_state:
                new_destination = os.path.join(dest, os.path.basename(source))
                os.makedirs(new_destination, exist_ok=True)
                dest = new_destination

            # Get all files with sizes
            file_list = []
            for root, _, files in os.walk(source):
                for file in files:
                    path = os.path.join(root, file)
                    file_list.append((path, os.path.getsize(path)))

            # Copy files with progress
            for src_path, size in file_list:
                if cancel_flag:
                    break
                rel_path = os.path.relpath(src_path, source)
                dest_path = os.path.join(dest, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                if os.path.exists(dest_path):
                    dpg.add_text(
                        f"Skipped (already exists): {rel_path}",
                        color=(139, 140, 0),  # Dark Orange
                        wrap=0,
                        parent="copy_log",
                    )
                    continue  # Skip this file

                with open(src_path, "rb") as f_src, open(dest_path, "wb") as f_dst:
                    while chunk := f_src.read(1024 * 1024):  # 1MB chunks
                        if cancel_flag:
                            break
                        f_dst.write(chunk)
                        copied_bytes += len(chunk)
                        progress_queue.put(("progress", copied_bytes))

                # Add a text item for the copied file
                dpg.add_text(
                    f"Copied: {rel_path}",
                    wrap=0,
                    color=(0, 140, 139),
                    parent="copy_log",
                )

        if not cancel_flag:
            progress_queue.put(("complete", "Copying completed."))
        else:
            progress_queue.put(("cancel", "Copy cancelled by user!"))

    except Exception as e:
        progress_queue.put(("error", f"Error: {str(e)}"))
    finally:
        cancel_flag = False


def copy_all_callback(sender, app_data):
    global copy_folder_checkbox_state, file_size_limit, cancel_flag
    cancel_flag = False
    dpg.delete_item("copy_log", children_only=True)
    dpg.set_value("speed_text", "")
    dpg.show_item("speed_text")

    if not sources or not destinations or not names:
        dpg.set_value("status_text", "No entries to copy.")
        return

    # Calculate total size and valid entries
    total_bytes = 0
    valid_entries = []
    for index in range(len(sources)):
        source = sources[index]
        folder_size = get_folder_size(source)
        if folder_size <= file_size_limit * 1024**3:  # Check size limit
            valid_entries.append(index)
            total_bytes += folder_size
        else:
            dpg.add_text(
                f"Skipped {source} as it exceeds size limit.",
                color=(139, 140, 0),
                wrap=0,
                parent="copy_log",
            )

    if not valid_entries:
        dpg.set_value("status_text", "No entries to copy (all exceed size limit).")
        return

    # Setup UI
    dpg.set_value("progress_bar", 0.0)
    dpg.set_value("status_text", "Copying directories...")
    dpg.show_item("progress_bar")

    # Start copy thread
    threading.Thread(target=copy_thread, args=(valid_entries, total_bytes)).start()


def source_callback(sender, app_data):
    sources.append(app_data["file_path_name"])  # Store the selected source
    dpg.set_value(
        "source_display", app_data["file_path_name"]
    )  # Display the selected source path


def destination_callback(sender, app_data):
    destinations.append(app_data["file_path_name"])  # Store the selected destination
    dpg.set_value(
        "destination_display", app_data["file_path_name"]
    )  # Display the selected destination path


def cancel_callback(sender, app_data):
    dpg.set_value("status_text", "Operation was cancelled.")


def search_files():
    local_app_data = os.getenv("LOCALAPPDATA")
    documents_path = os.path.join(os.path.expanduser("~"), "Documents")
    public_documents_path = os.path.join("C:\\Users\\Public\\Documents")
    common_paths = [
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        os.path.join(os.getenv("USERPROFILE"), "Desktop"),
        os.path.join(os.getenv("USERPROFILE"), "AppData", "Roaming"),
    ]

    file_extensions = (".sav", ".save")
    sav_directories = set()

    dpg.set_value("finder_progress_bar", 0.0)
    dpg.show_item("finder_progress_bar")
    dpg.set_value("finder_text", "Starting search...")
    dpg.show_item("finder_text")

    directories_to_search = [
        local_app_data,
        documents_path,
        public_documents_path,
    ] + common_paths

    total_dirs = sum(
        len(dirs)
        for dirpath in directories_to_search
        for _, dirs, _ in os.walk(dirpath)
    )
    dpg.set_value("finder_text", "Searching...")

    processed_dirs = 0  # To count processed directories
    total_files = 0  # Count total files found

    def process_directory(directory):
        nonlocal processed_dirs, total_files
        try:
            for root, dirs, files in os.walk(directory):
                processed_dirs += 1
                dpg.set_value("finder_progress_bar", processed_dirs / total_dirs)

                # Add files that match extensions
                for file in files:
                    if file.endswith(file_extensions):
                        sav_directories.add(root)
                        total_files += 1

                # Update progress every 10 directories
                if processed_dirs % 10 == 0:
                    dpg.set_value("finder_progress_bar", processed_dirs / total_dirs)

        except Exception as e:
            print(f"Error processing directory {directory}: {e}")

    # Use threading to prevent UI freezing
    def thread_target():
        for directory in directories_to_search:
            process_directory(directory)

        # Final UI update
        dpg.set_value("finder_progress_bar", 1.0)
        dpg.hide_item("finder_progress_bar")
        dpg.hide_item("finder_text")

        # Update UI with found directories
        if dpg.does_item_exist("directory_list"):
            dpg.delete_item("directory_list", children_only=True)

        colors = [
            (0, 140, 139),  # Dark Cyan
            (255, 140, 0),  # Dark Orange
        ]
        color_index = 0

        if sav_directories:
            for index, directory in enumerate(sorted(sav_directories), start=1):
                cur_color = colors[color_index]
                item_id = dpg.add_text(
                    f"{index}. {directory}",
                    wrap=0,
                    parent="directory_list",
                    color=cur_color,
                    user_data=directory,
                )

                with dpg.item_handler_registry(tag=f"text_handler_{item_id}"):
                    dpg.add_item_clicked_handler(
                        user_data=dpg.get_item_user_data(item_id),
                        callback=text_click_handler,
                    )
                dpg.bind_item_handler_registry(item_id, f"text_handler_{item_id}")

                color_index = (color_index + 1) % len(colors)
        else:
            dpg.add_text(
                "No files found.",
                wrap=0,
                parent="directory_list",
            )

    # Start the search in a separate thread
    thread = threading.Thread(target=thread_target)
    thread.start()


def start_search_thread():
    threading.Thread(target=search_files).start()


# File Dialog for selecting source directory
dpg.add_file_dialog(
    directory_selector=True,
    show=False,
    callback=source_callback,
    tag="source_file_dialog",
    cancel_callback=cancel_callback,
    width=800,
    height=450,
)

# File Dialog for selecting destination directory
dpg.add_file_dialog(
    directory_selector=True,
    show=False,
    callback=destination_callback,
    tag="destination_file_dialog",
    cancel_callback=cancel_callback,
    width=800,
    height=450,
)


with dpg.font_registry():
    # Add font file and size
    font_size = load_settings("DisplayOptions", "font_size")
    if font_size == None:
        font_size = default_font_size
    custom_font = dpg.add_font(font_path, font_size)


def change_font_size(sender, app_data):
    save_settings("DisplayOptions", "font_size", app_data)


def copy_folder_checkbox_callback(sender, app_data):
    global copy_folder_checkbox_state
    save_settings("DisplayOptions", "copy_folder_status", app_data)
    copy_folder_checkbox_state = load_settings("DisplayOptions", "copy_folder_status")
    if copy_folder_checkbox_state == None:
        copy_folder_checkbox_state = False


def file_size_limit_callback(sender, app_data):
    global file_size_limit
    save_settings("DisplayOptions", "file_size_limit", app_data)
    file_size_limit = load_settings("DisplayOptions", "file_size_limit")
    if file_size_limit == None:
        file_size_limit = 5


def open_settings():
    global copy_folder_checkbox_state

    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()

    # Set maximum width and height for the window
    max_width = 800
    max_height = 500

    # Calculate position to center within the viewport
    pos_x = max(0, (viewport_width - max_width) // 2)
    pos_y = max(0, (viewport_height - max_height) // 2)

    if not dpg.does_item_exist("settings_window"):
        with dpg.window(
            label="Settings",
            modal=True,
            width=max_width,
            height=max_height,
            no_collapse=True,
            no_resize=False,  # Change to true when needed
            no_move=False,  # Change to true when needed
            pos=[pos_x, pos_y - 30],
            tag="settings_window",
        ):
            dpg.add_text(
                "Changes to font size will be applied after application restart",
                wrap=0,
            )
            dpg.add_separator()
            dpg.add_spacer(height=10)

            with dpg.child_window(auto_resize_x=True, width=-1):
                with dpg.group(horizontal=True):
                    dpg.add_text("Font size")
                    dpg.add_slider_int(
                        min_value=8,
                        max_value=40,
                        default_value=font_size,
                        width=-100,
                        callback=change_font_size,
                    )
                dpg.add_spacer(height=20)
                with dpg.group(horizontal=True):
                    dpg.add_text(
                        "Copy entire source folder to destination (if disabled, only files inside selected folder)",
                        wrap=0,
                    )
                    dpg.add_checkbox(
                        default_value=copy_folder_checkbox_state,
                        callback=copy_folder_checkbox_callback,
                    )
                dpg.add_spacer(height=20)
                with dpg.group(horizontal=True):
                    dpg.add_text("Size limit")
                    dpg.add_slider_int(
                        label="GB",
                        min_value=1,
                        max_value=500,
                        default_value=file_size_limit,
                        width=-100,
                        callback=file_size_limit_callback,
                    )
    else:
        dpg.show_item("settings_window")


def image_resize_callback():
    window_width = dpg.get_item_width("Primary Window")
    new_x = window_width - 220
    new_y = 20
    dpg.set_item_pos(img_id, (new_x, new_y))


def save_window_positions():
    if dpg.does_item_exist("save_finder_window"):
        save_settings(
            "Window", "save_finder_height", dpg.get_item_height("save_finder_window")
        )
        save_settings(
            "Window", "save_finder_width", dpg.get_item_width("save_finder_window")
        )
    save_settings("Window", "main_height", dpg.get_item_height("Primary Window"))
    save_settings("Window", "main_width", dpg.get_item_width("Primary Window"))


def text_click_handler(sender, app_data, user_data):
    # Copy the text to the clipboard
    pyperclip.copy(user_data)
    # Update the status text to inform the user
    dpg.set_value("status_text", f"Copied to clipboard: {user_data}")


with dpg.texture_registry():
    width, height, channels, data = dpg.load_image(resource_path("docs/cute_image.png"))
    dpg.add_static_texture(
        width=width, height=height, default_value=data, tag="cute_image"
    )

with dpg.window(tag="Primary Window"):
    with dpg.menu_bar():
        with dpg.menu(label="Tools"):
            dpg.add_menu_item(label="Save Finder")
        with dpg.menu(label="Settings"):
            dpg.add_menu_item(label="Display options", callback=open_settings)
            dpg.add_menu_item(label="Save window pos", callback=save_window_positions)

    with dpg.tab_bar():
        with dpg.tab(label="Copy Manager"):
            dpg.add_text("Directory Copy Manager")
            dpg.add_separator()
            dpg.add_spacer(height=10)

            with dpg.collapsing_header(label="Add folder pairs"):
                with dpg.child_window(autosize_x=True, auto_resize_y=True):
                    # Input for the name
                    dpg.add_spacer(height=5)
                    dpg.add_input_text(label="Name", tag="name_input", width=-300)
                    dpg.add_spacer(height=5)

                    # Button to select source directory
                    dpg.add_button(
                        label="Select Source Directory",
                        callback=lambda: dpg.show_item("source_file_dialog"),
                    )
                    dpg.add_text("", tag="source_display")  # Display for source path
                    dpg.add_spacer(height=5)

                    # Button to select destination directory
                    dpg.add_button(
                        label="Select Destination Directory",
                        callback=lambda: dpg.show_item("destination_file_dialog"),
                    )
                    dpg.add_text(
                        "", tag="destination_display"
                    )  # Display for destination path
                    dpg.add_spacer(height=5)

                    # Button to add the entry
                    dpg.add_button(label="Add folder pair", callback=add_entry_callback)
                    dpg.add_spacer(height=5)

            dpg.add_spacer(height=5)
            dpg.add_separator()

            # Container for displaying entries
            dpg.add_text(
                "Folder pairs will appear below (click or double click to copy to clipboard):",
                wrap=0,
            )

            with dpg.child_window(tag="entry_list", auto_resize_y=True):
                # This will hold all entries
                pass

            # Button to copy all entries
            dpg.add_spacer(height=5)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Run Copy Operation", callback=copy_all_callback)
                dpg.add_button(
                    label="Cancel Copy",
                    callback=set_cancel_to_true,
                    tag="cancel_button",
                )

            # Progress Bar
            dpg.add_spacer(height=5)
            dpg.add_progress_bar(
                tag="progress_bar",
                default_value=0.0,
                width=-200,
                height=20,
                show=False,
                overlay="0.00 GB / 0.00 GB",
            )
            dpg.add_spacer(height=5)
            dpg.add_separator()

            # Horizontal group for Save and Clear All buttons
            dpg.add_spacer(height=5)
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Clear all entries", callback=clear_entries_callback
                )
                dpg.add_button(label="Save entries to JSON", callback=save_entries)

            dpg.add_spacer(height=5)
            dpg.add_text("", tag="status_text", color=(255, 140, 0), wrap=0)
            dpg.add_text("", tag="speed_text", color=(0, 255, 0), show=False, wrap=0)

            with dpg.collapsing_header(label="Log"):
                dpg.add_text("Log:")
                with dpg.child_window(tag="copy_log", auto_resize_y=True):
                    pass

            img_id = dpg.add_image("cute_image", pos=(0, 0), width=250, height=200)

        with dpg.tab(label="Save Finder"):
            with dpg.child_window(autosize_x=True, auto_resize_y=True):
                dpg.add_button(label="Search for files", callback=start_search_thread)
                dpg.add_spacer(height=5)
                dpg.add_progress_bar(
                    tag="finder_progress_bar",
                    default_value=0.0,
                    width=400,
                    height=20,
                    show=False,
                )
                dpg.add_text("", tag="finder_text", show=False)
                dpg.add_separator()
                dpg.add_text(
                    "Directories containing .sav and .save files will be listed below (click to copy to clipboard).",
                    wrap=0,
                )

                with dpg.group(tag="directory_list"):
                    pass

                dpg.add_separator()
                dpg.add_spacer(height=20)


def setup_viewport():
    global copy_folder_checkbox_state
    global file_size_limit
    main_height = load_settings("Window", "main_height")
    main_width = load_settings("Window", "main_width")

    copy_folder_checkbox_state = load_settings("DisplayOptions", "copy_folder_status")
    if copy_folder_checkbox_state != True and copy_folder_checkbox_state != False:
        copy_folder_checkbox_state = False

    file_size_limit = load_settings("DisplayOptions", "file_size_limit")
    if file_size_limit == None:
        file_size_limit = 5

    # Set maximum width and height for the window
    if main_height != None:
        max_width = main_width
        max_height = main_height
    else:
        max_width = 1000
        max_height = 600

    dpg.create_viewport(title="Save Manager", width=max_width, height=max_height)
    dpg.set_viewport_small_icon(resource_path("docs/icon.ico"))


def main():
    # Load entries on application start
    load_entries()

    with dpg.item_handler_registry(tag="window_handler") as handler:
        dpg.add_item_resize_handler(callback=image_resize_callback)

    dpg.bind_item_handler_registry("Primary Window", "window_handler")
    dpg.bind_font(custom_font)
    setup_viewport()
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("Primary Window", True)

    while dpg.is_dearpygui_running():
        while not progress_queue.empty():
            item_type, data = progress_queue.get()
            if item_type == "start":
                total_bytes_global = data
                start_time_global = time.time()
                last_update_time = start_time_global
            elif item_type == "progress":
                copied_bytes = data
                if total_bytes_global > 0:
                    copied_gb = copied_bytes / (1024**3)
                    total_gb = total_bytes_global / (1024**3)

                    # Update progress bar overlay text
                    dpg.configure_item(
                        "progress_bar",
                        overlay=f"{copied_gb:.2f} GB / {total_gb:.2f} GB",
                    )

                    progress_value = copied_bytes / total_bytes_global
                    dpg.set_value("progress_bar", progress_value)

                    # Calculate speed and time
                    current_time = time.time()
                    if current_time - last_update_time >= 0.5:
                        elapsed = current_time - start_time_global
                        if elapsed > 0:
                            speed = copied_bytes / elapsed  # bytes/sec
                            speed_mb = speed / (1024**2)
                            remaining = (total_bytes_global - copied_bytes) / max(
                                speed, 1
                            )
                            mins_remaining = remaining / 60
                            dpg.set_value(
                                "speed_text",
                                f"Speed: {speed_mb:.1f} MB/s | ETA: {mins_remaining:.1f} mins",
                            )
                        last_update_time = current_time
            elif item_type == "complete":
                dpg.set_value("status_text", data)
                dpg.hide_item("progress_bar")
                dpg.hide_item("speed_text")
            elif item_type == "cancel":
                dpg.set_value("status_text", data)
                dpg.hide_item("progress_bar")
                dpg.hide_item("speed_text")
            elif item_type == "error":
                dpg.add_text(data, color=(229, 57, 53), wrap=0, parent="copy_log")
                dpg.hide_item("progress_bar")
                dpg.hide_item("speed_text")

        dpg.render_dearpygui_frame()

    def cleanup():
        global cancel_flag
        cancel_flag = True

    dpg.set_exit_callback(cleanup)
    dpg.destroy_context()


if __name__ == "__main__":
    main()
