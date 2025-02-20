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
from PIL import ImageGrab
import keyboard
from datetime import datetime
import ast
import dxcam
import cv2
import logging
import shutil
import pywinstyles
from win32 import win32gui
import customtkinter as ct
from tkinter import filedialog


app_version: str = "2.6.0_Windows"
release_date: str = "2/20/2025"

sources: list = []
destinations: list = []
names: list = []

settings: dict = {
    "copy_folder_checkbox_state": False,
    "file_size_limit": 5,
    "show_image_status": False,
    "remember_window_pos": True,
    "skip_existing_files": True,
    "clear_destination_folder": False,
    "skip_hidden_files": False,
    "file_extensions": [".sav", ".save"],
    "folder_paths": [
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        os.path.join(os.getenv("USERPROFILE"), "Desktop"),
        os.path.join(os.getenv("USERPROFILE"), "AppData", "Roaming"),
        os.getenv("LOCALAPPDATA"),
        os.path.join(os.path.expanduser("~"), "Documents"),
        "C:\\Users\\Public\\Documents",
    ],
    "ignored_folders": [],
}

recording_settings: dict = {
    "screenshot_key": "f12",
    "screenshot_folder": os.path.join(os.path.expanduser("~"), "Documents"),
    "video_fps": 60,
    "video_folder": os.path.join(os.path.expanduser("~"), "Documents"),
    "video_duration": 30,
}

img_id = None
is_recording_keybind = False
target_app_frame_rate: int = -1

start_time_global = 0
total_bytes_global = 0
last_update_time = 0


config = configparser.ConfigParser()
progress_queue = queue.Queue()
cancel_flag = threading.Event()


"""def resource_path(relative_path):
    # Get the absolute path to the resource, works for dev and for PyInstaller
    if getattr(sys, "frozen", False):
        # If the application is frozen (i.e., running as a .exe)
        base_path = sys._MEIPASS
    else:
        # If running in a normal Python environment
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)"""


def resource_path(relative_path):
    # Get the directory of the executable (or script in development)
    if "__compiled__" in globals():  # Check if running as a Nuitka bundle
        base_path = os.path.dirname(sys.executable)  # Executable's directory
    else:
        base_path = os.path.abspath(".")

    full_path = os.path.join(base_path, relative_path)

    if not os.path.exists(full_path):
        os.makedirs(full_path, exist_ok=True)
        logging.error(f"Resource not found: {full_path}")

    return full_path


data_dir = resource_path("app_data")
json_file_path = os.path.join(data_dir, "save_folders.json")
config_file = os.path.join(data_dir, "settings.ini")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

font_path = resource_path("docs/font.otf")
default_font_size = 24


def run_application():
    logging.info("\n\n--------- APPLICATION START ---------\n")


def load_setting(section, key, default=None):
    if os.path.exists(config_file):
        config.read(config_file)
        if config.has_section(section) and key in config[section]:
            logging.debug(f"Loaded setting: {key}")
            return ast.literal_eval(
                config[section][key]
            )  # Convert string back to its original type
    logging.warning(f"Loading setting failed; Config file not found: {config_file}")
    return default


def load_settings():
    global settings, recording_settings

    if os.path.exists(config_file):
        config.read(config_file)
        if config.has_section("Settings"):
            for key in settings:
                try:
                    value = config.get("Settings", key)
                except:
                    value = None
                if value is not None:
                    # Convert string back to its original type
                    settings[key] = ast.literal_eval(value)
        if config.has_section("Recording"):
            for key in recording_settings:
                try:
                    value = config.get("Recording", key)
                except:
                    value = None
                if value is not None:
                    match key:
                        case "screenshot_folder":
                            recording_settings[key] = value
                        case "video_folder":
                            recording_settings[key] = value
                        case _:
                            # Convert string back to its original type
                            recording_settings[key] = ast.literal_eval(value)
        logging.debug(f"Loaded settings from: {config_file}")
    else:
        logging.warning(
            f"Loading settings failed; Config file not found: {config_file}"
        )


def save_settings(section, key, value):
    if not config.has_section(section):
        config.add_section(section)
    config[section][key] = str(value)
    with open(config_file, "w") as configfile:
        config.write(configfile)
    logging.debug(f"Saved setting: {key}")


def reset_settings():
    if os.path.exists(config_file):
        with open(config_file, "w"):
            if config.has_section("Settings"):
                config.remove_section("Settings")
                logging.debug("Reset section 'Settings' from config file")
            if config.has_section("DisplayOptions"):
                try:
                    value = config.get("DisplayOptions", "font_size")
                except:
                    value = None
                if value != None:
                    config.remove_option("DisplayOptions", "font_size")
                    logging.debug("Reset font_size from config file")


def load_entries():
    global sources, destinations, names

    sources.clear()
    destinations.clear()
    names.clear()

    if os.path.exists(json_file_path):
        with open(json_file_path, "r") as f:
            entries = json.load(f)
            for entry in entries:
                entry_name = entry["name"]
                entry_source = entry["source"]
                entry_dest = entry["destination"]

                names.append(entry_name)
                sources.append(entry_source)
                destinations.append(entry_dest)

                item_id = dpg.add_collapsing_header(
                    label=f"Folder Pair: {entry_name}",
                    parent="entry_list",
                )
                with dpg.theme() as entry_item_theme:
                    with dpg.theme_component(dpg.mvCollapsingHeader):
                        dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 5, 5)
                        dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0, 0)
                        dpg.add_theme_color(
                            dpg.mvThemeCol_Header,
                            (27, 94, 32),
                            category=dpg.mvThemeCat_Core,
                        )
                dpg.bind_item_theme(item_id, entry_item_theme)
                source_item_id = dpg.add_text(
                    f" Source: {entry_source}",
                    wrap=0,
                    color=(236, 64, 122),
                    parent=item_id,
                    user_data=entry_source,
                )
                dest_item_id = dpg.add_text(
                    f" Destination: {entry_dest}",
                    wrap=0,
                    color=(171, 71, 188),
                    parent=item_id,
                    user_data=entry_dest,
                )

                with dpg.item_handler_registry(tag=f"text_handler_{source_item_id}"):
                    dpg.add_item_clicked_handler(
                        user_data=dpg.get_item_user_data(source_item_id),
                        callback=text_click_handler,
                    )
                with dpg.item_handler_registry(tag=f"text_handler_{dest_item_id}"):
                    dpg.add_item_clicked_handler(
                        user_data=dpg.get_item_user_data(dest_item_id),
                        callback=text_click_handler,
                    )
                dpg.bind_item_handler_registry(
                    source_item_id, f"text_handler_{source_item_id}"
                )
                dpg.bind_item_handler_registry(
                    dest_item_id, f"text_handler_{dest_item_id}"
                )
        logging.debug(f"Copy Manager entries loaded: {json_file_path}")
    else:
        logging.warning(
            f"Loading Copy Manager entries failed; JSON file not found: {json_file_path}"
        )
    if dpg.get_item_children("entry_list", slot=1) == []:
        dpg.add_text(
            "No folder pairs added", tag="no_entries_text", parent="entry_list", wrap=0
        )


def save_entries():
    global sources, destinations, names

    entries = []
    for name, source, destination in zip(names, sources, destinations):
        entries.append({"name": name, "source": source, "destination": destination})
    with open(json_file_path, "w") as f:
        json.dump(entries, f, indent=4)
    dpg.set_value("status_text", "Folder pairs saved successfully.")
    logging.debug("Copy Manager entries saved to JSON")


