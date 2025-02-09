import dearpygui.dearpygui as dpg
import os
import json
import threading
import sys
import configparser
import pyperclip
import queue
import time
import ctypes
import webbrowser
import requests
from PIL import Image, ImageGrab
import numpy as np
import keyboard
from datetime import datetime


app_version = "2.1.4_Windows"
release_date = "2/9/2025"

sources: list = []
destinations: list = []
names: list = []

settings: dict = {
    "copy_folder_checkbox_state": False,
    "file_size_limit": 5,
    "show_image_status": True,
    "remember_window_pos": True,
    "skip_existing_files": True,
    "file_extensions": [".sav", ".save"],
    "folder_paths": [
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        os.path.join(os.getenv("USERPROFILE"), "Desktop"),
        os.path.join(os.getenv("USERPROFILE"), "AppData", "Roaming"),
        os.getenv("LOCALAPPDATA"),
        os.path.join(os.path.expanduser("~"), "Documents"),
        os.path.join("C:\\Users\\Public\\Documents"),
    ],
}

img_id = None

start_time_global = 0
total_bytes_global = 0
last_update_time = 0

texture_tag = None
drawlist_tag = None
zoom_level = 1.0
pan_offset = [0, 0]
drag_start_pos = None
img_size = (0, 0)
is_dragging = False

json_file_path = "save_folders.json"
config_file = "settings.ini"

config = configparser.ConfigParser()
progress_queue = queue.Queue()
cancel_flag = threading.Event()


def resource_path(relative_path):
    # Get the absolute path to the resource, works for dev and for PyInstaller
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


def load_setting(section, key, default=None):
    if os.path.exists(config_file):
        config.read(config_file)
        if config.has_section(section) and key in config[section]:
            return eval(
                config[section][key]
            )  # Convert string back to its original type
    return default


def load_settings():
    global settings

    if os.path.exists(config_file):
        config.read(config_file)
        # Check if the section exists and contains all settings
        if config.has_section("Settings"):
            for key in settings:
                try:
                    value = config.get("Settings", key)
                except:
                    value = None
                if value is not None:
                    # Convert string back to its original type
                    settings[key] = eval(value)

    return settings.copy()


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


def take_screenshot():
    img = ImageGrab.grab()
    filename = datetime.now().strftime("Screenshot_%Y-%m-%d_%H-%M-%S.png")
    filepath = os.path.join(
        os.path.join(os.path.expanduser("~"), "Documents"), filename
    )  # Save to the specified folder
    img.save(filepath)
    print(f"Screenshot saved as {filepath}")


def key_listener():
    keyboard.wait("F12")  # Wait for the F12 key to be pressed
    take_screenshot()


