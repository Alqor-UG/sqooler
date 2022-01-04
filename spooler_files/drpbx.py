"""
The module that contains all the necessary logic for the accessing the database.
"""

import sys
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError

# Add OAuth2 access token here.
# You can generate one for yourself in the App Console.
# See <https://blogs.dropbox.com/developers/2014/05/generate-an-access-token-for-your-own-account/>
APP_KEY = "gxmbubpg0njwyyt"
REFRESH_TOKEN = "guXvMqII2RkAAAAAAAAAAY8ROSd76uMMQB0iE7Vn73NGm2JRirK3CN0PWQK5Ag_6"

# Uploads contents of dump_str to Dropbox
def upload(dump_str, dbx_path):
    """
    Upload the file identified to the dropbox.
    """
    # Create an instance of a Dropbox class, which can make requests to the API.
    with dropbox.Dropbox(oauth2_refresh_token=REFRESH_TOKEN, app_key=APP_KEY) as dbx:
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
    with dropbox.Dropbox(oauth2_refresh_token=REFRESH_TOKEN, app_key=APP_KEY) as dbx:
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
    with dropbox.Dropbox(oauth2_refresh_token=REFRESH_TOKEN, app_key=APP_KEY) as dbx:
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