def clear_entries_callback(sender, app_data):
    global sources, destinations, names

    sources.clear()
    destinations.clear()
    names.clear()

    dpg.delete_item("entry_list", children_only=True)
    dpg.set_value("status_text", "All folder pairs cleared.")

    if os.path.exists(json_file_path):
        os.remove(json_file_path)
        logging.debug("JSON file deleted upon clearing entries")
    load_entries()


def clear_latest_entry(sender, app_data):
    global sources, destinations, names

    try:
        sources.pop()
        destinations.pop()
        names.pop()
    except IndexError:
        return

    dpg.delete_item("entry_list", children_only=True)

    if os.path.exists(json_file_path):
        os.remove(json_file_path)
    save_entries()
    load_entries()
    dpg.set_value("status_text", "The latest folder pair has been cleared.")
    logging.debug("Latest entry deleted from JSON file")


def add_entry_callback(sender, app_data):
    global sources, destinations, names

    name = dpg.get_value("name_input")
    if name in names:
        dpg.set_value(
            "status_text", f"Folder pair '{name}' already exists; pick another name"
        )
        dpg.set_value("name_input", "")
        return

    if name and sources and destinations:
        current_source = sources[-1]
        current_destination = destinations[-1]

        names.append(name)
        item_id = dpg.add_collapsing_header(
            label=f"Folder Pair: {name}",
            parent="entry_list",
        )
        with dpg.theme() as entry_item_theme:
            with dpg.theme_component(dpg.mvCollapsingHeader):
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 5, 5)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0, 0)
                dpg.add_theme_color(
                    dpg.mvThemeCol_Header, (27, 94, 32), category=dpg.mvThemeCat_Core
                )
        dpg.bind_item_theme(item_id, entry_item_theme)
        source_item_id = dpg.add_text(
            f" Source: {current_source}",
            wrap=0,
            color=(236, 64, 122),
            parent=item_id,
            user_data=current_source,
        )
        dest_item_id = dpg.add_text(
            f" Destination: {current_destination}",
            wrap=0,
            color=(171, 71, 188),
            parent=item_id,
            user_data=current_destination,
        )

        with dpg.item_handler_registry(tag=f"text_handler_{source_item_id}"):
            dpg.add_item_clicked_handler(
                user_data=dpg.get_item_user_data(source_item_id),
                callback=text_click_handler,
            )
        with dpg.item_handler_registry(tag=f"text_handler_{dest_item_id}"):
            dpg.add_item_clicked_handler(
                user_data=dpg.get_item_user_data(dest_item_id),
                callback=text_click_handler,
            )
        dpg.bind_item_handler_registry(source_item_id, f"text_handler_{source_item_id}")
        dpg.bind_item_handler_registry(dest_item_id, f"text_handler_{dest_item_id}")

        dpg.set_value("source_display", "")
        dpg.set_value("destination_display", "")
        dpg.set_value("name_input", "")
        dpg.set_value("status_text", f"Added folder pair: '{name}'")
        if dpg.does_item_exist("no_entries_text"):
            dpg.delete_item("no_entries_text")
        save_entries()
    else:
        dpg.set_value("status_text", "Please fill the name and select folders.")


def record_video_thread():
    global recording_settings, target_app_frame_rate

    target_app_frame_rate = 30
    target_fps = recording_settings["video_fps"]
    filename = datetime.now().strftime("SaveManager_recording_%Y-%m-%d_%H-%M-%S.mp4")
    filepath = os.path.join(recording_settings["video_folder"], filename)

    user32 = ctypes.windll.user32
    screen_width, screen_height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    try:
        openh264_path = resource_path("docs/openh264-1.8.0-win64.dll")
        ctypes.cdll.LoadLibrary(openh264_path)

        camera = dxcam.create(output_idx=0, output_color="BGR")
        camera.start(target_fps=target_fps, video_mode=True)
    except Exception as e:
        dpg.set_value("recording_status_text", f"Error initializing video: {e}")
        logging.error(f"Initializing video failed: {e}")

    # VideoWriter configuration (adjust codec if needed)
    writer = cv2.VideoWriter(
        filepath,
        cv2.VideoWriter_fourcc(*"avc1"),
        target_fps,
        (screen_width, screen_height),
    )
    dpg.show_item("recording_status_text")
    dpg.set_value("recording_status_text", f"Recording video...")

    try:
        for _ in range(target_fps * recording_settings["video_duration"]):
            frame = camera.get_latest_frame()
            writer.write(frame)
    except Exception as e:
        dpg.set_value("recording_status_text", f"Error recording video: {e}")
        logging.error(f"Error occurred while recording video: {e}")
        return

    camera.stop()
    writer.release()
    target_app_frame_rate = -1
    dpg.show_item("start_video_recording_button")
    dpg.set_value("recording_status_text", f"Recording saved as: {filename}")
    logging.debug("Video recorded successfully")


def start_video_recording_thread():
    global recording_settings

    dpg.hide_item("start_video_recording_button")
    video_folder = recording_settings["video_folder"]
    if not os.path.exists(video_folder):
        dpg.set_value(
            "recording_status_text", "Invalid folder path. Changing to default value."
        )
        logging.warning("Invalid folder path for video folder, defaulting")
        video_folder = os.path.join(os.path.expanduser("~"), "Documents")
        save_settings("Recording", "video_folder", video_folder)
        load_settings()

    logging.debug("Video recording thread started")
    video_thread = threading.Thread(target=record_video_thread, daemon=True)
    video_thread.start()


def set_video_setting(sender, app_data):
    global recording_settings

    setting = dpg.get_item_user_data(sender)
    if setting == "FPS":
        save_settings("Recording", "video_fps", int(app_data))
    elif setting == "duration":
        save_settings("Recording", "video_duration", int(app_data))
    else:
        dpg.set_value(
            "recording_status_text",
            "Changing setting failed; user_data incorrect or missing",
        )

    load_settings()


def take_screenshot():
    global recording_settings

    img = ImageGrab.grab()
    filename = datetime.now().strftime("Screenshot_%Y-%m-%d_%H-%M-%S.png")
    filepath = os.path.join(recording_settings["screenshot_folder"], filename)
    try:
        img.save(filepath)
    except Exception as e:
        dpg.set_value("recording_status_text", f"Saving screenshot failed: {e}")
        logging.error(f"Error occurred while saving screenshot: {e}")
        return
    dpg.show_item("recording_status_text")
    dpg.set_value("recording_status_text", f"Screenshot saved as {filepath}")
    logging.debug(f"Screenshot saved successfully as: {filepath}")


def key_listener():
    global recording_settings

    while True:
        try:
            keyboard.wait(recording_settings["screenshot_key"])
        except Exception as e:
            dpg.show_item("recording_status_text")
            dpg.set_value("recording_status_text", f"Error with key listener: {e}")
            logging.error(f"Screenhot key error when called by key listener: {e}")
            break
        take_screenshot()
        time.sleep(0.5)


def start_key_listener():
    global recording_settings

    dpg.hide_item("start_key_listener_button")
    screenshot_folder = recording_settings["screenshot_folder"]
    if not os.path.exists(screenshot_folder):
        dpg.set_value(
            "recording_status_text", "Invalid folder path. Changing to default value."
        )
        logging.warning("Invalid folder path for screenshot folder, defaulting")
        screenshot_folder = os.path.join(os.path.expanduser("~"), "Documents")
        save_settings("Recording", "screenshot_folder", screenshot_folder)
        load_settings()

    logging.debug("Screnshot key listener thread started")
    key_thread = threading.Thread(target=key_listener, daemon=True)
    key_thread.start()