def set_cancel_to_true():
    global cancel_flag
    cancel_flag.set()


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
    global cancel_flag, settings
    try:
        progress_queue.put(("start", total_bytes))
        copied_bytes = 0
        for index in valid_entries:
            if cancel_flag.is_set():
                progress_queue.put(("cancel", "Copy cancelled by user!"))
                return
            source = sources[index]
            dest = destinations[index]
            name = names[index]

            if settings["copy_folder_checkbox_state"]:
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
                if cancel_flag.is_set():
                    progress_queue.put(("cancel", "Copy cancelled by user!"))
                    return
                rel_path = os.path.relpath(src_path, source)
                dest_path = os.path.join(dest, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                if (
                    os.path.exists(dest_path)
                    and settings["skip_existing_files"] == True
                ):
                    dpg.add_text(
                        f"Skipped (already exists): {rel_path}",
                        color=(139, 140, 0),  # Dark Orange
                        wrap=0,
                        parent="copy_log",
                    )
                    total_bytes -= size  # Subtract the size of the skipped file
                    progress_queue.put(("adjust_total", total_bytes))
                    continue  # Skip this file

                with open(src_path, "rb") as f_src, open(dest_path, "wb") as f_dst:
                    while chunk := f_src.read(1024 * 1024):  # 1MB chunks
                        if cancel_flag.is_set():
                            progress_queue.put(("cancel", "Copy cancelled by user!"))
                            return
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

        progress_queue.put(("complete", "Copying completed."))

    except Exception as e:
        progress_queue.put(("error", f"Error: {str(e)}"))
    finally:
        cancel_flag.clear()


def copy_all_callback(sender, app_data):
    global settings, cancel_flag

    cancel_flag.clear()
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
        if folder_size <= settings["file_size_limit"] * 1024**3:  # Check size limit
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
    global settings, cancel_flag

    cancel_flag.clear()
    sav_directories = set()
    file_extensions_tuple = tuple(settings["file_extensions"])

    dpg.set_value("finder_progress_bar", 0.0)
    dpg.show_item("finder_progress_bar")
    dpg.set_value("finder_text", "Starting search...")
    dpg.show_item("finder_text")

    dpg.set_value("search_status_text", "")
    dpg.hide_item("search_status_text")

    directories_to_search: list = []
    for folder in settings["folder_paths"]:
        if os.path.exists(folder):
            directories_to_search.append(folder)
        else:
            dpg.show_item("search_status_text")
            dpg.set_value(
                "search_status_text",
                f"Skipped directory '{folder}' as it does not exist.",
            )

    total_dirs: int = sum(
        len(dirs)
        for dirpath in directories_to_search
        for _, dirs, _ in os.walk(dirpath)
    )
    dpg.set_value("finder_text", "Searching...")

    processed_dirs: int = 0  # To count processed directories
    total_files: int = 0  # Count total files found

    def process_directory(directory):
        nonlocal processed_dirs, total_files
        try:
            for root, dirs, files in os.walk(directory):
                if cancel_flag.is_set():  # Check for exit signal
                    return
                processed_dirs += 1
                dpg.set_value("finder_progress_bar", processed_dirs / total_dirs)

                # Add files that match extensions
                for file in files:
                    if file.endswith(file_extensions_tuple):
                        sav_directories.add(root)
                        total_files += 1

                # Update progress every 10 directories
                if processed_dirs % 10 == 0:
                    dpg.set_value("finder_progress_bar", processed_dirs / total_dirs)

        except Exception as e:
            dpg.show_item("search_status_text")
            dpg.set_value(
                "search_status_text", f"Error processing directory {directory}: {e}"
            )

    # Use threading to prevent UI freezing
    def thread_target():
        for directory in directories_to_search:
            if cancel_flag.is_set():
                return
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


def check_for_updates(sender, app_data):
    threading.Thread(target=check_for_updates_thread).start()


def compare_versions(current, latest):
    current_parts = list(map(int, current.split(".")))
    latest_parts = list(map(int, latest.split(".")))

    for c, l in zip(current_parts, latest_parts):
        if c < l:
            return -1
        elif c > l:
            return 1

    if len(current_parts) < len(latest_parts):
        return -1
    elif len(current_parts) > len(latest_parts):
        return 1
    return 0


def check_for_updates_thread():
    try:
        repo_owner = "FlamingWater35"
        repo_name = "SaveManager"
        api_url = (
            f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        )

        response = requests.get(api_url)
        response.raise_for_status()
        release_data = response.json()

        latest_version = release_data["tag_name"].lstrip("v")
        current_version = app_version.split("_")[0].lstrip("v")

        if compare_versions(current_version, latest_version) < 0:
            progress_queue.put(("update", f"New version {latest_version} available!"))
            time.sleep(1)
            progress_queue.put(("open_url", release_data["html_url"]))
        else:
            progress_queue.put(("update", "You have the latest version"))
    except Exception as e:
        progress_queue.put(("update", f"Update check failed: {str(e)}"))


def open_image(sender, app_data):
    global texture_tag, drawlist_tag, zoom_level, pan_offset, img_size

    file_path = app_data["file_path_name"]
    if not os.path.exists(file_path):
        dpg.set_value("image_viewer_status_text", "File not found!")
        return

    try:
        image = Image.open(file_path).convert("RGBA")
    except Exception as e:
        dpg.set_value("image_viewer_status_text", f"Error loading image: {e}")
        return

    width, height = image.size
    img_size = (width, height)
    image_array = np.array(image).astype(np.float32) / 255.0
    image_data = image_array.flatten().tolist()

    # Clean up previous resources
    if texture_tag:
        # dpg.remove_alias(texture_tag)
        pass
    if drawlist_tag:
        dpg.delete_item(drawlist_tag)

    # Create new texture, change to dynamic texture if needed
    texture_tag = dpg.add_static_texture(
        width, height, image_data, parent="image_registry", tag="image_viewer_img"
    )

    # Reset view parameters
    zoom_level = 1.0
    pan_offset = [0, 0]
    update_image_display()

    dpg.set_value(
        "image_information",
        f"Loaded: {os.path.basename(file_path)} ({width}x{height})",
    )


def update_image_display():
    global drawlist_tag, texture_tag, zoom_level, pan_offset, img_size

    if drawlist_tag and dpg.does_item_exist(drawlist_tag):
        dpg.delete_item(drawlist_tag)

    drawlist_tag = dpg.generate_uuid()
    with dpg.drawlist(
        dpg.get_viewport_width(),
        dpg.get_viewport_height() / 1.4,
        tag=drawlist_tag,
        parent="image_viewer_child_window",
    ):
        if texture_tag:
            # Calculate scaled dimensions
            scaled_width = img_size[0] * zoom_level
            scaled_height = img_size[1] * zoom_level

            # Draw image with current zoom and pan
            dpg.draw_image(
                texture_tag,
                (pan_offset[0], pan_offset[1]),
                (pan_offset[0] + scaled_width, pan_offset[1] + scaled_height),
                uv_min=(0, 0),
                uv_max=(1, 1),
            )


def zoom_callback(sender, app_data):
    global zoom_level, pan_offset

    if not dpg.does_item_exist("image_viewer_img"):
        return

    # Get mouse position relative to image
    mouse_pos = dpg.get_mouse_pos(local=False)
    canvas_pos = dpg.get_item_pos("image_viewer_child_window")
    img_pos = [
        mouse_pos[0] - canvas_pos[0] - pan_offset[0],
        mouse_pos[1] - canvas_pos[1] - pan_offset[1],
    ]

    # Zoom speed
    delta = app_data
    zoom_factor = 1.1 if delta > 0 else 0.9
    new_zoom = zoom_level * zoom_factor

    # Limit zoom levels
    if 0.1 <= new_zoom <= 10:
        # Adjust pan offset to zoom around mouse
        pan_offset[0] = pan_offset[0] * zoom_factor + (img_pos[0] * (zoom_factor - 1))
        pan_offset[1] = pan_offset[1] * zoom_factor + (img_pos[1] * (zoom_factor - 1))
        zoom_level = new_zoom

    update_image_display()
    dpg.set_value(
        "image_viewer_status_text",
        f"Zoom: {zoom_level*100:.0f}% | Use mouse wheel to zoom, click+drag to pan",
    )


def start_drag():
    global drag_start_pos, pan_offset, is_dragging
    if not dpg.is_item_hovered("image_viewer_child_window"):
        is_dragging = True
        mouse_pos = dpg.get_mouse_pos(local=False)
        drag_start_pos = (mouse_pos[0] - pan_offset[0], mouse_pos[1] - pan_offset[1])


def end_drag():
    global is_dragging
    is_dragging = False


def handle_drag():
    global drag_start_pos, pan_offset, is_dragging
    if is_dragging and drag_start_pos is not None:
        mouse_pos = dpg.get_mouse_pos(local=False)
        pan_offset[0] = mouse_pos[0] - drag_start_pos[0]
        pan_offset[1] = mouse_pos[1] - drag_start_pos[1]
        update_image_display()


def remove_current_extension(sender, app_data):
    global settings

    settings["file_extensions"].remove(dpg.get_item_user_data(sender))
    save_settings("Settings", "file_extensions", settings["file_extensions"])
    dpg.set_value(
        "save_finder_text",
        f"Directories containing {settings["file_extensions"]} files will be listed below (click to copy to clipboard).",
    )

    dpg.delete_item("extension_list", children_only=True)
    for index, extension in enumerate(settings["file_extensions"], start=1):
        dpg.add_text(f"{index}: {extension}", parent="extension_list")
    dpg.hide_item("select_extension_text")
    dpg.show_item("extension_remove_button")
    dpg.show_item("extension_add_button")


def remove_extensions():
    global settings

    dpg.delete_item("extension_list", children_only=True)
    for index, extension in enumerate(settings["file_extensions"], start=1):
        dpg.add_selectable(
            label=f"{index}: {extension}",
            parent="extension_list",
            callback=remove_current_extension,
            user_data=extension,
        )
    dpg.show_item("select_extension_text")
    dpg.hide_item("extension_remove_button")
    dpg.hide_item("extension_add_button")


def add_extension():
    dpg.show_item("add_extension_group")
    dpg.show_item("comfirm_add_extension")
    dpg.hide_item("extension_remove_button")
    dpg.hide_item("extension_add_button")


def add_current_extension():
    global settings

    extension = dpg.get_value("add_extension_input")
    if extension != "":
        settings["file_extensions"].append(extension)
        save_settings("Settings", "file_extensions", settings["file_extensions"])
        dpg.set_value(
            "save_finder_text",
            f"Directories containing {settings["file_extensions"]} files will be listed below (click to copy to clipboard).",
        )

        dpg.delete_item("extension_list", children_only=True)
        for index, extension in enumerate(settings["file_extensions"], start=1):
            dpg.add_text(f"{index}: {extension}", parent="extension_list")
        dpg.hide_item("add_extension_group")
        dpg.hide_item("comfirm_add_extension")
        dpg.show_item("extension_remove_button")
        dpg.show_item("extension_add_button")


def open_file_extension_menu():
    global settings

    if dpg.does_item_exist("extension_manager_window"):
        dpg.delete_item("extension_manager_window")
    window_width = dpg.get_viewport_width() / 3
    window_height = dpg.get_viewport_height() / 2
    with dpg.window(
        label="Manage extensions",
        tag="extension_manager_window",
        modal=True,
        no_collapse=True,
        width=window_width,
        height=window_height,
        pos=[
            (dpg.get_viewport_width() / 2) - (window_width / 2),
            (dpg.get_viewport_height() / 2) - (window_height / 2),
        ],
    ):
        with dpg.group(horizontal=True):
            dpg.add_button(
                label="Add", callback=add_extension, tag="extension_add_button"
            )
            dpg.add_button(
                label="Remove",
                callback=remove_extensions,
                tag="extension_remove_button",
            )
            dpg.add_button(
                label="Comfirm",
                tag="comfirm_add_extension",
                show=False,
                callback=add_current_extension,
            )
        with dpg.group(horizontal=True, show=False, tag="add_extension_group"):
            dpg.add_text("Extension name")
            dpg.add_input_text(width=-1, tag="add_extension_input")
        dpg.add_text(
            "Select an item to remove:", tag="select_extension_text", show=False
        )
        with dpg.child_window(
            autosize_x=True, auto_resize_y=True, tag="extension_list"
        ):
            for index, extension in enumerate(settings["file_extensions"], start=1):
                dpg.add_text(f"{index}: {extension}")


def remove_current_folderpath(sender, app_data):
    global settings

    settings["folder_paths"].remove(dpg.get_item_user_data(sender))
    save_settings("Settings", "folder_paths", settings["folder_paths"])
    dpg.set_value(
        "save_finder_text",
        f"Directories containing {settings["folder_paths"]} files will be listed below (click to copy to clipboard).",
    )

    dpg.delete_item("folderpath_list", children_only=True)
    for index, folderpath in enumerate(settings["folder_paths"], start=1):
        dpg.add_text(f"{index}: {folderpath}", parent="folderpath_list")
    dpg.hide_item("select_folderpath_text")
    dpg.show_item("folderpath_remove_button")
    dpg.show_item("folderpath_add_button")


def remove_folderpaths():
    global settings

    dpg.delete_item("folderpath_list", children_only=True)
    for index, folderpath in enumerate(settings["folder_paths"], start=1):
        dpg.add_selectable(
            label=f"{index}: {folderpath}",
            parent="folderpath_list",
            callback=remove_current_folderpath,
            user_data=folderpath,
        )
    dpg.show_item("select_folderpath_text")
    dpg.hide_item("folderpath_remove_button")
    dpg.hide_item("folderpath_add_button")


def add_folderpath():
    dpg.show_item("add_folderpath_group")
    dpg.show_item("comfirm_add_folderpath")
    dpg.hide_item("folderpath_remove_button")
    dpg.hide_item("folderpath_add_button")


def add_current_folderpath():
    global settings

    folderpath = dpg.get_value("add_folderpath_input")
    if folderpath != "":
        settings["folder_paths"].append(folderpath)
        save_settings("Settings", "folder_paths", settings["folder_paths"])

        dpg.delete_item("folderpath_list", children_only=True)
        for index, folderpath in enumerate(settings["folder_paths"], start=1):
            dpg.add_text(f"{index}: {folderpath}", parent="folderpath_list")
        dpg.hide_item("add_folderpath_group")
        dpg.hide_item("comfirm_add_folderpath")
        dpg.show_item("folderpath_remove_button")
        dpg.show_item("folderpath_add_button")


def open_folder_path_menu():
    global settings

    if dpg.does_item_exist("folderpath_manager_window"):
        dpg.delete_item("folderpath_manager_window")
    window_width = dpg.get_viewport_width() / 3
    window_height = dpg.get_viewport_height() / 2
    with dpg.window(
        label="Manage folder paths",
        tag="folderpath_manager_window",
        modal=True,
        no_collapse=True,
        width=window_width,
        height=window_height,
        pos=[
            (dpg.get_viewport_width() / 2) - (window_width / 2),
            (dpg.get_viewport_height() / 2) - (window_height / 2),
        ],
    ):
        with dpg.group(horizontal=True):
            dpg.add_button(
                label="Add", callback=add_folderpath, tag="folderpath_add_button"
            )
            dpg.add_button(
                label="Remove",
                callback=remove_folderpaths,
                tag="folderpath_remove_button",
            )
            dpg.add_button(
                label="Comfirm",
                tag="comfirm_add_folderpath",
                show=False,
                callback=add_current_folderpath,
            )
        with dpg.group(horizontal=True, show=False, tag="add_folderpath_group"):
            dpg.add_text("Folder path")
            dpg.add_input_text(width=-1, tag="add_folderpath_input")
        dpg.add_text(
            "Select an item to remove:", tag="select_folderpath_text", show=False
        )
        with dpg.child_window(
            autosize_x=True, auto_resize_y=True, tag="folderpath_list"
        ):
            for index, folderpath in enumerate(settings["folder_paths"], start=1):
                dpg.add_text(f"{index}: {folderpath}")


def change_font_size(sender, app_data):
    save_settings("DisplayOptions", "font_size", app_data)


def settings_change_callback(sender, app_data):
    global settings

    setting = dpg.get_item_user_data(sender)
    if setting == "copy_folder":
        save_settings("Settings", "copy_folder_status", app_data)
    elif setting == "file_size_limit":
        save_settings("Settings", "file_size_limit", app_data)
    elif setting == "show_image":
        save_settings("Settings", "show_image_status", app_data)
    elif setting == "remember_window_pos":
        save_settings("Settings", "remember_window_pos", app_data)
    elif setting == "skip_existing_files":
        save_settings("Settings", "skip_existing_files", app_data)
    else:
        dpg.set_value(
            "status_text", "Changing setting failed; user_data incorrect or missing"
        )

    settings = load_settings()


def image_resize_callback():
    global settings, img_id
    image_enabled = settings["show_image_status"]
    if image_enabled == True:
        image_width = dpg.get_viewport_width() / 5.6
        new_x = dpg.get_viewport_width() - image_width - image_width / 20
        new_y = image_width / 20
        dpg.set_item_pos(img_id, (new_x, new_y))


def save_window_positions():
    save_settings("Window", "main_height", dpg.get_viewport_height())
    save_settings("Window", "main_width", dpg.get_viewport_width())
    save_settings("Window", "main_pos", dpg.get_viewport_pos())


def text_click_handler(sender, app_data, user_data):
    # Copy the text to the clipboard
    pyperclip.copy(user_data)
    # Update the status text to inform the user
    dpg.set_value("status_text", f"Copied to clipboard: {user_data}")


def show_windows():
    global img_id, settings

    # Add mouse drag handler
    with dpg.handler_registry():
        # Mouse wheel for zoom
        dpg.add_mouse_wheel_handler(callback=zoom_callback)

        # Mouse drag for panning
        dpg.add_mouse_down_handler(button=dpg.mvMouseButton_Left, callback=start_drag)
        dpg.add_mouse_release_handler(button=dpg.mvMouseButton_Left, callback=end_drag)
        dpg.add_mouse_move_handler(callback=handle_drag)

    with dpg.font_registry():
        # Add font file and size
        font_size = load_setting("DisplayOptions", "font_size")
        if font_size == None:
            font_size = default_font_size
        custom_font = dpg.add_font(font_path, font_size)

    with dpg.texture_registry(tag="image_registry"):
        width, height, channels, data = dpg.load_image(
            resource_path("docs/cute_image.png")
        )
        dpg.add_static_texture(
            width=width, height=height, default_value=data, tag="cute_image"
        )

    with dpg.item_handler_registry(tag="window_handler") as handler:
        dpg.add_item_resize_handler(callback=image_resize_callback)

    with dpg.theme() as child_window_theme:
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 15, 10)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 3, 3)
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 4, 4)
            dpg.add_theme_color(dpg.mvThemeCol_Border, (93, 64, 55))
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 5)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4, 4)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 2, 2)

    with dpg.theme() as main_window_theme:
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_Border, (21, 101, 192))

    with dpg.theme() as main_window_add_folder_theme:
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (43, 35, 32))

    dpg.bind_font(custom_font)
    dpg.configure_item("cute_image", width=dpg.get_viewport_width() / 5.6)
    dpg.configure_item("cute_image", height=dpg.get_viewport_width() / 7)

    with dpg.window(tag="Primary Window"):
        with dpg.menu_bar():
            with dpg.menu(label="About"):
                with dpg.menu(label="Information"):
                    dpg.add_text(f"Version: {app_version}")
                    dpg.add_text(f"Released: {release_date}")
                    with dpg.group(horizontal=True):
                        dpg.add_text(f"Creator: ")
                        dpg.add_button(
                            label="Flaming Water",
                            callback=lambda: webbrowser.open(
                                "https://github.com/FlamingWater35"
                            ),
                            small=True,
                        )
                dpg.add_menu_item(label="Check For Updates", callback=check_for_updates)
            with dpg.menu(label="Debug"):
                dpg.add_menu_item(
                    label="Show Metrics",
                    callback=lambda: dpg.show_tool(dpg.mvTool_Metrics),
                )

        with dpg.tab_bar():
            with dpg.tab(label="Copy Manager"):
                with dpg.child_window(
                    autosize_x=True, auto_resize_y=True, tag="copy_manager_main_window"
                ):
                    dpg.add_text("Copy Manager")
                    dpg.add_separator()
                    dpg.add_spacer(height=10)

                    with dpg.collapsing_header(label="Add folder pairs"):
                        with dpg.child_window(
                            autosize_x=True,
                            auto_resize_y=True,
                            tag="copy_manager_add_folder_window",
                        ):
                            # Input for the name
                            dpg.add_spacer(height=5)
                            dpg.add_input_text(
                                label="Name", tag="name_input", width=-300
                            )
                            dpg.add_spacer(height=5)

                            # Button to select source directory
                            dpg.add_button(
                                label="Select Source Directory",
                                callback=lambda: dpg.show_item("source_file_dialog"),
                            )
                            dpg.add_text(
                                "", tag="source_display"
                            )  # Display for source path
                            dpg.add_spacer(height=5)

                            # Button to select destination directory
                            dpg.add_button(
                                label="Select Destination Directory",
                                callback=lambda: dpg.show_item(
                                    "destination_file_dialog"
                                ),
                            )
                            dpg.add_text(
                                "", tag="destination_display"
                            )  # Display for destination path
                            dpg.add_spacer(height=5)

                            # Button to add the entry
                            dpg.add_button(
                                label="Add folder pair", callback=add_entry_callback
                            )
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

                    dpg.add_spacer(height=5)
                    with dpg.group(horizontal=True):
                        dpg.add_button(
                            label="Clear all pairs", callback=clear_entries_callback
                        )
                        dpg.add_button(label="Save pairs", callback=save_entries)

                    # Button to copy all entries
                    dpg.add_spacer(height=5)
                    dpg.add_separator()
                    dpg.add_spacer(height=5)
                    with dpg.group(horizontal=True):
                        dpg.add_button(
                            label="Run Copy Operation", callback=copy_all_callback
                        )
                        dpg.add_button(
                            label="Cancel Copy",
                            callback=set_cancel_to_true,
                            tag="cancel_button",
                        )

                    dpg.add_spacer(height=5)
                    dpg.add_text("", tag="status_text", color=(255, 140, 0), wrap=0)

                    # Progress Bar
                    dpg.add_spacer(height=5)
                    dpg.add_progress_bar(
                        tag="progress_bar",
                        default_value=0.0,
                        width=-200,
                        height=30,
                        show=False,
                        overlay="0.00 GB / 0.00 GB",
                    )

                    dpg.add_spacer(height=5)
                    dpg.add_text(
                        "", tag="speed_text", color=(0, 255, 0), show=False, wrap=0
                    )

                    dpg.add_spacer(height=5)
                    with dpg.collapsing_header(label="Log"):
                        dpg.add_text("Log:")
                        with dpg.child_window(tag="copy_log", auto_resize_y=True):
                            pass

                    if settings["show_image_status"] == True:
                        img_id = dpg.add_image("cute_image", pos=(0, 0))

            with dpg.tab(label="File Finder"):
                with dpg.child_window(
                    autosize_x=True, auto_resize_y=True, tag="save_finder_main_window"
                ):
                    dpg.add_text("File Finder")
                    dpg.add_separator()
                    dpg.add_spacer(height=10)
                    dpg.add_button(
                        label="Search for files", callback=start_search_thread
                    )
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
                        "Directories containing specified files will be listed below (click to copy to clipboard).",
                        tag="save_finder_text",
                        wrap=0,
                    )
                    dpg.add_spacer(height=5)
                    dpg.add_text(
                        "",
                        tag="search_status_text",
                        color=(229, 57, 53),
                        wrap=0,
                        show=False,
                    )
                    dpg.add_spacer(height=5)
                    with dpg.child_window(tag="directory_list", auto_resize_y=True):
                        pass

            with dpg.tab(label="Image viewer"):
                with dpg.child_window(
                    autosize_x=True, auto_resize_y=True, tag="image_viewer_main_window"
                ):
                    dpg.add_text("Image viewer")
                    dpg.add_separator()
                    dpg.add_spacer(height=10)
                    with dpg.group(horizontal=True):
                        dpg.add_button(
                            label="Open Image",
                            callback=lambda: dpg.show_item("open_image_dialog"),
                        )
                        dpg.add_spacer(width=10)
                        dpg.add_text("", tag="image_information")
                    dpg.add_spacer(height=10)
                    with dpg.child_window(
                        autosize_x=True,
                        auto_resize_y=True,
                        tag="image_viewer_child_window",
                        # border=False,
                    ):
                        pass
                    with dpg.group(horizontal=True):
                        dpg.add_text("", tag="image_viewer_status_text")

            with dpg.tab(label="Settings"):
                with dpg.child_window(
                    autosize_x=True, auto_resize_y=True, tag="settings_main_window"
                ):
                    dpg.add_text(
                        "Changes to font size will be applied after application restart",
                        wrap=0,
                    )
                    dpg.add_separator()

                    dpg.add_spacer(height=10)
                    dpg.add_text("Display", wrap=0)
                    with dpg.child_window(
                        autosize_x=True,
                        auto_resize_y=True,
                        tag="display_settings_child_window",
                    ):
                        pass
                    dpg.add_spacer(height=10)
                    dpg.add_text("Copy Manager", wrap=0)
                    with dpg.child_window(
                        autosize_x=True,
                        auto_resize_y=True,
                        tag="copy_manager_settings_child_window",
                    ):
                        pass
                    dpg.add_spacer(height=10)
                    dpg.add_text("File Finder", wrap=0)
                    with dpg.child_window(
                        autosize_x=True,
                        auto_resize_y=True,
                        tag="save_finder_settings_child_window",
                    ):
                        pass

    dpg.add_spacer(height=10, parent="display_settings_child_window")
    with dpg.group(horizontal=True, parent="display_settings_child_window"):
        dpg.add_text("Font size", wrap=0)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text("Sets the size for text and GUI elements")
        dpg.add_input_int(
            min_value=8,
            max_value=40,
            default_value=font_size,
            step=2,
            step_fast=2,
            width=200,
            callback=change_font_size,
        )
    dpg.add_spacer(height=20, parent="display_settings_child_window")
    with dpg.group(horizontal=True, parent="display_settings_child_window"):
        dpg.add_text(
            "Remember window position",
            wrap=0,
        )
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text("Whether to remember main window position and size")
        dpg.add_checkbox(
            default_value=settings["remember_window_pos"],
            callback=settings_change_callback,
            user_data="remember_window_pos",
        )
    dpg.add_spacer(height=20, parent="display_settings_child_window")
    with dpg.group(horizontal=True, parent="display_settings_child_window"):
        dpg.add_text("Show image", wrap=0)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text("Cute image in Copy Manager :3")
        dpg.add_checkbox(
            default_value=settings["show_image_status"],
            callback=settings_change_callback,
            user_data="show_image",
        )
    dpg.add_spacer(height=10, parent="display_settings_child_window")
    dpg.add_spacer(height=10, parent="copy_manager_settings_child_window")
    with dpg.group(horizontal=True, parent="copy_manager_settings_child_window"):
        dpg.add_text(
            "Copy source folder to destination",
            wrap=0,
        )
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text("If disabled, only files inside the folder will be copied")
        dpg.add_checkbox(
            default_value=settings["copy_folder_checkbox_state"],
            callback=settings_change_callback,
            user_data="copy_folder",
        )
    dpg.add_spacer(height=20, parent="copy_manager_settings_child_window")
    with dpg.group(horizontal=True, parent="copy_manager_settings_child_window"):
        dpg.add_text("Folder size limit", wrap=0)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text("Skip folders over set size")
        dpg.add_input_int(
            label="GB",
            min_value=1,
            max_value=500,
            default_value=settings["file_size_limit"],
            step=1,
            step_fast=1,
            width=200,
            callback=settings_change_callback,
            user_data="file_size_limit",
        )
    dpg.add_spacer(height=20, parent="copy_manager_settings_child_window")
    with dpg.group(horizontal=True, parent="copy_manager_settings_child_window"):
        dpg.add_text(
            "Skip existing files",
            wrap=0,
        )
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text("Don't override files")
        dpg.add_checkbox(
            default_value=settings["skip_existing_files"],
            callback=settings_change_callback,
            user_data="skip_existing_files",
        )
    dpg.add_spacer(height=10, parent="copy_manager_settings_child_window")
    dpg.add_spacer(height=10, parent="save_finder_settings_child_window")
    with dpg.group(horizontal=True, parent="save_finder_settings_child_window"):
        dpg.add_text(
            "File extensions to search",
            wrap=0,
        )
        dpg.add_spacer(width=10)
        dpg.add_button(label="Manage extensions", callback=open_file_extension_menu)
    dpg.add_spacer(height=20, parent="save_finder_settings_child_window")
    with dpg.group(horizontal=True, parent="save_finder_settings_child_window"):
        dpg.add_text(
            "Folder paths to search",
            wrap=0,
        )
        dpg.add_spacer(width=10)
        dpg.add_button(label="Manage folder paths", callback=open_folder_path_menu)
    dpg.add_spacer(height=10, parent="save_finder_settings_child_window")

    # File Dialog for selecting source directory
    with dpg.file_dialog(
        directory_selector=True,
        show=False,
        callback=source_callback,
        tag="source_file_dialog",
        cancel_callback=cancel_callback,
        width=dpg.get_viewport_width() / 1.5,
        height=dpg.get_viewport_height() / 1.5,
    ):
        pass  # Just add some settings or extension filters

    # File Dialog for selecting destination directory
    with dpg.file_dialog(
        directory_selector=True,
        show=False,
        callback=destination_callback,
        tag="destination_file_dialog",
        cancel_callback=cancel_callback,
        width=dpg.get_viewport_width() / 1.5,
        height=dpg.get_viewport_height() / 1.5,
    ):
        pass

    with dpg.file_dialog(
        directory_selector=False,
        show=False,
        callback=open_image,
        tag="open_image_dialog",
        width=dpg.get_viewport_width() / 1.5,
        height=dpg.get_viewport_height() / 1.5,
    ):
        dpg.add_file_extension(
            "Image files (*.png *.jpg *.jpeg *.bmp *.gif){.png,.jpg,.jpeg,.bmp,.gif}"
        )
        dpg.add_file_extension(".*")

    dpg.set_value(
        "save_finder_text",
        f"Directories containing {settings["file_extensions"]} files will be listed below (click to copy to clipboard).",
    )

    dpg.bind_item_theme("Primary Window", child_window_theme)
    dpg.bind_item_theme("copy_manager_main_window", main_window_theme)
    dpg.bind_item_theme("save_finder_main_window", main_window_theme)
    dpg.bind_item_theme("image_viewer_main_window", main_window_theme)
    dpg.bind_item_theme("settings_main_window", main_window_theme)
    dpg.bind_item_theme("copy_manager_add_folder_window", main_window_add_folder_theme)

    dpg.bind_item_handler_registry("Primary Window", "window_handler")
    dpg.set_primary_window("Primary Window", True)


