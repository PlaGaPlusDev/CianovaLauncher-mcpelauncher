
import customtkinter as ctk
import os
import shutil
import time
import threading
from src.gui.main_window import CianovaLauncherApp
from src.gui.migration_dialog import MigrationDialog

def setup_mock_environment():
    # Create mock source and destination directories
    os.makedirs("mock_src/versions/1.0.0", exist_ok=True)
    os.makedirs("mock_dst", exist_ok=True)
    with open("mock_src/versions/1.0.0/test.txt", "w") as f:
        f.write("test")

def cleanup_mock_environment():
    shutil.rmtree("mock_src")
    shutil.rmtree("mock_dst")

def run_migration_test():
    setup_mock_environment()

    app = CianovaLauncherApp()

    # Create a mock active_path for the destination
    app.active_path = os.path.abspath("mock_dst")

    dialog = MigrationDialog(app)

    # Configure the dialog for the test
    dialog.entry_src.delete(0, "end")
    dialog.entry_src.insert(0, os.path.abspath("mock_src"))
    dialog.check_versions.set(True)

    # Override the messagebox to automatically answer "yes"
    dialog.askyesno = lambda title, message: True

    # Check for the progress dialog
    def check_for_progress():
        time.sleep(1) # Give the dialog time to appear
        found = False
        for widget in app.winfo_children():
            if isinstance(widget, ctk.CTkToplevel) and "Migrando..." in widget.title():
                found = True
                print("SUCCESS: Progress dialog was displayed.")
                widget.destroy()
                break
        if not found:
            print("FAILURE: Progress dialog was not displayed.")
        app.destroy()

    threading.Thread(target=check_for_progress).start()

    dialog.start_migration()
    app.mainloop()

    cleanup_mock_environment()

if __name__ == "__main__":
    run_migration_test()