def keybind_recorder_thread():
    global recording_settings, is_recording_keybind
    try:
        key = keyboard.read_key(suppress=False)
        current_keybind = recording_settings["screenshot_key"]
        if key != current_keybind:
            current_keybind = key
            save_settings("Recording", "screenshot_key", f'"{current_keybind}"')
            load_settings()
            dpg.configure_item(
                "start_keybind_recording_button", label=f"{current_keybind}"
            )
            dpg.set_value(
                "recording_status_text", f"New keybind set to: {current_keybind}"
            )
        else:
            dpg.set_value(
                "recording_status_text", f"Keybind unchanged: {current_keybind}"
            )
    except Exception as e:
        dpg.set_value("recording_status_text", f"Error when recording keybind: {e}")
        logging.error(f"Error during keybind recorder thread: {e}")
    finally:
        is_recording_keybind = False
        dpg.show_item("start_keybind_recording_button")


def start_keybind_recording():
    global is_recording_keybind
    if not is_recording_keybind:
        dpg.hide_item("start_keybind_recording_button")
        is_recording_keybind = True
        dpg.show_item("recording_status_text")
        dpg.set_value("recording_status_text", "Press any key...")
        logging.debug("Screenshot keybind recording thread started")
        threading.Thread(target=keybind_recorder_thread, daemon=True).start()


def set_cancel_to_true():
    global cancel_flag
    cancel_flag.set()
    dpg.show_item("copy_button")
    dpg.hide_item("cancel_button")
    logging.debug("Non-daemon threads signaled to exit")


def set_log_filter(sender, app_data):
    try:
        level = dpg.get_item_user_data(sender)[0]
        show_flag = dpg.get_item_user_data(sender)[1]

        if show_flag == "shown":
            log_items = dpg.get_item_children("copy_log", slot=1)
            for item in log_items:
                if dpg.get_item_user_data(item) == level:
                    dpg.hide_item(item)
            dpg.configure_item(sender, user_data=[level, "hidden"])
            sender_label = dpg.get_item_configuration(sender)["label"]
            dpg.configure_item(sender, label=f"{sender_label} (hidden)")

        elif show_flag == "hidden":
            log_items = dpg.get_item_children("copy_log", slot=1)
            for item in log_items:
                if dpg.get_item_user_data(item) == level:
                    dpg.show_item(item)
            dpg.configure_item(sender, user_data=[level, "shown"])
            sender_label = dpg.get_item_configuration(sender)["label"]
            new_label = sender_label.replace(" (hidden)", "")
            dpg.configure_item(sender, label=f"{new_label}")
    except Exception as e:
        logging.error(f"Exception occurred with log filter: {e}")


def delete_folder_with_children():
    global destinations

    dpg.set_value("status_text", "Clearing destination folders...")
    for destination_folder in destinations:
        if not os.path.exists(destination_folder):
            logging.error(
                f"The folder '{destination_folder}' does not exist. (this error should not be possible if everything above works correctly)"
            )
            return

        for item in os.listdir(destination_folder):
            item_path = os.path.join(destination_folder, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    # Delete files and symbolic links
                    os.unlink(item_path)
                    dpg.add_text(
                        f"Deleted file: '{item_path}'",
                        color=(139, 140, 0),
                        wrap=0,
                        parent="copy_log",
                        user_data="delete",
                    )
                elif os.path.isdir(item_path):
                    # Optionally, delete subfolders and their contents
                    shutil.rmtree(item_path)
                    dpg.add_text(
                        f"Deleted folder and its contents: '{item_path}'",
                        color=(139, 140, 0),
                        wrap=0,
                        parent="copy_log",
                        user_data="delete",
                    )
            except Exception as e:
                dpg.add_text(
                    f"Failed to delete '{item_path}': {e}",
                    color=(229, 57, 53),
                    wrap=0,
                    parent="copy_log",
                    user_data="error",
                )
                logging.error(f"Deleting files failed: {e}")


def get_folder_size(source):
    global settings

    total_size = 0
    for root, dirs, files in os.walk(source):
        # Check if the current folder should be ignored
        current_folder_abs = os.path.abspath(root)
        if current_folder_abs in settings["ignored_folders"]:
            dirs[:] = []
            continue
        # Prevent hidden folders
        if settings["skip_hidden_files"] and os.path.basename(root).startswith("."):
            dirs[:] = []
            continue

        # Add the size of files in non-ignored folders
        for file in files:
            if settings["skip_hidden_files"] and file.startswith("."):
                continue
            file_path = os.path.join(root, file)
            try:
                total_size += os.path.getsize(file_path)
            except FileNotFoundError:
                logging.error("File deleted during folder size calculation")
                continue
    return total_size


def copy_thread(valid_entries, total_bytes):
    global cancel_flag, settings, sources, destinations, names
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
            ignored_folders = settings["ignored_folders"]
            for root, dirs, files in os.walk(source):
                rel_dir_path = os.path.relpath(root, source)
                current_folder_abs = os.path.abspath(root)

                # Skip ignored folders
                if current_folder_abs in ignored_folders:
                    rel_ignored_path = os.path.relpath(current_folder_abs, source)
                    dpg.add_text(
                        f"Ignored because of a setting: '{rel_ignored_path}'",
                        color=(139, 140, 0),
                        wrap=0,
                        parent="copy_log",
                        user_data="ignore",
                    )
                    # Skip this folder and its contents by clearing the dirs list
                    dirs[:] = []
                    continue

                # Skip hidden folders
                if settings["skip_hidden_files"] and os.path.basename(root).startswith(
                    "."
                ):
                    dpg.add_text(
                        f"Skipped (hidden folder): '{rel_dir_path}'",
                        color=(139, 140, 0),
                        wrap=0,
                        parent="copy_log",
                        user_data="skip",
                    )
                    dirs[:] = []  # Prevent traversal into hidden folders
                    continue

                # Ensure empty folders are copied
                dest_dir_path = os.path.join(dest, rel_dir_path)
                os.makedirs(dest_dir_path, exist_ok=True)

                # Collect files from non-ignored folders
                for file in files:
                    if settings["skip_hidden_files"] and file.startswith(
                        "."
                    ):  # Skip hidden files
                        dpg.add_text(
                            f"Skipped (hidden file): '{file}'",
                            color=(139, 140, 0),
                            wrap=0,
                            parent="copy_log",
                            user_data="skip",
                        )
                        continue
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
                        f"Skipped (already exists): '{rel_path}'",
                        color=(139, 140, 0),
                        wrap=0,
                        parent="copy_log",
                        user_data="skip",
                    )
                    total_bytes -= size  # Adjust total size
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

                dpg.add_text(
                    f"Copied: '{rel_path}'",
                    wrap=0,
                    color=(0, 140, 139),
                    parent="copy_log",
                    user_data="copy",
                )

        progress_queue.put(("complete", "Copying completed."))

    except Exception as e:
        progress_queue.put(("error", f"Error: {str(e)}"))
    finally:
        cancel_flag.clear()
        dpg.show_item("copy_button")
        dpg.hide_item("cancel_button")


