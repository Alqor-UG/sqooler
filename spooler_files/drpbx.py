"""
The module that contains all the necessary logic for the accessing the database.
"""

import sys
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError

from decouple import config

# Add OAuth2 access token here.
# You can generate one for yourself in the App Console.
# See <https://blogs.dropbox.com/developers/2014/05/generate-an-access-token-for-your-own-account/>
APP_KEY = config("APP_KEY")
REFRESH_TOKEN = config("REFRESH_TOKEN")
APP_SECRET = config("APP_SECRET")

# Uploads contents of dump_str to Dropbox
def upload(dump_str, dbx_path):
    """
    Upload the file identified to the dropbox.
    """
    # Create an instance of a Dropbox class, which can make requests to the API.
    with dropbox.Dropbox(
        app_key=APP_KEY,
        app_secret=APP_SECRET,
        oauth2_refresh_token=REFRESH_TOKEN,
    ) as dbx:
        # Check that the access token is valid
        try:
            dbx.users_get_current_account()
        except AuthError:
            sys.exit("ERROR: Invalid access token.")
        try:
            dbx.files_upload(dump_str, dbx_path, mode=WriteMode("overwrite"))
        except ApiError as err:
            print(err)
            sys.exit()


def get_file_content(dbx_path):
    """
    Get the file content from the dropbox.
    """
    # Create an instance of a Dropbox class, which can make requests to the API.
    with dropbox.Dropbox(
        app_key=APP_KEY,
        app_secret=APP_SECRET,
        oauth2_refresh_token=REFRESH_TOKEN,
    ) as dbx:
        # Check that the access token is valid
        try:
            dbx.users_get_current_account()
        except AuthError:
            sys.exit("ERROR: Invalid access token.")
        try:
            _, res = dbx.files_download(path=dbx_path)
            data = res.content
            # print(data)
        except ApiError as err:
            print(err)
            sys.exit()
    return data


def move_file(start_path, final_path):
    """
    Move the file from start_path to final_path.
    """
    # Create an instance of a Dropbox class, which can make requests to the API.
    with dropbox.Dropbox(
        app_key=APP_KEY,
        app_secret=APP_SECRET,
        oauth2_refresh_token=REFRESH_TOKEN,
    ) as dbx:
        # Check that the access token is valid
        try:
            dbx.users_get_current_account()
        except AuthError:
            sys.exit("ERROR: Invalid access token.")
        try:
            _ = dbx.files_move_v2(start_path, final_path)
            # print(_)
        except ApiError as err:
            print(err)
            sys.exit()
