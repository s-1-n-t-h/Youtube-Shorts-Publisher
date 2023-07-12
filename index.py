import os
import random
import io
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/youtube.upload']

def main():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    drive_service = build('drive', 'v3', credentials=creds)
    youtube_service = build('youtube', 'v3', credentials=creds)

    # Call the Drive v3 API to get the files in the specific folder
    results = drive_service.files().list(
        q="'1HipkuXKkbtGnogtQxiP_c30F83mv6FCt' in parents",  # replace 'folder_id' with your folder's ID
        fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))

        # Select a random file
        file = random.choice(items)

        # Download the selected file
        request = drive_service.files().get_media(fileId=file['id'])
        fh = io.FileIO(file['name'], 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print("Download %d%%." % int(status.progress() * 100))

        # Upload the file to YouTube
        body=dict(
            snippet=dict(
                title="Test video",
                description="Test video upload",
                tags=["test", "video", "upload"],
                categoryId="22"  # You can change this to match your video's category
            ),
            status=dict(
                privacyStatus="public"  # You can change this to make the video public or unlisted
            )
        )

        # Call the API's videos.insert method to upload the video.
        insert_request = youtube_service.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=MediaFileUpload(file['name'], chunksize=-1, resumable=True)
        )

        response = None
        while response is None:
            status, response = insert_request.next_chunk()
            if status:
                print("Uploaded %d%%." % int(status.progress() * 100))

        print("Upload Complete!")

        # Delete the selected file from Drive
        try:
            drive_service.files().update(fileId=file['id'], body={'trashed': True}).execute()
            print(f"File {file['name']} has been deleted.")
        except HttpError as error:
            print(f'An error occurred: {error}')

if __name__ == '__main__':
    main()