def copy_all_callback(sender, app_data):
    global settings, cancel_flag, sources, destinations, names

    dpg.hide_item("copy_button")
    dpg.show_item("cancel_button")
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
        dest = destinations[index]
        name = names[index]
        invalid_entry: bool = False

        match (os.path.exists(source), os.path.exists(dest)):
            case (False, True):
                dpg.add_text(
                    f"Folder pair '{name}' skipped as folder '{source}' does not exist.",
                    color=(229, 57, 53),
                    wrap=0,
                    parent="copy_log",
                    user_data="skip",
                )
                invalid_entry = True
            case (True, False):
                dpg.add_text(
                    f"Folder pair '{name}' skipped as folder '{dest}' does not exist.",
                    color=(229, 57, 53),
                    wrap=0,
                    parent="copy_log",
                    user_data="skip",
                )
                invalid_entry = True
            case (False, False):
                dpg.add_text(
                    f"Folder pair '{name}' skipped as folders '{source}' and '{dest}' do not exist.",
                    color=(229, 57, 53),
                    wrap=0,
                    parent="copy_log",
                    user_data="skip",
                )
                invalid_entry = True

        if not invalid_entry:
            folder_size = get_folder_size(source)
            if folder_size <= settings["file_size_limit"] * 1024**3:  # Check size limit
                valid_entries.append(index)
                total_bytes += folder_size
            else:
                dpg.add_text(
                    f"Skipped folder pair '{name}' as it exceeds size limit.",
                    color=(139, 140, 0),
                    wrap=0,
                    parent="copy_log",
                    user_data="skip",
                )

    match invalid_entry:
        case False:
            if not valid_entries:
                dpg.set_value(
                    "status_text", "No entries to copy (all exceed size limit)."
                )
                return
        case True:
            if not valid_entries:
                dpg.set_value("status_text", "No entries to copy (check log).")
                return

    if settings["clear_destination_folder"]:
        delete_folder_with_children()

    dpg.set_value("progress_bar", 0.0)
    dpg.set_value("status_text", "Copying directories...")
    dpg.show_item("progress_bar")

    threading.Thread(target=copy_thread, args=(valid_entries, total_bytes)).start()


def open_source_file_dialog():
    global sources

    try:
        main = ct.CTk()
        main.iconbitmap(resource_path("docs/icon.ico"))
        main.withdraw()
        folder_path = filedialog.askdirectory(title="Select folder to copy")
        main.destroy()
    except Exception as e:
        logging.error(f"Exception occurred during folder select: {e}")

    if folder_path:
        sources.append(folder_path)
        dpg.set_value("source_display", folder_path)
    else:
        dpg.set_value("status_text", "Folder not selected")


def open_destination_file_dialog():
    global destinations

    try:
        main = ct.CTk()
        main.iconbitmap(resource_path("docs/icon.ico"))
        main.withdraw()
        folder_path = filedialog.askdirectory(title="Select folder to copy in")
        main.destroy()
    except Exception as e:
        logging.error(f"Exception occurred during folder select: {e}")

    if folder_path:
        destinations.append(folder_path)
        dpg.set_value("destination_display", folder_path)
    else:
        dpg.set_value("status_text", "Folder not selected")


def screenshot_folder_select_callback(sender, app_data):
    global recording_settings

    save_settings("Recording", "screenshot_folder", app_data["file_path_name"])
    load_settings()
    dpg.configure_item(
        "screenshot_file_dialog", default_path=recording_settings["screenshot_folder"]
    )
    dpg.set_value("recording_status_text", "Screenshot folder changed.")


def video_folder_select_callback(sender, app_data):
    global recording_settings

    save_settings("Recording", "video_folder", app_data["file_path_name"])
    load_settings()
    dpg.configure_item(
        "video_file_dialog", default_path=recording_settings["video_folder"]
    )
    dpg.set_value("recording_status_text", "Video folder changed.")


def cancel_callback(sender, app_data):
    dpg.set_value("status_text", "Operation was cancelled.")


def recording_cancel_callback(sender, app_data):
    dpg.set_value("recording_status_text", "Operation was cancelled.")


def search_files():
    global settings, cancel_flag

    dpg.hide_item("file_search_button")
    cancel_flag.clear()
    sav_directories = set()
    file_extensions_tuple = tuple(settings["file_extensions"])

    dpg.set_value("finder_progress_bar", 0.0)
    dpg.show_item("finder_progress_bar")
    dpg.set_value("finder_text", "Starting search... (might take a while)")
    dpg.show_item("finder_text")

    dpg.set_value("search_status_text", "")
    dpg.hide_item("search_status_text")

    directories_to_search: list = []
    invalid_paths: list = []
    for folder in settings["folder_paths"]:
        if os.path.exists(folder):
            directories_to_search.append(folder)
        else:
            invalid_paths.append(folder)
            if len(invalid_paths) == 1:
                dpg.show_item("search_status_text")
                dpg.set_value(
                    "search_status_text",
                    f"Skipped directory '{folder}' as it does not exist.",
                )
            else:
                dpg.set_value(
                    "search_status_text",
                    f"Skipped directories '{invalid_paths}' as they do not exist.",
                )

    total_dirs = sum(
        len(dirs)
        for dirpath in directories_to_search
        for _, dirs, _ in os.walk(dirpath)
    )
    dpg.set_value("finder_text", "Searching...")

    processed_dirs: int = 0
    total_files: int = 0

    def process_directory(directory):
        nonlocal processed_dirs, total_files
        try:
            for root, dirs, files in os.walk(directory):
                if cancel_flag.is_set():
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
            logging.error(f"Error when processing directory during file search: {e}")

    # Using threading to prevent UI freezing
    def thread_target():
        global cancel_flag

        for directory in directories_to_search:
            if cancel_flag.is_set():
                return
            process_directory(directory)

        dpg.set_value("finder_progress_bar", 1.0)
        dpg.hide_item("finder_progress_bar")
        dpg.hide_item("finder_text")

        if dpg.does_item_exist("directory_list"):
            dpg.delete_item("directory_list", children_only=True)

        colors = [
            (0, 140, 139),
            (255, 140, 0),
        ]
        color_index = 0

        if sav_directories:
            try:
                for index, directory in enumerate(sorted(sav_directories), start=1):
                    if cancel_flag.is_set():
                        return
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
            except Exception as e:
                logging.error(
                    f"Error occurred while adding searched files as text items: {e}"
                )
        else:
            dpg.add_text(
                "No files found.",
                wrap=0,
                parent="directory_list",
            )
        dpg.show_item("file_search_button")

    thread = threading.Thread(target=thread_target)
    thread.start()


def start_search_thread():
    logging.debug("Search thread started")
    threading.Thread(target=search_files).start()


def check_for_updates(sender, app_data):
    logging.debug("Update check thread started")
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
        logging.error(f"Update check failed: {e}")


def remove_current_extension(sender, app_data):
    global settings

    file_extension_list: list = settings["file_extensions"]
    file_extension_list.remove(dpg.get_item_user_data(sender))
    save_settings("Settings", "file_extensions", file_extension_list)
    dpg.set_value(
        "save_finder_text",
        f"Directories containing {file_extension_list} files will be listed below (click to copy to clipboard).",
    )

    dpg.delete_item("extension_list", children_only=True)
    for index, extension in enumerate(file_extension_list, start=1):
        dpg.add_text(f"{index}: {extension}", parent="extension_list", wrap=0)
    if dpg.get_item_children("extension_list", slot=1) == []:
        dpg.add_text("No file extensions added", parent="extension_list", wrap=0)
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
    file_extension_list: list = settings["file_extensions"]
    if len(extension) > 2:
        file_extension_list.append(extension)
        save_settings("Settings", "file_extensions", file_extension_list)
        dpg.set_value(
            "save_finder_text",
            f"Directories containing {file_extension_list} files will be listed below (click to copy to clipboard).",
        )

        dpg.delete_item("extension_list", children_only=True)
        for index, extension in enumerate(file_extension_list, start=1):
            dpg.add_text(f"{index}: {extension}", parent="extension_list", wrap=0)
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
            dpg.add_text("Extension name", wrap=0)
            dpg.add_input_text(width=-1, tag="add_extension_input")
        dpg.add_text(
            "Select an item to remove:", tag="select_extension_text", show=False, wrap=0
        )
        with dpg.child_window(
            autosize_x=True, auto_resize_y=True, tag="extension_list"
        ):
            for index, extension in enumerate(settings["file_extensions"], start=1):
                dpg.add_text(f"{index}: {extension}", wrap=0)
            if dpg.get_item_children("extension_list", slot=1) == []:
                dpg.add_text("No file extensions added", wrap=0)


