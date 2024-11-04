import os
import configparser
import logging
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.client.Extension import Extension
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.RunScriptAction import RunScriptAction

logger = logging.getLogger(__name__)

class DemoExtension(Extension):

    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())

class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):
        query = event.get_argument() or ""

        if not query:
            return RenderResultListAction([
                ExtensionResultItem(icon='images/icon.png',
                                    name='Enter an application name to view or launch it',
                                    description='For example: firefox or nemo',
                                    on_enter=None)
            ])

        # Extract the application name from the query
        app_name = query.strip()
        if not app_name:
            return RenderResultListAction([
                ExtensionResultItem(icon='images/icon.png',
                                    name='No application name provided',
                                    description='Please enter an application name',
                                    on_enter=None)
            ])

        # Define directories to search for .desktop files
        desktop_files_dirs = [
            "/usr/share/applications",
            os.path.expanduser("~/.local/share/applications"),
            "/var/lib/flatpak/exports/share/applications"
        ]
        
        # Find all matching desktop files for the given application name
        desktop_files = self.find_desktop_files(app_name, desktop_files_dirs)

        if not desktop_files:
            return RenderResultListAction([
                ExtensionResultItem(icon='images/icon.png',
                                    name=f'No .desktop file found for {app_name}',
                                    description='Please check the application name and try again',
                                    on_enter=None)
            ])

        # Create items for each matching desktop file
        items = []
        for desktop_file in desktop_files:
            # Get the desktop file information (Name, Exec, Icon, Actions)
            desktop_data = self.parse_desktop_file(desktop_file)

            if not desktop_data:
                continue

            # If there are no specific desktop actions, just add the main app launch
            desktop_actions = desktop_data.get('actions', {})
            if not desktop_actions:
                items.append(ExtensionResultItem(
                    icon=self.find_icon(desktop_data["Icon"]),
                    name=f'Launch {desktop_data["Name"]}',
                    description=f'Exec: {desktop_data["Exec"]}',
                    on_enter=RunScriptAction(desktop_data["Exec"], None)
                ))
            else:
                # Prepare items to display the desktop actions if present
                for action_name, action_details in desktop_actions.items():
                    items.append(ExtensionResultItem(
                        icon=self.find_icon(desktop_data["Icon"]),
                        name=action_name,
                        description=f"Exec: {action_details['Exec']}",
                        on_enter=RunScriptAction(action_details['Exec'], None)
                    ))

        return RenderResultListAction(items)

    def find_desktop_files(self, app_name, directories):
        """ Find all matching desktop files for the given app name """
        matching_files = []
        for directory in directories:
            if os.path.isdir(directory):
                logger.info(f"Scanning directory: {directory}")
                for file_name in os.listdir(directory):
                    if file_name.endswith(".desktop"):
                        file_path = os.path.join(directory, file_name)
                        desktop_data = self.parse_desktop_file(file_path)
                        if (app_name.lower() in file_name.lower() or 
                            app_name.lower() in desktop_data.get('Name', '').lower() or
                            app_name.lower() in desktop_data.get('Exec', '').lower()):
                            matching_files.append(file_path)
        return matching_files
    
    def parse_desktop_file(self, file_path):
        """ Parse the .desktop file and extract the relevant fields """
        config = configparser.ConfigParser(interpolation=None)
        try:
            config.read(file_path)
            logger.info(f"Parsing desktop file: {file_path}")
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return {}

        # Extract basic desktop file fields
        desktop_data = {
            'Name': config['Desktop Entry'].get('Name', ''),
            'Exec': config['Desktop Entry'].get('Exec', '').split(" ")[0],  # Keep the main executable command
            'Icon': config['Desktop Entry'].get('Icon', 'images/icon.png'),  # Default to a generic icon if not present
            'actions': {}
        }
        
        # Extract desktop actions if present
        for section in config.sections():
            if section.startswith("Desktop Action"):
                action_name = section.split()[-1]
                desktop_data['actions'][action_name] = {
                    'Name': config[section].get('Name', ''),
                    'Exec': config[section].get('Exec', '')
                }
        return desktop_data

    def find_icon(self, icon_name):
        """ Locate the icon file from various directories or return a default icon """
        icon_dirs = [
            "/usr/share/icons/hicolor/",  # Common system icon directory
            os.path.expanduser("~/.local/share/icons/"),  # User icon directory
            "/usr/share/pixmaps/"  # Fallback system directory
        ]

        for icon_dir in icon_dirs:
            icon_path = os.path.join(icon_dir, f"{icon_name}.png")
            if os.path.isfile(icon_path):
                return icon_path
        
        # Fallback to the default icon
        return "images/icon.png"

if __name__ == '__main__':
    DemoExtension().run()