def setup_viewport():
    global settings

    main_height = load_setting("Window", "main_height")
    main_width = load_setting("Window", "main_width")
    main_pos = load_setting("Window", "main_pos")
    user32 = ctypes.windll.user32
    screen_width, screen_height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

    launched = load_setting("DisplayOptions", "launched")
    if launched == None:
        launched = False

    # Set maximum width and height for the window
    if main_height != None:
        max_width = main_width
        max_height = main_height
    else:
        max_width = int(screen_width / 1.5)
        max_height = int(screen_height / 1.5)

    if launched == False:
        max_width = int(screen_width / 1.5)
        max_height = int(screen_height / 1.5)

    dpg.create_viewport(title="Save Manager", width=max_width, height=max_height)

    if main_pos != None and settings["remember_window_pos"] == True:
        dpg.set_viewport_pos(main_pos)

    if launched == False or settings["remember_window_pos"] == False:
        dpg.set_viewport_pos(
            [
                (screen_width / 2) - (dpg.get_viewport_width() / 2),
                (screen_height / 2) - (dpg.get_viewport_height() / 2),
            ]
        )

    save_settings("DisplayOptions", "launched", True)
    dpg.set_viewport_small_icon(resource_path("docs/icon.ico"))
    # Start the key listener in a separate thread
    key_thread = threading.Thread(target=key_listener, daemon=True)
    key_thread.start()