def remove_current_folderpath(sender, app_data):
    global settings

    folderpath_list: list = settings["folder_paths"]
    folderpath_list.remove(dpg.get_item_user_data(sender))
    save_settings("Settings", "folder_paths", folderpath_list)

    dpg.delete_item("folderpath_list", children_only=True)
    for index, folderpath in enumerate(folderpath_list, start=1):
        dpg.add_text(f"{index}: {folderpath}", parent="folderpath_list", wrap=0)
    if dpg.get_item_children("folderpath_list", slot=1) == []:
        dpg.add_text("No folder paths added", parent="folderpath_list", wrap=0)
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
    dpg.show_item("add_folderpath_dialog_group")
    dpg.hide_item("folderpath_remove_button")
    dpg.hide_item("folderpath_add_button")


def add_current_folderpath():
    global settings

    folderpath = dpg.get_value("add_folderpath_input")
    folderpath_list: list = settings["folder_paths"]
    if len(folderpath) > 2 and folderpath not in folderpath_list:
        folderpath_list.append(folderpath)
        save_settings("Settings", "folder_paths", folderpath_list)

        dpg.delete_item("folderpath_list", children_only=True)
        for index, folderpath in enumerate(folderpath_list, start=1):
            dpg.add_text(f"{index}: {folderpath}", parent="folderpath_list", wrap=0)
        dpg.hide_item("add_folderpath_group")
        dpg.hide_item("comfirm_add_folderpath")
        dpg.hide_item("add_folderpath_dialog_group")
        dpg.show_item("folderpath_remove_button")
        dpg.show_item("folderpath_add_button")


def open_folderpath_file_dialog():
    global settings

    try:
        main = ct.CTk()
        main.iconbitmap(resource_path("docs/icon.ico"))
        main.withdraw()
        folder_path = filedialog.askdirectory(title="Add folder to search in")
        main.destroy()
    except Exception as e:
        logging.error(f"Exception occurred during folder select: {e}")

    if folder_path:
        folderpath_list: list = settings["folder_paths"]
        true_folderpath = folder_path.replace("/", "\\")
        if true_folderpath not in folderpath_list:
            folderpath_list.append(true_folderpath)
            save_settings("Settings", "folder_paths", folderpath_list)

            dpg.delete_item("folderpath_list", children_only=True)
            for index, folderpath in enumerate(folderpath_list, start=1):
                dpg.add_text(f"{index}: {folderpath}", parent="folderpath_list", wrap=0)
            dpg.hide_item("add_folderpath_group")
            dpg.hide_item("comfirm_add_folderpath")
            dpg.hide_item("add_folderpath_dialog_group")
            dpg.show_item("folderpath_remove_button")
            dpg.show_item("folderpath_add_button")


def open_folder_path_menu():
    global settings

    if dpg.does_item_exist("folderpath_manager_window"):
        dpg.delete_item("folderpath_manager_window")
    window_width = dpg.get_viewport_width() / 1.5
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
        with dpg.group(horizontal=True, show=False, tag="add_folderpath_group"):
            dpg.add_text("Enter folder path", wrap=0)
            dpg.add_input_text(width=-120, tag="add_folderpath_input")
            dpg.add_button(
                label="Comfirm",
                tag="comfirm_add_folderpath",
                show=False,
                callback=add_current_folderpath,
            )
        dpg.add_spacer(height=3)
        with dpg.group(horizontal=True, show=False, tag="add_folderpath_dialog_group"):
            dpg.add_text("Select folder", wrap=0)
            dpg.add_button(label="Browse", callback=open_folderpath_file_dialog)
        dpg.add_spacer(height=3)
        dpg.add_text(
            "Select an item to remove:",
            tag="select_folderpath_text",
            show=False,
            wrap=0,
        )
        with dpg.child_window(
            autosize_x=True, auto_resize_y=True, tag="folderpath_list"
        ):
            for index, folderpath in enumerate(settings["folder_paths"], start=1):
                dpg.add_text(f"{index}: {folderpath}", wrap=0)
            if dpg.get_item_children("folderpath_list", slot=1) == []:
                dpg.add_text("No folder paths added", wrap=0)


def remove_current_ignored_folder(sender, app_data):
    global settings

    ignored_folders_list: list = settings["ignored_folders"]
    ignored_folders_list.remove(dpg.get_item_user_data(sender))
    save_settings("Settings", "ignored_folders", ignored_folders_list)

    dpg.delete_item("ignored_folders_list", children_only=True)
    for index, folderpath in enumerate(ignored_folders_list, start=1):
        dpg.add_text(f"{index}: {folderpath}", parent="ignored_folders_list")
    if dpg.get_item_children("ignored_folders_list", slot=1) == []:
        dpg.add_text("No folders added", parent="ignored_folders_list")
    dpg.hide_item("select_ignored_folders_text")
    dpg.show_item("ignored_folders_remove_button")
    dpg.show_item("ignored_folders_add_button")


def remove_ignored_folders():
    global settings

    dpg.delete_item("ignored_folders_list", children_only=True)
    for index, folderpath in enumerate(settings["ignored_folders"], start=1):
        dpg.add_selectable(
            label=f"{index}: {folderpath}",
            parent="ignored_folders_list",
            callback=remove_current_ignored_folder,
            user_data=folderpath,
        )
    dpg.show_item("select_ignored_folders_text")
    dpg.hide_item("ignored_folders_remove_button")
    dpg.hide_item("ignored_folders_add_button")


def ignored_folders_select_callback(sender, app_data):
    global settings

    if not app_data["file_path_name"] in settings["ignored_folders"]:
        settings["ignored_folders"].append(app_data["file_path_name"])
        save_settings("Settings", "ignored_folders", settings["ignored_folders"])
        load_settings()

        dpg.delete_item("ignored_folders_list", children_only=True)
        ignored_folders_list: list = settings["ignored_folders"]
        for index, folderpath in enumerate(ignored_folders_list, start=1):
            dpg.add_text(
                f"{index}: {folderpath}", parent="ignored_folders_list", wrap=0
            )
    else:
        logging.debug("Trying to add already added folder to ignored folders")


def change_font_size(sender, app_data):
    global font_path

    save_settings("DisplayOptions", "font_size", app_data)
    dpg.delete_item("font_registry", children_only=True)
    custom_font = dpg.add_font(font_path, app_data, parent="font_registry")
    dpg.bind_font(custom_font)


def settings_change_callback(sender, app_data):
    global settings, img_id

    setting = dpg.get_item_user_data(sender)
    if setting == "copy_folder":
        save_settings("Settings", "copy_folder_status", app_data)
    elif setting == "file_size_limit":
        save_settings("Settings", "file_size_limit", app_data)
    elif setting == "show_image":
        save_settings("Settings", "show_image_status", app_data)
        if app_data == False:
            dpg.delete_item(img_id)
        else:
            img_id = dpg.add_image(
                "cute_image", pos=(0, 0), parent="copy_manager_main_window"
            )
            load_settings()
            image_resize_callback()
    elif setting == "remember_window_pos":
        save_settings("Settings", "remember_window_pos", app_data)
    elif setting == "skip_existing_files":
        save_settings("Settings", "skip_existing_files", app_data)
    elif setting == "clear_destination_folder":
        save_settings("Settings", "clear_destination_folder", app_data)
    elif setting == "skip_hidden_files":
        save_settings("Settings", "skip_hidden_files", app_data)
    else:
        dpg.set_value(
            "status_text", "Changing setting failed; user_data incorrect or missing"
        )

    load_settings()


