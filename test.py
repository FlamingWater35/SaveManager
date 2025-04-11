import os
import dearpygui.dearpygui as dpg

class ModernFileDialog:
    """
    A Windows 11-style file dialog implementation for DearPyGUI.
    
    Features:
    - Navigation breadcrumb bar
    - File/folder navigation
    - Favorites sidebar
    - File filtering
    - Modern styling
    """
    
    def __init__(self, modal=True, directory=None, default_filename="", 
                 callback=None, extensions=None, title="Select File", 
                 file_mode="open", width=800, height=500):
        """
        Initialize the file dialog.
        
        Args:
            modal (bool): Whether the dialog should be modal
            directory (str): Starting directory, defaults to user home
            default_filename (str): Default filename for save dialogs
            callback (callable): Function to call with selected file(s)
            extensions (list): List of allowed file extensions (e.g. [".txt", ".py"])
            title (str): Dialog title
            file_mode (str): "open" or "save"
            width (int): Dialog width
            height (int): Dialog height
        """
        self.modal = modal
        self.directory = directory if directory else os.path.expanduser("~")
        self.default_filename = default_filename
        self.callback = callback
        self.extensions = extensions if extensions else []
        self.title = title
        self.file_mode = file_mode
        self.width = width
        self.height = height
        
        self.current_path = self.directory
        self.selected_files = []
        self.window_id = None
        self.history = [self.directory]
        self.history_index = 0
        
        # Quick access locations
        self.favorites = [
            {"name": "Desktop", "path": os.path.join(os.path.expanduser("~"), "Desktop")},
            {"name": "Documents", "path": os.path.join(os.path.expanduser("~"), "Documents")},
            {"name": "Downloads", "path": os.path.join(os.path.expanduser("~"), "Downloads")},
            {"name": "Pictures", "path": os.path.join(os.path.expanduser("~"), "Pictures")},
            {"name": "Music", "path": os.path.join(os.path.expanduser("~"), "Music")},
            {"name": "Videos", "path": os.path.join(os.path.expanduser("~"), "Videos")},
        ]
        
        # UI component IDs
        self.breadcrumb_id = None
        self.file_list_id = None
        self.filename_input_id = None
        self.filetype_combo_id = None
        self.status_text_id = None
        
        # Setup styling
        self._setup_style()
        
    def _setup_style(self):
        """Set up Windows 11-like styling for the dialog"""
        # Use theme if not already registered
        if not dpg.does_item_exist("file_dialog_theme"):
            with dpg.theme(tag="file_dialog_theme"):
                with dpg.theme_component(dpg.mvAll):
                    # Light theme colors inspired by Windows 11
                    dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (243, 243, 243, 255))
                    dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (0, 120, 212, 255))
                    dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (0, 120, 212, 255))
                    dpg.add_theme_color(dpg.mvThemeCol_Button, (240, 240, 240, 255))
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (229, 241, 251, 255))
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (204, 228, 247, 255))
                    dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (255, 255, 255, 255))
                    dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (229, 241, 251, 255))
                    dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (204, 228, 247, 255))
                    dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, (243, 243, 243, 255))
                    dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, (200, 200, 200, 255))
                    dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, (180, 180, 180, 255))
                    dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, (160, 160, 160, 255))
                    dpg.add_theme_color(dpg.mvThemeCol_Header, (0, 120, 212, 100))
                    dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (0, 120, 212, 150))
                    dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (0, 120, 212, 200))
                    
                    # Rounded elements
                    dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4.0)
                    dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 8.0)
                    dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 4.0)
                    dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 6, 6)
                    dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 6)
                    
        # Register font if needed (optional, you can modify this)
        if False and not dpg.does_item_exist("segoe_ui_font"):
            with dpg.font_registry():
                # You would need Segoe UI font file
                dpg.add_font("path/to/segoe-ui.ttf", 16, tag="segoe_ui_font")
    
    def _get_file_icon(self, path):
        """
        Returns an icon identifier based on file type.
        In a real implementation, you could return actual icons.
        """
        if os.path.isdir(path):
            return "📁"  # Folder
        
        _, ext = os.path.splitext(path)
        ext = ext.lower()
        
        if ext in ['.txt', '.md', '.log', '.csv']:
            return "📄"  # Document
        elif ext in ['.py', '.js', '.html', '.css', '.cpp', '.h', '.java']:
            return "🧩"  # Code
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
            return "🖼️"  # Image
        elif ext in ['.mp3', '.wav', '.flac', '.ogg', '.m4a']:
            return "🎵"  # Audio
        elif ext in ['.mp4', '.mov', '.avi', '.mkv', '.wmv']:
            return "🎬"  # Video
        elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
            return "📦"  # Archive
        elif ext in ['.exe', '.bat', '.msi', '.dll', '.so']:
            return "⚙️"  # Executable
        else:
            return "📎"  # Generic file
    
    def _get_file_size_str(self, file_path):
        """Convert file size to human-readable format"""
        if os.path.isdir(file_path):
            return "Folder"
        
        try:
            size = os.path.getsize(file_path)
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size < 1024.0:
                    return f"{size:.2f} {unit}" if unit != 'B' else f"{size} {unit}"
                size /= 1024.0
            return f"{size:.2f} PB"
        except:
            return "Unknown"
    
    def _get_file_date(self, file_path):
        """Get file modification date"""
        try:
            mtime = os.path.getmtime(file_path)
            return str(mtime)  # In a real app, format this properly
        except:
            return ""
    
    def _navigate_to(self, path):
        """Navigate to a directory and update the view"""
        if not os.path.isdir(path):
            return
        
        self.current_path = path
        
        # Update history
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        self.history.append(path)
        self.history_index = len(self.history) - 1
        
        # Update breadcrumb
        self._update_breadcrumb()
        
        # Update file list
        self._update_file_list()
        
        # Update status
        self._update_status()
    
    def _go_back(self):
        """Navigate to previous directory in history"""
        if self.history_index > 0:
            self.history_index -= 1
            self.current_path = self.history[self.history_index]
            self._update_breadcrumb()
            self._update_file_list()
            self._update_status()
    
    def _go_forward(self):
        """Navigate to next directory in history"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.current_path = self.history[self.history_index]
            self._update_breadcrumb()
            self._update_file_list()
            self._update_status()
    
    def _go_up(self):
        """Navigate to parent directory"""
        parent = os.path.dirname(self.current_path)
        if parent != self.current_path:  # Prevent going up from root
            self._navigate_to(parent)
    
    def _file_selected(self, sender, app_data, user_data):
        """Handle file selection in the list"""
        selected_indices = app_data
        
        if not selected_indices:
            self.selected_files = []
            dpg.set_value(self.filename_input_id, "")
        else:
            # Get selected items
            self.selected_files = []
            for idx in selected_indices:
                item = self.file_items[idx]
                path = item["path"]
                
                # If directory, navigate to it on double-click
                if os.path.isdir(path) and dpg.is_item_clicked(self.file_list_id) and dpg.get_mouse_clicks() == 2:
                    self._navigate_to(path)
                    return
                
                # Otherwise, add to selection
                self.selected_files.append(path)
            
            # Update filename input for single selection
            if len(self.selected_files) == 1:
                filename = os.path.basename(self.selected_files[0])
                dpg.set_value(self.filename_input_id, filename)
    
    def _update_breadcrumb(self):
        """Update the breadcrumb navigation bar"""
        # Clear existing breadcrumbs
        if dpg.does_item_exist(self.breadcrumb_id):
            dpg.delete_item(self.breadcrumb_id, children_only=True)
        
        # Windows-style path components
        parts = []
        path = self.current_path
        
        # Split path into components
        while True:
            dirname, basename = os.path.split(path)
            if path == dirname:  # Root directory
                parts.append(path)
                break
            elif basename:
                parts.append(path)
                path = dirname
            else:
                break
        
        # Reverse the parts to get correct order
        parts.reverse()
        
        # Add breadcrumb buttons
        for i, part in enumerate(parts):
            # Add separator except for first item
            if i > 0:
                dpg.add_text(parent=self.breadcrumb_id, default_value=" > ")
            
            # Get the part label (last component of path)
            if i == 0:
                label = part  # Root path (like C:\)
            else:
                label = os.path.basename(part) or part
            
            # Add clickable button
            dpg.add_button(
                parent=self.breadcrumb_id,
                label=label,
                callback=lambda s, a, u: self._navigate_to(u),
                user_data=part,
                width=-1
            )
    
    def _update_file_list(self):
        """Update the file list view"""
        dpg.delete_item(self.file_list_id, children_only=True)
        
        try:
            entries = os.listdir(self.current_path)
            self.file_items = []
            
            # Sort: directories first, then files
            dirs = [e for e in entries if os.path.isdir(os.path.join(self.current_path, e))]
            files = [e for e in entries if not os.path.isdir(os.path.join(self.current_path, e))]
            
            dirs.sort()
            files.sort()
            
            # Filter files by extension if needed
            if self.extensions:
                files = [f for f in files if any(f.lower().endswith(ext.lower()) for ext in self.extensions)]
            
            # Combine lists: directories first, then files
            all_entries = dirs + files
            
            # Add entries to the list
            for entry in all_entries:
                path = os.path.join(self.current_path, entry)
                
                try:
                    icon = self._get_file_icon(path)
                    size = self._get_file_size_str(path)
                    date = self._get_file_date(path)
                    
                    # Store for later reference (to map selected index to file)
                    self.file_items.append({
                        "name": entry,
                        "path": path,
                        "is_dir": os.path.isdir(path)
                    })
                    
                    # Add to the table
                    with dpg.table_row(parent=self.file_list_id):
                        dpg.add_text(default_value=icon)
                        dpg.add_text(default_value=entry)
                        dpg.add_text(default_value=size)
                        dpg.add_text(default_value=date)
                except Exception as e:
                    print(f"Error processing {entry}: {str(e)}")
        except Exception as e:
            print(f"Error listing directory {self.current_path}: {str(e)}")
            # Add error message to the list
            with dpg.table_row(parent=self.file_list_id):
                dpg.add_text(default_value="⚠️")
                dpg.add_text(default_value=f"Error accessing directory: {str(e)}")
                dpg.add_text(default_value="")
                dpg.add_text(default_value="")
    
    def _update_status(self):
        """Update status bar"""
        num_items = len(self.file_items) if hasattr(self, 'file_items') else 0
        dpg.set_value(self.status_text_id, f"{num_items} items | {self.current_path}")
    
    def _handle_confirm(self):
        """Handle the OK/Open/Save button click"""
        if self.file_mode == "save":
            # For save dialog, use the filename from input
            filename = dpg.get_value(self.filename_input_id)
            if not filename:
                return
            
            selected_path = os.path.join(self.current_path, filename)
            result = selected_path
        else:
            # For open dialog, use selected file(s)
            if not self.selected_files:
                return
            result = self.selected_files[0]  # Single selection for now
        
        # Close dialog
        dpg.delete_item(self.window_id)
        
        # Call callback with result
        if self.callback:
            self.callback(result)
    
    def _handle_cancel(self):
        """Handle the Cancel button click"""
        dpg.delete_item(self.window_id)
        
        # Call callback with None
        if self.callback:
            self.callback(None)
    
    def show(self):
        """Show the file dialog"""
        # Main window
        self.window_id = dpg.generate_uuid()
        
        with dpg.window(
            label=self.title,
            width=self.width,
            height=self.height,
            modal=self.modal,
            tag=self.window_id,
            on_close=self._handle_cancel
        ):
            # Apply Windows 11 theme
            dpg.bind_item_theme(self.window_id, "file_dialog_theme")
            
            # Top toolbar
            with dpg.group(horizontal=True):
                dpg.add_button(label="◀", callback=self._go_back, width=30)
                dpg.add_button(label="▶", callback=self._go_forward, width=30)
                dpg.add_button(label="▲", callback=self._go_up, width=30)
                
                # Breadcrumb navigation
                with dpg.group(horizontal=True):
                    self.breadcrumb_id = dpg.generate_uuid()
                    dpg.add_group(tag=self.breadcrumb_id, horizontal=True)
            
            dpg.add_separator()
            
            # Main content - split view
            with dpg.group(horizontal=True):
                # Left sidebar - Favorites/Quick access
                with dpg.child_window(width=180, height=-60):
                    dpg.add_text("Quick Access", color=(0, 120, 212, 255))
                    dpg.add_separator()
                    
                    # Add favorite locations
                    for fav in self.favorites:
                        dpg.add_button(
                            label=fav["name"],
                            callback=lambda s, a, u: self._navigate_to(u),
                            user_data=fav["path"],
                            width=-1
                        )
                
                # Right side - File list
                with dpg.child_window(width=-1, height=-60):
                    # File list table
                    self.file_list_id = dpg.generate_uuid()
                    with dpg.table(
                        tag=self.file_list_id,
                        header_row=True,
                        borders_innerH=True,
                        borders_outerH=True,
                        borders_innerV=True,
                        borders_outerV=True,
                        scrollY=True,
                        policy=dpg.mvTable_SizingStretchProp,
                        height=-1,
                        callback=self._file_selected
                    ):
                        dpg.add_table_column(label="", width_fixed=True, width=30)
                        dpg.add_table_column(label="Name", width_stretch=True, init_width_or_weight=3.0)
                        dpg.add_table_column(label="Size", width_fixed=True, width=100)
                        dpg.add_table_column(label="Date Modified", width_fixed=True, width=150)
            
            # Bottom bar - filename and buttons
            with dpg.group():
                # Filename row
                with dpg.group(horizontal=True):
                    dpg.add_text("File name:", width=80)
                    self.filename_input_id = dpg.generate_uuid()
                    dpg.add_input_text(
                        tag=self.filename_input_id,
                        default_value=self.default_filename,
                        width=-120
                    )
                
                # File type filter row
                with dpg.group(horizontal=True):
                    dpg.add_text("File type:", width=80)
                    self.filetype_combo_id = dpg.generate_uuid()
                    
                    # Create filter options
                    if self.extensions:
                        items = [f"{', '.join(self.extensions)} files"]
                    else:
                        items = ["All files"]
                    
                    dpg.add_combo(
                        tag=self.filetype_combo_id,
                        items=items,
                        default_value=items[0],
                        width=-120
                    )
                
                dpg.add_separator()
                
                # Status bar and buttons
                with dpg.group(horizontal=True):
                    # Status text
                    self.status_text_id = dpg.generate_uuid()
                    dpg.add_text(tag=self.status_text_id, default_value="")
                    
                    # Spacer
                    dpg.add_spacer(width=-1)
                    
                    # Action buttons
                    button_text = "Save" if self.file_mode == "save" else "Open"
                    dpg.add_button(label="Cancel", width=100, callback=self._handle_cancel)
                    dpg.add_button(
                        label=button_text,
                        width=100,
                        callback=self._handle_confirm
                    )
            
            # Initial update
            self._navigate_to(self.current_path)


# Example usage
if __name__ == "__main__":
    dpg.create_context()
    
    def file_callback(file_path):
        if file_path:
            print(f"Selected file: {file_path}")
        else:
            print("File selection canceled")
    
    def open_file_dialog():
        # Create and show the dialog
        dialog = ModernFileDialog(
            title="Open File",
            callback=file_callback, 
            extensions=[".py", ".txt"],
            file_mode="open"
        )
        dialog.show()
    
    def save_file_dialog():
        # Create and show the dialog
        dialog = ModernFileDialog(
            title="Save File", 
            callback=file_callback,
            extensions=[".py", ".txt"], 
            default_filename="untitled.txt",
            file_mode="save"
        )
        dialog.show()
    
    with dpg.window(label="File Dialog Demo", width=400, height=200):
        dpg.add_button(label="Open File", callback=open_file_dialog)
        dpg.add_button(label="Save File", callback=save_file_dialog)
    
    dpg.create_viewport(title="Modern File Dialog Demo", width=800, height=600)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()