def main():
    global settings
    dpg.create_context()
    settings = load_settings()
    setup_viewport()
    show_windows()
    load_entries()

    dpg.setup_dearpygui()
    dpg.show_viewport()

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
                    progress_value = copied_bytes / total_bytes_global

                    # Update progress bar overlay text
                    dpg.configure_item(
                        "progress_bar",
                        overlay=f"{copied_gb:.2f} GB / {total_gb:.2f} GB ({int(progress_value*100)}%)",
                    )
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

                            remaining_seconds = int(remaining)
                            eta_mins = remaining_seconds // 60
                            eta_secs = remaining_seconds % 60
                            dpg.set_value(
                                "speed_text",
                                f"Speed: {speed_mb:.1f} MB/s | ETA: {eta_mins} min {eta_secs} sec",
                            )
                        last_update_time = current_time
            elif item_type == "adjust_total":
                total_bytes_global = data
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
            elif item_type == "update":
                dpg.set_value("status_text", data)
            elif item_type == "open_url":
                webbrowser.open(data)

        dpg.render_dearpygui_frame()

    def cleanup():
        global cancel_flag, settings

        cancel_flag.set()
        for thread in threading.enumerate():
            if thread is not threading.main_thread() and not thread.daemon:
                thread.join(timeout=2)

        if settings["remember_window_pos"] == True:
            save_window_positions()

    dpg.set_exit_callback(cleanup)
    dpg.destroy_context()


if __name__ == "__main__":
    main()