def image_resize_callback():
    global settings, img_id

    image_enabled = settings["show_image_status"]
    if image_enabled == True and img_id != None:
        image_width = dpg.get_viewport_width() / 5.6
        image_height = dpg.get_viewport_width() / 7
        new_x = dpg.get_viewport_width() - image_width - image_width / 20
        new_y = image_width / 20

        dpg.set_item_pos(img_id, (new_x, new_y))
        dpg.configure_item(img_id, width=image_width)
        dpg.configure_item(img_id, height=image_height)


def save_window_positions():
    save_settings("Window", "main_height", dpg.get_viewport_height())
    save_settings("Window", "main_width", dpg.get_viewport_width())
    save_settings("Window", "main_pos", dpg.get_viewport_pos())


def text_click_handler(sender, app_data, user_data):
    pyperclip.copy(user_data)
    dpg.set_value("status_text", f"Copied to clipboard: {user_data}")


def setup_settings_window(font_size):
    global settings, recording_settings

    dpg.add_spacer(height=10, parent="display_settings_child_window")
    with dpg.group(horizontal=True, parent="display_settings_child_window"):
        dpg.add_text("Font size", wrap=0)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text("Sets the size for text and GUI elements", wrap=400)
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
            dpg.add_text("Whether to remember main window position and size", wrap=400)
        dpg.add_checkbox(
            default_value=settings["remember_window_pos"],
            callback=settings_change_callback,
            user_data="remember_window_pos",
        )
    dpg.add_spacer(height=20, parent="display_settings_child_window")
    with dpg.group(horizontal=True, parent="display_settings_child_window"):
        dpg.add_text("Show image", wrap=0)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text("Cute image in Copy Manager :3", wrap=400)
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
            dpg.add_text(
                "If disabled, only files inside the folder will be copied", wrap=400
            )
        dpg.add_checkbox(
            default_value=settings["copy_folder_checkbox_state"],
            callback=settings_change_callback,
            user_data="copy_folder",
        )
    dpg.add_spacer(height=20, parent="copy_manager_settings_child_window")
    with dpg.group(horizontal=True, parent="copy_manager_settings_child_window"):
        dpg.add_text("Folder size limit", wrap=0)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text("Skip folders over set size", wrap=400)
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
            dpg.add_text("Don't override files", wrap=400)
        dpg.add_checkbox(
            default_value=settings["skip_existing_files"],
            callback=settings_change_callback,
            user_data="skip_existing_files",
        )
    dpg.add_spacer(height=20, parent="copy_manager_settings_child_window")
    with dpg.group(horizontal=True, parent="copy_manager_settings_child_window"):
        dpg.add_text(
            "Clear destination",
            wrap=0,
        )
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text("Clear destination folder before copy operation", wrap=400)
        dpg.add_checkbox(
            default_value=settings["clear_destination_folder"],
            callback=settings_change_callback,
            user_data="clear_destination_folder",
        )
    dpg.add_spacer(height=20, parent="copy_manager_settings_child_window")
    with dpg.group(horizontal=True, parent="copy_manager_settings_child_window"):
        dpg.add_text(
            "Skip hidden files",
            wrap=0,
        )
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text("Skip files and folders starting with '.'", wrap=400)
        dpg.add_checkbox(
            default_value=settings["skip_hidden_files"],
            callback=settings_change_callback,
            user_data="skip_hidden_files",
        )
    dpg.add_spacer(height=20, parent="copy_manager_settings_child_window")
    with dpg.tree_node(
        label="Manage ignored folders",
        parent="copy_manager_settings_child_window",
        # span_full_width=True,
    ):
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(
                "Skip these folders when copying (note that this only affects subfolders)",
                wrap=400,
            )
        dpg.add_spacer(height=5)
        with dpg.child_window(
            tag="ignored_folders_manager_window",
            autosize_x=True,
            auto_resize_y=True,
        ):
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Add",
                    callback=lambda: dpg.show_item("ignored_folders_file_dialog"),
                    tag="ignored_folders_add_button",
                )
                dpg.add_button(
                    label="Remove",
                    callback=remove_ignored_folders,
                    tag="ignored_folders_remove_button",
                )
            dpg.add_text(
                "Select an item to remove:",
                tag="select_ignored_folders_text",
                show=False,
                wrap=0,
            )
            dpg.add_spacer(height=5)
            with dpg.child_window(
                autosize_x=True, auto_resize_y=True, tag="ignored_folders_list"
            ):
                for index, folderpath in enumerate(
                    settings["ignored_folders"], start=1
                ):
                    dpg.add_text(f"{index}: {folderpath}", wrap=0)
                if dpg.get_item_children("ignored_folders_list", slot=1) == []:
                    dpg.add_text("No folders added", wrap=0)

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

    with dpg.file_dialog(
        directory_selector=True,
        show=False,
        callback=screenshot_folder_select_callback,
        default_path=recording_settings["screenshot_folder"],
        tag="screenshot_file_dialog",
        cancel_callback=recording_cancel_callback,
        width=dpg.get_viewport_width() / 1.5,
        height=dpg.get_viewport_height() / 1.5,
        label="Select screenshot folder",
    ):
        pass
    if not os.path.exists(recording_settings["screenshot_folder"]):
        screenshot_folder = os.path.join(os.path.expanduser("~"), "Documents")
        dpg.configure_item("screenshot_file_dialog", default_path=screenshot_folder)
        save_settings("Recording", "screenshot_folder", screenshot_folder)

    with dpg.file_dialog(
        directory_selector=True,
        show=False,
        callback=video_folder_select_callback,
        default_path=recording_settings["video_folder"],
        tag="video_file_dialog",
        cancel_callback=recording_cancel_callback,
        width=dpg.get_viewport_width() / 1.5,
        height=dpg.get_viewport_height() / 1.5,
        label="Select video folder",
    ):
        pass
    if not os.path.exists(recording_settings["video_folder"]):
        video_folder = os.path.join(os.path.expanduser("~"), "Documents")
        dpg.configure_item("video_file_dialog", default_path=video_folder)
        save_settings("Recording", "video_folder", video_folder)

    with dpg.file_dialog(
        directory_selector=True,
        show=False,
        callback=ignored_folders_select_callback,
        tag="ignored_folders_file_dialog",
        cancel_callback=None,
        width=dpg.get_viewport_width() / 1.5,
        height=dpg.get_viewport_height() / 1.5,
        modal=True,
        label="Select folder to ignore",
    ):
        pass

    file_extension_list: list = settings["file_extensions"]
    dpg.set_value(
        "save_finder_text",
        f"Directories containing {file_extension_list} files will be listed below (click to copy to clipboard).",
    )


