import sys
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError

# Add OAuth2 access token here.
# You can generate one for yourself in the App Console.
# See <https://blogs.dropbox.com/developers/2014/05/generate-an-access-token-for-your-own-account/>
APP_KEY = "gxmbubpg0njwyyt"
refresh_token = "guXvMqII2RkAAAAAAAAAAY8ROSd76uMMQB0iE7Vn73NGm2JRirK3CN0PWQK5Ag_6"

# Uploads contents of DUMPSTRING to Dropbox
def upload(DUMPSTRING, DROPBOXPATH):
    # Create an instance of a Dropbox class, which can make requests to the API.
    with dropbox.Dropbox(oauth2_refresh_token=refresh_token, app_key=APP_KEY) as dbx:
        # Check that the access token is valid
        try:
            dbx.users_get_current_account()
        except AuthError:
            sys.exit("ERROR: Invalid access token.")
        try:
            dbx.files_upload(DUMPSTRING, DROPBOXPATH, mode=WriteMode("overwrite"))
        except ApiError as err:
            print(err)
            sys.exit()


def get_file_content(DROPBOXPATH):
    # Create an instance of a Dropbox class, which can make requests to the API.
    with dropbox.Dropbox(oauth2_refresh_token=refresh_token, app_key=APP_KEY) as dbx:
        # Check that the access token is valid
        try:
            dbx.users_get_current_account()
        except AuthError:
            sys.exit("ERROR: Invalid access token.")
        try:
            md, res = dbx.files_download(path=DROPBOXPATH)
            data = res.content
            # print(data)
        except Exception as err:
            print(err)
            sys.exit()
    return data


def move_file(STARTPATH, FINALPATH):
    # Create an instance of a Dropbox class, which can make requests to the API.
    with dropbox.Dropbox(oauth2_refresh_token=refresh_token, app_key=APP_KEY) as dbx:
        # Check that the access token is valid
        try:
            dbx.users_get_current_account()
        except AuthError:
            sys.exit("ERROR: Invalid access token.")
        try:
            resp = dbx.files_move_v2(STARTPATH, FINALPATH)
            # print(resp)
        except ApiError as err:
            print(err)
            sys.exit()