def show_windows():
    global img_id, settings, recording_settings, font_path

    with dpg.font_registry(tag="font_registry"):
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
    logging.debug("Image initialized")

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
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 2, 2)
        with dpg.theme_component(dpg.mvProgressBar):
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4, 4)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 2, 2)
            dpg.add_theme_color(dpg.mvThemeCol_Border, (183, 28, 28))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (40, 53, 147))
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, (27, 94, 32))
        with dpg.theme_component(dpg.mvInputInt):
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 20, 2.5)
            dpg.add_theme_color(dpg.mvThemeCol_Border, (191, 54, 12))
        with dpg.theme_component(dpg.mvInputText):
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 20, 6)
        with dpg.theme_component(dpg.mvCheckbox):
            dpg.add_theme_color(dpg.mvThemeCol_Border, (191, 54, 12))
        with dpg.theme_component(dpg.mvCombo):
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 20, 2.5)
            dpg.add_theme_color(dpg.mvThemeCol_Border, (191, 54, 12))
        with dpg.theme_component(dpg.mvCollapsingHeader):
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 5, 5)
            dpg.add_theme_color(dpg.mvThemeCol_Border, (0, 96, 100))
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 2, 2)

    with dpg.theme() as main_window_theme:
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_Border, (21, 101, 192))

    with dpg.theme() as main_recording_window_theme:
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_Border, (21, 101, 192))
        with dpg.theme_component(dpg.mvInputInt):
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 20, 2.5)
        with dpg.theme_component(dpg.mvCombo):
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 20, 2.5)

    with dpg.theme() as main_settings_window_theme:
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_Border, (21, 101, 192))
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 5)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 2, 2)
            dpg.add_theme_color(dpg.mvThemeCol_Border, (191, 54, 12))

    with dpg.theme() as main_window_add_folder_theme:
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (43, 35, 32))

    dpg.bind_font(custom_font)
    logging.debug("Font bound to main window")

    try:
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
                    dpg.add_menu_item(
                        label="Check For Updates", callback=check_for_updates
                    )
                with dpg.menu(label="Debug"):
                    dpg.add_menu_item(
                        label="Show Metrics",
                        callback=lambda: dpg.show_tool(dpg.mvTool_Metrics),
                    )

            with dpg.tab_bar(reorderable=True):
                with dpg.tab(label="Copy Manager"):
                    with dpg.child_window(
                        autosize_x=True,
                        auto_resize_y=True,
                        tag="copy_manager_main_window",
                    ):
                        dpg.add_text("Copy Manager", wrap=0)
                        dpg.add_separator()
                        dpg.add_spacer(height=10)

                        with dpg.collapsing_header(label="Add folder pairs"):
                            with dpg.child_window(
                                autosize_x=True,
                                auto_resize_y=True,
                                tag="copy_manager_add_folder_window",
                            ):
                                dpg.add_spacer(height=5)
                                with dpg.group(horizontal=True):
                                    dpg.add_text("Name:")
                                    dpg.add_input_text(
                                        tag="name_input",
                                        width=400,
                                        hint="write a name for the folder pair",
                                    )
                                dpg.add_spacer(height=10)

                                dpg.add_button(
                                    label="Select Source Directory",
                                    callback=open_source_file_dialog,
                                )
                                dpg.add_text("", tag="source_display", wrap=0)
                                dpg.add_spacer(height=5)

                                dpg.add_button(
                                    label="Select Destination Directory",
                                    callback=open_destination_file_dialog,
                                )
                                dpg.add_text("", tag="destination_display", wrap=0)
                                dpg.add_spacer(height=5)

                                dpg.add_button(
                                    label="Add folder pair", callback=add_entry_callback
                                )
                                dpg.add_spacer(height=5)

                        dpg.add_spacer(height=5)
                        dpg.add_separator()

                        dpg.add_text(
                            "Folder pairs will appear below (copy paths to clipboard by clicking them):",
                            wrap=0,
                        )
                        dpg.add_spacer(height=5)

                        with dpg.child_window(tag="entry_list", auto_resize_y=True):
                            pass

                        dpg.add_spacer(height=5)
                        with dpg.group(horizontal=True):
                            dpg.add_button(
                                label="Clear all pairs", callback=clear_entries_callback
                            )
                            dpg.add_button(
                                label="Clear latest pair", callback=clear_latest_entry
                            )

                        dpg.add_spacer(height=5)
                        dpg.add_separator()
                        dpg.add_spacer(height=10)
                        with dpg.group(horizontal=True):
                            dpg.add_button(
                                label="Run Copy Operation",
                                callback=copy_all_callback,
                                tag="copy_button",
                            )
                            dpg.add_button(
                                label="Cancel Copy Operation",
                                callback=set_cancel_to_true,
                                tag="cancel_button",
                                show=False,
                            )

                        dpg.add_spacer(height=5)
                        dpg.add_text("", tag="status_text", color=(255, 140, 0), wrap=0)

                        dpg.add_spacer(height=5)
                        dpg.add_progress_bar(
                            tag="progress_bar",
                            default_value=0.0,
                            width=-5,
                            height=40,
                            show=False,
                            overlay="0.00 GB / 0.00 GB (0%)",
                        )

                        dpg.add_spacer(height=5)
                        dpg.add_text(
                            "", tag="speed_text", color=(0, 255, 0), show=False, wrap=0
                        )

                        dpg.add_spacer(height=5)
                        with dpg.collapsing_header(label="Log"):
                            with dpg.child_window(
                                autosize_x=True, auto_resize_y=True, border=False
                            ):
                                dpg.add_spacer(height=5)
                                with dpg.group(horizontal=True):
                                    dpg.add_text("Filters:", wrap=0)
                                    dpg.add_button(
                                        label="Error",
                                        callback=set_log_filter,
                                        tag="log_error_filter_button",
                                        user_data=["error", "shown"],
                                    )
                                    dpg.add_button(
                                        label="Skip",
                                        callback=set_log_filter,
                                        tag="log_skip_filter_button",
                                        user_data=["skip", "shown"],
                                    )
                                    dpg.add_button(
                                        label="Ignore",
                                        callback=set_log_filter,
                                        tag="log_ignore_filter_button",
                                        user_data=["ignore", "shown"],
                                    )
                                    dpg.add_button(
                                        label="Copy",
                                        callback=set_log_filter,
                                        tag="log_copy_filter_button",
                                        user_data=["copy", "shown"],
                                    )
                                    dpg.add_button(
                                        label="Delete",
                                        callback=set_log_filter,
                                        tag="log_delete_filter_button",
                                        user_data=["delete", "shown"],
                                    )
                                dpg.add_spacer(height=5)
                            with dpg.child_window(tag="copy_log", auto_resize_y=True):
                                pass
                        dpg.add_spacer(height=10)

                        if settings["show_image_status"] == True:
                            img_id = dpg.add_image(
                                "cute_image",
                                pos=(0, 0),
                                parent="copy_manager_main_window",
                            )

                with dpg.tab(label="File Finder"):
                    with dpg.child_window(
                        autosize_x=True,
                        auto_resize_y=True,
                        tag="save_finder_main_window",
                    ):
                        dpg.add_text("File Finder", wrap=0)
                        dpg.add_separator()
                        dpg.add_spacer(height=10)
                        dpg.add_button(
                            label="Search for files",
                            callback=start_search_thread,
                            tag="file_search_button",
                        )
                        dpg.add_text("", tag="finder_text", show=False, wrap=0)
                        dpg.add_spacer(height=5)
                        dpg.add_progress_bar(
                            tag="finder_progress_bar",
                            default_value=0.0,
                            width=-5,
                            height=30,
                            show=False,
                        )
                        dpg.add_spacer(height=5)
                        dpg.add_separator()
                        dpg.add_spacer(height=5)
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
                        dpg.add_spacer(height=10)

                with dpg.tab(label="Recorder"):
                    with dpg.child_window(
                        autosize_x=True, auto_resize_y=True, tag="recording_main_window"
                    ):
                        dpg.add_text("Recorder", wrap=0)
                        dpg.add_separator()
                        dpg.add_spacer(height=10)
                        with dpg.group(horizontal=True):
                            dpg.add_button(
                                label="Start process",
                                callback=start_key_listener,
                                tag="start_key_listener_button",
                            )
                            with dpg.tooltip(dpg.last_item()):
                                dpg.add_text("Begin taking screenshots", wrap=400)
                            dpg.add_spacer(width=10)
                            dpg.add_text("Set keybind:", wrap=0)
                            screenshot_binding = recording_settings["screenshot_key"]
                            dpg.add_button(
                                label=f"{screenshot_binding}",
                                tag="start_keybind_recording_button",
                                callback=start_keybind_recording,
                            )
                            dpg.add_spacer(width=10)
                            dpg.add_button(
                                label="Change location",
                                callback=lambda: dpg.show_item(
                                    "screenshot_file_dialog"
                                ),
                            )
                            with dpg.tooltip(dpg.last_item()):
                                dpg.add_text("Where to save screenshots", wrap=400)
                        dpg.add_spacer(height=10)
                        dpg.add_separator()
                        dpg.add_spacer(height=10)
                        with dpg.group(horizontal=True):
                            dpg.add_button(
                                label="Record video",
                                callback=start_video_recording_thread,
                                tag="start_video_recording_button",
                            )
                            with dpg.tooltip(dpg.last_item()):
                                dpg.add_text("Start screen recording", wrap=400)
                        dpg.add_spacer(height=10)
                        with dpg.collapsing_header(label="Video settings"):
                            dpg.add_spacer(height=5)
                            with dpg.child_window(
                                autosize_x=True,
                                auto_resize_y=True,
                            ):
                                dpg.add_spacer(height=5)
                                with dpg.group():
                                    with dpg.group(horizontal=True):
                                        dpg.add_combo(
                                            items=[30, 45, 60, 75, 90, 120],
                                            label="FPS",
                                            default_value=recording_settings[
                                                "video_fps"
                                            ],
                                            width=100,
                                            user_data="FPS",
                                            callback=set_video_setting,
                                        )
                                        with dpg.tooltip(dpg.last_item()):
                                            dpg.add_text(
                                                "Record this many frames every second",
                                                wrap=400,
                                            )
                                        dpg.add_spacer(width=10)
                                        dpg.add_button(
                                            label="Change location",
                                            callback=lambda: dpg.show_item(
                                                "video_file_dialog"
                                            ),
                                        )
                                        with dpg.tooltip(dpg.last_item()):
                                            dpg.add_text(
                                                "Where to save screen recordings",
                                                wrap=400,
                                            )
                                    dpg.add_spacer(height=10)
                                    with dpg.group(horizontal=True):
                                        dpg.add_text("Duration:", wrap=0)
                                        dpg.add_input_int(
                                            label="sec",
                                            min_value=5,
                                            max_value=1200,
                                            default_value=recording_settings[
                                                "video_duration"
                                            ],
                                            step=1,
                                            step_fast=1,
                                            width=200,
                                            user_data="duration",
                                            callback=set_video_setting,
                                        )
                                        with dpg.tooltip(dpg.last_item()):
                                            dpg.add_text(
                                                "How long to record (over a few minutes not recommended)",
                                                wrap=400,
                                            )
                                    dpg.add_spacer(height=5)
                                    dpg.add_separator()
                                    dpg.add_spacer(height=5)
                                    with dpg.tree_node(
                                        label="Advanced settings",  # span_full_width=True
                                    ):
                                        dpg.add_spacer(height=5)
                                        with dpg.group(horizontal=True):
                                            dpg.add_text("Codec", wrap=0)
                                            dpg.add_combo(
                                                items=[".avc1"],
                                                default_value=".avc1",
                                                width=150,
                                                callback=None,
                                            )
                                    dpg.add_spacer(height=5)
                        dpg.add_spacer(height=5)
                        dpg.add_text(
                            "",
                            tag="recording_status_text",
                            color=(100, 200, 100),
                            show=False,
                            wrap=0,
                        )
                        dpg.add_spacer(height=10)

                with dpg.tab(label="Settings"):
                    with dpg.child_window(
                        autosize_x=True, auto_resize_y=True, tag="settings_main_window"
                    ):
                        with dpg.group(horizontal=True):
                            dpg.add_text("App settings", wrap=0)
                            dpg.add_spacer(width=10)
                            dpg.add_button(
                                label="Reset to default values", callback=reset_settings
                            )
                            with dpg.tooltip(dpg.last_item()):
                                dpg.add_text("Takes effect after app restart", wrap=400)
                        dpg.add_spacer(height=5)
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
                        dpg.add_spacer(height=10)

        setup_settings_window(font_size)

        dpg.bind_item_theme("Primary Window", child_window_theme)
        dpg.bind_item_theme("copy_manager_main_window", main_window_theme)
        dpg.bind_item_theme("save_finder_main_window", main_window_theme)
        dpg.bind_item_theme("recording_main_window", main_recording_window_theme)
        dpg.bind_item_theme("settings_main_window", main_settings_window_theme)
        dpg.bind_item_theme(
            "copy_manager_add_folder_window", main_window_add_folder_theme
        )

        dpg.bind_item_handler_registry("Primary Window", "window_handler")
        dpg.set_primary_window("Primary Window", True)
        logging.debug("Primary window set and bound to handler")
        image_resize_callback()

    except Exception as e:
        logging.critical(f"Setting up primary window and/or themes failed: {e}")


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

    # Set width and height for the window
    if main_height != None:
        max_width = main_width
        max_height = main_height
    else:
        max_width = int(screen_width / 1.5)
        max_height = int(screen_height / 1.5)

    if launched == False:
        max_width = int(screen_width / 1.5)
        max_height = int(screen_height / 1.5)

    dpg.create_viewport(
        title="Save Manager", width=max_width, height=max_height, vsync=True
    )

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


def main():
    global settings, target_app_frame_rate

    run_application()

    dpg.create_context()
    logging.debug("DPG context created")
    load_settings()

    setup_viewport()
    show_windows()
    load_entries()

    dpg.setup_dearpygui()
    dpg.show_viewport()

    hwnd = win32gui.FindWindow(None, "Save Manager")
    if hwnd == 0:
        logging.error("Window not found for pywinstyles")
    else:
        pywinstyles.apply_style(hwnd, "mica")

    while dpg.is_dearpygui_running():
        start_time = time.time()

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

                    dpg.configure_item(
                        "progress_bar",
                        overlay=f"{copied_gb:.2f} GB / {total_gb:.2f} GB ({int(progress_value*100)}%)",
                    )
                    dpg.set_value("progress_bar", progress_value)

                    current_time = time.time()
                    if current_time - last_update_time >= 0.5:
                        elapsed = current_time - start_time_global
                        if elapsed > 0:
                            speed = copied_bytes / elapsed
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
                dpg.add_text(
                    data,
                    color=(229, 57, 53),
                    wrap=0,
                    parent="copy_log",
                    user_data="error",
                )
                logging.error(f"Error during copy thread: {data}")
                dpg.hide_item("progress_bar")
                dpg.hide_item("speed_text")
            elif item_type == "update":
                dpg.set_value("status_text", data)
            elif item_type == "open_url":
                webbrowser.open(data)

        dpg.render_dearpygui_frame()

        if target_app_frame_rate != -1:
            frame_delay = 1.0 / target_app_frame_rate
            frame_time = time.time() - start_time
            # Maintain the target frame rate
            if frame_time < frame_delay:
                time.sleep(frame_delay - frame_time)

    def cleanup():
        global cancel_flag, settings

        logging.info("Application exited")
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
